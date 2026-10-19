# PostgreSQL → SQLite 迁移难度评估

> 评估对象：EasyInvoiceMgr（Flask + Flask-SQLAlchemy + PostgreSQL 15）
> 评估方式：静态代码通读 + 关键行为在本机 SQLite 3.53.2 / SQLAlchemy 2.0.51 上实测验证
> 结论先说：**难度中等偏低，单人 3–4 个工作日可完成，但有 3 个必须修的硬坑，其中 1 个不修会直接导致全站写入失败。**

---

## 一、综合结论

| 维度 | 评估 | 说明 |
| --- | --- | --- |
| 代码改动量 | 小 | 约 8 个文件、总计 < 300 行；业务路由（`backend/routes/*.py`，76 个端点）**几乎无需改动** |
| 技术风险 | 中 | 主键自增、时区语义、备份恢复三处是硬点 |
| 数据迁移风险 | 低 | 纯 ORM 无存储过程，10 张业务表，导出-导入即可 |
| 回归测试成本 | 中（占比最大） | 76 个端点 + 10 个页面的写入/时间/金额展示都要过一遍 |
| 运维收益 | 显著 | 去掉 postgres 容器、去 `pg_dump` 依赖、整库单文件可直接拷走 |
| 综合难度 | **★★☆☆☆（2.5/5）** | 不是"能不能"的问题，是"三小时内能不能跑通 + 一天能不能测完" |

**为什么整体不难**：这个项目的数据访问层非常"干净"——全库没有任何手写 SQL 方言依赖（`ILIKE`、`::` 转型、`ON CONFLICT`、`jsonb` 操作符、窗口函数、CTE 一个都没用），全部走 SQLAlchemy ORM / `func.*`，天然可移植。真正绑死 PostgreSQL 的东西集中在三处**外围**：`backend/sql/base.sql`、`pg_dump/psql` 备份链、以及 11 个 `BigInteger` 主键。

---

## 二、现状盘点

| 项目 | 现状 |
| --- | --- |
| 数据库 | PostgreSQL 15（`docker-compose.yml` 中 `postgres:15-alpine`） |
| ORM | Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.0 风格 |
| 模型 | `backend/models.py` 10 个模型 + `backend/utils/operation_log.py` 1 个（OperationLog） |
| 建表方式 | `backend/sql/base.sql`（426 行全量 DDL，PG 专用）+ `db.create_all()` 兜底 |
| Alembic | 基线迁移 `backend/migrations/versions/5cd03e0a4de7_初始基线_v1_0_0_schema.py` 是 **空操作**（`pass`），即 schema 实际由 base.sql 建；另两条迁移是 `create_table` / `add_column`，SQLite 可执行 |
| 数据访问 | 全 ORM；`db.session.execute` 仅 2 处，都是 PG 专用（见 P0-4） |
| 备份 | `pg_dump` / `psql` 子进程（`backend/utils/backup_service.py`、`backend/utils/db_backup.py`） |
| 运行形态 | 单进程 `python app.py`（Flask dev server），进程内有导出线程、备份线程、APScheduler |
| 其他 | 有 PostgreSQL 枚举类型（base.sql 定义，但模型层用 `String` 承载）、`JSONB`（模型层是 `db.JSON`）、`TIMESTAMPTZ` |

---

## 三、必须处理的硬点（按严重度排序）

### P0-1【阻断级】11 个 `BigInteger` 主键在 SQLite 上不自增

SQLite 只有声明为**恰好 `INTEGER`** 的单列主键才会成为 rowid 别名；`BIGINT PRIMARY KEY` 不是。以下为实测（SQLite 3.53.2）：

```
BIGINT PK  -> INSERT FAILED: IntegrityError NOT NULL constraint failed: t_big.a
INTEGER PK -> [(1, 'x')] | rowid: [(1,)]
```

SQLAlchemy 2.0.51 在 SQLite 上把 `BigInteger` 渲染为 `BIGINT`，不会自动降级：

```sql
CREATE TABLE demo (
	id BIGINT NOT NULL,      -- ← 不是 INTEGER，自增失效
	...
	PRIMARY KEY (id)
)
```

实测通过 SQLAlchemy 插入直接抛异常：

```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: demo.id
[SQL: INSERT INTO demo (name, amt, js) VALUES (?, ?, ?)]
```

**影响面：全站写入 100% 失败。** 涉及 11 个主键列：

- `backend/models.py`：`User.user_id:15`、`Event.event_id:37`、`EventMember.id:67`、`Invoice.invoice_id:85`、`Voucher.voucher_id:118`、`InvitationCode.id:143`、`PurchaseRecord.record_id:159`、`SystemConfig.id:201`、`ExportTask.task_id:216`、`BackupRecord.id:241`
- `backend/utils/operation_log.py:12`：`OperationLog.log_id`

