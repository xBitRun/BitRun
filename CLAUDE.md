# BitRun - Claude Code 项目指南

> AI 驱动的加密货币交易代理平台

## 项目概览

BitRun 是一个 AI 驱动的加密货币交易代理平台，支持自然语言定义交易策略、多模型 AI 智能决策和多交易所统一执行。

### 技术栈

| 层级     | 技术                                               |
| -------- | -------------------------------------------------- |
| 后端     | FastAPI (Python 3.12) + PostgreSQL + Redis         |
| 前端     | Next.js 16 + React 19 + Tailwind CSS 4 + shadcn/ui |
| 状态管理 | Zustand + SWR                                      |
| 国际化   | next-intl (中文/English)                           |
| 测试     | Jest + Playwright                                  |

### 目录结构

```
bitrun/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/routes/       # API 路由 (24 个模块)
│   │   │   ├── auth.py       #   认证
│   │   │   ├── accounts.py   #   交易所账户
│   │   │   ├── agents.py     #   Agent 执行实例 (NEW)
│   │   │   ├── strategies.py #   AI 策略
│   │   │   ├── quant_strategies.py # 量化策略
│   │   │   ├── decisions.py  #   决策记录
│   │   │   ├── backtest.py   #   回测
│   │   │   ├── dashboard.py  #   仪表盘
│   │   │   ├── models.py     #   AI 模型
│   │   │   ├── providers.py  #   AI Provider
│   │   │   ├── analytics.py  #   数据分析 (NEW)
│   │   │   ├── wallets.py    #   钱包管理 (NEW)
│   │   │   ├── recharge.py   #   充值 (NEW)
│   │   │   ├── channels.py   #   通知渠道 (NEW)
│   │   │   ├── accounting.py #   账务统计 (NEW)
│   │   │   ├── brand.py      #   品牌定制 (NEW)
│   │   │   ├── system.py     #   系统配置 (NEW)
│   │   │   ├── workers.py    #   Worker 管理
│   │   │   ├── data.py       #   市场数据
│   │   │   ├── metrics.py    #   Prometheus 指标
│   │   │   ├── notifications.py # 通知
│   │   │   ├── crypto.py     #   传输加密
│   │   │   └── ws.py         #   WebSocket
│   │   ├── db/repositories/  # Repository 层 (11 个)
│   │   │   ├── account.py    #   账户 CRUD
│   │   │   ├── agent.py      #   Agent CRUD (NEW)
│   │   │   ├── strategy.py   #   策略 CRUD
│   │   │   ├── quant_strategy.py # 量化策略 CRUD
│   │   │   ├── decision.py   #   决策 CRUD
│   │   │   ├── backtest.py   #   回测结果 CRUD (NEW)
│   │   │   ├── channel.py    #   渠道 CRUD (NEW)
│   │   │   ├── recharge.py   #   充值记录 CRUD (NEW)
│   │   │   ├── wallet.py     #   钱包 CRUD (NEW)
│   │   │   └── user.py       #   用户 CRUD
│   │   ├── services/         # 业务逻辑层 (20 个)
│   │   │   ├── ai/           #   AI 客户端 (9+ Provider)
│   │   │   ├── strategy_engine.py    # AI 策略引擎
│   │   │   ├── quant_engine.py       # 量化策略引擎
│   │   │   ├── debate_engine.py      # 辩论引擎
│   │   │   ├── order_manager.py      # 订单管理
│   │   │   ├── position_service.py   # 持仓服务
│   │   │   ├── agent_position_service.py # Agent 持仓 (NEW)
│   │   │   ├── wallet_service.py     # 钱包服务 (NEW)
│   │   │   ├── channel_service.py    # 渠道服务 (NEW)
│   │   │   ├── invite_service.py     # 邀请服务 (NEW)
│   │   │   ├── pnl_service.py        # 盈亏服务 (NEW)
│   │   │   ├── worker_heartbeat.py   # Worker 心跳 (NEW)
│   │   │   └── ...
│   │   ├── traders/          # 交易所适配器
│   │   └── workers/          # 后台 Worker (Unified 架构)
│   │       ├── unified_manager.py  # 统一管理器
│   │       ├── base_backend.py     # 抽象基类
│   │       ├── ai_backend.py       # AI Backend
│   │       ├── quant_backend.py    # Quant Backend
│   │       ├── lifecycle.py        # 生命周期管理
│   │       ├── queue.py            # ARQ 队列
│   │       └── tasks.py            # 任务定义
│   └── tests/                # 测试套件
├── frontend/                 # Next.js 前端
│   ├── src/
│   │   ├── app/[locale]/     # 国际化路由
│   │   │   ├── (auth)/       #   登录
│   │   │   ├── (dashboard)/  #   Dashboard 页面
│   │   │   │   ├── overview/ #     首页
│   │   │   │   ├── agents/   #     Agent 管理 (NEW)
│   │   │   │   ├── strategies/ #    策略配置
│   │   │   │   ├── accounts/ #     账户管理
│   │   │   │   ├── models/   #     AI 模型
│   │   │   │   ├── backtest/ #     回测
│   │   │   │   ├── decisions/ #    决策记录
│   │   │   │   ├── analytics/ #    数据分析 (NEW)
│   │   │   │   ├── wallet/   #     钱包管理 (NEW)
│   │   │   │   │   └── recharge/ # 充值 (NEW)
│   │   │   │   ├── channel/  #     通知渠道 (NEW)
│   │   │   │   ├── invite/   #     邀请系统 (NEW)
│   │   │   │   ├── marketplace/ #   策略市场 (NEW)
│   │   │   │   ├── settings/ #     设置
│   │   │   │   └── admin/    #     管理后台 (NEW)
│   │   │   │       ├── recharge/
│   │   │   │       ├── accounting/
│   │   │   │       └── channels/
│   │   │   └── (landing)/    #   Landing 页面
│   │   ├── components/       # React 组件
│   │   ├── hooks/            # SWR Hooks
│   │   ├── stores/           # Zustand 状态管理
│   │   └── messages/         # i18n 翻译 (en.json/zh.json)
│   └── e2e/                  # Playwright E2E
└── docs/                     # 项目文档
```

