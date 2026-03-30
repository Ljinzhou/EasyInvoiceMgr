# EasyInvoiceMgr 项目说明

## 项目结构

```
EasyInvoiceMgr/
├── backend/                 # 后端代码
│   ├── routes/             # 路由文件
│   │   ├── auth.py        # 认证路由
│   │   └── events.py      # 赛事路由
│   ├── sql/               # SQL文件
│   │   └── base.sql       # 数据库结构
│   ├── app.py             # Flask应用主文件
│   ├── config.py          # 配置文件
│   ├── models.py          # 数据库模型
│   ├── requirements.txt   # Python依赖
│   └── .env              # 环境变量
└── frontend/              # 前端代码
    ├── pages/            # 页面文件
    │   ├── login.vue    # 登录页面
    │   └── events/
    │       └── create.vue # 创建比赛页面
    ├── plugins/          # 插件
    │   └── axios.ts     # Axios配置
    └── nuxt.config.ts   # Nuxt配置
```

## 后端设置

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 创建数据库

首先，在PostgreSQL中创建数据库：

```sql
CREATE DATABASE easy_invoice_mgr;
```

然后执行SQL文件创建表结构：

```bash
psql -U postgres -d easy_invoice_mgr -f sql/base.sql
```

### 3. 配置环境变量

`.env` 文件已创建，包含以下配置：

```
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=jwt-secret-key-here
DATABASE_URL=postgresql://postgres:root@localhost/easy_invoice_mgr
```

### 4. 运行后端服务

```bash
python app.py
```

后端服务将在 `http://localhost:5000` 运行。

## 前端设置

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 运行前端服务

```bash
npm run dev
```

前端服务将在 `http://localhost:3000` 运行。

## 使用说明

### 1. 登录

1. 访问 `http://localhost:3000/login`
2. 使用默认管理员账户登录：
   - 用户名：`admin`
   - 密码：`admin`

### 2. 创建比赛

1. 登录成功后，自动跳转到创建比赛页面
2. 填写比赛信息：
   - 比赛名称（必填）
   - 比赛描述（可选）
   - 比赛类别（可选）
   - 比赛地点（可选）
   - 开始时间（必填）
   - 结束时间（必填）
   - 上传开始时间（可选）
   - 上传结束时间（可选）
   - 总预算（可选）
   - 负责人ID（可选）
3. 点击"创建比赛"按钮提交

## API接口

### 认证接口

- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/users/{user_id}` - 获取用户信息

### 赛事接口

- `POST /api/events` - 创建比赛
- `GET /api/events` - 获取比赛列表
- `GET /api/events/{event_id}` - 获取比赛详情

## 注意事项

1. 确保PostgreSQL服务正在运行
2. 确保数据库连接配置正确
3. 默认管理员账户密码为admin，请在生产环境中修改
4. 前端和后端服务需要同时运行
