# EasyInvoiceMgr 数据库迁移到 SQLite 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 EasyInvoiceMgr 的数据库从 PostgreSQL 15 整体切换到 SQLite，并让"备份/恢复"功能既能产出新的 SQLite 备份，也能把旧版 PG 备份包里的数据完整恢复进 SQLite。

**Architecture:** 业务层（76 个 API 端点）零改动，改动集中在三处边界：① ORM 类型层——用 `BigInteger` 方言变体让主键在 SQLite 上成为 rowid 别名、用 `TypeDecorator` 把时间统一成"库内 naive UTC / 读出 aware UTC"；② 引擎层——连接级 PRAGMA（WAL、`foreign_keys=ON`、`busy_timeout`）+ 启动时直接建表不再等 PG initdb；③ 备份层——`pg_dump`/`psql` 子进程替换为 SQLite 在线备份 API 与"换文件"，并新增一个只解析 `COPY` 数据块、不执行任何 DDL 的旧版 dump 导入器。

**Tech Stack:** Python 3.11（生产镜像 `python:3.11-slim`）/ 3.14（本机 `backend/venv`）、Flask 3.1.3、Flask-SQLAlchemy 3.1.1、SQLAlchemy 2.1.4（本机 venv）/ 2.0.x、Flask-Migrate 4.1.0、pytest 8。

**Spec:** `docs/SQLITE_MIGRATION_ASSESSMENT.md`（本计划实现该评估文档第三、五、六节的全部结论）

## Global Constraints

- **每一个 git commit message 必须是中文**（用户硬性要求）。沿用仓库现有 `type(scope): 中文说明` 风格，`type` 用 `feat`/`fix`/`test`/`refactor`/`chore`/`docs`。
- 迁完之后**只支持 SQLite**，不保留 PostgreSQL 兼容分支；PG 专用文件、依赖、子进程调用全部删除。
- 库内所有时间列统一存 **naive UTC**；Python 侧读出必须是 **aware UTC**（`tzinfo` 非 `None`），业务路由一行不改。
- 备份归档结构保持向后兼容：`tar.gz` 内必须是 `db_dump*` + `invoices/` + `avatars/` + `system_config.json`。
- 恢复功能必须同时接受两种归档：新版（内含 `db_dump.sqlite3`）与旧版（内含 `db_dump.sql` 或 `db_dump.sql.gz`，PG dump 文本）。
- 不新增运行时依赖；`pytest` 只进 `backend/requirements-dev.txt`。
- 测试统一在 `backend/` 目录下执行：`.\venv\Scripts\python.exe -m pytest -q`。
- 代码注释、日志、错误提示一律中文，与现有代码风格一致。
- 数据库文件默认落在 `backend/data/easy_invoice_mgr.sqlite`，该目录与 `*.sqlite*` 产物不入库。

## 预定的提交序列（全部中文）

| Task | 提交信息 |
| --- | --- |
| 0 | `chore: 提交密码加密功能改动并忽略 SQLite 数据文件` |
| 1 | `test(backend): 建立 pytest 测试基建与 SQLite 建表冒烟测试` |
| 2 | `fix(backend): 主键改用 SQLite 可自增的 Integer 方言变体` |
| 3 | `fix(backend): 统一时间列的 UTC 存取语义，消除时区比较异常` |
| 4 | `feat(backend): 切换到 SQLite 连接配置并简化启动建表流程` |
| 5 | `feat(backend): 备份恢复改为 SQLite 文件级操作` |
| 6 | `feat(backend): 新增旧版 PostgreSQL 备份数据导入器` |
| 7 | `feat(backend): 恢复备份支持新旧两种归档格式` |
| 8 | `refactor(backend): 清理 PostgreSQL 专用代码与依赖` |
| 9 | `chore: 部署编排与文档同步为 SQLite` |
| 10 | `test(backend): 新增 SQLite 全链路冒烟回归脚本` |
| 11 | （等真实备份文件，验证后单独提交修复） |

---

### Task 0: 固定干净的迁移起点

迁移要改 `backend/models.py`，而工作区里已有未提交的"密码加密"改动。先把它们单独提交，后续每个提交才能只含迁移内容、可单独 revert。

**Files:**
- Modify: `.gitignore`
- Commit（不改内容）: `backend/app.py`、`backend/models.py`、`backend/routes/auth.py`、`backend/sql/base.sql`、`backend/utils/crypto_utils.py`、`backend/utils/operation_log.py`、`frontend/pages/users/index.vue`、`backend/migrations/versions/d4e5f6a7b8c9_add_password_encrypted_column.py`

**Interfaces:**
- Consumes: 无
- Produces: 干净的工作区 + 分支 `feat/sqlite-migration`，后续任务都在其上提交

- [ ] **Step 1: 确认 `rs-backend/` 未被忽略**

Run:
```powershell
git check-ignore -v rs-backend
```
Expected: 无输出（exit code 1）。说明它是未跟踪目录而非被忽略，必须先补 `.gitignore`，否则后续 `git add -A` 会把整个 Rust 工程卷进来。

- [ ] **Step 2: 在 `.gitignore` 末尾追加忽略项**

在 `.gitignore` 文件末尾追加：

```gitignore
# SQLite 数据文件与备份暂存
*.sqlite
*.sqlite3
*.sqlite-wal
*.sqlite-shm
*.db-wal
*.db-shm
backend/data/
backend/exports/

# 独立 Rust 工程（自带 .git，不应进入主仓库）
rs-backend/
```

- [ ] **Step 3: 确认忽略生效**

Run:
```powershell
git check-ignore -v rs-backend; git status --short
```
Expected: `rs-backend` 被 `.gitignore` 命中；`git status --short` 只剩 8 个已知的密码加密相关改动，不再出现 `?? rs-backend/`。

- [ ] **Step 4: 建迁移分支**

Run:
```powershell
git switch -c feat/sqlite-migration
```
Expected: `Switched to a new branch 'feat/sqlite-migration'`

- [ ] **Step 5: 提交密码加密改动**

Run:
```powershell
git add .gitignore backend/app.py backend/models.py backend/routes/auth.py backend/sql/base.sql backend/utils/crypto_utils.py backend/utils/operation_log.py frontend/pages/users/index.vue backend/migrations/versions/d4e5f6a7b8c9_add_password_encrypted_column.py
git commit -m "chore: 提交密码加密功能改动并忽略 SQLite 数据文件"
```

- [ ] **Step 6: 确认工作区干净**

Run:
```powershell
git status --short
```
Expected: 无输出。

---

### Task 1: pytest 基建 + 建表冒烟测试

项目当前没有任何 pytest 测试。先搭最小基建：一个只初始化 `db` 的最小 Flask app fixture（不跑 `app.py` 的完整启动流程，避免 30 秒等待与真实库污染），加一条"模型能在 SQLite 上建出全部表"的绿色测试。

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_sqlite_schema.py`

**Interfaces:**
- Consumes: `models.db`、`models.User` 等全部模型
- Produces:
  - fixture `db_path` -> `str`（临时 SQLite 文件绝对路径）
  - fixture `app` -> 已 `db.create_all()` 的最小 Flask app（已在 app context 内可用）
  - fixture `sqlite_connection` -> 可执行的 `sqlite3.Connection`（直连 `db_path`）

- [ ] **Step 1: 创建 `backend/requirements-dev.txt`**

```
pytest==8.4.2
```

- [ ] **Step 2: 创建 `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -ra
```

- [ ] **Step 3: 创建 `backend/tests/conftest.py`**

```python
"""pytest 公共夹具：构造只带数据库的最小 Flask 应用。"""
import os
import sqlite3
import sys

import pytest
from flask import Flask

# 让 tests 目录能 import backend 根目录下的 models / utils
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 导入一次，确保 operation_logs 表注册进 db.metadata
import models  # noqa: E402,F401
import utils.operation_log  # noqa: E402,F401


@pytest.fixture()
def db_path(tmp_path):
    """临时 SQLite 数据库文件路径。"""
    return str(tmp_path / 'test.sqlite')


@pytest.fixture()
def app(db_path):
    """最小 Flask 应用：只初始化数据库并按模型建表。"""
    from models import db

    flask_app = Flask(__name__)
    flask_app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///' + db_path.replace('\\', '/'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='test-secret',
        JWT_SECRET_KEY='test-jwt-secret',
    )
    db.init_app(flask_app)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()


@pytest.fixture()
def sqlite_connection(db_path, app):
    """绕过 ORM 直连数据库文件，用于断言真实存储格式。"""
    connection = sqlite3.connect(db_path)
    try:
        yield connection
    finally:
        connection.close()
```

- [ ] **Step 4: 创建 `backend/tests/test_sqlite_schema.py`**

```python
"""SQLite 建表冒烟测试：确认全部模型都能在 SQLite 上建出来。"""
from sqlalchemy import inspect

EXPECTED_TABLES = {
    'users', 'events', 'event_members', 'invoices', 'vouchers',
    'purchase_records', 'invitation_codes', 'system_configs',
    'export_tasks', 'backup_records', 'operation_logs',
}


def test_create_all_builds_every_table(app):
    from models import db

    existing = set(inspect(db.engine).get_table_names())
    assert EXPECTED_TABLES.issubset(existing)


