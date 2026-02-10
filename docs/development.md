# 开发者指南

本文档面向参与 BITRUN 开发的工程师，涵盖本地开发环境搭建、代码结构、测试、代码规范和数据库迁移。

## 本地开发环境搭建

### 方式一：使用开发脚本

```bash
./scripts/start-dev.sh
```

脚本会自动：
1. 启动 PostgreSQL 和 Redis (Docker)
2. 运行数据库迁移
3. 检测端口冲突
4. 可选启动后端和前端进程

### 方式二：Docker 开发环境

```bash
./scripts/docker-dev.sh build   # 构建镜像
./scripts/docker-dev.sh         # 启动所有服务
./scripts/docker-dev.sh logs    # 查看日志
./scripts/docker-dev.sh shell   # 进入后端容器 shell
./scripts/docker-dev.sh migrate # 运行迁移
./scripts/docker-dev.sh down    # 停止
```

此方式使用 `docker-compose.yml` + `docker-compose.dev.yml`，前后端代码通过 volume 挂载，支持热重载。

### 方式三：完全本地开发

#### 前置条件

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (或通过 Docker 启动)
- Redis 7 (或通过 Docker 启动)

#### 启动基础设施

```bash
docker compose up -d postgres redis
```

#### 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置 DATABASE_URL, REDIS_URL 等

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器 (自动重载)
python run.py
```

#### 启动前端

```bash
cd frontend
npm install

# 配置环境变量
cp .env.local.example .env.local
# 编辑 .env.local 设置 API 地址

