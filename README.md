# EasyInvoiceMgr - 发票管理系统

为学校AI技术研究社团（机器人实验室）开发的发票管理程序，实现发票便捷管理，提高报销处理效率。

## 项目概述

### 背景

本项目专为学校AI技术研究社团——机器人实验室设计，旨在解决社团活动经费管理中发票管理繁琐、报销流程复杂等问题。通过数字化管理方式，实现发票的便捷上传、智能识别、状态跟踪以及自动化报销流程。

**本项目完全通过 Vibe Coding 开发完成。**

### 主要功能

- **用户管理**：支持学生、教师、管理员等多种角色，提供邀请码注册机制
- **项目管理**：创建和管理科研项目/活动，设定预算，跟踪支出
- **发票管理**：上传发票图片或PDF文件，智能识别发票信息，自动提取关键数据
- **购买记录**：记录购物明细，关联发票，支持补录发票信息
- **报销审核**：支持多级审核流程，实时跟踪报销状态
- **数据导出**：支持Excel、PDF等多种格式导出，便于财务对账
- **预算管理**：实时跟踪项目预算使用情况，自动计算剩余金额

## 技术栈

**后端**：Flask + SQLAlchemy + PostgreSQL/SQLite + JWT + 腾讯云COS

**前端**：Nuxt 3 + Vue 3 + Pinia + Axios

**智能服务**：GLM-4.6V-Flash（智谱AI发票识别）+ PyMuPDF + cnocr

**数据处理**：Pandas + OpenPyXL + PyPDF2 + ReportLab

## 未来计划

- **Salvo框架重构**：计划使用基于Rust的高性能Web框架Salvo重构后端代码，保持API兼容的同时提升性能、增强类型安全性和异步支持
- **与astrbot对接**：实现发票管理的机器人交互
- **自动化测试完善**：建立完整的测试体系，确保代码质量
- **监控和日志系统**：引入监控和日志系统，便于问题排查和系统维护
- **邮件/短信通知功能**：支持关键操作的即时通知
- **缓存优化**：引入Redis缓存热点数据，减少数据库查询压力
- **数据库优化**：添加索引优化查询性能，使用数据库连接池
- **批量操作优化**：支持更大规模的批量上传、批量审核
- **审计日志**：记录关键操作日志，便于问题追溯和安全审计
- **数据统计分析**：增加仪表盘数据可视化，支持自定义报表
- **权限细分**：细化角色权限，支持更灵活的权限配置
- **API限流与防护**：防止恶意请求，保障服务稳定性
- **文档自动化**：使用Swagger/OpenAPI自动生成API文档

## Docker 一键部署

以下教程假设你有一台已安装 Docker 的服务器（Linux 推荐，Windows/macOS 同样适用）。

### 1. 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- Git

### 2. 克隆仓库

```bash
git clone https://github.com/Ljinzhou/EasyInvoiceMgr.git
cd EasyInvoiceMgr
```

### 3. 配置环境变量

创建 `.env` 文件（直接复制以下内容后根据实际情况修改）：

```bash
# ========== 必填 ==========

# 你的服务器 IP 或域名（如 http://192.168.1.100:3000 或 https://invoice.example.com）
# 仅前端访问地址需要指定端口，后端地址固定为 http://your-server-ip:5000/api
SERVER_URL=http://localhost:3000
BACKEND_URL=http://localhost:5000/api

# 管理员初始密码（首次部署后建议登录系统修改）
ADMIN_PASSWORD=admin

# ========== 强烈建议修改 ==========

# 后端密钥（请替换为随机字符串）
SECRET_KEY=change-me-to-a-random-string
JWT_SECRET_KEY=change-me-to-another-random-string

# 数据库密码（需与下方的 POSTGRES_PASSWORD 一致）
DB_PASSWORD=root

```

完整的 `.env` 文件参考：

```bash
# 服务器访问地址
SERVER_URL=http://localhost:3000
BACKEND_URL=http://localhost:5000/api

# 管理员密码
ADMIN_PASSWORD=admin

# 后端密钥
SECRET_KEY=your-random-secret-key
JWT_SECRET_KEY=your-random-jwt-key

# 数据库
DB_PASSWORD=root

# CORS 允许的前端来源（通常与 SERVER_URL 一致，可逗号分隔多个）
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# 前端构建时注入的 API 地址（通常与 BACKEND_URL 一致）
NUXT_PUBLIC_API_BASE=http://localhost:5000/api
```

