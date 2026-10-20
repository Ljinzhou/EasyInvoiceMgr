# EasyInvoiceMgr 项目结构导航手册

> 面向 AI 与开发者的索引层文档。读完本篇即可精确定位文件与调用链路，无需全仓搜索。  
> 统计口径：Python 行数为「实际行数（含末行）」；统计于 HEAD `fd8a456`（2026-10-11）。  
> 维护方式：随代码变更增量更新对应小节，并同步页脚「统计于 / 复核于」。

---

## 1. 项目概述与技术栈

| 项     | 内容                                                                                                                                                            |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 项目用途  | 武汉生物工程学院机器人实验室的**活动经费管理与发票报销系统**。以「项目（event）」为预算单元，管理购买记录（收据）、发票、凭证（voucher）的上传/OCR识别/审核/报销/批量导出                                                              |
| 前端    | Nuxt 3.9+ / Vue 3.3 / Pinia 2 / TypeScript 5 / Tailwind-free 手写 CSS / pdfjs-dist / cropperjs / dayjs / file-saver / axios。**入口 `frontend/app.vue`，开发端口 3000** |
| 后端    | Flask 3.1 + SQLAlchemy 3.1 + Flask-JWT-Extended 4.7 + Flask-Migrate（Alembic）+ APScheduler。**入口 `backend/app.py`（`create_app()` 工厂），开发端口 5000**                |
| 数据库   | SQLite（单文件 `backend/data/easy_invoice_mgr.sqlite`），ORM 模型集中在 `backend/models.py`；建表由 Alembic + `db.create_all()` 完成                          |
| 对象存储  | 本地文件系统（默认，`backend/uploads`）或腾讯云 COS（`STORAGE_BACKEND=cos`），由 `backend/utils/storage.py` 做统一抽象                                                                |
| AI 能力 | 智谱 GLM 视觉模型（默认 `GLM-4V-Flash`）做发票图片识别；PDF 文本兜底解析用 PyPDF2/PyMuPDF                                                                                              |
| 导出    | openpyxl + pandas 生成 Excel，fpdf 合并 PDF，zip 打包，异步任务表 `export_tasks`                                                                                            |
| 部署    | `docker-compose.yml` 两服务（backend / frontend），数据落在具名卷 dbdata/uploads/exports；生产建议 Nginx 反代 3000→/、5000→/api、/uploads                                 |
| 本地开发  | 根目录 `dev.ps1`（`dev.bat` 为双击入口）：Flask:5000 → Nuxt:3000（数据库为本地 SQLite 文件，无需外部服务）。后端优先 conda 环境 `py311`，不可用时回退 `backend/venv`                 |

**核心依赖作用（后端 `backend/requirements.txt`）**

| 包                                                    | 作用                                                   |
| ---------------------------------------------------- | ---------------------------------------------------- |
| Flask / flask-cors / flask_jwt_extended              | 路由、CORS、JWT 鉴权（token 支持 header 与 `?token=` 查询参数两种位置） |
| flask_sqlalchemy / Flask-Migrate                   | ORM 与数据库迁移（SQLite 内置驱动，无需额外数据库驱动）        |
| openpyxl / pandas / fpdf / PyPDF2 / PyMuPDF / Pillow | Excel 导出、PDF 合并/解析、PDF 渲染为图、图片处理                     |
| cos-python-sdk-v5                                    | 腾讯云 COS 上传/预签名 URL                                   |
| cryptography                                         | Fernet 加密系统敏感配置（`ai_api_key`）                        |
| APScheduler                                          | 定时数据库备份调度                                            |
| python-dotenv / Requests                             | `.env` 加载、AI/外部 HTTP 调用                              |

---

## 2. 目录结构树