# 启动开发服务器
npm run dev
```

## 代码结构说明

### 后端 (`backend/`)

```
backend/
├── app/
│   ├── api/                      # API 层
│   │   ├── main.py               #   FastAPI 应用入口，中间件配置，路由注册
│   │   ├── websocket.py          #   WebSocket 连接管理器和事件发布器
│   │   └── routes/               #   路由模块 (每个功能一个文件)
│   │       ├── auth.py           #     认证 (注册/登录/刷新/登出)
│   │       ├── accounts.py       #     交易所账户管理
│   │       ├── strategies.py     #     AI Agent 策略
│   │       ├── quant_strategies.py #   量化策略
│   │       ├── decisions.py      #     决策记录查询
│   │       ├── backtest.py       #     回测
│   │       ├── dashboard.py      #     仪表盘统计
│   │       ├── models.py         #     AI 模型查询
│   │       ├── providers.py      #     AI Provider 管理
│   │       ├── workers.py        #     Worker 状态和控制
│   │       ├── data.py           #     市场数据和缓存
│   │       ├── metrics.py        #     Prometheus 指标
│   │       ├── notifications.py  #     通知管理
│   │       ├── crypto.py         #     传输加密
│   │       └── ws.py             #     WebSocket 端点
│   │
│   ├── backtest/                 # 回测模块
│   │   ├── engine.py             #   回测引擎主编排
│   │   ├── simulator.py          #   模拟交易器
│   │   └── data_provider.py      #   历史数据提供
│   │
│   ├── core/                     # 核心基础设施
│   │   ├── config.py             #   应用配置 (pydantic-settings)
│   │   ├── security.py           #   加密服务 (AES-256, RSA)
│   │   ├── dependencies.py       #   FastAPI 依赖注入 (认证、限流)
│   │   ├── errors.py             #   异常定义和处理
│   │   └── circuit_breaker.py    #   熔断器 (保护外部服务调用)
│   │
│   ├── db/                       # 数据库层
│   │   ├── database.py           #   数据库连接和会话管理
│   │   ├── models.py             #   SQLAlchemy 模型定义
│   │   └── repositories/         #   Repository 模式数据访问
│   │       ├── account.py        #     账户 CRUD
│   │       ├── strategy.py       #     策略 CRUD
│   │       ├── quant_strategy.py #     量化策略 CRUD
│   │       ├── decision.py       #     决策记录 CRUD
│   │       └── user.py           #     用户 CRUD
│   │
│   ├── models/                   # Pydantic 领域模型
│   │   ├── decision.py           #   决策模型 (ActionType, DecisionResponse)
│   │   ├── strategy.py           #   策略配置 (StrategyConfig, RiskControls)
│   │   ├── quant_strategy.py     #   量化策略模型 (Grid/DCA/RSI 配置)
│   │   ├── debate.py             #   辩论模型 (DebateConfig, DebateResult)
│   │   └── market_context.py     #   市场上下文 (技术指标)
│   │
│   ├── monitoring/               # 监控
│   │   ├── middleware.py          #   Prometheus 中间件
│   │   ├── metrics.py            #   指标采集器
│   │   └── sentry.py             #   Sentry 初始化
│   │
│   ├── services/                 # 业务逻辑层
│   │   ├── ai/                   #   AI 客户端
│   │   │   ├── base.py           #     基类 (BaseAIClient, AIProvider)
│   │   │   ├── factory.py        #     工厂 (AIClientFactory)
│   │   │   ├── credentials.py    #     凭证解析 (Provider → API Key)
│   │   │   ├── deepseek_client.py #    DeepSeek 实现
│   │   │   ├── qwen_client.py    #     Qwen 实现
│   │   │   ├── openai_client.py  #     OpenAI 实现
│   │   │   ├── gemini_client.py  #     Gemini 实现
│   │   │   ├── zhipu_client.py   #     Zhipu 实现
│   │   │   ├── minimax_client.py #     MiniMax 实现
│   │   │   ├── kimi_client.py    #     Kimi 实现
│   │   │   ├── grok_client.py    #     Grok 实现
│   │   │   └── custom_client.py  #     自定义 OpenAI 兼容
│   │   ├── strategy_engine.py    #   AI 策略执行引擎
│   │   ├── prompt_builder.py     #   Prompt 构建器
│   │   ├── prompt_templates.py   #   Prompt 模板 (中英文)
│   │   ├── decision_parser.py    #   决策解析器
│   │   ├── debate_engine.py      #   多模型辩论引擎
│   │   ├── quant_engine.py       #   量化策略引擎 (Grid/DCA/RSI)
│   │   ├── order_manager.py      #   订单生命周期管理
│   │   ├── position_service.py   #   持仓跟踪与管理
│   │   ├── data_access_layer.py  #   统一数据访问 (K 线 + 指标)
│   │   ├── indicator_calculator.py # 技术指标计算
│   │   ├── market_data_cache.py  #   市场数据 Redis 缓存
│   │   ├── redis_service.py      #   Redis 操作封装
│   │   └── notifications.py      #   通知服务
│   │
│   ├── traders/                  # 交易所适配层
│   │   ├── base.py               #   BaseTrader 抽象接口
│   │   ├── ccxt_trader.py        #   CCXT 统一交易适配器
│   │   ├── exchange_pool.py      #   交易所连接池
│   │   └── hyperliquid.py        #   Hyperliquid 工具函数
│   │
│   └── workers/                  # 后台任务
│       ├── execution_worker.py   #   AI 策略执行 Worker
│       ├── quant_worker.py       #   量化策略执行 Worker
│       ├── queue.py              #   ARQ 分布式任务队列
│       └── tasks.py              #   任务定义
│
├── alembic/                      # 数据库迁移
│   ├── env.py                    #   迁移环境 (异步支持)
│   └── versions/                 #   迁移脚本
│       ├── 001_initial_schema.py
│       ├── 002_add_ai_model_to_strategies.py
│       ├── ...
│       └── 010_add_debate_fields_to_decisions.py
│
├── tests/                        # 测试套件
├── alembic.ini                   # Alembic 配置
├── requirements.txt              # Python 依赖
├── Dockerfile                    # 容器定义
├── .env.example                  # 环境变量模板
├── run.py                        # 开发服务器入口
└── run_worker.py                 # Worker 进程入口
```

### 前端 (`frontend/`)

```
frontend/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── layout.tsx            #   根布局 (字体、元数据)
│   │   ├── [locale]/             #   国际化路由
│   │   │   ├── layout.tsx        #     Locale 布局 (i18n Provider)
│   │   │   ├── (auth)/           #     认证页面组
│   │   │   │   └── login/        #       登录页
│   │   │   ├── (dashboard)/      #     Dashboard 页面组
│   │   │   │   ├── overview/     #       首页 (Dashboard)
│   │   │   │   ├── agents/       #       AI Agent 策略
│   │   │   │   ├── strategies/   #       量化策略
│   │   │   │   ├── accounts/     #       交易所账户
│   │   │   │   ├── models/       #       AI 模型管理
│   │   │   │   ├── backtest/     #       回测
│   │   │   │   ├── decisions/    #       决策记录
│   │   │   │   └── settings/     #       设置
│   │   │   └── (landing)/        #     Landing 页面组
│   │   └── middleware.ts         #   路由中间件 (认证 + 国际化)
│   │
│   ├── components/               # React 组件
│   │   ├── ui/                   #   shadcn/ui 基础组件 (Button, Card, Dialog...)
│   │   ├── auth/                 #   认证组件 (AuthGuard)
│   │   ├── layout/               #   布局组件 (Sidebar, Header)
│   │   ├── strategy-studio/      #   策略工作室 (5 Tab 配置界面)
│   │   ├── charts/               #   图表组件 (Recharts + TradingView)
│   │   ├── decisions/            #   决策展示组件
│   │   ├── dialogs/              #   模态对话框
│   │   ├── landing/              #   Landing 页面组件
│   │   ├── onboarding/           #   新手引导
│   │   ├── error-boundary/       #   错误边界
│   │   └── list-page/            #   列表页工具组件
│   │
│   ├── hooks/                    # 自定义 Hooks
│   │   ├── use-accounts.ts       #   账户管理
│   │   ├── use-backtest.ts       #   回测操作
│   │   ├── use-dashboard.ts      #   仪表盘统计
│   │   ├── use-decisions.ts      #   决策记录
│   │   ├── use-models.ts         #   AI 模型管理
│   │   ├── use-providers.ts      #   AI Provider 管理
│   │   ├── use-quant-strategies.ts # 量化策略
│   │   ├── use-strategies.ts     #   AI 策略管理
│   │   ├── use-strategy-studio.ts #  策略工作室状态
│   │   ├── use-websocket.ts      #   WebSocket 连接
│   │   └── use-mobile.ts         #   移动端检测
│   │
│   ├── lib/                      # 工具和客户端
│   │   ├── api/
│   │   │   ├── client.ts         #     HTTP 客户端 (Token 自动刷新)
│   │   │   ├── endpoints.ts      #     API 端点定义
│   │   │   └── schemas.ts        #     Zod 校验 Schema
│   │   ├── logger.ts             #   条件日志 (仅开发环境)
│   │   └── utils.ts              #   通用工具函数
│   │
│   ├── stores/                   # Zustand 状态管理
│   │   ├── auth-store.ts         #   认证状态 (用户、Token、登录/登出)
│   │   └── app-store.ts          #   应用状态 (侧边栏、主题、通知)
│   │
│   ├── messages/                 # i18n 翻译
│   │   ├── en.json               #   English
│   │   └── zh.json               #   简体中文
│   │
│   ├── i18n/                     # 国际化配置
│   │   ├── routing.ts            #   路由配置
│   │   ├── request.ts            #   请求处理
│   │   └── navigation.ts         #   类型化导航辅助
│   │
│   ├── providers/                # React Context Providers
│   │   ├── index.tsx             #   主 Provider 包装器
│   │   └── swr-provider.tsx      #   SWR 全局配置
│   │
│   ├── types/                    # TypeScript 类型定义
│   │
│   └── __tests__/                # Jest 单元测试
│
├── e2e/                          # Playwright E2E 测试
├── Dockerfile                    # 多阶段构建
├── package.json                  # Node.js 依赖
├── next.config.ts                # Next.js 配置
├── tsconfig.json                 # TypeScript 配置
└── .env.local.example            # 环境变量模板
```

## 测试

### 后端测试

```bash
cd backend
source venv/bin/activate

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_strategy_engine.py

