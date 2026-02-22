# BITRUN

**AI 驱动的加密货币交易代理平台** — 用自然语言定义交易策略，多模型 AI 智能决策，多交易所统一执行。

## 核心特性

### 🎯 AI 驱动交易

- **Prompt 驱动策略** — 用自然语言描述交易逻辑，AI 自动分析市场并生成决策
- **多模型辩论引擎** — 多个 AI 模型并行分析、投票表决，提升决策质量
- **9+ AI Provider** — DeepSeek、Qwen、OpenAI、Gemini、Grok 等，支持自定义端点

### 📈 多市场支持

- **6+ 加密交易所** — Binance、Bybit、OKX、Bitget、KuCoin、Gate.io (CCXT 统一接口)
- **DEX 支持** — Hyperliquid 原生集成
- **传统市场 (Beta)** — 外汇 (Forex) 和贵金属 (XAU/XAG)

### ⚙️ 策略与执行

- **量化策略引擎** — 内置 Grid、DCA、RSI 策略，无需 AI 即可运行
- **回测系统** — 历史数据验证，支持收益曲线、最大回撤、夏普比率
- **Agent 实例管理** — 策略与执行分离，多账户、多交易类型

### 📊 平台能力

- **实时监控** — WebSocket 推送决策、持仓、账户状态
- **多渠道通知** — Telegram、Discord、Email
- **白标定制** — 自定义品牌名称、Logo、主题
- **完整国际化** — 中英文双语界面

## 技术栈

### 后端

| 类别     | 技术                                                                       |
| -------- | -------------------------------------------------------------------------- |
| 框架     | FastAPI (Python 3.12)                                                      |
| 数据库   | PostgreSQL 16 + SQLAlchemy 2.0 (asyncpg)                                   |
| 缓存     | Redis 7 (AOF 持久化)                                                       |
| 任务队列 | ARQ (异步 Redis 队列)                                                      |
| AI 集成  | DeepSeek / Qwen / Zhipu / MiniMax / Kimi / OpenAI / Gemini / Grok / Custom |
| 交易对接 | CCXT (统一多交易所) + Hyperliquid SDK                                      |
| 认证     | JWT (access + refresh token) + bcrypt                                      |
| 监控     | Prometheus + Sentry                                                        |

### 前端

| 类别     | 技术                                             |
| -------- | ------------------------------------------------ |
| 框架     | Next.js 16 (App Router)                          |
| 语言     | TypeScript 5                                     |
| UI       | React 19 + Tailwind CSS 4 + Radix UI (shadcn/ui) |
| 状态管理 | Zustand + SWR                                    |
| 国际化   | next-intl (中文 / English)                       |
| 图表     | Recharts                                         |
| 测试     | Jest + Playwright (E2E)                          |

### 基础设施

| 类别     | 技术                            |
| -------- | ------------------------------- |
| 容器化   | Docker (多阶段构建)             |
| 编排     | Docker Compose (开发 / 生产)    |
| 反向代理 | Nginx (限流、安全头、WebSocket) |
| CI/CD    | GitHub Actions                  |
| 错误追踪 | Sentry (前端 + 后端)            |

## 项目结构

```
bitrun/
├── backend/                  # FastAPI 后端应用
│   ├── app/
│   │   ├── api/              #   API 路由 + WebSocket (23 个模块)
│   │   │   └── routes/       #   各模块路由
│   │   ├── backtest/         #   回测引擎 (Engine + Simulator + DataProvider)
│   │   ├── core/             #   配置、安全、依赖注入
│   │   ├── db/               #   数据库模型 + Repository 层 (10 个)
│   │   ├── models/           #   Pydantic 领域模型
│   │   ├── monitoring/       #   Prometheus + Sentry
│   │   ├── services/         #   业务逻辑层 (19 个)
│   │   │   └── ai/           #     AI 客户端实现 (12 个客户端，9+ Provider)
│   │   ├── traders/          #   交易所适配器 (CCXT / Hyperliquid)
│   │   └── workers/          #   后台 Worker (Unified 架构)
│   ├── alembic/              #   数据库迁移 (21 个)
│   └── tests/                #   测试套件 (30+ 测试文件)
├── frontend/                 # Next.js 前端应用
│   ├── src/
│   │   ├── app/[locale]/     #   国际化路由页面
│   │   │   ├── (auth)/       #     登录
│   │   │   └── (dashboard)/  #     Dashboard / Agents / Strategies / ...
│   │   ├── components/       #   React 组件
│   │   │   ├── ui/           #     shadcn/ui 基础组件
│   │   │   └── strategy-studio/ # 策略工作室
│   │   ├── hooks/            #   自定义 Hooks
│   │   ├── lib/api/          #   API 客户端
│   │   ├── stores/           #   Zustand 状态管理
│   │   └── messages/         #   i18n 翻译文件 (en.json / zh.json)
│   └── e2e/                  #   Playwright E2E 测试
├── scripts/                  # 部署和开发脚本
│   ├── install.sh            #   一键安装
│   ├── quick-start.sh        #   一键启动
│   ├── deploy.sh             #   生产部署
│   ├── start-dev.sh          #   本地开发启动
│   └── health-check.sh       #   健康检查
├── docs/                     # 项目文档
├── docker-compose.yml        # Docker 基础配置
├── docker-compose.dev.yml    # 开发环境覆盖
└── docker-compose.prod.yml   # 生产环境配置
```