---

## 开发规范

### 1. 工作流程

1. **提案优先**: 先提出解决方案 → 等待确认 → 实施
2. **文档先行**: 编码前检查 `docs/` 是否有现有模式，架构变更时更新文档

### 2. 国际化 (i18n) - 关键规范

**绝对禁止在 `.tsx` 文件中硬编码用户可见文本**

```tsx
// ✅ 正确
import { useTranslations } from 'next-intl';

export function MyComponent() {
  const t = useTranslations('myModule');
  return <Button>{t('buttonLabel')}</Button>;
}

// ❌ 错误
export function MyComponent() {
  return <Button>点击我</Button>;
}
```

**翻译文件位置**: `frontend/src/messages/zh.json` 和 `frontend/src/messages/en.json`

**必须翻译的内容**:

- 按钮标签、菜单项、标题、描述
- Toast 消息 (`toast.success()`, `toast.error()`)
- 错误消息、加载状态、占位符
- 表单标签、验证消息、空状态

**无需翻译的内容**:

- 技术标识符 (ID、Key)
- URL、文件路径
- 代码/调试输出
- 货币符号 ($)、单位 (%, x)

**Key 命名规范**:

- 使用点号: `module.section.key`
- 按功能分组: `accounts.toast.success`, `agents.error.loadFailed`
- 通用 Key 放 `common.*`: `common.loading`, `common.retry`

### 3. Git Commit 规范 - 关键规范

**格式**: `<emoji> <type>: <主标题>`

| Emoji | Type     | 用途          |
| ----- | -------- | ------------- |
| ✨    | feat     | 新功能        |
| 🐛    | fix      | Bug 修复      |
| 🎨    | style    | UI 样式调整   |
| ♻️    | refactor | 代码重构      |
| 📝    | docs     | 文档更新      |
| 🔧    | chore    | 配置/依赖更新 |
| ✅    | test     | 测试相关      |
| 🚀    | perf     | 性能优化      |

**标题规则**:

- 使用中文
- 简洁明了，不超过 50 字符
- 动词开头 (新增/修复/优化/调整/重构)

**示例**:

```bash
✨ feat: 新增用户登录功能
✨ feat: 新增交易模块 UI
- 实现 Spot 现货交易面板
- 实现 Equities 权益交易面板
🐛 fix: 修复订单提交失败问题
- 修正签名参数格式
```

