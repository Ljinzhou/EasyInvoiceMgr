# EasyInvoiceMgr - 赛事发票管理系统

## 项目描述

EasyInvoiceMgr 是一款面向高校和科研机构的赛事/活动发票管理系统，旨在简化和规范化赛事经费的报销流程。系统支持用户管理、赛事管理、发票上传与智能识别、凭证管理、预算跟踪等功能，帮助团队高效管理赛事财务，提升报销效率和透明度。

## 主要功能

### 用户与权限管理
- 支持多种用户角色：管理员(Admin)、教师(Teacher)、学生管理员(Student Admin)、普通学生(Student)
- 基于邀请码的用户注册机制
- JWT 认证的 API 访问控制
- 完整的用户信息管理和账户状态控制

### 赛事管理
- 创建和管理赛事活动
- 设置赛事预算和报销额度
- 赛事成员管理（添加、移除、角色分配）
- 赛事状态跟踪（进行中、已结束）
- 上传时间窗口控制

### 发票管理
- 发票图片上传（支持本地存储和腾讯云COS）
- 基于 OCR 的发票智能识别（支持发票号、金额、日期等字段自动提取）
- 发票审核流程（提交、审核、批准/拒绝）
- 发票状态跟踪（待审核、已批准、已拒绝、已报销）
- 发票统计报表（数量、金额、状态分布）

### 凭证管理
- 购物凭证上传和管理
- 购买渠道和日期记录
- 与发票关联管理

### 采购记录
- 完整的采购流程记录
- 支持有无发票的状态标记
- 报销状态跟踪

## 技术架构

### 前端技术栈
- **框架**: Nuxt 3 (Vue 3)
- **状态管理**: Pinia
- **HTTP 客户端**: Axios
- **日期处理**: dayjs
- **文件导出**: file-saver
- **语言**: TypeScript

### 后端技术栈
- **框架**: Flask 3.0
- **认证**: Flask-JWT-Extended
- **ORM**: SQLAlchemy + Flask-SQLAlchemy
- **数据库**: PostgreSQL
- **文件存储**: 腾讯云COS（可选本地存储）
- **OCR 识别**: cnocr + PDF2image

### 数据库设计
- **users**: 用户信息表
- **events**: 赛事信息表
- **event_members**: 赛事成员关联表
- **invoices**: 发票信息表
- **vouchers**: 凭证信息表
- **purchase_records**: 采购记录表
- **invitation_codes**: 邀请码表
- **audit_logs**: 审核日志表

## 项目结构

```
EasyInvoiceMgr/
├── backend/                    # Flask 后端服务
│   ├── routes/                 # API 路由模块
│   │   ├── auth.py            # 用户认证接口
│   │   ├── events.py          # 赛事管理接口
│   │   ├── invoices.py        # 发票管理接口
│   │   ├── vouchers.py        # 凭证管理接口
│   │   ├── purchase_records.py # 采购记录接口
│   │   ├── invitation_codes.py # 邀请码接口
│   │   └── parse.py           # OCR 解析接口
│   ├── utils/                  # 工具模块
│   │   ├── cos_manager.py     # 腾讯云COS管理
│   │   ├── glm_vision_service.py # 视觉服务
│   │   └── invoice_parser.py  # 发票解析工具
│   ├── sql/                    # 数据库脚本
│   │   ├── base.sql           # 基础表结构
│   │   ├── migration_purchase_records.sql # 采购记录迁移
│   │   └── reset_database.sql  # 数据库重置脚本
│   ├── app.py                 # Flask 应用入口
│   ├── config.py              # 配置文件
│   ├── models.py              # 数据模型
│   └── requirements.txt        # Python 依赖
├── frontend/                   # Nuxt 3 前端应用
│   ├── pages/                  # 页面组件
│   │   ├── login.vue          # 登录页
│   │   ├── register.vue       # 注册页
│   │   ├── dashboard.vue      # 管理面板
│   │   ├── events/            # 赛事相关页面
│   │   ├── purchases/         # 采购记录页面
│   │   └── users/             # 用户管理页面
│   ├── components/             # 公共组件
│   ├── layouts/                # 布局组件
│   ├── stores/                 # Pinia 状态管理
│   ├── plugins/                # Nuxt 插件
│   ├── types/                  # TypeScript 类型定义
│   └── package.json           # 前端依赖配置
└── README.md                   # 项目说明文档
```

## 部署指南

### 环境要求

- **Python**: 3.9+
- **Node.js**: 18+
- **PostgreSQL**: 14+
- **pnpm**: 8+ (前端包管理)

### 后端部署

1. **克隆项目并进入后端目录**
   ```bash
   cd backend
   ```

2. **创建 Python 虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   .\venv\Scripts\activate   # Windows
   ```

3. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   
   创建 `.env` 文件或设置系统环境变量：
   ```bash
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret-key
   DATABASE_URL=postgresql://postgres:root@localhost/easy_invoice_mgr
   
   # 腾讯云COS配置（可选，用于文件存储）
   COS_SECRET_ID=your-cos-secret-id
   COS_SECRET_KEY=your-cos-secret-key
   COS_REGION=ap-guangzhou
   COS_BUCKET=your-bucket-name
   ```

5. **初始化数据库**
   
   使用 PostgreSQL 客户端执行 SQL 脚本：
   ```bash
   psql -U postgres -d easy_invoice_mgr -f sql/base.sql
   ```

6. **启动后端服务**
   ```bash
   python app.py
   ```
   
   后端服务将在 `http://localhost:5000` 启动

### 前端部署

1. **进入前端目录**
   ```bash
   cd frontend
   ```

2. **安装前端依赖**
   ```bash
   pnpm install
   ```

3. **启动开发服务器**
   ```bash
   pnpm dev
   ```
   
   前端应用将在 `http://localhost:3000` 启动

### 生产环境构建

**前端构建**
```bash
cd frontend
pnpm build
pnpm preview
```

**后端部署**
- 建议使用 Gunicorn 或 uWSGI 作为生产 WSGI 服务器
- 配置 Nginx 作为反向代理

## API 接口

详细 API 接口文档请参考 [service-api-documentation.md](backend/service-api-documentation.md)

### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录

### 赛事接口
- `GET /api/events` - 获取赛事列表
- `POST /api/events` - 创建赛事
- `GET /api/events/:id` - 获取赛事详情
- `PUT /api/events/:id` - 更新赛事信息

### 发票接口
- `POST /api/invoices` - 上传发票
- `GET /api/invoices` - 获取发票列表
- `PUT /api/invoices/:id/review` - 审核发票

### 凭证接口
- `POST /api/vouchers` - 上传凭证
- `GET /api/vouchers` - 获取凭证列表

## 数据库初始化

系统默认管理员账户：
- **用户名**: admin
- **密码**: admin

> ⚠️ **安全提示**: 请在生产环境中务必修改默认管理员密码！

## 致谢

### 开源项目

本项目使用了以下优秀的开源项目，感谢各位作者的贡献：

- **Flask** - 轻量级 Python Web 框架
- **Vue 3** - 渐进式 JavaScript 框架
- **Nuxt 3** - 基于 Vue 3 的全栈框架
- **SQLAlchemy** - Python SQL 工具包和 ORM
- **cnocr** - 中文 OCR 库
- **腾讯云 COS SDK** - 对象存储服务 SDK
- **Pinia** - Vue 状态管理库

### 技术支持

- 发票 OCR 识别技术支持
- 腾讯云对象存储服务

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，请通过项目仓库提交 Issue。