### 4. 启动服务

```bash
# 构建镜像并启动所有服务（首次构建需要几分钟下载依赖）
docker compose up -d --build

# 查看启动日志，确认无报错
docker compose logs -f
```

等待看到类似以下日志说明启动成功：

```
backend   |  * Running on http://0.0.0.0:5000
frontend  |  Listening on http://0.0.0.0:3000
```

### 5. 访问系统

- **前端页面**：浏览器打开 `http://<你的服务器IP>:3000`
- **管理员登录**：用户名 `admin`，密码为你设置的 `ADMIN_PASSWORD`（默认 `admin`）

### 6. 部署到外网服务器

如果你将项目部署到云服务器上，需要将 `localhost` 替换为服务器的实际 IP 或域名：

**场景 A：通过 IP 访问**

```bash
SERVER_URL=http://192.168.1.100:3000
BACKEND_URL=http://192.168.1.100:5000/api
CORS_ORIGINS=http://192.168.1.100:3000,http://127.0.0.1:3000
NUXT_PUBLIC_API_BASE=http://192.168.1.100:5000/api
```

修改后需要重新构建前端（因为 `NUXT_PUBLIC_API_BASE` 是构建时注入的）：

```bash
docker compose up -d --build frontend
```

**场景 B：通过域名 + Nginx 反向代理访问**

`.env` 中填写实际域名：

```bash
SERVER_URL=https://invoice.example.com
BACKEND_URL=https://invoice.example.com/api
CORS_ORIGINS=https://invoice.example.com
NUXT_PUBLIC_API_BASE=https://invoice.example.com/api
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name invoice.example.com;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 上传文件
    location /uploads/ {
        proxy_pass http://127.0.0.1:5000/uploads/;
    }
}
```

### 服务架构

| 服务         | 端口   | 说明                |
| ---------- | ---- | ----------------- |
| `postgres` | 5432 | PostgreSQL 15 数据库 |
| `backend`  | 5000 | Flask API 服务      |
| `frontend` | 3000 | Nuxt 3 前端应用       |

### 数据持久化与备份

所有持久化数据存储在 Docker 命名卷中，`docker compose down` 不会删除：

```bash
# 备份所有数据卷
docker run --rm -v easyinvoicemgr_pgdata:/data -v $(pwd)/backup:/backup alpine tar czf /backup/pgdata-$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v easyinvoicemgr_uploads:/data -v $(pwd)/backup:/backup alpine tar czf /backup/uploads-$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v easyinvoicemgr_exports:/data -v $(pwd)/backup:/backup alpine tar czf /backup/exports-$(date +%Y%m%d).tar.gz -C /data .

# 恢复数据卷（以 pgdata 为例）
docker run --rm -v easyinvoicemgr_pgdata:/data -v $(pwd)/backup:/backup alpine tar xzf /backup/pgdata-20260509.tar.gz -C /data
```

### 常用运维命令

```bash
# 查看各服务状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 仅重启某个服务
docker compose restart backend
docker compose restart frontend

# 代码更新后重新构建
git pull
docker compose up -d --build

# 仅重建后端（前端无变更时更快）
docker compose up -d --build backend

# 进入容器排查问题
docker compose exec backend bash
docker compose exec frontend sh

# 停止服务
docker compose down

# 停止并删除所有数据（谨慎！）
docker compose down -v
```

### 生产环境安全检查清单

- [ ] 将 `SECRET_KEY` 和 `JWT_SECRET_KEY` 替换为随机长字符串（可用 `openssl rand -hex 32` 生成）
- [ ] 将 `ADMIN_PASSWORD` 改为强密码
- [ ] 将 `DB_PASSWORD` 改为非默认值（首次启动前修改，启动后数据库已初始化则需同时删除 pgdata 卷重建）
- [ ] 配置防火墙，仅对外开放 3000 端口（或 Nginx 的 80/443）
- [ ] 如果使用 Nginx 反向代理，建议开启 HTTPS（Let's Encrypt 免费证书）
- [ ] 设置定期备份 cron 任务
- [ ] 配置 Docker 日志轮转，防止磁盘写满（参考下方配置）

Docker Compose 日志轮转配置（在每个服务的 `docker-compose.yml` 中添加）：

```yaml
services:
  backend:
    # ... 其他配置 ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 许可证

本项目基于 Apache-2.0 License 开源。
