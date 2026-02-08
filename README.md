# BITRUN

**AI 驱动的加密货币交易代理平台** — 用自然语言定义交易策略，多模型 AI 智能决策，多交易所统一执行。

## 核心特性

- **Prompt 驱动策略** — 用自然语言描述你的交易逻辑，AI 自动分析市场数据并生成交易决策
- **多模型辩论引擎 (Debate Engine)** — 多个 AI 模型并行分析、投票表决，提升决策质量
- **量化策略引擎** — 内置网格交易 (Grid)、定投 (DCA)、RSI 策略，无需 AI 即可运行
- **多交易所支持** — 通过 CCXT 统一接口对接 Binance、Bybit、OKX，原生支持 Hyperliquid DEX
- **回测系统** — 基于历史数据验证策略表现，支持收益曲线、最大回撤、夏普比率等指标
- **策略工作室** — 可视化配置交易标的、技术指标、风控参数、自定义 Prompt
- **实时监控** — WebSocket 推送交易决策、持仓变动、账户状态，Dashboard 一览全局
- **9+ AI Provider** — DeepSeek、Qwen、Zhipu、MiniMax、Kimi、OpenAI、Gemini、Grok，以及自定义 OpenAI 兼容端点
- **国际化** — 完整的中英文双语界面

## 技术栈

### 后端

| 类别 | 技术 |
|------|------|
| 框架 | FastAPI (Python 3.12) |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 (asyncpg) |
| 缓存 | Redis 7 (AOF 持久化) |
| 任务队列 | ARQ (异步 Redis 队列) |
| AI 集成 | DeepSeek / Qwen / Zhipu / MiniMax / Kimi / OpenAI / Gemini / Grok / Custom |
| 交易对接 | CCXT (统一多交易所) + Hyperliquid SDK |
| 认证 | JWT (access + refresh token) + bcrypt |
| 监控 | Prometheus + Sentry |

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | Next.js 16 (App Router) |
| 语言 | TypeScript 5 |
| UI | React 19 + Tailwind CSS 4 + Radix UI (shadcn/ui) |
| 状态管理 | Zustand + SWR |
| 国际化 | next-intl (中文 / English) |
| 图表 | Recharts |
| 测试 | Jest + Playwright (E2E) |

### 基础设施

| 类别 | 技术 |
|------|------|
| 容器化 | Docker (多阶段构建) |
| 编排 | Docker Compose (开发 / 生产) |
| 反向代理 | Nginx (限流、安全头、WebSocket) |
| 错误追踪 | Sentry (前端 + 后端) |

## 项目结构

```
bitrun/
├── backend/                  # FastAPI 后端应用
│   ├── app/
│   │   ├── api/              #   API 路由 + WebSocket
│   │   │   └── routes/       #   各模块路由 (auth, strategies, accounts...)
│   │   ├── backtest/         #   回测引擎 (Engine + Simulator + DataProvider)
│   │   ├── core/             #   配置、安全、依赖注入
│   │   ├── db/               #   数据库模型 + Repository 层
│   │   ├── models/           #   Pydantic 领域模型
│   │   ├── monitoring/       #   Prometheus + Sentry
│   │   ├── services/         #   业务逻辑层
│   │   │   └── ai/           #     AI 客户端实现 (9+ Provider)
│   │   ├── traders/          #   交易所适配器 (CCXT / Hyperliquid)
│   │   └── workers/          #   后台 Worker (AI 策略 + 量化策略)
│   ├── alembic/              #   数据库迁移
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
├── nginx/                    # Nginx 配置
├── scripts/                  # 部署和开发脚本
│   ├── quick-start.sh        #   一键启动
│   ├── deploy.sh             #   生产部署
│   ├── start-dev.sh          #   本地开发启动
│   ├── docker-dev.sh         #   Docker 开发环境
│   └── health-check.sh       #   健康检查
├── docs/                     # 项目文档
├── docker-compose.yml        # Docker 基础配置
├── docker-compose.dev.yml    # 开发环境覆盖
└── docker-compose.prod.yml   # 生产环境配置
```

## 快速开始

### Railway 一键部署 (云端)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/bitrun)

Railway 部署步骤:

1. 点击上方按钮，创建新项目
2. Railway 会自动添加 PostgreSQL 和 Redis 服务
3. 设置以下环境变量:
   - `JWT_SECRET`: 运行 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成
   - `DATA_ENCRYPTION_KEY`: 同上方式生成
   - `ENVIRONMENT`: 设置为 `production`
   - `CORS_ORIGINS`: 前端 URL (如 `https://your-frontend.up.railway.app`)
4. 前端服务需额外设置:
   - `NEXT_PUBLIC_API_URL`: 后端 API 地址 (如 `https://your-backend.up.railway.app/api`)
   - `NEXT_PUBLIC_WS_URL`: WebSocket 地址 (如 `wss://your-backend.up.railway.app/api/ws`)

> 详细配置请查看 [Railway 部署指南](docs/deployment.md#railway-部署)

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

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接字符串 |
| `REDIS_URL` | Redis 连接字符串 |
| `JWT_SECRET` | JWT 签名密钥 (留空自动生成) |
| `DATA_ENCRYPTION_KEY` | AES-256 数据加密密钥 (留空自动生成) |
| `WORKER_ENABLED` | 是否启用策略执行 Worker (默认 `true`) |
| `PROXY_URL` | 代理地址 (用于受地域限制的交易所 API) |
| `SENTRY_DSN` | Sentry 错误追踪 DSN |

AI Provider 的 API Key 通过应用内「模型管理」页面配置，加密存储在数据库中。

完整变量列表请查看 `backend/.env.example`。

### 前端 (`frontend/.env.local`)

| 变量 | 说明 |
|------|------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 |
| `NEXT_PUBLIC_WS_URL` | WebSocket 地址 |

完整变量列表请查看 `frontend/.env.local.example`。

## 文档

| 文档 | 说明 |
|------|------|
| [架构概览](docs/architecture.md) | 系统架构图、模块职责、数据流、技术选型 |
| [快速开始](docs/getting-started.md) | 环境要求、安装步骤、首次配置、常见问题 |
| [策略模块](docs/strategy-guide.md) | AI 策略原理、策略工作室、量化策略、Debate Engine |
| [回测模块](docs/backtest-guide.md) | 回测引擎架构、配置运行、指标说明 |
| [交易所对接](docs/exchange-setup.md) | API Key 获取、Hyperliquid 配置、代理设置 |
| [AI 模型配置](docs/ai-models.md) | Provider 列表、API Key 获取、模型选择建议 |
| [部署指南](docs/deployment.md) | Docker 部署、SSL/HTTPS、Nginx、监控告警 |
| [开发者指南](docs/development.md) | 本地开发、代码规范、测试、数据库迁移 |
| [API 参考](docs/api-reference.md) | REST API、WebSocket API、认证机制 |

## License

Private - All rights reserved.
