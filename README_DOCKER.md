# EasyInvoiceMgr Docker 部署指南

## 环境要求

- **Docker** 20.10+  
- **Docker Compose** 2.0+  
- 可用磁盘空间 ≥ 2GB  

## 快速开始

```bash
# 1. 克隆项目（如未克隆）
git clone <repo-url> && cd EasyInvoiceMgr

# 2. 构建并启动所有服务
docker compose up -d --build

# 3. 查看服务状态
docker compose ps

# 4. 查看日志
docker compose logs -f
```

启动后访问：
- 前端：http://localhost:3000
- 后端 API：http://localhost:5000/api
- 默认管理员：`admin` / `admin`

## 服务架构

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `postgres` | postgres:15-alpine | 5432 | PostgreSQL 数据库 |
| `backend` | 本地构建 | 5000 | Flask API 服务 |
| `frontend` | 本地构建 | 3000 | Nuxt 3 前端 |

## 构建与运行

### 首次构建

```bash
docker compose build --no-cache
docker compose up -d
```

### 仅重建某个服务

```bash
docker compose build backend
docker compose up -d backend
```

### 停止服务

```bash
docker compose down           # 停止并保留数据卷
docker compose down -v        # 停止并删除所有数据（慎用）
```

## 环境变量

在项目根目录创建 `.env` 文件（可选，默认值适用于本地开发）：

```env
# 管理员密码
ADMIN_PASSWORD=admin

# 前端 API 地址（构建时注入）
NUXT_PUBLIC_API_BASE=http://localhost:5000/api

# CORS 允许的前端地址
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# JWT 密钥（生产环境务必修改）
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-production-jwt-secret-key-32bytes
```

### 生产环境部署

在服务器上部署时，修改 `.env` 中的地址为实际域名：

```env
NUXT_PUBLIC_API_BASE=https://api.yourdomain.com/api
CORS_ORIGINS=https://yourdomain.com
ADMIN_PASSWORD=<strong-password>
SECRET_KEY=<random-64-char-string>
JWT_SECRET_KEY=<random-64-char-string>
```

然后重新构建前端（API 地址在构建时注入）：

```bash
docker compose build --no-cache frontend
docker compose up -d
```

## 数据持久化

| 数据卷 | 内容 | 说明 |
|--------|------|------|
| `pgdata` | PostgreSQL 数据 | 数据库文件，删除即丢失所有数据 |
| `uploads` | 上传文件 | 发票、凭证图片、头像 |
| `exports` | 导出文件 | Excel、PDF 导出结果（30分钟自动过期清理） |

## 数据库

- 首次启动时自动执行 `backend/sql/base.sql` 创建表结构和索引
- 管理员账户由应用启动时自动创建并设置密码哈希
- 数据库默认连接：`postgresql://postgres:root@localhost:5432/easy_invoice_mgr`

### 连接数据库

```bash
# 通过容器
docker compose exec postgres psql -U postgres -d easy_invoice_mgr

# 通过本地 psql（如果安装）
psql -h localhost -U postgres -d easy_invoice_mgr
```

## 常见问题

### Q: 前端页面空白或 API 请求失败？

检查 CORS 配置。默认 `CORS_ORIGINS` 为 `http://localhost:3000`。如果通过其他地址访问前端，需要更新 `.env` 中的 `CORS_ORIGINS` 并重启后端。

### Q: 登录失败（用户名或密码错误）？

容器首次启动时会自动重置 admin 密码为 `ADMIN_PASSWORD` 环境变量的值（默认 `admin`）。查看后端日志确认：

```bash
docker compose logs backend | grep "管理员"
```

### Q: 端口冲突？

修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8080:3000"   # 将前端映射到 8080
  - "8081:5000"   # 将后端映射到 8081
```

同时更新 `NUXT_PUBLIC_API_BASE` 和 `CORS_ORIGINS`。

### Q: 如何备份数据？

```bash
# 备份数据库
docker compose exec postgres pg_dump -U postgres easy_invoice_mgr > backup.sql

# 备份上传文件
docker compose cp uploads:/app/uploads ./backup_uploads

# 恢复
docker compose exec -T postgres psql -U postgres -d easy_invoice_mgr < backup.sql
```

### Q: PyMuPDF 安装失败？

Dockerfile 已包含 `mupdf-tools` 系统依赖。如仍有问题，尝试：
```bash
docker compose build --no-cache backend
```

## 切换到腾讯云 COS 存储

```env
STORAGE_BACKEND=cos
COS_SECRET_ID=your-secret-id
COS_SECRET_KEY=your-secret-key
COS_REGION=ap-guangzhou
COS_BUCKET=your-bucket-name
```

重启后端即可，无需修改代码。

## 容器安全管理

- 非 root 用户运行（backend/frontend 使用 slim 镜像，需额外配置）
- PostgreSQL 端口（5432）仅建议在开发环境暴露到宿主机
- 生产环境建议在 `docker-compose.yml` 中注释掉 postgres 的 ports 映射
- 定期更新基础镜像：`docker compose pull`