```
EasyInvoiceMgr/
├── backend/                     Flask 后端（Python）
│   ├── app.py                 ★ 入口：create_app() 工厂、蓝图注册、静态文件路由、启动时自动迁移 + 种子管理员
│   ├── config.py              ★ 环境变量 → Config 类（SECRET/JWT/DATABASE_URL/STORAGE_BACKEND/COS/GLM）
│   ├── models.py              ★ 全部 ORM 模型（10 张表）
│   ├── generate_password.py   小工具：生成 admin 密码 hash
│   ├── requirements.txt / Dockerfile / VERSION
│   ├── VERSION                版本号，app.py `_read_version()` 读取
│   ├── routes/                ★ 各业务蓝图
│   │   ├── auth.py            /api/auth：注册、登录、用户 CRUD、头像、改密
│   │   ├── events.py          /api：项目（event）CRUD、成员管理、用户汇总统计
│   │   ├── invoices.py        /api：发票 CRUD、审核、批量报销、预览/下载
│   │   ├── purchase_records.py /api：购买记录 CRUD、转移、批量转移、报销、重解析发票
│   │   ├── vouchers.py        /api：凭证 CRUD、MD5 秒传检查、批量报销
│   │   ├── parse.py           /api：文件上传、OCR/文本解析发票、文件预览下载、PDF 转图
│   │   ├── export.py          /api：异步导出任务（Excel+PDF+zip）
│   │   ├── invitation_codes.py /api：邀请码 CRUD/校验/启停
│   │   ├── operation_logs.py  /api/operation-logs：操作日志查询/删除（管理员）
│   │   └── system.py          /api/system：系统配置、版本更新提示、备份/恢复、模型连通测试、AI 摘要
│   ├── utils/                  业务服务层（无 HTTP 语义）
│   │   ├── storage.py         ★ 存储后端单例（local / cos 分派）
│   │   ├── local_storage.py   LocalStorageManager：uploads 目录读写、头像、预签名
│   │   ├── cos_manager.py     COSManager：同接口的 COS 实现 + 单例 cos_manager
│   │   ├── invoice_parser.py  PDF 文本兜底解析（InvoiceParser）
│   │   ├── glm_vision_service.py GLM 视觉识别 + DB 配置优先的模型/密钥解析
│   │   ├── export_service.py  异步导出：取数 → Excel → 图片嵌入 → PDF 合并 → zip
│   │   ├── backup_service.py  备份/恢复（SQLite 在线备份 + uploads + system_configs），APScheduler 定时
│   │   ├── legacy_pg_dump.py  旧版 PostgreSQL 备份包（db_dump.sql.gz）解析导入
│   │   ├── operation_log.py   ★ OperationLog 模型 + LogService（实际被所有路由使用）
│   │   ├── crypto_utils.py    Fernet encrypt_value / decrypt_value
│   │   └── __init__.py        （空文件）
│   ├── models/operation_log.py OperationLog+LogService 的**重复副本**，无任何引用（见「已知坑」）
│   ├── migrations/            Alembic：env.py + versions/（基线 + 3 个增量）
│   ├── data/                  运行时目录：SQLite 数据库文件（gitignore）
│   ├── uploads/  exports/     运行时目录（gitignore）
│   └── test_image_access.py   独立诊断脚本（requests，非 pytest）
├── frontend/                   Nuxt 3 前端
│   ├── app.vue               ★ 根组件，仅 NuxtLayout + NuxtPage + 全局样式
│   ├── nuxt.config.ts        ★ Pinia 模块、runtimeConfig.public.apiBase
│   ├── layouts/default.vue   ★ 全站外壳：侧边导航、用户菜单、改密、角色判定
│   ├── pages/                路由即页面（见下表）
│   ├── components/AvatarUpload.vue 头像裁剪上传（cropperjs）
│   ├── plugins/axios.ts      ★ 创建 $api 实例、注入 Authorization、401 跳登录
│   ├── stores/               userStore / eventStore / cache / counter
│   ├── composables/          useUploadUrl / useUserSearch
│   ├── utils/dateUtils.ts    日期格式化
│   ├── types/index.d.ts      $api 类型声明与 *.vue 模块声明
│   ├── server/middleware/proxy-uploads.ts ★ Nitro 中间件：/uploads/** 原样反代后端
│   └── Dockerfile / package.json / pnpm-lock.yaml
├── docker-compose.yml        两服务编排（backend / frontend）
├── dev.ps1 / dev.bat          本地一键启动（注意：已在 .gitignore 中）
├── docs/PROJECT_GUIDE.md      本文件
└── README.md                  项目说明与部署指南（权威）
```

**主调用链路（读）**：浏览器 → `frontend/pages/**` → `plugins/axios.ts` 的 `$api` → `runtimeConfig.public.apiBase`（默认 `http://localhost:5000/api`）→ Flask 蓝图 `backend/routes/*.py` → `backend/models.py` → SQLite；图片/文件 URL 走 `/uploads/**`，由 Nitro 中间件原样反代。

**主调用链路（写/上传）**：`pages/purchases/[id].vue` → `POST /api/upload-file`（`routes/parse.py`）→ `storage_manager.upload_file()` 落盘 → `POST /api/parse-image`（GLM 视觉）或 `/api/parse-invoice`（PDF 文本）→ 返回结构化发票字段 → 用户确认后 `POST /api/events/<id>/records` 入库。

---

## 3. 核心模块说明


### 3.1 后端

