# EasyInvoiceMgr - 发票与账单管理系统

本项目由**武汉生物工程学院——机器人实验室**开发。

## 项目概述

### 背景

本项目专为武汉生物工程学院机器人实验室设计，旨在解决社团活动经费管理中的账单录入繁琐、发票管理复杂、报销流程冗长等问题。通过数字化管理方式，实现账单便捷记录、发票智能识别与状态跟踪，以及自动化报销流程，既是一套高效的发票管理工具，也是一个实用的社团记账系统。

**本项目完全通过 Vibe Coding 开发完成。**

### 主要功能

- **用户管理**：支持学生、教师、管理员等多种角色，提供邀请码注册机制
- **项目管理**：创建和管理科研项目/活动，设定预算，跟踪支出
- **账单管理**：记录日常收支明细，灵活分类，关联发票，支持补录
- **发票管理**：上传发票图片或PDF文件，智能OCR识别发票信息，自动提取关键数据
- **报销审核**：支持多级审核流程，实时跟踪报销状态
- **数据导出**：支持Excel、PDF等多种格式导出，便于财务对账
- **预算管理**：实时跟踪项目预算使用情况，自动计算剩余金额

## 技术栈

**后端**：Flask + SQLAlchemy + PostgreSQL

**前端**：Nuxt 3 + Vue 3

**智能服务**：GLM-4.6V-Flash

## 未来计划

- **Salvo框架重构**：计划使用基于Rust的高性能Web框架Salvo重构后端代码，保持API兼容的同时提升性能、增强类型安全性和异步支持
- **与astrbot对接**：实现账单与发票管理的机器人交互
- **自动化测试完善**：建立完整的测试体系，确保代码质量
- **邮件/短信通知功能**：支持关键操作的即时通知
- **数据库优化**：添加索引优化查询性能，使用数据库连接池
- **批量操作优化**：支持更大规模的批量上传、批量审核
- **审计日志**：记录关键操作日志，便于问题追溯和安全审计
- **数据统计分析**：增加仪表盘数据可视化，支持自定义报表
- **权限细分**：细化角色权限，支持更灵活的权限配置
- **API限流与防护**：防止恶意请求，保障服务稳定性

## 部署指南

以下教程假设你有一台 Linux 服务器（推荐 Ubuntu 22.04+）。

### 前置准备

```bash
# 安装 Node.js 22+
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 pnpm
npm install -g pnpm

# 安装 Docker & Docker Compose
curl -fsSL https://get.docker.com | bash
sudo apt install -y docker-compose-plugin git nginx
```

```bash
git clone https://github.com/Ljinzhou/EasyInvoiceMgr.git
cd EasyInvoiceMgr
```

> 前端依赖由 Dockerfile 在构建时自动安装（`pnpm install --frozen-lockfile`），无需预先手动安装。

### 环境变量说明

部署需要关注两个关键变量：

- **`NUXT_PUBLIC_API_BASE`**（前端）— 浏览器向后端发请求的地址，**构建时注入**，修改后需重新构建前端。开发时 `nuxt.config.ts` 默认为 `http://localhost:5000/api`，无需手动设置。
- **`CORS_ORIGINS`**（后端）— 允许哪些前端域名跨域访问 API。开发时 `config.py` 默认包含了 `localhost:3000`，无需手动设置。

Docker 部署中这些变量通过 `.env` 文件统一配置：

| 变量                     | 作用                              | 默认值                         |
| ---------------------- | ------------------------------- | --------------------------- |
| `ADMIN_PASSWORD`       | 管理员初始密码                         | `admin`                     |
| `SECRET_KEY`           | Flask 会话密钥                      | 内置默认值                       |
| `JWT_SECRET_KEY`       | JWT 签名密钥                        | 内置默认值                       |
| `CORS_ORIGINS`         | 后端允许的跨域来源（逗号分隔）                 | `http://localhost:3000,...` |
| `NUXT_PUBLIC_API_BASE` | 前端访问后端的完整地址                     | `http://localhost:5000/api` |
| `GLM_API_KEY`          | 智谱AI 视觉模型 API Key（可选，不填则无法识别发票） | 空                           |
| `GLM_MODEL`            | 智谱AI 模型名称                       | `glm-4.6v-flash`            |

> `SECRET_KEY` 和 `JWT_SECRET_KEY` 用于加密会话和签名令牌，生产环境务必修改。用以下命令生成随机密钥：
>
> ```bash
> openssl rand -hex 32
> ```

> **注意**：若 `glm-4.6v-flash` 持续报错，请将 `GLM_MODEL` 改为 `glm-4v-flash`。

