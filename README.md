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
# 安装 Docker & Docker Compose
curl -fsSL https://get.docker.com | bash
sudo apt install -y docker-compose-plugin git nginx
```

```bash
git clone https://github.com/Ljinzhou/EasyInvoiceMgr.git
cd EasyInvoiceMgr
```

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

> 如果部署在云服务器上，除了服务器自身的防火墙，还需要在云服务商控制台的**安全组**中放行 3000 端口（TCP），否则外网无法访问。

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

## 许可证

本项目基于 Apache-2.0 License 开源。