### 4. 测试规范 - 关键规范

#### 边界值强制覆盖

- 对带约束的字段 (如 Pydantic `ge=1`, `le=50`)，**必须测试边界值和非法值**
- 边界值: 约束边界本身及其两侧
- 示例: `leverage` 字段 `ge=1, le=50` → 必须覆盖 `0, 1, 50, 51, -1, None`

#### 断言必须验证核心行为

```python
# ❌ 错误
assert result is not None  # should clamp leverage

# ✅ 正确
assert result.decisions[0].leverage == 3  # clamped from 5
```

#### 异常路径必须覆盖

- 代码中每个 `except` 分支都要有对应的测试用例
- 捕获多种异常类型时，每种类型都需要独立的测试用例

#### 外部输入必须模拟真实脏数据

- 解析 AI/第三方 API 响应的代码，测试数据**不能只用理想格式**
- 必须包含: 缺失字段、类型错误、越界值、空值、额外字段

#### 修 Bug 必须补回归测试

- 每次 bug fix **必须附带**能复现该 bug 的测试用例
- 测试应在修复前失败、修复后通过

---

## 常用命令

### 开发环境

```bash
# 一键启动 (推荐)
./scripts/quick-start.sh

# Docker 开发环境
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 后端本地开发
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py

# 前端本地开发
cd frontend
npm install
npm run dev

# 数据库迁移
docker compose exec backend alembic upgrade head
```

### 测试

```bash
# 前端测试
cd frontend
npm test                    # 运行所有测试
npm test -- --coverage      # 带覆盖率

# 后端测试
cd backend
pytest                      # 运行所有测试
pytest --cov=app            # 带覆盖率
```

---

## 环境变量

### 后端 Worker 配置

```bash
# Worker 错误处理
WORKER_MAX_CONSECUTIVE_ERRORS=5
WORKER_ERROR_WINDOW_SECONDS=600
WORKER_RETRY_BASE_DELAY=2.0
WORKER_RETRY_MAX_DELAY=60.0

# Worker 心跳
WORKER_HEARTBEAT_INTERVAL_SECONDS=60
WORKER_HEARTBEAT_TIMEOUT_SECONDS=300
WORKER_HEARTBEAT_RETRY_ATTEMPTS=3
```

### 生产环境

```bash
# 域名配置
FRONTEND_DOMAIN=app.qemind.xyz
BACKEND_DOMAIN=api.qemind.xyz

# 安全密钥
JWT_SECRET=<32+ 字符随机串>
DATA_ENCRYPTION_KEY=<32 字节 base64>
POSTGRES_PASSWORD=<强密码>
REDIS_PASSWORD=<强密码>
```

---

## 关键文件

| 文件                                | 用途             |
| ----------------------------------- | ---------------- |
| `frontend/src/messages/zh.json`     | 中文翻译         |
| `frontend/src/messages/en.json`     | 英文翻译         |
| `frontend/src/lib/api/endpoints.ts` | API 端点定义     |
| `frontend/src/hooks/`               | SWR Hooks        |
| `frontend/src/stores/`              | Zustand 状态管理 |
| `backend/app/services/`             | 业务逻辑层       |
| `backend/app/api/routes/`           | API 路由         |
| `backend/app/workers/unified_manager.py` | 统一 Worker 管理 (NEW) |
| `backend/app/services/worker_heartbeat.py` | 心跳追踪 (NEW) |
| `backend/app/api/routes/agents.py`  | Agent CRUD + Worker 控制 (NEW) |
| `backend/app/api/routes/wallets.py` | 钱包 API (NEW) |
| `backend/app/api/routes/channels.py` | 通知渠道 (NEW) |
| `docs/deployment.md`                | 部署指南         |

---

## 访问地址

| 服务     | 开发环境                    | 生产环境                         |
| -------- | --------------------------- | -------------------------------- |
| 前端     | http://localhost:3000       | https://app.qemind.xyz           |
| 后端 API | http://localhost:8000       | https://api.qemind.xyz           |
| API 文档 | http://localhost:8000/api/v1/docs | https://api.qemind.xyz/api/v1/docs |