def test_primary_keys_are_integer_type(app, sqlite_connection):
    """SQLite 只有 INTEGER 主键才能自增，BIGINT 主键会插入失败。"""
    rows = sqlite_connection.execute("PRAGMA table_info('users')").fetchall()
    primary_keys = [row for row in rows if row[5]]
    assert [row[1] for row in primary_keys] == ['user_id']
    assert primary_keys[0][2].upper() == 'INTEGER'
```

> 注意：`test_primary_keys_are_integer_type` 此时**是红的**（当前是 `BIGINT`）。这是 Task 2 的红灯，先不要改它，也不要为它加 skip。

- [ ] **Step 5: 安装测试依赖**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```
Expected: `Successfully installed pytest-8.4.2`

- [ ] **Step 6: 跑测试确认基线**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_sqlite_schema.py -v
```
Expected:
- `test_create_all_builds_every_table` PASSED
- `test_primary_keys_are_integer_type` FAILED，断言信息为 `assert 'BIGINT' == 'INTEGER'`

- [ ] **Step 7: 提交基础设施**

Run:
```powershell
cd ..
git add backend/requirements-dev.txt backend/pytest.ini backend/tests/conftest.py backend/tests/test_sqlite_schema.py
git commit -m "test(backend): 建立 pytest 测试基建与 SQLite 建表冒烟测试"
```

---

### Task 2: 主键改为 SQLite 可自增的类型

SQLite 里只有声明为**恰好 `INTEGER`** 的单列主键才会成为 rowid 别名并自动赋值；`BIGINT PRIMARY KEY` 插入时主键列不参与赋值，直接撞 `NOT NULL constraint failed`。这一条不修，全站写入 100% 失败。

**Files:**
- Modify: `backend/models.py:4` 之后（新增 `BigIntPK` 常量）
- Modify: `backend/models.py` 的 10 个主键列：`15`(`user_id`)、`39`(`event_id`)、`69`(`id`)、`87`(`invoice_id`)、`120`(`voucher_id`)、`145`(`id`)、`161`(`record_id`)、`203`(`id`)、`218`(`task_id`)、`243`(`id`)
- Modify: `backend/utils/operation_log.py:12`
- Test: `backend/tests/test_sqlite_hardpoints.py`（新建）

**Interfaces:**
- Consumes: `models.db`
- Produces: `models.BigIntPK` —— 一个可复用的 `Variant` 类型实例，PG 上渲染 `BIGINT`、SQLite 上渲染 `INTEGER`

- [ ] **Step 1: 写失败的测试**

创建 `backend/tests/test_sqlite_hardpoints.py`：

```python
"""SQLite 迁移的三个硬点回归测试。"""
from datetime import datetime, timezone


def test_user_primary_key_autoincrements(app):
    """BigInteger 主键在 SQLite 上必须能自增，否则插入直接失败。"""
    from models import db, User

    with app.app_context():
        user = User(username='pk_probe', password_hash='x', real_name='主键探针')
        db.session.add(user)
        db.session.commit()
        assert user.user_id == 1


def test_operation_log_primary_key_autoincrements(app):
    from models import db, User
    from utils.operation_log import OperationLog

    with app.app_context():
        user = User(username='log_probe', password_hash='x', real_name='日志探针')
        db.session.add(user)
        db.session.commit()

        log = OperationLog(
            user_id=user.user_id,
            username=user.username,
            action_type='test',
            action_description='探针',
        )
        db.session.add(log)
        db.session.commit()
        assert log.log_id == 1


def test_datetime_roundtrip_keeps_utc_timezone(app):
    """写 aware UTC，读出来仍应是 aware UTC；当前 SQLite 会退化成 naive。"""
    from models import db, User

    with app.app_context():
        moment = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        user = User(
            username='tz_probe',
            password_hash='x',
            real_name='时区探针',
            created_at=moment,
        )
        db.session.add(user)
        db.session.commit()
        db.session.expire_all()

        loaded = db.session.get(User, user.user_id)
        assert loaded.created_at.tzinfo is not None
        assert loaded.created_at == moment
```

- [ ] **Step 2: 跑测试确认红**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_sqlite_hardpoints.py -v
```
Expected:
- `test_user_primary_key_autoincrements` FAILED，`sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: users.user_id`
- `test_operation_log_primary_key_autoincrements` FAILED，`NOT NULL constraint failed: operation_logs.log_id`
- `test_datetime_roundtrip_keeps_utc_timezone` FAILED，`assert None is not None`

- [ ] **Step 3: 在 `backend/models.py` 定义主键类型常量**

在 `backend/models.py:9`（`_utcnow()` 函数之后）插入：

```python
# SQLite 只有声明为 INTEGER 的单列主键才会成为 rowid 别名并自动赋值；
# BIGINT 主键在 SQLite 上不会自增，插入会因主键列 NOT NULL 而失败。
# 这里做方言变体：PostgreSQL 侧保持 BIGINT，SQLite 侧退化为 INTEGER。
BigIntPK = db.BigInteger().with_variant(db.Integer, 'sqlite')
```

- [ ] **Step 4: 逐个替换 10 个主键列**

把 `backend/models.py` 中这 10 行的 `db.BigInteger` 换成 `BigIntPK`（`primary_key=True, autoincrement=True` 保持不变）：

```python
    user_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)        # 行 15 User
    event_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)       # 行 39 Event
    id = db.Column(BigIntPK, primary_key=True, autoincrement=True)             # 行 69 EventMember
    invoice_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)     # 行 87 Invoice
    voucher_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)     # 行 120 Voucher
    id = db.Column(BigIntPK, primary_key=True, autoincrement=True)             # 行 145 InvitationCode
    record_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)      # 行 161 PurchaseRecord
    id = db.Column(BigIntPK, primary_key=True, autoincrement=True)             # 行 203 SystemConfig
    task_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)        # 行 218 ExportTask
    id = db.Column(BigIntPK, primary_key=True, autoincrement=True)             # 行 243 BackupRecord
```

> 外键列（`event_id = db.Column(db.BigInteger, db.ForeignKey(...))` 等）**不要动**，只有主键需要变体。

- [ ] **Step 5: 替换 `backend/utils/operation_log.py:12`**

```python
    log_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
```
改为（并在文件顶部 `from models import db` 之后补导入）：

```python
from models import db, BigIntPK
...
    log_id = db.Column(BigIntPK, primary_key=True, autoincrement=True)
```

- [ ] **Step 6: 跑测试确认主键两条变绿**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_sqlite_hardpoints.py -v -k "primary_key or integer_type"
```
Expected: `test_user_primary_key_autoincrements`、`test_operation_log_primary_key_autoincrements`、`test_primary_keys_are_integer_type` 三条 PASSED；`test_datetime_roundtrip_keeps_utc_timezone` 仍 FAILED（下一任务处理）。

- [ ] **Step 7: 提交**

Run:
```powershell
cd ..
git add backend/models.py backend/utils/operation_log.py backend/tests/test_sqlite_hardpoints.py
git commit -m "fix(backend): 主键改用 SQLite 可自增的 Integer 方言变体"
```

---

### Task 3: 统一时间列的 UTC 存取语义

SQLite 的 `DATETIME` 读出来是 naive，而且落盘时**时区偏移会被静默丢弃**。业务代码里 6 处 `xxx < datetime.now(timezone.utc)` 会因此抛 `TypeError: can't compare offset-naive and offset-aware datetimes`。用 `TypeDecorator` 在 ORM 层统一语义，路由一行不改。

**Files:**
- Create: `backend/utils/db_types.py`
- Modify: `backend/models.py`（新增 import，替换约 40 处 `db.DateTime(timezone=True)`）
- Modify: `backend/utils/operation_log.py:1-25`
- Test: `backend/tests/test_sqlite_hardpoints.py`

**Interfaces:**
- Consumes: `sqlalchemy.types.TypeDecorator`
- Produces: `utils.db_types.UTCDateTime` —— 无参可实例化的列类型；写库时 aware→naive UTC，读库时 naive→aware UTC

- [ ] **Step 1: 创建 `backend/utils/db_types.py`**

```python
"""SQLite 友好的列类型。

SQLite 的 DATETIME 不保存时区，读回来是 naive datetime，而业务代码大量
直接与 datetime.now(timezone.utc) 比较。这里在 ORM 层把语义统一为
「库内 naive UTC，Python 侧 aware UTC」，避免改动任何业务代码。
"""
from datetime import timezone

from sqlalchemy.types import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator):
    """始终以 naive UTC 落库、以 aware UTC 读出的 DateTime。"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        # 传入 naive 时间时一律视为 UTC（库内既有数据即为此约定）
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
```