> `DATABASE_URL` 已硬编码在 `docker-compose.yml` 中，无需在 `.env` 中设置。如需修改数据库密码，请同步修改 `docker-compose.yml` 中 `postgres` 的 `POSTGRES_PASSWORD` 和 `backend` 的 `DATABASE_URL`。

<details>
<summary><b>如何修改数据库密码？</b></summary>

1. 编辑 `docker-compose.yml`，找到以下两处：

```yaml
# postgres 服务中
POSTGRES_PASSWORD: root   # 改为你的新密码

# backend 服务中
DATABASE_URL: postgresql://postgres:root@postgres:5432/easy_invoice_mgr
#                                  ^^^^ 把这里的 root 也改为新密码
```

2. 如果之前已经部署过（已有数据卷），需要删除旧数据卷使新密码生效：

```bash
docker compose down -v   # -v 会删除数据卷，旧数据将丢失
docker compose up -d --build
```

> `-v` 会删除数据库数据卷，**已有数据将丢失**。如需保留数据，建议先通过 `docker compose exec postgres pg_dump` 备份。

3. 如果是首次部署，直接启动即可：

```bash
docker compose up -d --build
```

</details>

***

### 方式一：Docker 快速部署

适合快速体验、内网使用。服务端口直接对外暴露。

**`.env`** **示例（本地/内网）：**

```bash
ADMIN_PASSWORD=admin
SECRET_KEY=your-random-secret-key
JWT_SECRET_KEY=your-random-jwt-key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NUXT_PUBLIC_API_BASE=http://localhost:5000/api
GLM_API_KEY=your-glm-api-key
GLM_MODEL=glm-4.6v-flash
```

**`.env`** **示例（外网服务器 IP）：**

```bash
ADMIN_PASSWORD=admin
SECRET_KEY=your-random-secret-key
JWT_SECRET_KEY=your-random-jwt-key
CORS_ORIGINS=http://192.168.1.100:3000
NUXT_PUBLIC_API_BASE=http://192.168.1.100:5000/api
GLM_API_KEY=your-glm-api-key
GLM_MODEL=glm-4.6v-flash
```

**启动：**

```bash
docker compose up -d --build
docker compose logs -f   # 确认无报错后 Ctrl+C 退出
```

浏览器打开 `http://<IP>:3000`，默认管理员 `admin` / 密码为 `ADMIN_PASSWORD` 的值。

> 如果部署在云服务器上，除了服务器自身的防火墙，还需要在云服务商控制台的**安全组**中放行 **3000 和 5000 端口**（TCP），否则外网无法访问。

> **推荐**：若服务器已安装 Nginx 且 80 端口已对外放开，可将 `NUXT_PUBLIC_API_BASE` 设为相对路径（如 `/api`），搭配 Nginx 反向代理统一从 80 端口提供服务，无需放行 3000 端口。具体配置参考上方"方式二"的 Nginx 配置部分。

***

### 方式二：Nginx 反向代理部署

适合生产环境，由 Nginx 统一入口，仅 80/443 对外，支持 HTTPS。

**`.env`** **示例（域名）：**

```bash
ADMIN_PASSWORD=admin
SECRET_KEY=your-random-secret-key
JWT_SECRET_KEY=your-random-jwt-key
CORS_ORIGINS=https://invoice.example.com
NUXT_PUBLIC_API_BASE=https://invoice.example.com/api
GLM_API_KEY=your-glm-api-key
GLM_MODEL=glm-4.6v-flash
```

**1. 修改端口绑定为仅本地回环：**

编辑 `docker-compose.yml`，将 `backend` 和 `frontend` 的 ports 改为 `127.0.0.1:xxxx:xxxx`：

```yaml
# backend
ports:
  - "127.0.0.1:5000:5000"

# frontend
ports:
  - "127.0.0.1:3000:3000"
```

**2. 启动服务：**

```bash
docker compose up -d --build
```

**3. 配置 Nginx：**

```bash
sudo nano /etc/nginx/sites-available/invoice
```

```nginx
server {
    listen 80;
    server_name invoice.example.com;
    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:5000/uploads/;
        proxy_set_header Host $host;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/invoice /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**4. 开启 HTTPS：**

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d invoice.example.com
sudo certbot renew --dry-run
```

**5. 配置防火墙：**

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

> 云服务器还需在**安全组**中放行 80 和 443 端口（TCP）。

访问 `https://invoice.example.com`。

## 更新部署

当代码仓库有更新后，需要在服务器上拉取最新代码并重新构建容器。

### 方式一：通过 Git 更新（推荐）