## 快速开始

### Railway 一键部署 (云端)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/deploy/GNLLo_?referralCode=Lg6be0&utm_medium=integration&utm_source=template&utm_campaign=generic)

Railway 部署步骤:

1. 点击上方按钮，创建新项目
2. Railway 会自动添加 PostgreSQL 和 Redis 服务
3. **后端服务** 设置以下环境变量:

   **必填变量:**

   | 变量                  | 说明                    | 示例                                                                     |
   | --------------------- | ----------------------- | ------------------------------------------------------------------------ |
   | `JWT_SECRET`          | JWT 签名密钥 (32+ 字符) | 运行 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成 |
   | `DATA_ENCRYPTION_KEY` | 数据加密密钥            | 同上方式生成                                                             |
   | `ENVIRONMENT`         | 运行环境                | `production`                                                             |
   | `CORS_ORIGINS`        | 前端域名                | `https://your-frontend.up.railway.app`                                   |
   | `DATABASE_URL`        | PostgreSQL 连接         | Railway 自动注入                                                         |
   | `REDIS_URL`           | Redis 连接              | Railway 自动注入                                                         |

   **品牌定制 (可选):**

   | 变量            | 说明     | 默认值                     |
   | --------------- | -------- | -------------------------- |
   | `BRAND_NAME`    | 品牌名称 | `BITRUN`                   |
   | `BRAND_TAGLINE` | 品牌标语 | `AI-Powered Trading Agent` |

4. **前端服务** 设置以下环境变量:

   **必填变量:**

   | 变量                  | 说明           | 示例                                          |
   | --------------------- | -------------- | --------------------------------------------- |
   | `NEXT_PUBLIC_API_URL` | 后端 API 地址  | `https://your-backend.up.railway.app/api`     |
   | `NEXT_PUBLIC_WS_URL`  | WebSocket 地址 | `wss://your-backend.up.railway.app/api/v1/ws` |

   **品牌与主题 (可选):**

   | 变量                             | 说明          | 默认值                     |
   | -------------------------------- | ------------- | -------------------------- |
   | `NEXT_PUBLIC_BRAND_NAME`         | 品牌名称      | `BITRUN`                   |
   | `NEXT_PUBLIC_BRAND_TAGLINE`      | 品牌标语      | `AI-Powered Trading Agent` |
   | `NEXT_PUBLIC_BRAND_THEME_PRESET` | 主题预设      | `bitrun` / `binance`       |
   | `NEXT_PUBLIC_BRAND_LOGO_DEFAULT` | 默认 Logo URL | -                          |
   | `NEXT_PUBLIC_BRAND_LOGO_ICON`    | 图标 Logo URL | -                          |

