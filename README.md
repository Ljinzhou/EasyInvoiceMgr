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

### 一键启动

```bash
# 1. 安装 Docker（约 30 秒）
sudo apt install -y docker.io docker-compose-v2 && sudo systemctl enable --now docker

# 2. 克隆项目
git clone https://github.com/Ljinzhou/EasyInvoiceMgr.git && cd EasyInvoiceMgr

# 3. 启动
docker compose up -d
```

浏览器打开 `http://<服务器IP>:3000`，默认账号 `admin`，密码 `admin`。

> 云服务器需在安全组放行 **3000 端口**（TCP）。首次启动需拉取镜像，约 3-10 分钟。

---

### 自定义配置

在项目目录下创建 `.env` 文件，可覆盖默认配置：

```bash
ADMIN_PASSWORD=my-password          # 管理员密码，默认 admin
NUXT_PUBLIC_API_BASE=http://1.2.3.4:5000/api   # 服务器公网IP
CORS_ORIGINS=http://1.2.3.4:3000              # 前端访问地址
SECRET_KEY=$(openssl rand -hex 32)            # 生产环境务必修改
JWT_SECRET_KEY=$(openssl rand -hex 32)        # 生产环境务必修改
GLM_API_KEY=your-key              # 智谱AI（可选，用于发票OCR）
```

全部可用变量及默认值见下表：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_PASSWORD` | `admin` | 管理员初始密码 |
| `DB_PASSWORD` | `root` | 数据库密码 |
| `SECRET_KEY` | 内置值 | Flask 会话密钥 |
| `JWT_SECRET_KEY` | 内置值 | JWT 签名密钥 |
| `CORS_ORIGINS` | `http://localhost:3000` | 跨域白名单 |
| `NUXT_PUBLIC_API_BASE` | `http://localhost:5000/api` | 前端访问后端的地址 |
| `GLM_API_KEY` | 空 | 智谱AI密钥 |
| `GLM_MODEL` | `glm-4.6v-flash` | 智谱AI模型 |

> 修改 `.env` 后执行 `docker compose up -d --build` 重新构建即可生效。

### 更新部署

```bash
cd EasyInvoiceMgr
git pull origin dev
docker compose up -d --build backend frontend
```

### 国内服务器

国内服务器访问 Docker Hub 可能超时，需额外三步：

**1. 配置 Docker 镜像加速：**

```bash
sudo tee /etc/docker/daemon.json << 'EOF'
{"registry-mirrors": ["https://docker.1ms.run", "https://docker.xuanyuan.me"]}
EOF
sudo systemctl restart docker
```

**2. 编辑 `backend/Dockerfile`**，在 `RUN apt-get update` 前加一行，`pip install` 加镜像参数：

```dockerfile
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
# ...
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt
```

**3. 编辑 `frontend/Dockerfile`**，`pnpm install` 前加镜像：

```dockerfile
RUN pnpm config set registry https://registry.npmmirror.com && \
    pnpm install --frozen-lockfile
```

### 生产环境（Nginx + HTTPS）

<details>
<summary>展开查看完整配置</summary>

修改 `docker-compose.yml`，将端口绑定到本地：

```yaml
ports:
  - "127.0.0.1:5000:5000"   # backend
  - "127.0.0.1:3000:3000"   # frontend
```

Nginx 配置（`/etc/nginx/sites-available/invoice`）：

```nginx
server {
    listen 80;
    server_name your-domain.com;
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
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/invoice /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

</details>

---

## 许可证

本项目基于 Apache-2.0 License 开源。