如果服务器上的项目目录是通过 `git clone` 获取的：

```bash
cd EasyInvoiceMgr
git pull origin dev          # 拉取最新代码
docker compose up -d --build backend frontend   # 仅重建后端和前端
```

> PostgreSQL 容器无需重建，`--build` 参数确保代码变更被打包进新镜像。

### 方式二：手动上传文件更新

如果服务器上未配置 Git（例如通过 FTP/SCP 部署），需要将本地修改过的文件上传到服务器对应目录后重建：

```bash
# 1. 在本地将修改的文件上传到服务器的 /root/EasyInvoiceMgr/ 对应路径

# 2. 在服务器上重建容器
cd /root/EasyInvoiceMgr
docker compose up -d --build backend frontend
```

### 快速验证

更新完成后确认服务正常：

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
docker compose logs --tail=5 backend frontend
```

浏览器访问 `http://<IP>:3000` 验证功能。

## 故障排除

### 前端构建失败：`packages field missing or empty`

**现象**：`docker compose up -d --build` 执行时前端构建报错 `ERROR packages field missing or empty`。

**原因**：`frontend/pnpm-workspace.yaml` 文件损坏或内容不正确。pnpm 检测到该文件后会按 workspace 模式运行，但缺少必需的 `packages` 字段。

**修复**：确保 `pnpm-workspace.yaml` 内容为：

```yaml
packages:
  - '.'
```

### 后端构建失败：`fatal error: stdlib.h: No such file or directory`

**现象**：后端镜像构建时 `pip install psycopg2` 编译失败，提示 `fatal error: stdlib.h: No such file or directory`。

**原因**：`psycopg2` 需要完整的 C 编译工具链（gcc + libc-dev），而 `python:3.11-slim` 基础镜像不包含这些。

**修复**：将 `backend/requirements.txt` 中的 `psycopg2==2.9.12` 改为 `psycopg2-binary==2.9.12`，使用预编译版本：

```diff
- psycopg2==2.9.12
+ psycopg2-binary==2.9.12
```

同时可将 `backend/Dockerfile` 中不再需要的构建依赖（`gcc`、`libpq-dev`）移除。

### pip/apt 下载慢或超时（国内服务器）

**现象**：构建过程中 `apt-get update` 或 `pip install` 长时间无响应，或构建超过 10 分钟仍未完成。

**原因**：国内服务器访问 Debian/PyPI 官方源速度极慢。

**修复**：在 `backend/Dockerfile` 中配置国内镜像源加速：

```dockerfile
FROM python:3.11-slim

# apt 使用阿里云镜像（加速 Debian 包下载）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# pip 使用阿里云镜像（加速 Python 包下载）
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt

COPY . .
RUN mkdir -p uploads exports
EXPOSE 5000
CMD ["python", "app.py"]
```

### 外网无法访问前端（端口 3000 被拦截）

**现象**：服务启动后内网访问正常，但外网浏览器无法打开页面。

**原因**：云服务商安全组默认只开放了常用端口（22、80、443），3000 端口未放行。

**解决方案**（二选一）：

1. **放行端口**：在云服务商控制台的安全组中添加 3000 和 5000 端口的 TCP 入站规则。
2. **使用 Nginx 反向代理**：利用已开放的 80 端口代理前后端服务（参考上方"方式二"），配置 `/` 转发到前端 3000 端口，`/api/` 转发到后端 5000 端口。

### 容器启动后立即退出

**现象**：`docker compose up -d` 后容器很快变为 `Exited` 状态。

**排查**：

```bash
# 查看容器退出日志
docker logs easyinvoicemgr-backend-1 --tail 50
docker logs easyinvoicemgr-postgres-1 --tail 50

# 检查端口是否被占用（特别是 5432、5000、3000）
ss -tlnp | grep -E '(:5432|:5000|:3000)'

# 检查 .env 文件是否存在且配置正确
cat .env
```

常见原因：端口冲突、`.env` 文件缺失或配置错误、数据库连接失败。

### 数据库密码修改后连接失败

如果修改了数据库密码但忘记同步更新 `docker-compose.yml` 中 `DATABASE_URL` 的密码部分，后端将无法连接数据库。

检查两处密码必须一致：
- `docker-compose.yml` → `postgres.POSTGRES_PASSWORD`
- `docker-compose.yml` → `backend.environment.DATABASE_URL` 中的密码

修改后需重建容器：
```bash
docker compose down -v   # -v 会删除旧数据卷
docker compose up -d --build
```

## 许可证

本项目基于 Apache-2.0 License 开源。