| 模块                                   | 职责                                                                                                                                                                                                                                                                         | 对外接口                                                           | 依赖                                                        |                                                       |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------- |
| `app.py`                             | 应用工厂；CORS、JWT、Migrate 初始化；10 个蓝图注册；`/uploads/<path>` 与 `/api/uploads/<path>` 静态服务；启动时按 alembic_version 表存在与否自动 `upgrade / stamp`，由 `utils/schema_init.py: ensure_schema()` 统一处理（空库直接 `db.create_all()` 并 `stamp('head')`）；`_seed_admin_user()` 每次启动重置 admin 密码                                                                                        | `create_app()`                                                 | `config`、`models.db`、全部 `routes/*`、`utils.backup_service` |                                                       |
| `routes/events.py`                   | 项目是全系统的聚合根：CRUD + 成员角色 + 预算变更后调用 `recalc_event_stats()` 重算；`ensure_event_membership` 已下沉至 `utils/permissions.py`；`_normalize_event_value`/`_format_event_value` 处理 `extra_fields` JSON 扩展字段；**加入申请审核**：`create_join_request`（`auto` 模式当场通过、审核人记为管理员）/`get_join_requests`/`review_join_request`，权限判定 `utils.permissions.is_event_reviewer`，通过后由 `_grant_membership()` 落 `EventMember.joined_by`+`join_source`                                                                                                                         | 见 §5 接口表                                                       | `models`、`utils.operation_log`、`utils.permissions`、`utils.event_stats`                            |                                                       |
| `routes/purchase_records.py`         | 购买记录全链路；`transfer_purchase_record`/`batch_transfer_purchase_records` 在项目间迁移并重算预算；`re_parse_invoice` 触发二次 OCR；`get_presigned_url` 统一签发图片临时链接                                                                                                                                | 同上                                                             | `models`、`utils.storage`、`utils.operation_log`            |                                                       |
| `routes/invoices.py` / `vouchers.py` | 结构几乎同构（列表/创建/删除/更新/批量报销/下载），发票额外有 `approve_invoice`、`generate_preview`；凭证额外有 `check_file_md5` 秒传                                                                                                                                                                           | 同上                                                             | 同上                                                        |                                                       |
| `routes/parse.py`                    | PDF 转图（`PDFConverter` 已下沉至 `utils/pdf_converter.py`）→ GLM 识别或 `InvoiceParser` 文本兜底；\`/invoices/<file_key>/preview                                                                                                                                                                             | download\` 按 key 取文件                                           | 同上                                                        | `utils.storage`、`glm_vision_service`、`invoice_parser` |
| `routes/system.py`                   | 系统配置读写（`ai_model` / `ai_api_key`(加密) / `ai_api_url`）、备份列表与下载/恢复、备份配置（启用、频率、时间、保留数）、`check_update` 返回运维命令清单、`test_model`、`ai_summary`                                                                                                                                       | 同上                                                             | `utils.backup_service`、`crypto_utils`                     |                                                       |
| `routes/export.py`                   | 创建 `ExportTask` 后台线程执行 `ExportService.run_export`，前端轮询 `/export/status` 后 `/export/download`                                                                                                                                                                               | 同上                                                             | `utils.export_service`                                    |                                                       |
| `utils/storage.py`                   | 导入即初始化单例 `storage_manager`，按 `STORAGE_BACKEND` 选择 `LocalStorageManager` 或 `cos_manager`。**两实现需保持同名方法**：`generate_file_key/generate_avatar_key/upload_file/upload_file_from_bytes/upload_bytes/upload_avatar/download_file/get_presigned_url/delete_file/check_file_exists` | `storage_manager`                                              | `local_storage` / `cos_manager`                           |                                                       |
| `utils/glm_vision_service.py`        | 配置解析优先级：**DB(system_configs) > 环境变量**；`extract_invoice_info` 组装 base64 图 + prompt 调 GLM，`_parse_response` 归一化字段                                                                                                                                                            | `resolve_ai_model/api_key/api_url`、`GLMVisionService`          | `models.SystemConfig`、`utils.crypto_utils`                |                                                       |
| `utils/export_service.py`            | `_fetch_data` 汇总三类记录 → `_generate_excel` → `_download_and_save_image` 把票据图片嵌入 Excel → 合并 PDF → `_create_zip`；`check_cache` 命中已有产物直接返回                                                                                                                                      | `ExportService(app).run_export(task_id)`                       | `utils.storage`、openpyxl、fpdf                             |                                                       |
| `utils/backup_service.py`            | `BackupService`：`run_backup`（SQLite 在线备份 + 打包 uploads + 导出 system_configs JSON）、`restore_backup`、`list_backups`；`_import_legacy_pg_dump` 让旧版 PostgreSQL 备份包仍可恢复；`init_backup_service` 注册 APScheduler 并读 `backup_schedule_*` 配置；`recover_stale_backups` 把长期停在 `pending/running` 的僵尸记录标记失败（启动时无条件回收，接口/定时任务里按 `STALE_BACKUP_MINUTES=30` 超时回收），避免一条历史记录让备份永远返回 409 | `init_backup_service`、`get_backup_service`、`reschedule_backup` | `utils.legacy_pg_dump`、`crypto_utils`                          |                                                       |
| `utils/operation_log.py`             | `OperationLog` 模型 + `LogService.log/get_logs/delete_log(s)/get_action_types`；所有路由通过本地 import 调用                                                                                                                                                                            | `LogService`                                                   | `models.db`                                               |                                                       |
| `models.py`                          | `User/Event/EventMember/Invoice/Voucher/InvitationCode/PurchaseRecord/SystemConfig/ExportTask/BackupRecord/EventJoinRequest`；统一约定：`is_deleted` 软删、`extra_fields` JSON 扩展、`created_at/updated_at` 带时区、`_utcnow()`；**时间列用 `utils/db_types.UTCDateTime()`（不是 `db.DateTime(timezone=True)`）**；主键用 `BigIntPK`（SQLite 走 Integer 方言变体才能自增）；`Event.join_review_mode`（`auto`/`manual`）决定加入申请是否需人工审核，`EventMember.joined_by`/`join_source` 记录审核人与加入途径                                                                            | `db`、各 Model                                                   | SQLAlchemy                                                |                                                       |

### 3.2 前端

| 模块                                   | 职责                                                                                                                                                    | 关键点                                |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| `plugins/axios.ts`                   | 全站唯一 HTTP 出口：`baseURL = $config.public.apiBase`，请求拦截注入 `localStorage.token`，FormData 时删 Content-Type，401 强制跳 `/login`                                 | 改动 API 基址、鉴权头、错误处理都在这里             |
| `layouts/default.vue`                | 侧边导航 + 顶栏 + 用户信息/改密弹窗；按 `userType` 控制菜单可见性（`canManageUsers`/`canManageInvitationCodes`/`isAdmin`）                                                     | 新增页面入口同步改这里                        |
| `stores/userStore.ts`                | 登录态与用户资料在 `localStorage('user')` 的读写，`realName/userType/userRole/userId/initial` 计算属性                                                                 | 角色中文映射写在这里                         |
| `stores/eventStore.ts`               | 项目列表的**唯一数据源**：`fetchEvents/ensureLoaded/refreshAfterMutation/invalidateAndRefresh`，叠加 `stores/cache.ts` 缓存；getter `fullStats`/`totalStats`/`isStale`；**待审加入申请红点**：`fetchPendingJoinCounts()` 拉 `GET /events/join-requests/pending-summary`，写入 `pendingJoinCounts`/`pendingJoinTotal`，getter `pendingJoinCountFor(eventId)` 供项目卡片复用（拉过汇总接口后以它为准，避免列表数据过期红点不消失） | 任何项目相关页面都应通过它取数，不要各自 `GET /events`；任何会改变待审数量的动作（审核通过/驳回）后都要调 `fetchPendingJoinCounts()` |
| `stores/cache.ts`                    | 带 TTL 的 Map 缓存 + 命中率统计 + localStorage 持久化；`invalidateEventCache/invalidateInvoiceCache/invalidateUserCache`                                           | 改缓存时长改 `defaultExpiry`             |
| `pages/purchases/[id].vue`           | **全站最大文件（4122 行）**：项目详情 + 购买记录增删改 + 上传 + OCR 解析 + 转图预览 + 转移 + 报销                                                                                      | 核心链路，改动前先定位再动                      |
| `pages/events/[id]/members.vue`      | 人员管理：成员列表（含**加入时间 / 加入方式 / 审核人**）、添加/编辑/移除成员；`can_review_join` 为真时才渲染「加入申请」入口与待审数量角标                                                                            | 审核入口必须由后端 `can_review_join` 驱动，不要在前端硬编码角色                |
| `pages/events/[id]/join-requests.vue` | 加入申请审核页（`/events/<id>/join-requests`）：按 `pending/approved/rejected/全部` 筛选、通过（直接成为成员）/驳回（可填理由）；接口返回 403 时整页渲染「无权访问」，不显示任何申请数据                                 | 新增审核动作走 `POST .../review`，成功后必须 `loadRequests()` 刷新                   |
| `pages/settings/index.vue`           | 系统配置、AI 模型配置、备份/恢复、版本更新指引（管理员）                                                                                                                        | 与 `routes/system.py` 一一对应          |
| `server/middleware/proxy-uploads.ts` | Nitro 层把 `/uploads/**` 完整路径反代到后端（刻意不用 `routeRules.proxy`，因后者会剥掉 `/uploads` 前缀）                                                                        | 注释已说明，改动前先读                        |

---

## 4. 配置与外部依赖

### 4.1 环境变量（`backend/config.py` 读取，`.env` 覆盖）

| 变量                                                                             | 默认值                                                          | 作用                     |       |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------ | ---------------------- | ----- |
| `SECRET_KEY`                                                                   | `easy-invoice-mgr-secret-key`                                | Flask 签名密钥             |       |
| `JWT_SECRET_KEY`                                                               | `easy-invoice-mgr-jwt-secret`                                | JWT 签名（生产必须改）          |       |
| `DATABASE_URL`                                                                 | `sqlite:///<backend>/data/easy_invoice_mgr.sqlite`           | 数据库连接串；必须以 `sqlite:///` 开头，部署时由 `docker-compose.yml` 指向 `/app/data/...` |       |
| `JWT_ACCESS_TOKEN_EXPIRES`                                                     | 3600（代码内固定）                                                  | token 有效期（秒）           |       |
| `STORAGE_BACKEND`                                                              | `local`                                                      | `local`                | `cos` |
| `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_REGION`(ap-guangzhou) / `COS_BUCKET` | 空                                                            | COS 凭据，仅 cos 模式需要      |       |
| `GLM_API_KEY` / `GLM_MODEL`(GLM-4V-Flash) / `GLM_API_URL`                      | 空 / 默认                                                       | AI 兜底配置，**DB 配置优先**    |       |
| `CORS_ORIGINS`                                                                 | `http://localhost:3000,3001,127.0.0.1:3000,3001`             | 逗号分隔，`config.py` 解析为列表 |       |
| `ADMIN_PASSWORD`                                                               | `admin`                                                      | 每次启动强制重置 admin 密码      |       |
| `HOST_PROJECT_DIR`                                                             | 无                                                            | 容器内映射的项目目录，备份范围用       |       |

> `FERNET_KEY` 不是 `config.py` 变量，由 `backend/utils/crypto_utils.py` 直接读取，用于加密 `system_configs.ai_api_key` 和用户 `password_encrypted`；未设置时从 `SECRET_KEY` 派生。生产环境应显式设置为随机值并妥善备份，更换密钥会导致既有密文无法解密。

> **本地启动踩坑**：`backend/.env` 由 `app.py` 的 `load_dotenv()` 加载，优先级高于默认值。如果迁移前留下的 `.env` 里还有 `DATABASE_URL=postgresql://...`，`create_app()` 会直接抛 `数据库方言为 'postgresql'，本项目只支持 SQLite`——把那一行删掉或注释即可回到默认的 `backend/data/easy_invoice_mgr.sqlite`。可参照 `backend/.env.example` 重建该文件。`config.py` 只在 URL 以 `sqlite` 开头时才注入 `check_same_thread`/`timeout`，避免这些 SQLite 专用参数被传给其他方言驱动。

前端：`NUXT_PUBLIC_API_BASE`（`nuxt.config.ts` → `runtimeConfig.public.apiBase`，构建期注入，`docker-compose.yml` 作为 build arg 传入）。非本地部署必须设置，否则登录 Network Error。

### 4.2 数据库内配置（表 `system_configs`，键值对）

| config_key                  | 读取位置                                              | 说明                                                                |
| --------------------------- | ------------------------------------------------- | ----------------------------------------------------------------- |
| `ai_model`                  | `glm_vision_service.resolve_ai_model`、`system.py` | 模型名                                                               |
| `ai_api_key`                | 同上                                                | **加密存储**（`ENCRYPTED_KEYS = {'ai_api_key'}`，`crypto_utils` Fernet） |
| `ai_api_url`                | `resolve_ai_url`                                  | 推理接口地址                                                            |
| `backup_schedule_enabled`   | `backup_service._setup_schedule`                  | 定时备份开关（默认 'false'）                                                |
| `backup_schedule_frequency` | 同上                                                | 默认 `daily`                                                        |
| `backup_schedule_time`      | 同上                                                | 默认 `03:00`                                                        |
| `backup_retention_count`    | `backup_service` 清理逻辑                             | 保留份数                                                              |

### 4.3 外部服务调用点

| 服务                                                              | 调用位置                                             | 用途                                                    |
| --------------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------- |
| 智谱 GLM（`https://open.bigmodel.cn/api/paas/v4/chat/completions`） | `backend/utils/glm_vision_service.py`            | 发票图片识别、`system/ai-summary`                            |
| 腾讯云 COS                                                         | `backend/utils/cos_manager.py`                   | `STORAGE_BACKEND=cos` 时的文件存储                          |
| sqlite3 备份 API（进程内）                                          | `backend/utils/backup_service.py`、`utils/legacy_pg_dump.py` | 备份与恢复；旧版 PostgreSQL 备份包仍可导入                        |
| Docker CLI（子进程）                                                 | `backend/routes/system.py:check_update` 附近       | 仅返回命令文本供用户执行，不自动执行                                    |
| Docker 守护进程                                                     | `docker-compose.yml` 挂载 `/var/run/docker.sock`   | 供容器内 docker CLI 使用                                    |

---

## 5. 常见修改场景对照表

| 场景                           | 需改动的文件（相对路径）                                                                                                                                 | 关键函数 / 代码位置                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 新增一个 API 接口                  | `backend/routes/<模块>.py`                                                                                                                     | 在对应蓝图加 `@xxx_bp.route(...)` + 处理函数；若属新模块，还需在 `backend/app.py` `create_app()` 中 import 并 `register_blueprint`       |
| 修改已有接口的入参/出参                 | `backend/routes/<模块>.py` + `frontend/pages/<对应页>.vue`                                                                                        | 后端处理函数签名与 `jsonify` 载荷；前端调用处解构字段（**两端字段名必须同步，无类型校验**）                                                              |
| 新增数据库字段                      | `backend/models.py`（模型）→ 新建 `backend/migrations/versions/<rev>_xxx.py`（`down_revision` 指向当前 head `e5f6a7b8c9d0`） | 两处都要改：模型 + Alembic 迁移（SQLite 的 `ALTER COLUMN` 由 Flask-Migrate 默认的 `render_as_batch=True` 走批量重建表）                |
| 新增整张表                        | `backend/models.py` + Alembic 迁移                                                                                    | 同上                                                                                                                 |
| 改文件存储行为（key 规则、目录结构）         | `backend/utils/local_storage.py` **和** `backend/utils/cos_manager.py`                                                                        | 两边方法名必须一致，`utils/storage.py` 才能正常分派                                                                                |
| 切换/接入对象存储                    | `backend/utils/storage.py: _init_storage()`                                                                                                  | 新后端实现同名方法并在 `_init_storage` 注册                                                                                     |
| 改发票 AI 识别字段或 prompt          | `backend/utils/glm_vision_service.py`                                                                                                        | `_build_prompt()`、`_parse_response()`；文本兜底同步改 `utils/invoice_parser.py:_extract_invoice_data()`                    |
| 改 AI 模型 / 密钥                 | DB `system_configs`（页面 `frontend/pages/settings/index.vue`）优先，其次 `backend/config.py` 环境变量                                                    | `glm_vision_service.resolve_ai_*` 的优先级链                                                                            |
| 改导出内容或打包格式                   | `backend/utils/export_service.py`                                                                                                            | `_fetch_data`（取哪些字段）、`_generate_excel`、`_process_invoices`、`_create_zip`                                           |
| 改备份范围/保留策略                   | `backend/utils/backup_service.py`                                                                                                            | `run_backup`、`restore_backup`、`_setup_schedule`（读 `backup_schedule_*`）、`backup_retention_count`                    |
| 改角色可见菜单                      | `frontend/layouts/default.vue`                                                                                                               | 导航项的 `v-if`（`canManageUsers`/`canManageInvitationCodes`/`isAdmin`），角色映射在 `frontend/stores/userStore.ts` `userRole` |
| 新增前端页面                       | `frontend/pages/<path>.vue`（文件即路由）+ `frontend/layouts/default.vue` 加导航                                                                       | 动态路由用 `[id].vue` 约定（见 `pages/purchases/[id].vue`）                                                                  |
| 改全局 HTTP 行为（baseURL、鉴权、错误提示） | `frontend/plugins/axios.ts`                                                                                                                  | 拦截器两处                                                                                                              |
| 改 API 根地址                    | `frontend/nuxt.config.ts` `runtimeConfig.public.apiBase` 或环境变量 `NUXT_PUBLIC_API_BASE`                                                        | 生产需 `docker compose up -d --build` 重建                                                                              |
| 改图片访问路径                      | `frontend/server/middleware/proxy-uploads.ts` + `backend/app.py: serve_upload_file`                                                          | 前端中间件必须保留完整 `/uploads` 前缀                                                                                          |
| 新增操作日志埋点                     | `backend/routes/<模块>.py`                                                                                                                    | 直接调用 `utils.operation_log.log_operation()`（已全局导入，8 个路由文件共 35 处调用）。**不要**再自定义 `_log_operation` 私有函数                                                    |
| 改权限判定（学生能否操作某项目数据）           | `backend/utils/permissions.py`                                                                                                                 | `check_student_event_access(event_id, user)` 与 `ensure_event_membership(event_id, user_id)`；角色常量 `PRIVILEGED_USER_TYPES = ['admin','teacher','student_admin']`             |
| 改比赛加入审核规则                    | `backend/utils/permissions.py`（`is_event_reviewer` 谁能审）→ `backend/routes/events.py`（`create_join_request`/`review_join_request`）→ `frontend/pages/events/[id]/join-requests.vue`（审核页） | `Event.join_review_mode`：`manual` 待审、`auto` 提交即入；自动审核的审核人取 `permissions.resolve_auto_reviewer_id()`（管理员）           |
| 改初始管理员账号                     | `backend/app.py: _seed_admin_user()` + 环境变量 `ADMIN_PASSWORD`                                                                                 | 注意：**每次启动都会覆盖密码哈希与 `password_encrypted`**                                                                                                  |
| 改用户密码存储 / 管理员查看密码           | `backend/models.py`（`password_encrypted`）→ `backend/utils/crypto_utils.py`（`encrypt_password`/`decrypt_password`）→ `backend/routes/auth.py`（`register`、`change_password`、`get_user_passwords`、`reset_user_password`）→ `frontend/pages/users/index.vue` | 注册/改密/重置时同时写单向哈希与可逆密文；历史账号只能由管理员重置补密文；禁止把明文写入日志 |
| 加依赖                          | 后端 `backend/requirements.txt`；前端 `frontend/package.json`（用 pnpm，勿混用 npm）                                                                     | —                                                                                                                  |

---

## 6. 接口全表（后端蓝图前缀见括号）

> 鉴权：除 `/api/auth/register`、`/api/auth/login` 外，均需 `Authorization: Bearer <token>`。

**auth（`/api/auth`）**：POST `/register`、`/login`｜GET `/users`、`/users/<id>`、`/users/passwords`｜PUT `/users/<id>`、`/users/<id>/password`｜DELETE `/users/<id>`｜POST `/users/<id>/reset-password`｜GET `/avatar`、POST `/avatar/upload`、DELETE `/avatar`

> 管理员密码相关：GET `/users/passwords` 与 POST `/users/<id>/reset-password` 仅 `admin` 可用；前者返回明文列表（历史无密文返回 `available=false`），后者生成 12 位随机密码并只返回一次，均写操作日志且响应带 `Cache-Control: no-store`。

**events（`/api`）**：POST/GET `/events`｜GET/PUT/DELETE `/events/<id>`｜GET/POST `/events/<id>/members`｜PUT/DELETE `/events/<id>/members/<user_id>`｜GET `/events/stats/user-summary`｜**加入申请**：POST/GET `/events/<id>/join-requests`（GET 支持 `?status=pending|approved|rejected`）、POST `/events/<id>/join-requests/<request_id>/review`（`{action:'approve'|'reject', reject_reason?}`）、GET `/events/join-requests/pending-summary`（`{total, by_event}`，只统计当前用户有权审核的赛事，供导航栏/项目卡片红点）

> 加入申请红点：`GET /events` 每个赛事带 `pending_join_request_count`（仅审核人可能非 0）；`GET /events/join-requests/pending-summary` 给全局红点。`layouts/default.vue` 在挂载、路由切换、切回标签页与每 60 秒轮询刷新，「项目管理」菜单项与「人员管理」按钮据此显示红点。

> 加入申请权限：`GET /join-requests` 与 `review` 仅**比赛负责人 / 指导老师 / admin**（`utils.permissions.is_event_reviewer`）可用，其他人返回 403，前端不渲染入口；`POST /events/<id>/join-requests` 任何未加入且比赛进行中的用户可调，`join_review_mode='auto'` 时当场成为成员。

**purchase_records（`/api`）**：GET/POST `/events/<id>/records`｜PUT/DELETE `/records/<id>`｜POST `/records/<id>/transfer`、`/records/batch-transfer`、`/records/<id>/reimburse`、`/records/<id>/re-parse-invoice`｜GET `/records/<id>/download-invoice`、`/records/<id>/preview-invoice`

**invoices（`/api`）**：GET/POST `/invoices`｜PUT/DELETE `/invoices/<id>`｜POST `/invoices/<id>/approve`、`/invoices/batch-reimburse`、`/invoices/<id>/reimburse`｜GET `/invoices/<id>/preview`、`/invoices/<id>/download`｜POST `/invoices/<id>/generate-preview`

**vouchers（`/api`）**：GET/POST `/vouchers`｜PUT/DELETE `/vouchers/<id>`｜GET `/vouchers/<id>/download`、`/check-file-md5`｜POST `/vouchers/batch-reimburse`

**parse（`/api`）**：POST `/upload-file`、`/parse-image`、`/parse-invoice`｜GET `/invoices/<file_key>/preview`、`/download`

**invitation_codes（`/api`）**：GET/POST `/invitation-codes`｜POST `/invitation-codes/verify`、`/invitation-codes/<id>/toggle`｜DELETE `/invitation-codes/<id>`

**export（`/api`）**：POST `/events/<id>/export`｜GET `/events/<id>/export/status`、`/export/download`

**system（`/api/system`）**：GET/PUT `/config`｜GET `/check-update`｜POST `/backup`、GET `/backups`、`/backup/<id>/download`、DELETE `/backup/<id>`、POST `/backup/restore/<id>`、`/backup/restore/upload`、GET/PUT `/backup/config`｜POST `/test-model`、`/ai-summary`

**operation_logs（`/api/operation-logs`，仅 admin）**：GET ``（列表）、GET `/action-types`、DELETE ``

---

## 7. 代码约定

| 方面     | 约定                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 后端分层   | `routes/`（HTTP + 权限 + 日志）→ `utils/`（业务服务，无 HTTP 语义）→ `models.py`（ORM）。路由内禁止写大段业务逻辑，应下沉到 `utils/`                                              |
| 后端命名   | 蓝图 `<模块>_bp`，变量 `xxx_bp`；处理函数 `动词_名词`（`create_event`、`batch_reimburse_invoices`）；私有辅助 `_` 前缀（`_invoice_values_equal`、`_format_invoice_value`）；日志与权限已上提为 `utils.operation_log.log_operation` / `utils.permissions.*`  |
| 后端导入约定 | `LogService`、`ExportService`、`backup_service` 等**在函数体内 import**（避免循环引用与启动期副作用），见各路由文件                                                         |
| 错误处理   | 路由统一 `try/except` + `logger.error(..., exc_info=True)` + `return jsonify({'code':..., 'message':...}), status`；权限失败返回 403                     |
| 日志     | `logging.getLogger(__name__)`；app 启动日志带 emoji 标记（📷/✅/❌/⚠️），便于 grep                                                                           |
| 响应约定   | 统一 `{code, message, data}` 三段式（见 `routes/operation_logs.py`、`routes/system.py`）；部分旧接口直接返回裸对象，新增时优先用三段式                                        |
| 软删除    | 所有业务表统一 `is_deleted` 布尔位，查询需过滤；`audit_logs` 表已定义但代码中未实际使用                                                                                     |
| 时间     | 一律 `UTCDateTime()`（`backend/utils/db_types.py`，落库为 naive UTC、读出为 aware UTC）+ `datetime.now(timezone.utc)`；**不要**再用 `db.DateTime(timezone=True)`，SQLite 会丢掉时区导致比较异常                                                                                             |
| 扩展字段   | 各表 `extra_fields` JSON，配套 `_normalize_*_value` / `_format_*_value` / `*_values_equal` 做展示与变更比对（审计日志 diff）                                     |
| 前端命名   | 页面文件 kebab/flat 小写（`operation-logs.vue`），动态段用 `[id].vue`；store 用 `xxxStore.ts` 定义式或 setup 式均可（`userStore` setup 式，`eventStore`/`cache` 选项式并存） |
| 前端数据获取 | **优先走 `eventStore`**，其次 `useUserSearch`；禁止在页面里裸调 `GET /events`（会绕过缓存导致数据不一致）                                                                  |
| 前端样式   | 页面内 `<style scoped>` 手写 CSS + 响应式断点（768px / 509px 等），无 UI 框架；全局重置在 `app.vue`                                                                  |
| 类型     | `nuxt.config.ts` 开启 `strict: true` 但 `typeCheck: false`（不阻塞构建）；`types/index.d.ts` 声明 `$api`                                                   |
| 测试     | **无自动化测试框架**。`backend/test_image_access.py` 是 requests 诊断脚本；`frontend` 无测试。README 的「未来计划」提到要补测试体系                                             |
| 日志文件   | `backend/_verify_*.log`、`frontend/_verify_*.log`、`frontend/pnpm-install*.log` 是本地遗留产物，已被 `.gitignore` 的 `*.log` 忽略                            |

---

## 8. 已知坑与技术债

| 类别      | 内容                                                                                                                                                                                                                                             |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 重复文件    | `backend/models/operation_log.py` 与 `backend/utils/operation_log.py` 是同一实现的两份副本（前者少 `to_dict()` 与部分 action_types）。**全仓无任何模块 import `models.operation_log`**，实际生效的是 `utils/operation_log.py`。改日志逻辑请只改 utils 那份；`models/operation_log.py` 可视为死代码 |
| 历史脚本    | `backend/migrate.py` 等 PostgreSQL 时代的硬编码连接串脚本已在 SQLite 迁移中删除；`utils/legacy_pg_dump.py` 保留只为解析旧备份包                                                                                                    |
| 启动副作用   | `app.py: _seed_admin_user()` **每次启动都用 `ADMIN_PASSWORD` 覆盖 admin 的密码哈希与 `password_encrypted`**，手工改库会被覆盖                                                                                                                                                                |
| 迁移语义    | Alembic 版本链为 基线 `5cd03e0a4de7` → `a1b2c3d4e5f6`（backup_records）→ `c3d4e5f6a7b8`（cannot_invoice 列）→ `d4e5f6a7b8c9`（password_encrypted，head）。空库启动时 `utils/schema_init.py: ensure_schema()` 走 `db.create_all()` + `stamp('head')`；已有 `alembic_version` 的库执行 `upgrade()`                                                       |
| 表定义漂移   | `utils/legacy_pg_dump.py` 会忽略旧 dump 中模型不存在的表（如历史 `audit_logs`）和列，只灌模型已定义的字段，并打印跳过清单                                                                                                                                         |
| 静态文件路由  | `app.py: serve_upload_file` 内使用了 `jsonify` 但该函数所在文件未 import `jsonify`（仅 import 了 `send_from_directory/send_file/request`）——错误分支会二次抛 `NameError`                                                                                                |
| 上传路由鉴权  | `parse.py` 的 `/upload-file` 使用 `@cross_origin` 但**未加 `@jwt_required`**，是唯一免鉴权的写接口                                                                                                                                                              |
| 前端代理    | `nuxt.config.ts` 的 `routeRules.proxy` 会剥掉 `/uploads` 前缀（注释已记录），故改用 `server/middleware/proxy-uploads.ts`；改代理时勿退回 routeRules                                                                                                                     |
| 超大文件    | `pages/purchases/[id].vue` 4122 行、`pages/projects/index.vue` 1982 行、`pages/settings/index.vue` 2068 行，混合了列表/表单/弹窗/预览/上传逻辑。修改前先用 grep 定位，避免整文件重写                                                                                                |
| 本地未入库文件 | `dev.ps1` / `dev.bat` 出现在 `.gitignore` 末尾，新克隆的仓库**拿不到本地启动脚本**，需按 README 手工起服务或 `docker compose up -d`                                                                                                                                          |
| 产物目录    | `backend/exports/` 里存在历史导出 zip（`睿抗2026_6_20260630141740.zip`），已被 gitignore；`backend/uploads/` 同理                                                                                                                                               |
| 密码可逆存储  | `users.password_encrypted` 使用 Fernet 可逆加密（`utils/crypto_utils.encrypt_password/decrypt_password`），密钥来自 `FERNET_KEY` 或 `SECRET_KEY`，更换密钥会导致旧密文全部无法解密；登录仍只校验 `password_hash`。历史账号（除由 `ADMIN_PASSWORD` 种子写入的 admin 外）该列为空，管理员查看时显示“不可恢复”，需用“重置”生成新密码后才能查看。`ADMIN_PASSWORD` 每次启动会同时覆盖 admin 的哈希与密文 |
| 数据库驱动    | 项目已迁移到 SQLite（Python 内置驱动，无额外依赖）。`backend/config.py` 要求 `DATABASE_URL` 以 `sqlite:///` 开头，并统一注入 `SQLite PRAGMA`（WAL / `foreign_keys=ON` / busy_timeout）；SQLite 不支持 `ALTER COLUMN`，改字段必须走 Alembic batch 迁移 |

---

## 9. 增量维护指引

1. **改动路由接口** → 更新 §3 对应模块的接口说明与 §6 接口表。
2. **新增/删除文件** → 更新 §2 目录树与 §5 场景表。
3. **新增环境变量或 system_configs 键** → 更新 §4.1 / §4.2。
4. **发现新坑** → 追加 §8 一行，注明权威位置。
5. **复核而不改动**：若 HEAD 与上次统计一致且 `git status --porcelain` 源码区为空，只需把页脚「复核于」顺延，**不要重写内容**。
6. 数字口径保持一致：行数用「实际行数（含末行）」脚本产出，勿手工估算。

*统计于 2026-10-11（HEAD `fd8a456`）。复核于 2026-10-20（管理员密码查看功能）。*