- [ ] **Step 2: 跑测试确认时区那条仍红**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_sqlite_hardpoints.py::test_datetime_roundtrip_keeps_utc_timezone -v
```
Expected: FAILED，`assert None is not None`

- [ ] **Step 3: 在 `backend/models.py` 引入 `UTCDateTime`**

在 `backend/models.py` 顶部（`db = SQLAlchemy()` 之后、`_utcnow()` 之前）插入：

```python
from utils.db_types import UTCDateTime
```

- [ ] **Step 4: 全局替换模型里的时间列类型**

把 `backend/models.py` 中所有 `db.DateTime(timezone=True)` 替换为 `UTCDateTime()`。共 40 处，涉及行：`28,29,30,31,43,44,45,46,57,58,73,74,75,102,104,107,108,132,134,135,148,153,187,190,191,209,210,225,230,231,232,233,254,255,256` 以及同一批中其余同类声明的行。

Run（PowerShell 批量替换，执行后再人工核对 diff）：
```powershell
cd backend
(Get-Content models.py -Raw -Encoding UTF8).Replace('db.DateTime(timezone=True)', 'UTCDateTime()') | Set-Content models.py -Encoding UTF8 -NoNewline
Select-String -Path models.py -Pattern 'DateTime\(timezone=True\)' | Measure-Object
```
Expected: `Count : 0`

- [ ] **Step 5: 修正 `backend/utils/operation_log.py` 的时间列**

`backend/utils/operation_log.py:25` 当前用的是本地时间 `datetime.now()`，与全库 UTC 约定不一致，一并修正：

```python
from datetime import datetime, timezone
...
from models import db, BigIntPK
from utils.db_types import UTCDateTime
...
    created_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 6: 跑测试确认时区变绿、全绿**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -v
```
Expected: 全部 PASSED（`test_datetime_roundtrip_keeps_utc_timezone` 现在通过）

- [ ] **Step 7: 提交**

Run:
```powershell
cd ..
git add backend/utils/db_types.py backend/models.py backend/utils/operation_log.py
git commit -m "fix(backend): 统一时间列的 UTC 存取语义，消除时区比较异常"
```

---

### Task 4: 切换连接配置并简化启动建表

**Files:**
- Modify: `backend/config.py`
- Create: `backend/utils/db_engine.py`
- Create: `backend/utils/schema_init.py`
- Modify: `backend/app.py:193-228`
- Test: `backend/tests/test_app_startup.py`（新建）

**Interfaces:**
- Consumes: `models.db`
- Produces:
  - `config.Config.SQLALCHEMY_DATABASE_URI` -> `str`，默认 `sqlite:///<backend>/data/easy_invoice_mgr.sqlite`
  - `config.Config.SQLALCHEMY_ENGINE_OPTIONS` -> `dict`
  - `utils.db_engine.database_file_path(database_uri: str) -> str`
  - `utils.db_engine.register_sqlite_pragmas(engine) -> None`
  - `utils.schema_init.ensure_schema(app) -> None`（幂等：有 alembic_version 就 upgrade，有表无版本就 stamp，空库就 create_all + stamp）

- [ ] **Step 1: 写失败的测试（真实启动一次）**

创建 `backend/tests/test_app_startup.py`：

```python
"""启动流程测试：真实跑一次 create_app()，确认不再等待 PostgreSQL。"""
import os
import sqlite3
import subprocess
import sys
import time

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_create_app_bootstraps_schema_without_waiting(tmp_path):
    db_file = tmp_path / 'boot.sqlite'
    database_url = 'sqlite:///' + str(db_file).replace('\\', '/')

    env = os.environ.copy()
    env.update({
        'DATABASE_URL': database_url,
        'SECRET_KEY': 'boot-secret',
        'JWT_SECRET_KEY': 'boot-jwt-secret',
        'ADMIN_PASSWORD': 'admin',
        'PYTHONPATH': BACKEND_DIR,
    })

    started = time.time()
    completed = subprocess.run(
        [sys.executable, '-c', 'from app import create_app; create_app(); print("BOOT_OK")'],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.time() - started

    assert completed.returncode == 0, completed.stderr[-3000:]
    assert 'BOOT_OK' in completed.stdout
    assert db_file.exists()
    # 旧实现在等 PG initdb，固定空转 30 秒；新实现必须远低于这个值
    assert elapsed < 20, f'启动耗时 {elapsed:.1f}s，疑似仍在等待数据库初始化'

    connection = sqlite3.connect(str(db_file))
    try:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        version = connection.execute('SELECT version_num FROM alembic_version').fetchone()
    finally:
        connection.close()

    assert {'users', 'events', 'operation_logs', 'alembic_version'}.issubset(tables)
    assert version is not None
```

- [ ] **Step 2: 跑测试确认红**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_app_startup.py -v
```
Expected: FAILED。当前 `backend/config.py:24-26` 的默认连接串仍是 `postgresql+psycopg2://...`，子进程会因连不上 PostgreSQL 而报错（`sqlalchemy.exc.OperationalError` 或启动超时）。

- [ ] **Step 3: 重写 `backend/config.py` 的数据库段**

把 `backend/config.py:9-29` 整段（`def _normalize_database_url` 起，到 `JWT_ACCESS_TOKEN_EXPIRES = 3600` 止，**共 21 行全部删除后替换**）改为：

```python
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB_FILE = os.path.join(_BACKEND_DIR, 'data', 'easy_invoice_mgr.sqlite')


def _default_database_url() -> str:
    """默认落在 backend/data 下的单文件 SQLite 库。"""
    os.makedirs(os.path.dirname(_DEFAULT_DB_FILE), exist_ok=True)
    return 'sqlite:///' + _DEFAULT_DB_FILE.replace('\\', '/')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'easy-invoice-mgr-secret-key'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'easy-invoice-mgr-jwt-secret'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _default_database_url()
    # 进程内有多线程写库（导出线程、备份线程、APScheduler），
    # SQLite 需要放开线程检查并给足写锁等待时间
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False, 'timeout': 30},
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_MIGRATE_REPO = os.path.join(_BACKEND_DIR, 'migrations')
    JWT_ACCESS_TOKEN_EXPIRES = 3600
```

> `Config` 里其余行（`STORAGE_BACKEND`、COS、GLM 配置）保持原样。

- [ ] **Step 4: 创建 `backend/utils/db_engine.py`**

```python
"""SQLite 引擎辅助：连接串解析 + 连接级 PRAGMA。"""
import logging
import os

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_SQLITE_PREFIX = 'sqlite:///'


def database_file_path(database_uri: str) -> str:
    """从 SQLAlchemy URI 解析出 SQLite 数据库文件的绝对路径。"""
    if not database_uri.startswith(_SQLITE_PREFIX):
        raise ValueError(f'仅支持 SQLite 数据库，当前连接串为: {database_uri}')
    path = database_uri[len(_SQLITE_PREFIX):]
    if not path or path.startswith(':'):
        raise ValueError(f'无法从连接串解析数据库文件路径: {database_uri}')
    return os.path.abspath(path)


def register_sqlite_pragmas(engine: Engine) -> None:
    """为每个新连接设置 SQLite PRAGMA。

    - journal_mode=WAL：读写不互相阻塞，导出/备份线程不会卡住请求
    - foreign_keys=ON：SQLite 默认不强制外键，不开启等于静默丢掉引用完整性
    - busy_timeout=30000：写锁竞争时最多等待 30 秒而不是立刻抛 database is locked
    - synchronous=NORMAL：WAL 下的安全/性能平衡点
    """
    if engine.dialect.name != 'sqlite':
        logger.warning(f'当前数据库方言为 {engine.dialect.name}，跳过 SQLite PRAGMA 设置')
        return
    if getattr(engine, '_easy_invoice_pragma_ready', False):
        return

    @event.listens_for(engine, 'connect')
    def _apply_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA busy_timeout=30000')
            cursor.execute('PRAGMA synchronous=NORMAL')
        finally:
            cursor.close()

    engine._easy_invoice_pragma_ready = True
    logger.info('SQLite PRAGMA 已注册: WAL / foreign_keys / busy_timeout')
```

- [ ] **Step 5: 创建 `backend/utils/schema_init.py`**

从 `backend/app.py:193-227` 抽出建库逻辑，去掉 30 秒等待：

```python
"""数据库结构初始化：启动与恢复备份后共用。"""
import logging

from sqlalchemy import inspect

logger = logging.getLogger(__name__)


def ensure_schema():
    """幂等地保证数据库结构与当前模型一致。

    - 已有 alembic_version：执行待定迁移
    - 有业务表但无版本表：标记为当前 head
    - 空库（含刚被换文件/刚建出的 SQLite 文件）：按模型建表并标记 head
    """
    from flask_migrate import stamp, upgrade
    from models import db

    existing_tables = set(inspect(db.engine).get_table_names())

    if 'alembic_version' in existing_tables:
        logger.info('检测到 Alembic 版本控制，执行待定迁移...')
        upgrade()
        logger.info('数据库迁移完成')
        return

    if 'users' in existing_tables:
        logger.info('检测到已有数据库结构，标记为当前版本...')
        stamp(revision='head')
        logger.info('已标记数据库版本为当前 head')
        return

    logger.info('未检测到数据库结构，按模型创建全部表...')
    db.create_all()
    stamp(revision='head')
    logger.info('数据库结构创建完成')
```

- [ ] **Step 6: 改写 `backend/app.py:193-228`**

把该段（`with app.app_context():` 到 `_seed_admin_user(app)` 之前的内容）替换为：

```python
    with app.app_context():
        from utils.db_engine import register_sqlite_pragmas
        from utils.schema_init import ensure_schema

        register_sqlite_pragmas(db.engine)
        ensure_schema()

        _seed_admin_user(app)
```

- [ ] **Step 7: 跑启动测试确认绿**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_app_startup.py -v
```
Expected: PASSED（耗时通常在 2–5 秒）

- [ ] **Step 8: 跑全量测试**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q
```
Expected: 全部 PASSED

