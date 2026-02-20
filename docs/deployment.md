# 部署指南

本文档说明 BITRUN 的各种部署方式，包括 Docker 开发/生产部署、SSL 配置、Nginx 反向代理、GitHub Actions CI/CD 和监控告警。

## 生产环境架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户访问                              │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │ app.example.com   │            │ api.example.com   │
    │   (Frontend)     │            │    (Backend)     │
    │   Next.js 16     │            │    FastAPI       │
    └──────────────────┘            └──────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
    ┌─────────────────────────────────────────────────────┐
    │                    Docker Network                    │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │
    │  │ Nginx   │  │ Frontend│  │ Backend │  │Worker  │ │
    │  │ :80/443 │  │  :3000  │  │  :8000  │  │ (后台) │ │
    │  └─────────┘  └─────────┘  └─────────┘  └────────┘ │
    │  ┌─────────┐  ┌─────────┐                          │
    │  │Postgres │  │  Redis  │                          │
    │  │  :5432  │  │  :6379  │                          │
    │  └─────────┘  └─────────┘                          │
    └─────────────────────────────────────────────────────┘
```

**前后端分离域名优势**：
- 独立扩展：前后端可独立水平扩展
- CDN 加速：前端静态资源可接入 CDN
- 安全隔离：API 和页面分离，便于安全策略配置

## Docker 部署

BITRUN 提供三个 Docker Compose 配置文件：

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 基础配置 (PostgreSQL + Redis + 后端 + 前端) |
| `docker-compose.dev.yml` | 开发环境覆盖 (热重载 + 调试日志) |
| `docker-compose.prod.yml` | 生产环境配置 (Nginx + 资源限制 + 日志轮转) |

### 开发环境部署

开发环境支持代码热重载，适合日常开发。

```bash
# 启动
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 运行数据库迁移
docker compose exec backend alembic upgrade head

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 停止
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

开发环境特性：
- 后端 `app/` 目录通过 volume 挂载，代码修改自动重载
- 前端 `src/` 目录通过 volume 挂载，支持 HMR
- 开启 Debug 模式 (Swagger 文档可访问)
- 日志级别为 DEBUG

### 生产环境部署

#### 使用部署脚本 (推荐)

```bash
# 首次部署
./scripts/deploy.sh start

# 查看状态
./scripts/deploy.sh status

# 查看日志
./scripts/deploy.sh logs

# 重启
./scripts/deploy.sh restart

# 停止
./scripts/deploy.sh stop

# 数据库迁移
./scripts/deploy.sh migrate

# 数据库备份
./scripts/deploy.sh backup
```

`deploy.sh` 会自动：
1. 检查 Docker 环境
2. 生成 `.env.production` (如不存在)
3. 生成安全密钥 (JWT_SECRET, DATA_ENCRYPTION_KEY)
4. 构建镜像
5. 启动所有服务
6. 等待健康检查通过

#### 手动部署

```bash
# 1. 创建生产环境配置
cp backend/.env.example .env.production

# 2. 编辑配置 (务必修改安全密钥)
vim .env.production

# 3. 构建并启动
docker compose -f docker-compose.prod.yml up -d --build

# 4. 运行数据库迁移
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 生产环境配置要点

#### 必须配置

```bash
# 安全密钥 (必须设置，否则重启后 session 和加密数据失效)
JWT_SECRET=<生成一个随机字符串>
DATA_ENCRYPTION_KEY=<32 字节 base64 编码>

# 数据库密码
POSTGRES_PASSWORD=<强密码>

# 环境标识
ENVIRONMENT=production