> 详细配置请查看 [Railway 部署指南](docs/deployment.md#railway-部署)

### 一键部署（云服务器）

```bash
# 本地/开发环境 (localhost, 无 SSL)
curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/scripts/install.sh | bash

# 生产环境 (域名 + SSL)
curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/scripts/install.sh | bash -s -- --prod
```

自动检查 Docker 环境、拉取镜像、生成密钥、启动全部服务。

### 本地一键启动 (推荐)

```bash
git clone <repository-url>
cd bitrun
./scripts/quick-start.sh
```

脚本会自动检查依赖、创建配置文件、启动所有服务并运行数据库迁移。

### Docker 手动启动

```bash
# 1. 复制环境配置
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# 2. 启动开发环境
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 3. 运行数据库迁移
docker compose exec backend alembic upgrade head

# 4. 访问应用
#    前端: http://localhost:3000
#    后端 API: http://localhost:8000
#    API 文档: http://localhost:8000/api/v1/docs
```

### 本地开发

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py

# 前端
cd frontend
npm install
npm run dev
```

> 详细说明请查看 [快速开始指南](docs/getting-started.md)

## 环境变量

### 后端 (`backend/.env`)

#### 基础配置

| 变量          | 说明         | 默认值        |
| ------------- | ------------ | ------------- |
| `ENVIRONMENT` | 运行环境     | `development` |
| `HOST`        | 服务监听地址 | `0.0.0.0`     |
| `PORT`        | 服务监听端口 | `8000`        |

#### 数据库

| 变量           | 说明                  | 默认值                                                         |
| -------------- | --------------------- | -------------------------------------------------------------- |
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql+asyncpg://postgres:postgres@localhost:5432/bitrun` |
| `REDIS_URL`    | Redis 连接字符串      | `redis://localhost:6379/0`                                     |

#### 安全

| 变量                           | 说明                     | 默认值                    |
| ------------------------------ | ------------------------ | ------------------------- |
| `JWT_SECRET`                   | JWT 签名密钥             | 留空自动生成 (重启后失效) |
| `DATA_ENCRYPTION_KEY`          | AES-256 数据加密密钥     | 留空自动生成 (重启后失效) |
| `TRANSPORT_ENCRYPTION_ENABLED` | 启用传输加密 (RSA+AES)   | `false`                   |
| `CORS_ORIGINS`                 | CORS 允许的源 (逗号分隔) | `http://localhost:3000`   |

#### Worker 配置

| 变量             | 说明                    | 默认值 |
| ---------------- | ----------------------- | ------ |
| `WORKER_ENABLED` | 是否启用策略执行 Worker | `true` |

#### 通知配置

| 变量                  | 说明                                    |
| --------------------- | --------------------------------------- |
| `TELEGRAM_BOT_TOKEN`  | Telegram Bot Token (从 @BotFather 获取) |
| `TELEGRAM_CHAT_ID`    | Telegram Chat ID (从 @userinfobot 获取) |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL                     |
| `RESEND_API_KEY`      | Resend 邮件 API Key                     |
| `RESEND_FROM`         | 发件人邮箱 (需在 Resend 验证域名)       |

#### 代理配置

| 变量        | 说明                                                |
| ----------- | --------------------------------------------------- |
| `PROXY_URL` | 代理地址 (用于 Bybit、OKX 等受地域限制的交易所 API) |

#### 监控

| 变量         | 说明                |
| ------------ | ------------------- |
| `SENTRY_DSN` | Sentry 错误追踪 DSN |

#### 品牌配置 (后端通知用)

| 变量                | 说明     | 默认值                               |
| ------------------- | -------- | ------------------------------------ |
| `BRAND_NAME`        | 品牌名称 | `BITRUN`                             |
| `BRAND_TAGLINE`     | 品牌标语 | `AI-Powered Trading Agent`           |
| `BRAND_DESCRIPTION` | 品牌描述 | `Prompt-driven automated trading...` |

#### 管理员账户 (首次启动自动创建)

| 变量             | 说明       | 默认值              |
| ---------------- | ---------- | ------------------- |
| `ADMIN_EMAIL`    | 管理员邮箱 | `admin@example.com` |
| `ADMIN_PASSWORD` | 管理员密码 | ⚠️ 生产环境必须修改 |
| `ADMIN_NAME`     | 管理员名称 | `Admin`             |

> AI Provider 的 API Key 通过应用内「模型管理」页面配置，加密存储在数据库中。

### 前端 (`frontend/.env.local`)

#### API 配置

| 变量                  | 说明           | 默认值                          |
| --------------------- | -------------- | ------------------------------- |
| `NEXT_PUBLIC_API_URL` | 后端 API 地址  | `http://localhost:8000/api/v1`  |
| `NEXT_PUBLIC_WS_URL`  | WebSocket 地址 | `ws://localhost:8000/api/v1/ws` |

#### 品牌配置

| 变量                            | 说明     | 默认值                     |
| ------------------------------- | -------- | -------------------------- |
| `NEXT_PUBLIC_BRAND_NAME`        | 品牌名称 | `BITRUN`                   |
| `NEXT_PUBLIC_BRAND_SHORT_NAME`  | 品牌简称 | `BITRUN`                   |
| `NEXT_PUBLIC_BRAND_TAGLINE`     | 品牌标语 | `AI-Powered Trading Agent` |
| `NEXT_PUBLIC_BRAND_DESCRIPTION` | 品牌描述 | -                          |

#### 品牌资源

| 变量                                      | 说明                            |
| ----------------------------------------- | ------------------------------- |
| `NEXT_PUBLIC_BRAND_LOGO_DEFAULT`          | 默认 Logo URL                   |
| `NEXT_PUBLIC_BRAND_LOGO_COMPACT`          | 紧凑 Logo URL                   |
| `NEXT_PUBLIC_BRAND_LOGO_ICON`             | 图标 Logo URL                   |
| `NEXT_PUBLIC_BRAND_FAVICON`               | Favicon 路径                    |
| `NEXT_PUBLIC_BRAND_THEME_PRESET`          | 主题预设 (`bitrun` / `binance`) |
| `NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE` | 主题颜色覆盖 (JSON 格式)        |

#### 法律与链接

| 变量                                 | 说明         | 默认值     |
| ------------------------------------ | ------------ | ---------- |
| `NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER` | 版权持有者   | `BITRUN`   |
| `NEXT_PUBLIC_BRAND_TERMS_URL`        | 服务条款 URL | `/terms`   |
| `NEXT_PUBLIC_BRAND_PRIVACY_URL`      | 隐私政策 URL | `/privacy` |
| `NEXT_PUBLIC_BRAND_HOMEPAGE_URL`     | 官网 URL     | -          |
| `NEXT_PUBLIC_BRAND_DOCS_URL`         | 文档 URL     | -          |
| `NEXT_PUBLIC_BRAND_SUPPORT_URL`      | 支持 URL     | -          |

### 生产环境 (docker-compose.prod.yml)

生产环境需要额外配置以下变量：

| 变量                | 说明                            | 必填               |
| ------------------- | ------------------------------- | ------------------ |
| `POSTGRES_DB`       | 数据库名称                      | 否 (默认 `bitrun`) |
| `POSTGRES_USER`     | 数据库用户                      | 否 (默认 `bitrun`) |
| `POSTGRES_PASSWORD` | 数据库密码                      | **是**             |
| `REDIS_PASSWORD`    | Redis 密码                      | **是**             |
| `FRONTEND_DOMAIN`   | 前端域名 (如 `app.example.com`) | **是**             |
| `BACKEND_DOMAIN`    | 后端域名 (如 `api.example.com`) | **是**             |

> 完整变量列表请查看 `backend/.env.example` 和 `frontend/.env.local.example`。

## 访问地址

| 服务      | 开发环境                          | 生产环境                            |
| --------- | --------------------------------- | ----------------------------------- |
| 前端      | http://localhost:3000             | https://app.example.com             |
| 后端 API  | http://localhost:8000             | https://api.example.com             |
| API 文档  | http://localhost:8000/api/v1/docs | https://api.example.com/api/v1/docs |
| WebSocket | ws://localhost:8000/api/v1/ws     | wss://api.example.com/api/v1/ws     |

## 文档

| 文档                                              | 说明                                                    |
| ------------------------------------------------- | ------------------------------------------------------- |
| [架构概览](docs/architecture.md)                  | 系统架构图、模块职责、数据流、技术选型                  |
| [快速开始](docs/getting-started.md)               | 环境要求、安装步骤、首次配置、常见问题                  |
| [策略模块](docs/strategy-guide.md)                | AI 策略原理、策略工作室、量化策略、Debate Engine        |
| [回测模块](docs/backtest-guide.md)                | 回测引擎架构、配置运行、指标说明                        |
| [交易所对接](docs/exchange-setup.md)              | API Key 获取、Hyperliquid 配置、代理设置                |
| [AI 模型配置](docs/ai-models.md)                  | Provider 列表、API Key 获取、模型选择建议               |
| [部署指南](docs/deployment.md)                    | Docker 部署、SSL/HTTPS、Nginx、GitHub Actions、监控告警 |
| [开发者指南](docs/development.md)                 | 本地开发、代码规范、测试、数据库迁移                    |
| [API 参考](docs/api-reference.md)                 | REST API、WebSocket API、认证机制                       |
| [Redis 备份与恢复](docs/redis-backup-recovery.md) | Redis 数据备份、恢复、自动备份配置                      |

## License

Private - All rights reserved.