- [ ] **Step 9: 提交**

Run:
```powershell
cd ..
git add backend/config.py backend/utils/db_engine.py backend/utils/schema_init.py backend/app.py backend/tests/test_app_startup.py
git commit -m "feat(backend): 切换到 SQLite 连接配置并简化启动建表流程"
```

---

### Task 5: 备份恢复改为文件级操作

`pg_dump`/`psql` 在容器里会直接 `FileNotFoundError`。改成：备份用 SQLite 在线备份 API 产出一个一致性快照文件，恢复用"释放连接池 → 清理 WAL 边车 → 换文件"。

**Files:**
- Modify: `backend/utils/backup_service.py:52-54`（错误提示）、`433-452`（`_dump_database`）、`454-497`（`_restore_database`）、`316-334`（`_do_restore` 的 dump 探测）
- Test: `backend/tests/test_backup_service.py`（新建）

**Interfaces:**
- Consumes: `utils.db_engine.database_file_path`
- Produces:
  - `BackupService._dump_database(db_url: str, output_dir: str) -> str | None` —— 产出 `<output_dir>/db_dump.sqlite3`
  - `BackupService._restore_database(db_url: str, dump_path: str, staging_dir: str) -> None`
  - `BackupService._replace_database_file(target_path: str, source_path: str) -> None`

- [ ] **Step 1: 写失败的测试**

创建 `backend/tests/test_backup_service.py`：

```python
"""备份与恢复的文件级行为测试。"""
import os
import sqlite3

import pytest


@pytest.fixture()
def service(app):
    from utils.backup_service import BackupService

    return BackupService(app)


def _insert_user(app, username):
    from models import db, User

    with app.app_context():
        user = User(username=username, password_hash='x', real_name=username)
        db.session.add(user)
        db.session.commit()
        return user.user_id


def _usernames(db_file):
    connection = sqlite3.connect(db_file)
    try:
        return [row[0] for row in connection.execute('SELECT username FROM users ORDER BY user_id')]
    finally:
        connection.close()


def test_dump_database_produces_sqlite_snapshot(app, service, db_path, tmp_path):
    _insert_user(app, 'alice')
    dump_dir = tmp_path / 'dump'
    dump_dir.mkdir()
    dump_path = service._dump_database('sqlite:///' + db_path.replace('\\', '/'), str(dump_dir))

    assert dump_path is not None
    assert os.path.basename(dump_path) == 'db_dump.sqlite3'
    assert _usernames(dump_path) == ['alice']


def test_restore_database_replaces_file(app, service, db_path, tmp_path):
    from models import db

    _insert_user(app, 'alice')
    dump_dir = tmp_path / 'dump'
    dump_dir.mkdir()
    dump_path = service._dump_database('sqlite:///' + db_path.replace('\\', '/'), str(dump_dir))

    _insert_user(app, 'bob')
    assert _usernames(db_path) == ['alice', 'bob']

    staging_dir = tmp_path / 'staging'
    staging_dir.mkdir()
    service._restore_database('sqlite:///' + db_path.replace('\\', '/'), dump_path, str(staging_dir))

    assert _usernames(db_path) == ['alice']
    # 替换后连接池仍然可用
    with app.app_context():
        from models import User
        assert User.query.count() == 1
```