**修法（一处统一定义，逐列替换即可）**：

```python
# models.py 顶部
BigIntPK = db.BigInteger().with_variant(db.Integer, 'sqlite')
# 用法：user_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)
```

> 注意：外键列（`event_id`、`uploader_id` 等）**不用改**，只有主键需要。

---

### P0-2【阻断级】时区语义变化 → 6 处 aware/naive 比较会抛 TypeError

现在 `TIMESTAMPTZ` 读出来是 **aware** datetime，代码大量与 `datetime.now(timezone.utc)` 直接比较。SQLite 上 `DATETIME` 读回来是 **naive**，实测：

```
amt in : 1234.56 -> Decimal('1234.56')
ts  in : 2026-05-16 12:00:00+00:00 -> tzinfo None  value 2026-05-16 12:00:00
RAW STORAGE: '2026-05-16 12:00:00.000000'   -- 偏移量被静默丢弃
```

（好消息：同一时刻的 aware 与 naive 写入落盘字符串完全一致，`ORDER BY` / 范围过滤不受影响；坏消息：Python 侧比较会炸。）

**会在运行时报 `TypeError: can't compare offset-naive and offset-aware datetimes` 的位置**：

| 文件:行 | 代码 | 触发场景 |
| --- | --- | --- |
| `backend/routes/auth.py:44` | `if code_obj.expires_at < datetime.now(timezone.utc)` | 邀请码注册 |
| `backend/routes/invitation_codes.py:52` | `is_expired = code.expires_at < datetime.now(timezone.utc)` | 邀请码列表 |
| `backend/routes/invitation_codes.py:212` | `if invitation_code.expires_at < datetime.now(timezone.utc)` | 邀请码校验 |
| `backend/routes/export.py:154` | `if task.expires_at and task.expires_at < datetime.now(timezone.utc)` | 导出任务下载 |
| `backend/utils/export_service.py:669` | `recent_task.expires_at < datetime.now(timezone.utc)` | 复用导出结果 |
| `backend/utils/export_service.py:700` | `ExportTask.expires_at < datetime.now(timezone.utc)`（SQL 侧，不抛异常但语义需确认） | 清理过期导出 |

**修法（推荐，治本且不动路由）**：定义一个 `TypeDecorator`，bind/result 两端统一成 naive UTC：

```python
class UTCDateTime(db.TypeDecorator):
    impl = db.DateTime
    cache_ok = True
    def process_bind_param(self, v, dialect):
        if v is None: return None
        if v.tzinfo is not None: v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v
    def process_result_value(self, v, dialect):
        return v.replace(tzinfo=timezone.utc) if v is not None else None
```

然后把模型里的 `db.DateTime(timezone=True)` 换成 `UTCDateTime()`（全库约 40 处），路由侧**一行不改**。比"逐个把 `datetime.now(timezone.utc)` 改成 `datetime.utcnow()`"安全得多——后者容易漏，且会改变 API 返回的 ISO 字符串（前端可能依赖 `+00:00` 或 `Z`）。

---

### P0-3【阻断级】备份/恢复整条链路是 PostgreSQL 专用的

| 位置 | 现有实现 | SQLite 需要 |
| --- | --- | --- |
| `backend/utils/backup_service.py:433-452` `_dump_database` | `pg_dump --no-owner --no-acl` | `sqlite3.Connection.backup()` 或直接拷贝 .db 文件（WAL 模式下需先 checkpoint） |
| `backend/utils/backup_service.py:454-497` `_restore_database` | `DROP SCHEMA public CASCADE` + `psql -f` | 关闭连接 → 删除/替换 .db 文件 → 重连 |
| `backend/utils/backup_service.py:462-463` | `text('DROP SCHEMA public CASCADE')` / `CREATE SCHEMA public` | 同上（全项目唯一的 2 处裸 SQL） |
| `backend/utils/db_backup.py:44-70` | `pg_dump \| gzip`，找不到时日志提示"请安装 postgresql-client" | 同上 |
| `backend/utils/backup_service.py:54` | `raise RuntimeError('数据库备份失败，请检查 pg_dump 是否可用')` | 改提示语 |

恢复流程要特别小心：现有实现是"清空 schema + 灌 SQL"，这在 SQLite 上要改成**换文件**，而 Flask-SQLAlchemy 的连接池不能还握着旧文件句柄——必须 `db.engine.dispose()` 后再替换。这也是整个迁移里最需要真机验证的一段。

---

### P1-4【重要】并发写入：SQLite 单写者 + 进程内多线程

进程内同时写库的有：`backend/routes/export.py:65` 导出线程、`backend/routes/system.py:356/529/621` 备份/恢复线程、`backend/utils/backup_service.py:397` 备份线程、`backend/utils/backup_service.py:553` APScheduler。SQLite 默认 rollback journal 模式下写锁是全局的，会撞 `database is locked`。