# 域名配置
FRONTEND_DOMAIN=app.example.com
BACKEND_DOMAIN=api.example.com
```

#### 资源限制

生产环境 Docker Compose 默认资源限制：

| 服务 | 内存限制 | CPU 限制 |
|------|---------|---------|
| PostgreSQL | 1 GB | 2 核 |
| Redis | 512 MB | 1 核 |
| Backend | 2 GB | 2 核 |
| Frontend | 1 GB | 1 核 |
| Nginx | 256 MB | - |

可在 `docker-compose.prod.yml` 中调整。

#### 日志配置

生产环境使用 JSON 文件驱动记录日志，支持自动轮转：

| 服务 | 单文件上限 | 保留文件数 |
|------|-----------|-----------|
| Backend | 50 MB | 5 个 |
| Frontend | 20 MB | 3 个 |
| PostgreSQL / Redis / Nginx | 10 MB | 3 个 |

## GitHub Actions CI/CD

### 前置条件

1. **服务器**: 阿里云 ECS (Ubuntu 20.04+) 或其他云服务器
2. **DNS 配置**:
   - `app.example.com` → 服务器 IP
   - `api.example.com` → 服务器 IP
3. **安全组**: 开放 22, 80, 443 端口

### 配置 GitHub Secrets

路径: `仓库 → Settings → Secrets → Actions`

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 服务器 IP |
| `SERVER_USER` | SSH 用户 (如 `root`) |
| `SSH_PRIVATE_KEY` | SSH 私钥 |
| `FRONTEND_DOMAIN` | `app.example.com` |
| `BACKEND_DOMAIN` | `api.example.com` |
| `POSTGRES_PASSWORD` | 数据库密码 |
| `JWT_SECRET` | JWT 密钥 |
| `DATA_ENCRYPTION_KEY` | 加密密钥 |
| `REDIS_PASSWORD` | Redis 密码 |

> 密钥生成: `openssl rand -base64 32`

### 自动部署流程

推送到 `main` 分支 → GitHub Actions 自动部署：

1. 检出代码
2. 构建 Docker 镜像
3. SSH 到服务器
4. 拉取最新代码
5. 重新构建并启动服务
6. 运行数据库迁移
7. 健康检查

### 首次部署

SSH 到服务器执行：

```bash
# 生产环境一键安装 (域名 + SSL)
curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/scripts/install.sh | bash -s -- --prod
```

脚本会自动完成：
- 安装 Docker 和系统依赖
- 配置防火墙
- 申请 SSL 证书 (Let's Encrypt)
- 生成所有密钥
- 构建并启动服务

> 部署后使用 `./scripts/deploy.sh` 管理服务（start/stop/logs/status 等）

## Nginx 反向代理

生产环境使用 Nginx 作为统一入口，提供反向代理、限流和安全防护。

### 配置文件

Nginx 配置位于 `nginx/nginx.prod.conf`，支持前后端分离域名：

```nginx
# Frontend - app.example.com
server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend - api.example.com
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    location /api/ {
        proxy_pass http://backend:8000;
        # ... 代理配置
    }

    location /api/v1/ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 速率限制

| 区域 | 限制 | 突发 | 说明 |
|------|------|------|------|
| API | 30 req/s | 50 | 常规 API 请求 |
| WebSocket | 5 req/s | 10 | WebSocket 连接 |

### 安全头

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 其他特性

- Gzip 压缩 (text/html, CSS, JS, JSON)
- 客户端请求体大小限制：10 MB
- WebSocket 连接超时：24 小时
- 健康检查端点不限流

## SSL/HTTPS 配置

### 获取 SSL 证书

#### Let's Encrypt (免费)

```bash
# 安装 certbot
apt install certbot

# 获取证书 (前端域名)
certbot certonly --webroot -w /var/www/certbot -d app.example.com

# 获取证书 (后端域名)
certbot certonly --webroot -w /var/www/certbot -d api.example.com
```

证书文件：
- 证书链：`/etc/letsencrypt/live/<domain>/fullchain.pem`
- 私钥：`/etc/letsencrypt/live/<domain>/privkey.pem`

#### 自动续期

```bash
# 测试续期
certbot renew --dry-run

# 添加 cron 任务
0 3 * * * certbot renew --quiet && docker compose -f /opt/bitrun/docker-compose.prod.yml restart nginx
```

### 启用 HTTPS

需要修改三个地方：

#### 1. 取消 Nginx SSL 配置注释

编辑 `nginx/nginx.prod.conf`，确保 SSL 配置正确。

#### 2. 取消 Docker Compose SSL 配置注释

编辑 `docker-compose.prod.yml`：