# 带覆盖率
pytest --coverage

# 详细输出
pytest -v

# 仅运行标记的测试
pytest -m "not integration"
```

测试目录包含 30+ 测试文件，覆盖：
- 服务层单元测试 (AI 客户端、策略引擎、决策解析等)
- API 路由集成测试
- 数据库 Repository 测试
- 使用 `testcontainers` 的集成测试
- 使用 `fakeredis` 的 Redis 模拟测试

### 前端测试

```bash
cd frontend

# 单元测试 (Jest)
npm test

# 监视模式
npm run test:watch

# 覆盖率报告
npm run test:coverage

# E2E 测试 (Playwright)
npm run test:e2e

# E2E 测试 UI 模式
npm run test:e2e:ui
```

## 代码规范

### Git Commit 规范

使用 emoji 前缀的中文提交信息：

| Emoji | 类型 | 用途 |
|-------|------|------|
| ✨ | `feat` | 新功能 |
| 🐛 | `fix` | Bug 修复 |
| 🎨 | `style` | UI 样式调整 |
| ♻️ | `refactor` | 代码重构 |
| 📝 | `docs` | 文档更新 |
| 🔧 | `chore` | 配置/依赖更新 |
| ✅ | `test` | 测试相关 |
| 🚀 | `perf` | 性能优化 |

**格式**：`<emoji> <type>: <主标题>`

**示例**：

```
✨ feat: 新增用户登录功能