- [ ] **Step 2: 跑测试确认红**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_backup_service.py -v
```
Expected: FAILED —— `_dump_database` 调用 `pg_dump` 返回 `None`，断言 `assert None is not None` 失败（或 `FileNotFoundError: pg_dump`）。

- [ ] **Step 3: 替换 `_dump_database`（`backend/utils/backup_service.py:433-452`）**

```python
    def _dump_database(self, db_url, output_dir):
        """用 SQLite 在线备份 API 产出一致性快照（含 WAL 中未合并的内容）。"""
        import sqlite3

        from utils.db_engine import database_file_path

        source_path = database_file_path(db_url)
        if not os.path.exists(source_path):
            logger.error(f'数据库文件不存在，无法备份: {source_path}')
            return None

        dump_path = os.path.join(output_dir, 'db_dump.sqlite3')
        source = sqlite3.connect(source_path, timeout=30)
        destination = sqlite3.connect(dump_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

        size_mb = os.path.getsize(dump_path) / (1024 * 1024)
        logger.info(f'数据库快照完成: {dump_path} ({size_mb:.2f} MB)')
        return dump_path
```

- [ ] **Step 4: 替换 `_restore_database`（`backend/utils/backup_service.py:454-497`）**

```python
    def _restore_database(self, db_url, dump_path, staging_dir):
        """用备份里的数据库文件整体替换当前数据库。"""
        from utils.db_engine import database_file_path

        if dump_path.endswith('.gz'):
            import gzip

            sql_path = dump_path[:-3]
            with gzip.open(dump_path, 'rb') as source, open(sql_path, 'wb') as target:
                shutil.copyfileobj(source, target)
            dump_path = sql_path

        target_path = database_file_path(db_url)

        if dump_path.endswith(('.sqlite3', '.sqlite', '.db')):
            self._replace_database_file(target_path, dump_path)
            return

        if dump_path.endswith('.sql'):
            self._import_legacy_pg_dump(target_path, dump_path)
            return

        raise RuntimeError(f'无法识别的数据库备份文件: {os.path.basename(dump_path)}')

    def _replace_database_file(self, target_path, source_path):
        """断开连接后整体替换数据库文件。

        WAL/SHM 边车文件必须一起清理，否则旧 WAL 会被应用到新库上。
        """
        import sqlite3

        from models import db

        probe = sqlite3.connect(source_path)
        try:
            probe.execute('SELECT count(*) FROM sqlite_master').fetchone()
        finally:
            probe.close()

        db.session.remove()
        db.engine.dispose()

        for suffix in ('', '-wal', '-shm'):
            sidecar = target_path + suffix
            if os.path.exists(sidecar):
                os.remove(sidecar)

        shutil.copyfile(source_path, target_path)
        logger.info(f'数据库文件已替换: {target_path}')
```

- [ ] **Step 5: 修正备份失败提示（`backend/utils/backup_service.py:54`）**

```python
                        raise RuntimeError('数据库备份失败，请检查数据库文件是否可读')
```

- [ ] **Step 6: 更新 `_do_restore` 的 dump 探测（`backend/utils/backup_service.py:316-321`）**

```python
        # 查找数据库备份文件：新版为 db_dump.sqlite3，旧版为 db_dump.sql(.gz)
        db_dump_path = None
        for file_name in sorted(os.listdir(staging_dir)):
            if not file_name.startswith('db_dump'):
                continue
            if file_name.endswith(('.sqlite3', '.sqlite', '.db', '.sql', '.sql.gz')):
                db_dump_path = os.path.join(staging_dir, file_name)
                break
```

同时把 `_do_restore` 的 docstring 中"`_restore_database` 会执行 DROP SCHEMA public CASCADE"改为"会整体替换数据库文件"。

- [ ] **Step 7: 跑测试确认绿**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_backup_service.py -v
```
Expected: 两条 PASSED

- [ ] **Step 8: 提交**

Run:
```powershell
cd ..
git add backend/utils/backup_service.py backend/tests/test_backup_service.py
git commit -m "feat(backend): 备份恢复改为 SQLite 文件级操作"
```

---

### Task 6: 旧版 PostgreSQL dump 导入器

生产服务器上现存的备份包是 `tar.gz` 里装 `pg_dump` 出来的 `db_dump.sql(.gz)`。要能在 SQLite 版程序里把它恢复进去，需要一个**只解析 `COPY` 数据块、不执行任何 DDL** 的导入器：结构由 SQLAlchemy 模型建，dump 里的 `CREATE TYPE`/`ALTER TABLE`/`CREATE INDEX`/`setval` 全部忽略。

**Files:**
- Create: `backend/utils/legacy_pg_dump.py`
- Create: `backend/tests/fixtures/legacy_dump_sample.sql`
- Test: `backend/tests/test_legacy_pg_dump.py`（新建）

**Interfaces:**
- Consumes: `models.db.metadata`（表与列类型）
- Produces:
  - `legacy_pg_dump.parse_copy_blocks(sql_text: str) -> Iterator[CopyBlock]`
  - `legacy_pg_dump.CopyBlock(table: str, columns: list[str], rows: list[list[str | None]])`
  - `legacy_pg_dump.ImportReport(row_counts: dict[str,int], skipped_tables: list[str], skipped_columns: dict[str,list[str]], foreign_key_violations: list[tuple])`，带 `.summary() -> str`
  - `legacy_pg_dump.import_pg_dump_file(db_path: str, sql_path: str) -> ImportReport`
  - `legacy_pg_dump.import_pg_dump_text(db_path: str, sql_text: str) -> ImportReport`

- [ ] **Step 1: 创建测试用 dump 样本 `backend/tests/fixtures/legacy_dump_sample.sql`**

```sql
--
-- PostgreSQL database dump
--
SET statement_timeout = 0;
CREATE TYPE public.user_type_enum AS ENUM ('student', 'teacher');
CREATE TABLE public.users (
    user_id bigint NOT NULL,
    username character varying(50) NOT NULL
);
ALTER TABLE public.users OWNER TO postgres;

COPY public.users (user_id, username, password_hash, real_name, user_type, account_status, register_time, created_at, is_deleted, legacy_flag) FROM stdin;
1	admin	hash1	管理员	student	active	2025-08-01 12:34:56.789+00	2025-08-01 12:34:56.789+00	f	t
2	张三	hash2	张三	teacher	active	2025-08-02 08:00:00+08	2025-08-02 00:00:00+00	f	f
3	tab\tname	hash3	反斜杠\\名字	student	active	\N	2025-08-03 00:00:00+00	f	f
\.

COPY public.system_configs (id, config_key, config_value, is_encrypted, description) FROM stdin;
1	site_name	EasyInvoiceMgr	f	站点名称
2	smtp_password	ciphertext	t	\N
\.

COPY public.ignored_table (id) FROM stdin;
99
\.

SELECT pg_catalog.setval('public.users_user_id_seq', 3, true);
```

- [ ] **Step 2: 写失败的测试**

创建 `backend/tests/test_legacy_pg_dump.py`：

```python
"""旧版 PostgreSQL dump 导入器测试。"""
import os
from datetime import datetime, timezone

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'legacy_dump_sample.sql')


def _fixture_text():
    with open(FIXTURE, 'r', encoding='utf-8') as handle:
        return handle.read()


def test_parse_copy_blocks_handles_escapes_and_nulls():
    from utils.legacy_pg_dump import parse_copy_blocks

    blocks = {block.table: block for block in parse_copy_blocks(_fixture_text())}

    assert set(blocks) == {'users', 'system_configs', 'ignored_table'}
    assert blocks['users'].columns[:3] == ['user_id', 'username', 'password_hash']
    assert blocks['users'].rows[0][0] == '1'
    assert blocks['users'].rows[2][1] == 'tab\tname'
    assert blocks['users'].rows[2][3] == '反斜杠\\名字'
    assert blocks['users'].rows[2][6] is None


def test_timestamp_is_converted_to_naive_utc():
    from models import User
    from utils.legacy_pg_dump import _coerce_value

    column = User.__table__.columns['created_at']

    # +00 偏移：原样保留墙钟时间
    assert _coerce_value(column, '2025-08-01 12:34:56.789+00') == '2025-08-01 12:34:56.789000'
    # +08 偏移：换算成 UTC
    assert _coerce_value(column, '2025-08-02 08:00:00+08') == '2025-08-02 00:00:00.000000'


def test_import_writes_rows_and_skips_unknown(app, db_path):
    from models import db, SystemConfig, User
    from utils.legacy_pg_dump import import_pg_dump_text

    report = import_pg_dump_text(db_path, _fixture_text())

    assert report.row_counts == {'users': 3, 'system_configs': 2}
    assert 'ignored_table' in report.skipped_tables
    assert report.skipped_columns['users'] == ['legacy_flag']
    assert report.foreign_key_violations == []

    with app.app_context():
        assert User.query.count() == 3
        admin = db.session.get(User, 1)
        assert admin.username == 'admin'
        assert admin.is_deleted is False
        assert admin.created_at == datetime(2025, 8, 1, 12, 34, 56, 789000, tzinfo=timezone.utc)
        assert SystemConfig.query.count() == 2
```

- [ ] **Step 3: 跑测试确认红**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_legacy_pg_dump.py -v
```
Expected: FAILED，`ModuleNotFoundError: No module named 'utils.legacy_pg_dump'`

- [ ] **Step 4: 创建 `backend/utils/legacy_pg_dump.py`**

```python
"""旧版 PostgreSQL dump 到 SQLite 的数据导入。

只解析 pg_dump 的 COPY 数据块，不执行任何 DDL —— 表结构由 SQLAlchemy
模型（db.create_all / Alembic）负责。dump 里的 CREATE TYPE / ALTER TABLE /
CREATE INDEX / setval 等语句全部忽略。
"""
import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

_COPY_HEADER = re.compile(r'^COPY\s+(?P<table>[\w."]+)\s*\((?P<columns>.*?)\)\s+FROM\s+stdin;\s*$')
_TZ_SUFFIX = re.compile(r'([+-]\d{2})$')

# 父表在前，保证数据顺序天然满足外键
IMPORT_ORDER = [
    'users', 'events', 'event_members', 'invoices', 'vouchers',
    'purchase_records', 'invitation_codes', 'system_configs',
    'export_tasks', 'backup_records', 'operation_logs',
]

_UNESCAPE = {
    '\\': '\\', 't': '\t', 'n': '\n', 'r': '\r',
    'b': '\b', 'f': '\f', 'v': '\v',
}


def _unescape(value: str) -> str:
    """还原 COPY 文本格式的转义序列。"""
    if '\\' not in value:
        return value
    parts = []
    index = 0
    length = len(value)
    while index < length:
        char = value[index]
        if char == '\\' and index + 1 < length:
            nxt = value[index + 1]
            parts.append(_UNESCAPE.get(nxt, nxt))
            index += 2
            continue
        parts.append(char)
        index += 1
    return ''.join(parts)


@dataclass
class CopyBlock:
    table: str
    columns: list
    rows: list = field(default_factory=list)


@dataclass
class ImportReport:
    row_counts: dict = field(default_factory=dict)
    skipped_tables: list = field(default_factory=list)
    skipped_columns: dict = field(default_factory=dict)
    foreign_key_violations: list = field(default_factory=list)

    def summary(self) -> str:
        tables = ', '.join(f'{name}={count}' for name, count in self.row_counts.items())
        total = sum(self.row_counts.values())
        extra = f'；忽略的表: {self.skipped_tables}' if self.skipped_tables else ''
        return f'共导入 {total} 行（{tables}）{extra}'


def parse_copy_blocks(sql_text: str):
    """从 pg_dump 文本中按出现顺序产出 COPY 数据块。"""
    block = None
    for raw_line in sql_text.splitlines():
        if block is None:
            match = _COPY_HEADER.match(raw_line)
            if match:
                table = match.group('table').split('.')[-1].strip('"')
                columns = [item.strip().strip('"') for item in match.group('columns').split(',')]
                block = CopyBlock(table=table, columns=columns)
            continue

        if raw_line == '\\.':
            yield block
            block = None
            continue

        block.rows.append([
            None if item == '\\N' else _unescape(item)
            for item in raw_line.split('\t')
        ])

    if block is not None:
        raise ValueError(f'COPY 数据块未正常结束: {block.table}')


def _parse_timestamp(raw: str) -> str:
    """pg_dump 的 timestamptz 文本 -> naive UTC 字符串（SQLite 存储格式）。"""
    text = raw.strip()
    if ' ' in text and 'T' not in text:
        text = text.replace(' ', 'T', 1)
    # PostgreSQL 可能输出 +00 / +08 这类两位偏移，补成 +00:00 才能解析
    text = _TZ_SUFFIX.sub(r'\1:00', text)
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment.strftime('%Y-%m-%d %H:%M:%S.%f')


def _base_type(column_type):
    """剥掉 TypeDecorator 外壳，取出真正的存储类型。

    Task 3 之后时间列是 UTCDateTime（TypeDecorator），直接 isinstance 判断
    会落到 else 分支，所以这里统一先拆壳。
    """
    from sqlalchemy.types import TypeDecorator

    while isinstance(column_type, TypeDecorator):
        column_type = getattr(column_type, 'impl_instance', None) or column_type.impl
    return column_type


def _coerce_value(column, raw):
    """按 SQLAlchemy 列类型把 COPY 文本转成 SQLite 可写入的值。"""
    from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, JSON, Numeric, SmallInteger

    if raw is None:
        return None

    column_type = _base_type(column.type)

    if isinstance(column_type, JSON):
        return json.dumps(json.loads(raw), ensure_ascii=False)
    if isinstance(column_type, DateTime):
        return _parse_timestamp(raw)
    if isinstance(column_type, Date):
        return date.fromisoformat(raw[:10]).isoformat()
    if isinstance(column_type, Boolean):
        return 1 if raw in ('t', 'true', '1') else 0
    if isinstance(column_type, Numeric):
        return str(Decimal(raw))
    if isinstance(column_type, (Integer, BigInteger, SmallInteger)):
        return int(raw)
    return raw


def _load_tables():
    """加载 SQLAlchemy metadata（含 operation_logs）。"""
    import utils.operation_log  # noqa: F401  确保 operation_logs 表注册
    from models import db

    return db.metadata.tables


def import_pg_dump_file(db_path: str, sql_path: str) -> ImportReport:
    with open(sql_path, 'r', encoding='utf-8', errors='replace') as handle:
        return import_pg_dump_text(db_path, handle.read())


def import_pg_dump_text(db_path: str, sql_text: str) -> ImportReport:
    """把 dump 里的 COPY 数据灌进已建好表的 SQLite 数据库。"""
    tables = _load_tables()
    blocks = {}
    for block in parse_copy_blocks(sql_text):
        blocks.setdefault(block.table, block)

    report = ImportReport()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute('PRAGMA foreign_keys=OFF')

        ordered = [name for name in IMPORT_ORDER if name in blocks]
        ordered += sorted(name for name in blocks if name not in IMPORT_ORDER)

        for table_name in ordered:
            block = blocks[table_name]
            table = tables.get(table_name)
            if table is None:
                report.skipped_tables.append(table_name)
                logger.warning(f'dump 中的表 {table_name} 在当前模型中不存在，已跳过')
                continue

            usable = [(index, name) for index, name in enumerate(block.columns) if name in table.columns]
            missing = [name for name in block.columns if name not in table.columns]
            if missing:
                report.skipped_columns[table_name] = missing
                logger.warning(f'表 {table_name} 的列 {missing} 在当前模型中不存在，已跳过')

            columns = [table.columns[name] for _index, name in usable]
            column_sql = ', '.join(f'"{column.name}"' for column in columns)
            placeholder_sql = ', '.join('?' * len(columns))
            statement = f'INSERT INTO "{table_name}" ({column_sql}) VALUES ({placeholder_sql})'

            rows = []
            for raw_row in block.rows:
                rows.append([
                    _coerce_value(column, raw_row[index] if index < len(raw_row) else None)
                    for (index, _name), column in zip(usable, columns)
                ])

            connection.executemany(statement, rows)
            report.row_counts[table_name] = len(rows)

        connection.commit()
        violations = connection.execute('PRAGMA foreign_key_check').fetchall()
        report.foreign_key_violations = [tuple(item) for item in violations]
        if report.foreign_key_violations:
            logger.warning(
                f'外键完整性检查发现 {len(report.foreign_key_violations)} 条异常，'
                f'样例: {report.foreign_key_violations[:5]}'
            )
    finally:
        connection.close()

    logger.info(f'旧版 dump 导入完成: {report.summary()}')
    return report
```

- [ ] **Step 5: 跑测试确认绿**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_legacy_pg_dump.py -v
```
Expected: 三条 PASSED

- [ ] **Step 6: 提交**

Run:
```powershell
cd ..
git add backend/utils/legacy_pg_dump.py backend/tests/fixtures/legacy_dump_sample.sql backend/tests/test_legacy_pg_dump.py
git commit -m "feat(backend): 新增旧版 PostgreSQL 备份数据导入器"
```

---

### Task 7: 恢复备份支持新旧两种归档

`_restore_database` 里 `.sql` 分支已经指向 `self._import_legacy_pg_dump`，本任务把它实现出来，并保证恢复后 Alembic 版本被正确标记。

**Files:**
- Modify: `backend/utils/backup_service.py`（新增 `_import_legacy_pg_dump`，紧邻 `_replace_database_file` 之后）
- Test: `backend/tests/test_backup_service.py`（追加用例）

**Interfaces:**
- Consumes: `utils.legacy_pg_dump.import_pg_dump_file`、`utils.schema_init.ensure_schema`
- Produces: `BackupService._import_legacy_pg_dump(target_path: str, sql_path: str) -> ImportReport`

- [ ] **Step 1: 追加失败测试**

在 `backend/tests/test_backup_service.py` 末尾追加：

```python
def test_restore_legacy_pg_dump_rebuilds_database(app, service, db_path):
    """旧版 pg_dump 备份：重建库 → 灌数据 → 标记 Alembic 版本。"""
    import shutil
    from pathlib import Path

    from sqlalchemy import text

    from models import db, User

    _insert_user(app, 'wiped_by_restore')

    fixture = Path(__file__).parent / 'fixtures' / 'legacy_dump_sample.sql'
    legacy_sql = str(Path(db_path).parent / 'db_dump.sql')
    shutil.copyfile(fixture, legacy_sql)

    service._restore_database('sqlite:///' + db_path.replace('\\', '/'), legacy_sql, str(Path(db_path).parent))

    with app.app_context():
        usernames = [row[0] for row in db.session.execute(
            text('SELECT username FROM users ORDER BY user_id')
        )]
        assert usernames == ['admin', '张三', 'tab\tname']
        assert User.query.count() == 3
        versions = db.session.execute(text('SELECT version_num FROM alembic_version')).fetchall()
        assert versions, '恢复后必须写入 alembic_version，否则下次启动会重复建表'
```

- [ ] **Step 2: 跑测试确认红**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_backup_service.py -v -k legacy
```
Expected: FAILED，`AttributeError: 'BackupService' object has no attribute '_import_legacy_pg_dump'`

- [ ] **Step 3: 实现 `_import_legacy_pg_dump`**

在 `backend/utils/backup_service.py` 的 `_replace_database_file` 方法之后插入：

```python
    def _import_legacy_pg_dump(self, target_path, sql_path):
        """把旧版 PostgreSQL dump 恢复成全新的 SQLite 数据库。"""
        from models import db
        from utils.legacy_pg_dump import import_pg_dump_file
        from utils.schema_init import ensure_schema

        db.session.remove()
        db.engine.dispose()

        for suffix in ('', '-wal', '-shm'):
            sidecar = target_path + suffix
            if os.path.exists(sidecar):
                os.remove(sidecar)

        # 先按模型建出空库（旧 dump 里的 DDL 一律不执行）
        db.create_all()
        db.session.commit()

        report = import_pg_dump_file(target_path, sql_path)

        # 建表后没有 alembic_version，ensure_schema 会标记为 head
        ensure_schema()

        logger.info(f'旧版备份恢复完成: {report.summary()}')
        return report
```

- [ ] **Step 4: 修正 `_do_restore` 里的恢复记录创建（外键风险）**

`backend/utils/backup_service.py:303` 的导入改为：

```python
        from models import db, BackupRecord, User
```

并把 `backend/utils/backup_service.py:356-365` 的恢复记录创建改为：

```python
        # 旧 dump 里可能没有这个用户，SQLite 已开启外键强制，必须回退为 NULL
        creator_id = created_by
        if creator_id is not None and db.session.get(User, creator_id) is None:
            logger.warning(f'恢复记录的原创建者 id={creator_id} 不在恢复后的数据库中，改为 NULL')
            creator_id = None

        # 创建恢复完成记录（旧 record 已随数据库替换销毁）
        restore_record = BackupRecord(
            backup_type='restore',
            backup_scope='full',
            status='completed',
            progress=100,
            progress_message='恢复完成',
            completed_at=datetime.now(timezone.utc),
            created_by=creator_id,
        )
```

- [ ] **Step 5: 跑测试确认绿**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_backup_service.py -v
```
Expected: 三条全部 PASSED

- [ ] **Step 6: 跑全量测试**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q
```
Expected: 全部 PASSED

- [ ] **Step 7: 提交**

Run:
```powershell
cd ..
git add backend/utils/backup_service.py backend/tests/test_backup_service.py
git commit -m "feat(backend): 恢复备份支持新旧两种归档格式"
```

---

### Task 8: 清理 PostgreSQL 专用代码与依赖

**Files:**
- Delete: `backend/sql/base.sql`、`backend/migrate.py`、`backend/utils/db_backup.py`
- Modify: `backend/requirements.txt:16`（删 `psycopg2-binary`）
- Modify: `backend/Dockerfile:10`（删 `postgresql-client`）
- Modify: `backend/migrations/env.py`（加 `render_as_batch`）
- Test: `backend/tests/test_no_postgres_leftovers.py`（新建）

**Interfaces:**
- Consumes: 无
- Produces: 后端源码中不再出现 `psycopg2` / `pg_dump` / `psql` / `base.sql` 字样

- [ ] **Step 1: 确认 `db_backup.py` 确实无人引用**

Run:
```powershell
cd backend
Select-String -Path *.py,utils\*.py,routes\*.py -Pattern 'db_backup' -List
```
Expected: 只在 `utils\db_backup.py` 自身出现（`from utils import db_backup` 之类的引用为 0），可安全删除。

- [ ] **Step 2: 写守卫测试**

创建 `backend/tests/test_no_postgres_leftovers.py`：

```python
"""守卫测试：迁移完成后后端不应再残留 PostgreSQL 专用代码。"""
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN = ('psycopg2', 'pg_dump', 'pg_restore', 'base.sql')
SKIP_DIRS = {'venv', 'tests', '__pycache__', 'migrations', '.pytest_cache'}


def _iter_sources():
    for root, dirs, files in os.walk(BACKEND_DIR):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            if name.endswith('.py'):
                yield os.path.join(root, name)


def test_no_postgres_specific_code_remains():
    offenders = []
    for path in _iter_sources():
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            for lineno, line in enumerate(handle, start=1):
                for token in FORBIDDEN:
                    if token in line:
                        offenders.append(f'{os.path.relpath(path, BACKEND_DIR)}:{lineno}: {line.strip()}')
    assert offenders == [], '仍有 PostgreSQL 专用残留:\n' + '\n'.join(offenders)


def test_postgres_artifacts_are_deleted():
    assert not os.path.exists(os.path.join(BACKEND_DIR, 'sql', 'base.sql'))
    assert not os.path.exists(os.path.join(BACKEND_DIR, 'migrate.py'))
    assert not os.path.exists(os.path.join(BACKEND_DIR, 'utils', 'db_backup.py'))
```

- [ ] **Step 3: 跑测试确认红**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_no_postgres_leftovers.py -v
```
Expected: 两条都 FAILED，报告列出 `config.py`（如果 Task 4 未清干净）、`migrate.py`、`utils/db_backup.py` 等残留。

- [ ] **Step 4: 删除 PG 专用文件**

Run:
```powershell
cd backend
git rm sql\base.sql migrate.py utils\db_backup.py
```
Expected: 三个 `rm '...'` 输出。

- [ ] **Step 5: 移除 `psycopg2-binary`**

把 `backend/requirements.txt:16` 的 `psycopg2-binary==2.9.12` 整行删除。

- [ ] **Step 6: 移除镜像里的 `postgresql-client`**

把 `backend/Dockerfile:10` 的 `    postgresql-client \` 整行删除。

- [ ] **Step 7: 为 Alembic 打开批处理模式**

SQLite 不支持 `ALTER COLUMN`，Alembic 必须用 batch 模式重建表。在 `backend/migrations/env.py` 的 `context.configure(...)` 调用中补一个参数：

```python
        render_as_batch=True,
```

（位置：`context.configure(` 的参数列表内，与 `compare_type=...` 同级。）

- [ ] **Step 8: 跑测试确认绿**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q
```
Expected: 全部 PASSED

- [ ] **Step 9: 提交**

Run:
```powershell
cd ..
git add -A backend
git commit -m "refactor(backend): 清理 PostgreSQL 专用代码与依赖"
```

---

### Task 9: 部署编排与文档同步

**Files:**
- Modify: `docker-compose.yml:2-18`、`27`、`44-46`、`60-63`
- Modify: `backend/Dockerfile:49`
- Modify: `docs/PROJECT_GUIDE.md:16,20,21,28,67,68,146,177,189,265,276`
- Modify: `README.md:50`、`README.md:94`
- Modify: `dev.ps1:15-22`

**Interfaces:**
- Consumes: `backend/data/` 数据目录
- Produces: `docker compose config` 可通过的三服务编排（backend / frontend + 两个具名卷）

- [ ] **Step 1: 改写 `docker-compose.yml`**

完整替换为：

```yaml
services:
  backend:
    build:
      context: ./backend
      args:
        USE_CHINA_MIRROR: ${USE_CHINA_MIRROR:-false}
    restart: unless-stopped
    environment:
      DATABASE_URL: sqlite:////app/data/easy_invoice_mgr.sqlite
      SECRET_KEY: ${SECRET_KEY:-easy-invoice-mgr-secret-key}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:-easy-invoice-mgr-jwt-secret-32bytes}
      STORAGE_BACKEND: local
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:-admin}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}
      GLM_API_KEY: ${GLM_API_KEY:-}
      GLM_MODEL: ${GLM_MODEL:-GLM-4V-Flash}
      HOST_PROJECT_DIR: ${PWD}
    volumes:
      - dbdata:/app/data
      - uploads:/app/uploads
      - exports:/app/exports
      - ./backend/VERSION:/app/VERSION:ro
      - /var/run/docker.sock:/var/run/docker.sock
      - ${PWD}:${PWD}
    ports:
      - "5000:5000"

  frontend:
    build:
      context: ./frontend
      args:
        NUXT_PUBLIC_API_BASE: ${NUXT_PUBLIC_API_BASE:-http://localhost:5000/api}
        USE_CHINA_MIRROR: ${USE_CHINA_MIRROR:-false}
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  dbdata:
  uploads:
  exports:
```

- [ ] **Step 2: 让镜像准备好数据目录**

把 `backend/Dockerfile:49` 的 `RUN mkdir -p uploads exports` 改为：

```
RUN mkdir -p uploads exports data
```

- [ ] **Step 3: 验证编排文件可解析**

Run:
```powershell
docker compose config --quiet; if ($LASTEXITCODE -ne 0) { 'docker 不可用，改为静态检查'; Select-String -Path docker-compose.yml -Pattern 'postgres' } 
```
Expected: `docker compose config --quiet` 无输出且 exit 0；若 docker 不可用，`Select-String` 也应为空（文件中已无 `postgres`）。

- [ ] **Step 4: 同步 `docs/PROJECT_GUIDE.md`**

逐处改写（保持表格列宽风格）：
- 行 16：`| 数据库 | SQLite（单文件 `backend/data/easy_invoice_mgr.sqlite`），ORM 模型集中在 `backend/models.py`；建表由 Alembic + `db.create_all()` 完成 |`
- 行 20：`三服务` → `两服务（backend / frontend），数据落在具名卷 dbdata/uploads/exports`
- 行 21：`PostgreSQL(Docker) → Flask:5000 → Nuxt:3000` → `Flask:5000 → Nuxt:3000（数据库为本地 SQLite 文件，无需外部服务）`
- 行 28：删除 `psycopg2-binary` 行，说明改为 `flask_sqlalchemy / Flask-Migrate：ORM 与数据库迁移（SQLite 内置驱动）`
- 行 67：`pg_dump + uploads + system_configs` → `SQLite 在线备份 + uploads + system_configs`
- 行 68：删除 `db_backup.py` 整行
- 行 146：`DATABASE_URL` 默认值改为 `sqlite:///<backend>/data/easy_invoice_mgr.sqlite`，说明改为"数据库连接串，部署时由 `docker-compose.yml` 指向 `/app/data/...`"
- 行 177：`pg_dump / pg_restore（子进程）` 整行改为 `| sqlite3 备份 API（进程内） | backend/utils/backup_service.py、utils/legacy_pg_dump.py | 备份与恢复；旧版 PG 备份包仍可导入 |`
- 行 189：`同步改 backend/sql/base.sql` → 删除该半句，改为"两处都要改：模型 + Alembic 迁移（SQLite 需 `render_as_batch=True`）"
- 行 265：`backend/migrate.py` 整行删除
- 行 276：整行改为 `| 数据库驱动 | 项目已迁移到 SQLite，内置驱动，无需额外安装；连接串必须以 sqlite:/// 开头，add_argument 见 config.py |`

- [ ] **Step 5: 同步 `README.md`**

- 行 50：把 `依次拉起三个服务：PostgreSQL（Docker，仅数据库）→ 后端 Flask` 改为 `依次拉起两个服务：后端 Flask`
- 行 94：删除 `| DB_PASSWORD | root | 数据库密码 |` 整行；在 `.env` 表格上方补一行说明：`> 数据库已迁移到 SQLite，数据文件位于具名卷 dbdata（容器内 /app/data），不再需要数据库密码。`

- [ ] **Step 6: 同步 `dev.ps1`**

把 `dev.ps1:15-22` 的 PostgreSQL 启动段整段替换为：

```powershell
# ---- 1) 数据库: SQLite 无需外部服务，首次运行自动建库 ----
Write-Host '[1/2] SQLite 本地文件数据库，无需启动外部服务' -ForegroundColor Cyan
```

并把脚本里后续的 `'[2/3]'`、`'[3/3]'` 段落编号改成 `'[2/2]'` 之外的表述（保持简单即可，例如统一去掉序号）。

- [ ] **Step 7: 验证没有遗留引用**

Run:
```powershell
Select-String -Path docker-compose.yml,README.md,dev.ps1,docs\PROJECT_GUIDE.md -Pattern 'postgres|pg_dump|pg_isready|5432|DB_PASSWORD'
```
Expected: 无匹配（若 `docs/PROJECT_GUIDE.md` 的历史记录段仍刻意保留旧说明，需在行尾注明"已迁移，仅存档"）。

- [ ] **Step 8: 提交**

Run:
```powershell
git add docker-compose.yml backend/Dockerfile README.md dev.ps1 docs/PROJECT_GUIDE.md
git commit -m "chore: 部署编排与文档同步为 SQLite"
```

---

### Task 10: 全链路冒烟回归脚本

**Files:**
- Create: `backend/scripts/smoke_sqlite.py`

**Interfaces:**
- Consumes: `app.create_app`（经环境变量指向临时 SQLite）
- Produces: `python scripts/smoke_sqlite.py` 退出码 0/1，逐条打印 `PASS/FAIL 用例名`

- [ ] **Step 1: 编写脚本**

创建 `backend/scripts/smoke_sqlite.py`：

```python
"""SQLite 全链路冒烟回归：真实走 HTTP 端点，逐条断言。

用法：在 backend 目录执行  .\\venv\\Scripts\\python.exe scripts\\smoke_sqlite.py
退出码 0 表示全部通过；数据库落在临时目录，不会污染 backend/data。
"""
import os
import sys
import tempfile
import traceback

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

TEMP_DIR = tempfile.mkdtemp(prefix='easyinvoice_smoke_')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(TEMP_DIR, 'smoke.sqlite').replace('\\', '/')
os.environ.setdefault('SECRET_KEY', 'smoke-secret')
os.environ.setdefault('JWT_SECRET_KEY', 'smoke-jwt-secret')
os.environ['ADMIN_PASSWORD'] = 'admin'

RESULTS = []


def check(name):
    def decorator(func):
        RESULTS.append((name, func))
        return func
    return decorator


@check('管理员登录')
def _login(client, state):
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    assert payload['code'] == 200, payload
    state['token'] = payload['data']['token']
    state['headers'] = {'Authorization': f"Bearer {state['token']}"}


@check('新建赛事')
def _create_event(client, state):
    response = client.post('/api/events', json={
        'event_name': '冒烟赛事',
        'description': 'SQLite 冒烟',
        'event_start_time': '2026-01-01T00:00:00+00:00',
        'event_end_time': '2026-12-31T00:00:00+00:00',
        'total_budget': 10000,
    }, headers=state['headers'])
    assert response.status_code == 201, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    assert payload['code'] == 200, payload
    state['event_id'] = payload['data']['event_id']
    assert state['event_id'], payload


@check('赛事列表含新建赛事')
def _list_events(client, state):
    response = client.get('/api/events', headers=state['headers'])
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    assert '冒烟赛事' in response.get_data(as_text=True)


@check('操作日志可查询')
def _operation_logs(client, state):
    response = client.get(
        '/api/operation-logs',
        headers=state['headers'],
        query_string={'page': 1, 'per_page': 10},
    )
    assert response.status_code == 200, response.get_data(as_text=True)[:300]


@check('发起手动备份')
def _manual_backup(client, state):
    response = client.post('/api/system/backup', headers=state['headers'])
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    assert payload['code'] == 200, payload
    state['backup_id'] = payload['data']['id']
    assert state['backup_id']


@check('备份记录可见')
def _list_backups(client, state):
    response = client.get('/api/system/backups', headers=state['headers'])
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    items = response.get_json()['data']['items']
    assert any(item['id'] == state['backup_id'] for item in items), items


def main():
    from app import create_app

    application = create_app()
    failures = 0

    with application.test_client() as client:
        state = {}
        for name, func in RESULTS:
            try:
                func(client, state)
                print(f'PASS  {name}')
            except Exception as error:
                failures += 1
                print(f'FAIL  {name}: {error}')
                traceback.print_exc()

    print(f'\n共 {len(RESULTS)} 项，失败 {failures} 项')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 2: 运行脚本**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe scripts\smoke_sqlite.py
```
Expected: 输出 6 行 `PASS`，末行 `共 6 项，失败 0 项`，退出码 0。

> 若某个端点的路径或请求体与脚本假设不一致，以 `backend/routes/*.py` 中的实际路由为准修正脚本，**不要**为了迁就脚本去改业务路由。

- [ ] **Step 3: 提交**

Run:
```powershell
cd ..
git add backend/scripts/smoke_sqlite.py
git commit -m "test(backend): 新增 SQLite 全链路冒烟回归脚本"
```

---

### Task 11: 真实旧备份文件验收（阻塞：等待用户提供文件）

用户会提供一份由**旧版程序**（PostgreSQL 时代）生成的 `full_backup_*.tar.gz`。这是唯一能证明旧格式恢复真的可用的证据，必须实测。

**Files:**
- Create（临时）: `backend/scripts/verify_legacy_backup.py`
- Modify（视实测结果）: `backend/utils/legacy_pg_dump.py`

**Interfaces:**
- Consumes: `utils.backup_service.BackupService.restore_from_file`、用户提供的 `full_backup_*.tar.gz`
- Produces: 一份逐表行数比对报告（旧备份 vs 恢复后的 SQLite）

- [ ] **Step 1: 解包查看真实归档结构**

Run（把 `<备份文件>` 换成实际路径）：
```powershell
cd backend
.\venv\Scripts\python.exe -c "import tarfile,sys; t=tarfile.open(sys.argv[1]); print('\n'.join(t.getnames()))" "<备份文件>"
```
Expected: 包含 `db_dump.sql` 或 `db_dump.sql.gz`、`invoices/`、`avatars/`、`system_config.json`。若文件名或结构与本计划假设不符，**先停下**并把实际结构报给用户，再调整 Task 5/7 的探测逻辑。

- [ ] **Step 2: 抽取 COPY 表清单与行数**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -c "import sys,collections; from utils.legacy_pg_dump import parse_copy_blocks; data=open(sys.argv[1],encoding='utf-8',errors='replace').read(); c=collections.Counter(b.table for b in parse_copy_blocks(data) for _ in [0]); [print(f'{k}\t{v}') for k,v in sorted(c.items())]" "<解包后的 db_dump.sql>"
```
Expected: 打印 11 张表的行数（与旧系统一致）。

- [ ] **Step 3: 在临时环境完整跑一次恢复**

创建 `backend/scripts/verify_legacy_backup.py`：

```python
"""用真实旧备份验证恢复链路（临时脚本，验证后删除）。"""
import os
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

TEMP_DIR = tempfile.mkdtemp(prefix='easyinvoice_verify_')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(TEMP_DIR, 'verify.sqlite').replace('\\', '/')
os.environ.setdefault('SECRET_KEY', 'verify-secret')
os.environ.setdefault('JWT_SECRET_KEY', 'verify-jwt-secret')
os.environ['ADMIN_PASSWORD'] = 'admin'

from sqlalchemy import text  # noqa: E402

from app import create_app  # noqa: E402
from models import db  # noqa: E402
from utils.backup_service import get_backup_service  # noqa: E402


def main(archive_path):
    application = create_app()
    print(f'临时数据库文件: {os.environ["DATABASE_URL"]}')
    with application.app_context():
        from models import BackupRecord

        record = BackupRecord(backup_type='restore', backup_scope='full', status='pending')
        db.session.add(record)
        db.session.commit()

        service = get_backup_service()
        # 走与「上传备份恢复」路由完全相同的入口
        new_id = service.restore_from_file(record.id, archive_path)
        print(f'恢复完成，恢复记录 id={new_id}')

        for table in db.metadata.sorted_tables:
            count = db.session.execute(text(f'SELECT count(*) FROM "{table.name}"')).scalar()
            print(f'{table.name}\t{count}')

        missing = db.session.execute(text('PRAGMA foreign_key_check')).fetchall()
        print(f'外键异常条数: {len(missing)}')
        if missing:
            print(missing[:5])


if __name__ == '__main__':
    main(sys.argv[1])
```

Run:
```powershell
cd backend
.\venv\Scripts\python.exe scripts\verify_legacy_backup.py "<备份文件>"
```
Expected: 打印 11 张表的行数，且与 Step 2 的结果逐表一致。

- [ ] **Step 4: 抽查关键业务数据**

Run:
```powershell
cd backend
.\venv\Scripts\python.exe -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('SELECT sum(total_amount) FROM invoices').fetchone()); print(c.execute('SELECT count(*) FROM users WHERE is_deleted=0').fetchone()); print(c.execute('PRAGMA foreign_key_check').fetchall()[:5])" "<TEMP_DIR>/verify.sqlite"
```
Expected: 金额总额、有效用户数与旧系统一致；`foreign_key_check` 为空列表。

- [ ] **Step 5: 把实测发现的问题修进去并提交**

若解析器需要适配真实 pg_dump 输出（例如出现 `\restrict`、字节序标记、`CREATE TYPE` 之外的意外格式），在 `backend/utils/legacy_pg_dump.py` 修正并补一条对应的 fixture 测试，然后：

```powershell
git add backend/utils/legacy_pg_dump.py backend/tests/
git commit -m "fix(backend): 适配真实旧版备份 dump 格式"
```

- [ ] **Step 6: 清理临时脚本**

Run:
```powershell
git rm --cached backend/scripts/verify_legacy_backup.py 2>$null; Remove-Item backend/scripts/verify_legacy_backup.py -ErrorAction SilentlyContinue
```
Expected: 临时验证脚本不出现在仓库里。

---

## 生产切换操作手册（执行完 Task 0–10 后，由用户按此上线）

1. 生产服务器：`git pull` 拿到 `feat/sqlite-migration`（或合并后的 `dev`）。
2. **先备份旧备份包**：把服务器上现存的 `full_backup_*.tar.gz` 下载到本地留存一份。
3. `docker compose down`（**不要** `-v`，保留 uploads/exports 卷），然后 `docker compose up -d --build`。
4. 新容器起来后会自动建出空 SQLite 库（`/app/data/easy_invoice_mgr.sqlite`），`admin` 账号按 `ADMIN_PASSWORD` 播种。
5. 登录 → 系统设置 → 备份恢复 → 上传旧 `full_backup_*.tar.gz` → 恢复。程序会自动识别 `db_dump.sql.gz` 为旧格式并导入。
6. 恢复完成后核对：用户数、赛事数、发票总数与金额合计、操作日志条数。
7. 核对无误后，删除服务器上的 `pgdata` Docker 卷（`docker volume rm <project>_pgdata`）释放磁盘。

## Self-Review 结论

- **Spec 覆盖**：评估文档第三节 P0-1→Task 2、P0-2→Task 3、P0-3→Task 5/7、P1-4→Task 4、P1-5→Task 4（`foreign_keys=ON`）+ Task 8（记录为已知差异）、P2-6→Task 4、P2-7→Task 8；第五节数据搬迁→Task 6/7/11；第六节阶段 1→Task 4、阶段 2→Task 6、阶段 3→Task 5、阶段 4→Task 9、阶段 5→Task 10。第七节决策（彻底切 SQLite）→Task 8。
- **已知差异（本计划不修，记录在案）**：`base.sql` 里的 `CHECK (amount >= 0)` 等约束在模型层没有对应 `CheckConstraint`，迁移后这些校验只由业务逻辑保证。
- **类型一致性**：`BigIntPK`（Task 2）在 Task 3 的模型替换中保持；`UTCDateTime`（Task 3）在 Task 6 的 `_coerce_value` 中通过 SQLAlchemy 列类型判断，不重复实现；`database_file_path`（Task 4）在 Task 5/7 中一致使用；`ensure_schema`（Task 4）在 Task 7 复用。
