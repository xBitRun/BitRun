# 快速开始指南

本文档帮助你从零开始搭建和运行 BITRUN。

## 环境要求

### Docker 部署 (推荐)

| 依赖 | 最低版本 |
|------|---------|
| Docker | 20.10+ |
| Docker Compose | v2.0+ |

### 本地开发

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.12+ | 后端运行环境 |
| Node.js | 20+ | 前端运行环境 |
| PostgreSQL | 16 | 可通过 Docker 启动 |
| Redis | 7 | 可通过 Docker 启动 |

## 安装步骤

### 方式一：一键启动 (推荐)

```bash
git clone <repository-url>
cd bitrun
./scripts/quick-start.sh
```

`quick-start.sh` 脚本会自动完成：
1. 检查 Docker 环境
2. 从模板创建 `.env` 配置文件
3. 构建并启动所有 Docker 服务
4. 运行数据库迁移
5. 输出访问地址

支持的启动模式：

```bash
./scripts/quick-start.sh          # 默认模式 (Docker Compose)
./scripts/quick-start.sh --dev    # 开发模式 (热重载)
./scripts/quick-start.sh --prod   # 生产模式 (Nginx + 资源限制)
./scripts/quick-start.sh --stop   # 停止所有服务
```

### 方式二：Docker Compose 手动启动

#### 1. 克隆仓库

```bash
git clone <repository-url>
cd bitrun
```

#### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

编辑 `backend/.env`，根据需要修改以下配置：

```bash
# 数据库 (Docker 环境使用默认值即可)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bitrun

# Redis
REDIS_URL=redis://localhost:6379/0

# 安全密钥 (留空会自动生成，但重启后会失效)
JWT_SECRET=your-secret-key
DATA_ENCRYPTION_KEY=your-32-byte-base64-key

# 启用策略自动执行
WORKER_ENABLED=true
```

> 生成加密密钥：`python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`

#### 3. 启动服务

**开发环境** (支持热重载)：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**生产环境** (Nginx + 资源限制)：

```bash
docker compose -f docker-compose.prod.yml up -d
```

#### 4. 运行数据库迁移

```bash
docker compose exec backend alembic upgrade head
```

#### 5. 访问应用

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/api/v1/docs |
| 健康检查 | http://localhost:8000/health |

### 方式三：本地开发 (前后端分离)

适用于需要频繁修改代码的开发场景。

#### 1. 启动基础服务

使用 Docker 启动 PostgreSQL 和 Redis：

```bash
docker compose up -d postgres redis
```

或使用开发脚本：

```bash
./scripts/start-dev.sh
```

#### 2. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器 (自动重载)
python run.py
```

后端默认运行在 `http://localhost:8000`。

#### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`。

## 首次配置向导

成功启动后，按以下步骤配置系统：

### Step 1: 注册账户

打开 `http://localhost:3000`，点击注册，输入邮箱和密码创建管理员账户。

### Step 2: 配置 AI Provider

进入 **「模型管理」** 页面：

1. 点击「添加 Provider」
2. 选择一个 AI 服务商 (推荐 DeepSeek，性价比最高)
3. 填入 API Key
4. 选择要启用的模型
5. 点击「测试连接」验证配置

> 详细配置说明请查看 [AI 模型配置指南](ai-models.md)

### Step 3: 添加交易所账户

进入 **「账户管理」** 页面：

1. 点击「添加账户」
2. 选择交易所 (Binance / Bybit / OKX / Hyperliquid)
3. 填入 API Key 和 Secret (Hyperliquid 填入私钥)
4. 可选勾选「测试网」进行安全测试
5. 点击「测试连接」验证 API 权限

> 详细配置说明请查看 [交易所对接指南](exchange-setup.md)

### Step 4: 创建第一个策略

进入 **「AI Agent」** 页面：

1. 点击「新建 Agent」
2. 填写策略名称和描述
3. 在「策略工作室」中配置：
   - **Coins** — 选择交易标的 (如 BTC/USDT)
   - **Indicators** — 配置技术指标 (EMA, RSI, MACD, ATR)
   - **Risk** — 设置风控参数 (最大杠杆、仓位比例、最大回撤)
   - **Prompt** — 编写自定义策略描述
   - **Debate** — 可选启用多模型辩论
4. 选择 AI 模型和交易所账户
5. 选择交易模式 (保守 / 平衡 / 激进)
6. 点击创建，然后激活策略

> 详细策略配置请查看 [策略模块文档](strategy-guide.md)

## 常见问题

### 数据库连接失败

**错误信息**: `Database: Connection failed`

**解决方法**:
1. 确认 PostgreSQL 已启动：`docker compose ps postgres`
2. 检查 `DATABASE_URL` 配置是否正确
3. Docker 环境中，主机名应为 `postgres` (服务名)，本地开发使用 `localhost`

### Redis 连接失败

**错误信息**: `Redis: Connection failed`

**解决方法**:
1. 确认 Redis 已启动：`docker compose ps redis`
2. 检查 `REDIS_URL` 配置
3. Docker 环境中，主机名应为 `redis` (服务名)

### 前端无法连接后端

**错误信息**: 页面加载后提示网络错误

**解决方法**:
1. 检查 `frontend/.env.local` 中的 `NEXT_PUBLIC_API_URL`
2. Docker 环境: `http://localhost:8000/api`
3. 确认后端已成功启动：访问 `http://localhost:8000/health`

### 端口被占用

**错误信息**: `port is already allocated`

**解决方法**:

```bash
# 查找占用端口的进程
lsof -i :3000  # 前端
lsof -i :8000  # 后端

# 终止进程
kill -9 <PID>
```

或使用开发脚本自动处理端口冲突：

```bash
./scripts/start-dev.sh
```

### 数据库迁移失败

**解决方法**:

```bash
# 查看当前迁移版本
docker compose exec backend alembic current

# 查看历史记录
docker compose exec backend alembic history

# 强制升级到最新
docker compose exec backend alembic upgrade head
```

### Docker 构建缓慢

**解决方法**:
1. 使用国内 Docker 镜像源
2. 开发环境使用 `docker-compose.dev.yml`，利用 volume 挂载避免每次重建
3. 使用 `docker compose build --no-cache` 完全重建 (解决缓存导致的问题)

### 交易所 API 连接超时

**解决方法**:
1. 部分交易所 (Bybit, OKX) 在中国大陆需要代理
2. 在 `backend/.env` 中配置代理：

```bash
# Surge
PROXY_URL=http://host.docker.internal:6152

# Clash
PROXY_URL=http://host.docker.internal:7890
```

> Docker 环境使用 `host.docker.internal` 访问宿主机代理

## 下一步

- [架构概览](architecture.md) — 了解系统整体设计
- [策略模块文档](strategy-guide.md) — 深入了解策略配置
- [AI 模型配置](ai-models.md) — 配置更多 AI Provider
- [交易所对接](exchange-setup.md) — 连接更多交易所
- [部署指南](deployment.md) — 生产环境部署