✨ feat: 新增交易模块 UI
- 实现 Spot 现货交易面板
- 实现 Equities 权益交易面板

🐛 fix: 修复订单提交失败问题
- 修正签名参数格式
```

**规则**：
- 标题使用中文，简洁明了，不超过 50 字符
- 动词开头（新增/修复/优化/调整/重构）
- 每次提交只做一件事
- 相关联的改动合并为一次提交

### 国际化 (i18n) 规范

**核心原则**：所有用户可见文本必须使用翻译函数，禁止硬编码。

```tsx
// 正确
import { useTranslations } from "next-intl";
export function MyComponent() {
  const t = useTranslations("myModule");
  return <Button>{t("buttonLabel")}</Button>;
}

// 错误
export function MyComponent() {
  return <Button>点击</Button>;
}
```

**必须翻译的内容**：
- 按钮标签、菜单项、标题、描述
- Toast 消息 (`toast.success()`, `toast.error()`)
- 错误消息、加载状态、占位符
- 表单标签、验证消息
- 空状态、兜底文本

**不需要翻译的内容**：
- 技术标识符 (ID, Key)
- URL、文件路径
- 代码/调试输出
- 货币符号 ($)、单位 (%, x)

**翻译 Key 命名**：
- 点分法：`module.section.key`
- 按功能分组：`accounts.toast.success`、`agents.error.loadFailed`
- 公共 Key：`common.loading`、`common.retry`、`common.cancel`

**添加新文本的流程**：
1. 在 `frontend/src/messages/zh.json` 和 `en.json` 中添加 Key
2. 在组件中使用 `t("key")`
3. 动态内容使用 `t("key", { count: 5 })`

### 后端代码风格

- 格式化：`black`
- Lint：`ruff`
- 类型注解：建议对所有公共函数添加类型注解
- 异步优先：所有 IO 操作使用 `async/await`

## 数据库迁移

BITRUN 使用 [Alembic](https://alembic.sqlalchemy.org) 管理数据库 Schema 变更。

### 常用命令

```bash
cd backend
source venv/bin/activate

# 查看当前迁移版本
alembic current

# 查看迁移历史
alembic history

# 升级到最新
alembic upgrade head

# 升级一个版本
alembic upgrade +1

# 回退一个版本
alembic downgrade -1

# 回退到指定版本
alembic downgrade <revision>
```

### 创建新迁移

当修改了 `backend/app/db/models.py` 中的数据模型后：

```bash
# 自动生成迁移脚本
alembic revision --autogenerate -m "add_new_table"
```

生成的迁移文件位于 `backend/alembic/versions/`，请检查生成的 SQL 是否正确。

### 迁移最佳实践

1. **先备份**：生产环境迁移前务必备份数据库

```bash
./scripts/deploy.sh backup
```

2. **检查迁移脚本**：自动生成的迁移可能不完美，务必人工审查
3. **不可逆操作**：删除列/表前确保数据已迁移或备份
4. **测试迁移**：在开发环境测试 upgrade 和 downgrade
5. **Docker 环境**：

```bash
# Docker 中运行迁移
docker compose exec backend alembic upgrade head
```

### 当前迁移历史

| 版本 | 说明 |
|------|------|
| 001 | 初始 Schema (User, Account, Strategy, Decision) |
| 002 | 策略增加 AI 模型字段 |
| 003 | AI Provider 配置表 |
| 004 | Provider 配置增加模型列表 |
| 005 | 决策记录增加市场快照 |
| 006 | 决策记录增加账户快照 |
| 007 | 量化策略表 |
| 008 | 策略持仓表 (strategy_positions) |
| 009 | 交易所账户索引优化 |
| 010 | 决策记录增加辩论字段 (Debate Engine) |

## 相关文档

- [架构概览](architecture.md) — 系统设计和模块划分
- [API 参考](api-reference.md) — API 端点详情
- [部署指南](deployment.md) — 生产环境部署