```yaml
nginx:
  ports:
    - "${HTTP_PORT:-80}:80"
    - "${HTTPS_PORT:-443}:443"
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

#### 3. 更新前端环境变量

```bash
NEXT_PUBLIC_API_URL=https://api.example.com/api
NEXT_PUBLIC_WS_URL=wss://api.example.com/api/v1/ws
```

## Railway 部署

Railway 提供一键云端部署，无需管理服务器。

### 部署架构

```
Railway Project
├── PostgreSQL (Railway 数据库服务)
├── Redis (Railway 缓存服务)
├── Backend (FastAPI 应用)
└── Frontend (Next.js 应用)
```

### 一键部署

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/bitrun)

点击按钮后，Railway 会自动:
1. 创建 PostgreSQL 和 Redis 数据库服务
2. 部署后端服务 (使用 `Dockerfile.railway`)
3. 部署前端服务 (使用 `frontend/Dockerfile`)

### 手动部署步骤

如果需要手动配置:

1. **创建 Railway 项目**
   - 登录 [Railway](https://railway.app)
   - 创建新项目

2. **添加数据库服务**
   - 添加 PostgreSQL (Railway 会自动注入 `DATABASE_URL`)
   - 添加 Redis (Railway 会自动注入 `REDIS_URL`)

3. **部署后端**
   - 新建服务，选择 GitHub 仓库
   - 设置 Root Directory: `/` (使用根目录的 `Dockerfile.railway`)
   - 设置环境变量

4. **部署前端**
   - 新建服务，选择 GitHub 仓库
   - 设置 Root Directory: `/frontend`
   - 设置环境变量

### 环境变量配置

#### 后端环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DATABASE_URL` | Railway 自动注入 | 自动 |
| `REDIS_URL` | Railway 自动注入 | 自动 |
| `JWT_SECRET` | JWT 签名密钥 (32+ 字符) | 是 |
| `DATA_ENCRYPTION_KEY` | 数据加密密钥 | 是 |
| `ENVIRONMENT` | 设置为 `production` | 是 |
| `CORS_ORIGINS` | 前端域名 | 是 |

生成密钥:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 前端环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 | 是 |
| `NEXT_PUBLIC_WS_URL` | WebSocket 地址 | 是 |

示例:
```bash
NEXT_PUBLIC_API_URL=https://bitrun-backend.up.railway.app/api
NEXT_PUBLIC_WS_URL=wss://bitrun-backend.up.railway.app/api/v1/ws
```

### 自动迁移

后端启动脚本 (`railway/start.sh`) 会自动执行:
1. 转换 `DATABASE_URL` 为 asyncpg 格式
2. 等待数据库就绪
3. 运行 Alembic 迁移
4. 启动 uvicorn 服务

### 费用参考

Railway 按使用量计费，参考价格:

| 服务 | 月费用 (估算) |
|------|-------------|
| PostgreSQL | $5-10 |
| Redis | $3-5 |
| Backend | $5-10 |
| Frontend | $3-5 |
| **总计** | **$16-30** |

> 注: 实际费用取决于使用量，新用户有 $5 免费额度。

### 注意事项

- Railway 动态分配端口，通过 `PORT` 环境变量传递
- 后端 Dockerfile.railway 已适配动态端口
- 数据库 URL 会自动转换为 asyncpg 格式
- 生产环境必须设置 `JWT_SECRET` 和 `DATA_ENCRYPTION_KEY`

---

## 云服务器部署

### 推荐配置

| 配置 | 最低要求 | 推荐 |
|------|---------|------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 40 GB SSD | 100 GB SSD |
| 带宽 | 5 Mbps | 10 Mbps |
| 系统 | Ubuntu 22.04 | Ubuntu 22.04 |

### 部署步骤

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 克隆项目
git clone <repository-url>
cd bitrun

# 3. 一键部署
./scripts/deploy.sh start

# 4. 配置防火墙
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 访问地址

| 服务 | 开发环境 | 生产环境 |
|------|---------|---------|
| 前端 | http://localhost:3000 | https://app.example.com |
| 后端 API | http://localhost:8000 | https://api.example.com |
| API 文档 | http://localhost:8000/api/v1/docs | https://api.example.com/api/v1/docs |
| WebSocket | ws://localhost:8000/api/v1/ws | wss://api.example.com/api/v1/ws |

