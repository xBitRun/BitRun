# BitRun 部署指南

## 部署架构

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

## 文件说明

| 文件 | 用途 |
|------|------|
| `scripts/install.sh` | 一键安装脚本（支持 `--prod` 生产模式） |
| `scripts/deploy.sh` | 服务管理脚本（start/stop/logs 等） |
| `docker-compose.prod.yml` | 生产环境 Docker Compose 配置 |
| `nginx/nginx.prod.conf` | 生产环境 Nginx 配置（前后端分离域名） |
| `.github/workflows/test.yml` | GitHub Actions 测试工作流 |
| `backend/.env.example` | 后端环境变量模板 |
| `frontend/.env.local.example` | 前端环境变量模板 |

---

## 生产环境部署

### 前置条件

1. **服务器**: 阿里云 ECS (Ubuntu 20.04+)
2. **DNS 配置**:
   - `app.example.com` → 服务器 IP
   - `api.example.com` → 服务器 IP
3. **安全组**: 开放 22, 80, 443 端口

### 部署步骤

#### 1. 配置 GitHub Secrets

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

#### 2. 首次部署

SSH 到服务器执行：

```bash
# 生产环境一键安装 (域名 + SSL)
curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/scripts/install.sh | bash -s -- --prod
```

脚本会自动完成：
- 安装 Docker
- 申请 SSL 证书 (Let's Encrypt)
- 生成所有密钥
- 构建并启动服务

#### 3. 后续更新

推送到 `main` 分支 → GitHub Actions 自动部署

---

## 本地开发环境

```bash
# 快速启动
./scripts/quick-start.sh

# 或使用 Docker
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---

## 常用命令

```bash
# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 重新构建并启动
docker compose up -d --build

# 停止服务
docker compose down

# 数据库迁移
docker compose exec backend alembic upgrade head
```

---

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | https://app.example.com |
| 后端 API | https://api.example.com |
| API 文档 | https://api.example.com/api/v1/docs |

---

## 故障排查

### SSL 证书问题

```bash
# 查看证书状态
certbot certificates

# 手动续期
certbot renew

# 重新申请
certbot certonly --webroot -w /var/www/certbot -d app.example.com
```

### 服务无法启动

```bash
# 查看服务状态
docker compose ps

# 查看详细日志
docker compose logs backend
docker compose logs frontend
```

### 数据库连接失败

```bash
# 检查数据库状态
docker compose exec postgres pg_isready

# 手动连接测试
docker compose exec postgres psql -U bitrun -d bitrun
```