**必须在 `backend/config.py` 加引擎选项**：

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {'check_same_thread': False, 'timeout': 30},
}
```

并在每个连接上开 PRAGMA。注意 `db.engine` 需要 app context 才能取到，建议在 `create_app()` 内 `db.init_app(app)` **之后**注册：

```python
from sqlalchemy import event

def _register_sqlite_pragmas(engine):
    if engine.dialect.name != 'sqlite':
        return
    @event.listens_for(engine, 'connect')
    def _pragma(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute('PRAGMA journal_mode=WAL')
        cur.execute('PRAGMA foreign_keys=ON')
        cur.execute('PRAGMA busy_timeout=30000')
        cur.close()

# create_app() 中：db.init_app(app) 之后
with app.app_context():
    _register_sqlite_pragmas(db.engine)
```

（若担心连接池里已有连接在注册前建立，可改用 `sqlalchemy.engine.Engine` 级的全局 `connect` 监听，再按 `engine.dialect.name` 过滤。）

`foreign_keys=ON` 这条**不是可选项**：SQLite 默认**不**强制外键，而 `base.sql` 里所有 `REFERENCES` 在 PG 上是强制的。不开启就等于静默丢掉全部引用完整性（删用户会留下孤儿发票记录）。

---

### P1-5【重要】`foreign_keys` / `CHECK` 约束的落差

- `base.sql` 里有 `CHECK (total_budget >= 0)`、`CHECK (amount >= 0)` 等 10 余处金额非负约束；`models.py` **没有**对应的 `CheckConstraint`，所以 `db.create_all()` 不会生成它们。迁移后这些校验消失，只剩应用层逻辑兜着。
- 若在意，在模型里补 `__table_args__ = (db.CheckConstraint('amount >= 0'),)`；不在意则记录为已知差异。

---

### P2-6【一般】全新安装会白等 30 秒

`backend/app.py:207-222`：检测不到 `users` 表时进入 `for attempt in range(30): time.sleep(1)`，等 `base.sql` 被 PG 的 initdb 执行完；超时才 `db.create_all()`。SQLite 下没有 initdb 这一步，必然空转 30 秒。应在检测到 `sqlite` 方言时直接 `db.create_all()` + `stamp(head)`。

---

### P2-7【一般】`base.sql` 本身是 PG 专用，且现有版本有 bug

- PG 专用成分：`CREATE TYPE ... AS ENUM` ×5、`JSONB` ×5、`BIGSERIAL` ×12、`TIMESTAMP WITH TIME ZONE` ×约 40、plpgsql `update_timestamp()` 函数 + 9 个触发器。
- **顺带发现的既有缺陷**：`backend/sql/base.sql:364`

  ```sql
  CREATE INDEX idx_purchase_records_status ON purchase_records(status);
  ```

  但 `purchase_records` 表（`base.sql:166-208`）**没有 `status` 列**（模型 `PurchaseRecord` 也没有）。这条语句在 PostgreSQL 上必然 `ERROR: column "status" does not exist`。而官方 postgres 镜像的 `docker-entrypoint-initdb.d` 以 `ON_ERROR_STOP=1` 执行脚本——意味着**新部署时 base.sql 会在这行中断，其后的 9 个 `updated_at` 触发器全部不会被创建**（表本身在此之前已建完，所以问题被掩盖了；SQLAlchemy 的 `onupdate=_utcnow` 恰好补上了这个缺口）。
- 迁移到 SQLite 后 `base.sql` 直接不参与建库，这个隐患自动消失——算是本次迁移的一个附带收益。

---

## 四、"看起来难、实际不用改"的部分（避免过度估算）

| 项 | 结论 | 依据 |
| --- | --- | --- |
| `db.JSON` / `JSONB` | 不用改 | SQLite 存 TEXT，SQLAlchemy 自动序列化；实测 `{'a': [1, 2]}` 往返正常；全库无 JSON 字段查询（无 `json_extract`/`.op()`） |
| `Numeric(12,2)` 金额 | 不用改 | 实测单值 `Decimal('1234.56')`、`func.sum()` 与 `coalesce(sum,0)` **均返回 Decimal**，与 PG 行为一致 |
| `db.Date` | 不用改 | SQLite 存 `DATE` 字符串，SQLAlchemy 解析回 `date` |
| `ilike` 模糊搜索（`backend/routes/auth.py:204-206`） | 不用改 | SQLAlchemy 在 SQLite 编译为 `lower(x) LIKE lower(y)`；中文场景无差异，仅失去索引优势 |
| `.paginate()`、`order_by(...desc())`、`func.coalesce`、子查询 join | 不用改 | `backend/utils/event_stats.py`、`backend/routes/events.py:898-923` 全为标准 SQL |
| 76 个 API 端点 | 不用改 | 无任何方言耦合 |
| Alembic 3 条迁移 | 不用改 | 基线是空操作；`add_column`（`c3d4e5f6a7b8`，带 `server_default`）与 `create_table`（`a1b2c3d4e5f6`）SQLite 均支持；无 `alter_column`，不需要 `render_as_batch` |
| 文件存储 / COS / GLM 解析 / 导出 Excel | 不用改 | 与数据库无关 |

---

## 五、数据迁移方案（历史数据搬迁）

1. 用 PG 连接跑 `SELECT * FROM <table> ORDER BY <pk>`，按 `users → events → event_members → invoices → vouchers → purchase_records → invitation_codes → system_configs → export_tasks → backup_records → operation_logs` 顺序导入 SQLite（满足外键）。
2. 字段处理：
   - 主键**显式带值**插入（保留原 ID，否则前端缓存的 ID 会错位）；
   - `TIMESTAMPTZ` → `astimezone(utc).replace(tzinfo=None)` 后写 naive；
   - `JSONB` → Python dict 直接交给 `db.JSON`；
   - `Numeric` → `Decimal` 原样。
3. 迁移后置 `PRAGMA foreign_key_check`，并逐表比对 `COUNT(*)` 与 `SUM(金额列)`（金额用 `Decimal` 比较，容差 0）。
4. 主键 `AUTOINCREMENT` 起始值：SQLite 的 rowid 会取 `max(rowid)+1`，显式插入高 ID 后自然接续，无需 `sqlite_sequence` 干预（非 `AUTOINCREMENT` 关键字表）。

预估：迁移脚本 150–250 行，加校验 0.5–1 人日。

---

## 六、建议落地顺序

| 阶段 | 内容 | 预估 |
| --- | --- | --- |
| 1. 让程序在 SQLite 上跑起来（P0） | `config.py` 连接串 + 引擎选项 + PRAGMA；`models.py`/`operation_log.py` 的 11 个主键；`UTCDateTime`；`app.py` 启动分支 | 0.5–1 人日 |
| 2. 数据迁移 + 校验（P0） | 一次性脚本 + `foreign_key_check` + 金额/行数比对 | 0.5–1 人日 |
| 3. 备份恢复改造（P0） | `backup_service.py` / `db_backup.py` 改为文件级备份 + `dispose()` 后替换 | 0.5 人日 |
| 4. 部署与文档（P2） | `docker-compose.yml` 去掉 postgres 服务、加 `.sqlite` 数据卷；`Dockerfile` 可去掉 `postgresql-client`；`requirements.txt` 去掉 `psycopg2-binary`；README / `docs/PROJECT_GUIDE.md` / `dev.ps1` 同步 | 0.5 人日 |
| 5. 回归测试 | 76 端点 ×（登录、邀请码、项目 CRUD、发票上传/审核/报销、凭证、购买记录、导出、备份恢复、操作日志） | 1–1.5 人日 |

**合计 3–4 人日（单人串行），其中回归测试占比最大。**

---

## 七、值不值得迁？（决策建议）

**适合迁**，理由：

- 单进程、单机部署（`docker-compose.yml` 3 服务 → 可减到 2 服务），没有水平扩展需求；
- 使用方是单个赛事团队（`docs/PROJECT_GUIDE.md` 描述为项目/发票/报销管理），并发写入量极低，SQLite 的单写者限制不构成瓶颈；
- 运维大幅简化：一个 `.sqlite` 文件 + `uploads/` 就是全部状态，备份即拷贝，不再依赖 `pg_dump`/`postgresql-client`；
- 附带修掉 `base.sql` 的触发器缺失隐患。

**需要接受的代价**：

- 失去 `CHECK` 约束与（默认关闭的）外键强制——要在 PRAGMA 与模型里补回来；
- 失去 `TIMESTAMPTZ` 的真实时区语义，退化为"全员约定 naive UTC"，需要一次全量代码审视；
- 未来的 `ALTER TABLE` 迁移能力倒退，改列必须走 Alembic `render_as_batch=True` 或重建表。

**不建议迁的情况**：如果计划上多实例 / 多租户 / 定时任务密集（APScheduler 多 job 并发写），或数据量预期上万级项目 × 数十万发票，则保留 PostgreSQL 更划算——那就改成"补 base.sql 的 `status` bug + 加 `pg_dump` 健康检查"这种低成本维修，而不是迁移。

---

## 附：实测环境

- SQLite 3.53.2（Python 3.11 `sqlite3`）
- SQLAlchemy 2.0.51
- 验证结论均来自真实执行，非文档推断；验证用探针脚本为临时文件，已清理。