## 监控与告警

### Sentry — 错误追踪

BITRUN 前后端均集成了 Sentry，用于实时错误追踪和性能监控。

#### 配置

1. 在 [Sentry.io](https://sentry.io) 创建项目
2. 获取 DSN

**后端配置** (`backend/.env`)：

```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
```

**前端配置**：

前端目前未集成 Sentry SDK。如需启用，可安装 `@sentry/nextjs` 并按官方文档配置。

#### 后端 Sentry 功能

- 自动捕获未处理异常
- FastAPI 请求追踪
- SQLAlchemy 查询追踪
- Redis 操作追踪
- 采样率：traces 10%, profiles 10%
- PII 数据自动脱敏

#### 前端 Sentry 功能

- 客户端错误捕获
- Session Replay：正常会话 10% 采样，错误会话 100% 记录
- 自动过滤：网络错误、请求取消、Chunk 加载失败等

### Prometheus — 指标采集

后端暴露 Prometheus 指标端点：

```
GET /api/v1/metrics                    # Prometheus 格式
GET /api/v1/metrics/json               # JSON 格式
GET /api/v1/health/detailed            # 组件级健康检查
GET /api/v1/health/circuit-breakers    # 熔断器状态
```

采集的指标包括：

- HTTP 请求延迟和吞吐
- 数据库查询性能
- Redis 命中率
- AI 调用延迟和成功率
- 交易所 API 调用状态
- WebSocket 连接数

可接入 Grafana 进行可视化。

### 通知渠道

支持多种告警通知渠道：

| 渠道 | 配置 |
|------|------|
| **Telegram** | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` |
| **Discord** | `DISCORD_WEBHOOK_URL` |
| **邮件 (Resend)** | `RESEND_API_KEY` + `RESEND_FROM` |

通知触发场景：
- 策略执行成功/失败
- 交易执行结果
- 账户余额异常
- 系统错误

## 数据库备份

### 手动备份

```bash
# 使用部署脚本
./scripts/deploy.sh backup
```

备份文件保存在 `backups/` 目录，格式为 `bitrun_YYYYMMDD_HHMMSS.sql.gz`。

### 自动备份

建议通过 cron 定时备份：

```bash
# 每天凌晨 3 点备份
0 3 * * * /path/to/bitrun/scripts/deploy.sh backup
```

### 恢复

```bash
# 解压
gunzip backups/bitrun_20250101_030000.sql.gz

# 恢复
docker compose exec -T postgres psql -U postgres -d bitrun < backups/bitrun_20250101_030000.sql
```

## 健康检查

使用健康检查脚本验证所有服务状态：

```bash
./scripts/health-check.sh
```

检查项目：
- 后端 HTTP 端点 (`/health`)
- 前端 HTTP 服务
- PostgreSQL TCP 连接
- Redis TCP 连接
- Docker 容器运行状态

## 故障排查

### SSL 证书问题

```bash
# 查看证书状态
certbot certificates

# 手动续期
certbot renew

# 重新申请
certbot certonly --webroot -w /var/www/certbot -d app.example.com
certbot certonly --webroot -w /var/www/certbot -d api.example.com
```

### 服务无法启动

```bash
# 查看服务状态
docker compose ps

# 查看详细日志
docker compose logs backend
docker compose logs frontend
docker compose logs nginx
```

### 数据库连接失败

```bash
# 检查数据库状态
docker compose exec postgres pg_isready

# 手动连接测试
docker compose exec postgres psql -U bitrun -d bitrun
```

### Worker 不执行

```bash
# 检查 Worker 状态
docker compose exec backend python -c "from app.workers.unified_manager import UnifiedWorkerManager; ..."

# 查看心跳状态
docker compose exec backend python -c "
from app.db.database import get_db
from app.db.models import Agent
# 检查 Agent 状态
"
```

## 相关文档

- [快速开始](getting-started.md) — 开发环境搭建
- [开发者指南](development.md) — 本地开发和测试
- [架构概览](architecture.md) — 系统设计详情
