# API 参考文档

BITRUN 后端提供 RESTful API 和 WebSocket API。所有 API 均以 `/api/v1` 为前缀。

## 认证机制

### JWT Bearer Token

大部分 API 端点需要认证。认证流程：

1. 通过 `/api/v1/auth/login` 获取 access_token 和 refresh_token
2. 后续请求在 Header 中携带 access_token

```
Authorization: Bearer <access_token>
```

### Token 说明

| Token | 有效期 | 用途 |
|-------|--------|------|
| access_token | 60 分钟 | API 请求认证 |
| refresh_token | 7 天 | 刷新 access_token |

### Token 刷新

access_token 过期后，使用 refresh_token 获取新的 token 对：

```bash
POST /api/v1/auth/refresh
{
  "refresh_token": "<refresh_token>"
}
```

### 速率限制

| 端点 | 限制 | 说明 |
|------|------|------|
| `/auth/*` | 5 次/分钟/IP | 防止暴力破解 |
| `/accounts` (POST) | 20 次/分钟/IP | 账户创建限制 |
| `/agents/*/status` (POST) | 10 次/分钟/IP | Agent 状态变更限制 |
| 其他 API | 100 次/分钟/IP | 通用限制 |

超过限制返回 `429 Too Many Requests`。

## REST API 端点

### Auth — 认证

#### 注册

```
POST /api/v1/auth/register
```

```json
// 请求
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "name": "John"
}

// 响应 200
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John",
  "is_active": true
}
```

#### 登录

使用 OAuth2 密码流 (form-data 格式)：

```
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePass123
```

```json
// 响应 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

> 连续 5 次登录失败会触发账户锁定。

#### 刷新 Token

```
POST /api/v1/auth/refresh
```

```json
// 请求
{ "refresh_token": "eyJ..." }

// 响应 200
{
  "access_token": "eyJ...(new)",
  "refresh_token": "eyJ...(new)",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### 登出

```
POST /api/v1/auth/logout
```

```json
// 请求
{ "refresh_token": "eyJ..." }

// 响应 200
{ "message": "Successfully logged out" }
```

#### 获取当前用户

```
GET /api/v1/auth/me
```

```json
// 响应 200
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John",
  "is_active": true
}
```

#### 更新资料

```
PUT /api/v1/auth/profile
```

```json
// 请求
{ "name": "New Name" }
```

#### 修改密码

```
POST /api/v1/auth/change-password
```

```json
// 请求
{
  "current_password": "OldPass123",
  "new_password": "NewPass456"
}
```

---

### Accounts — 交易所账户

#### 创建账户

```
POST /api/v1/accounts
```

```json
// 请求 (CEX - Binance / Bybit)
{
  "name": "Binance 主账户",
  "exchange": "binance",
  "is_testnet": false,
  "api_key": "xxx",
  "api_secret": "xxx"
}

// 请求 (CEX - OKX, 需要额外 passphrase)
{
  "name": "OKX 主账户",
  "exchange": "okx",
  "is_testnet": false,
  "api_key": "xxx",
  "api_secret": "xxx",
  "passphrase": "xxx"
}

// 请求 (DEX - Hyperliquid, 私钥方式)
{
  "name": "Hyperliquid",
  "exchange": "hyperliquid",
  "is_testnet": false,
  "private_key": "0x..."
}

// 请求 (DEX - Hyperliquid, 助记词方式)
{
  "name": "Hyperliquid",
  "exchange": "hyperliquid",
  "is_testnet": false,
  "mnemonic": "word1 word2 ... word12"
}

// 响应 200
{
  "id": "uuid",
  "name": "Binance 主账户",
  "exchange": "binance",
  "is_testnet": false,
  "is_connected": true,
  "connection_error": null,
  "created_at": "2025-01-01T00:00:00Z",
  "has_api_key": true,
  "has_api_secret": true,
  "has_private_key": false
}
```

#### 列表

```
GET /api/v1/accounts
GET /api/v1/accounts?exchange=binance
```

#### 获取详情

```
GET /api/v1/accounts/{account_id}
```

#### 更新

```
PATCH /api/v1/accounts/{account_id}
```

#### 删除

```
DELETE /api/v1/accounts/{account_id}
```

#### 测试连接

```
POST /api/v1/accounts/{account_id}/test
```

```json
// 响应 200
{
  "success": true,
  "exchange": "binance",
  "balance": { "USDT": 1000.0 }
}
```

#### 获取余额

```
GET /api/v1/accounts/{account_id}/balance
```

```json
// 响应 200
{
  "account_id": "uuid",
  "equity": 10000.0,
  "available_balance": 8000.0,
  "total_margin_used": 2000.0,
  "unrealized_pnl": 150.0,
  "positions": [...]
}
```

#### 获取持仓

```
GET /api/v1/accounts/{account_id}/positions
```

---

### Agents — 执行实例管理

Agent 是策略的实际执行实例，由 Strategy 配置生成。

#### 创建 Agent

```
POST /api/v1/agents
```

```json
// 请求
{
  "strategy_id": "uuid",
  "account_id": "uuid",
  "name": "BTC 趋势 Agent",
  "trade_type": "crypto_perp"  // crypto_perp / crypto_spot
}

// 响应 200
{
  "id": "uuid",
  "strategy_id": "uuid",
  "account_id": "uuid",
  "name": "BTC 趋势 Agent",
  "status": "stopped",
  "trade_type": "crypto_perp",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### 列表

```
GET /api/v1/agents
GET /api/v1/agents?status=active
GET /api/v1/agents?account_id=uuid
```

#### 获取绑定账户信息

```
GET /api/v1/agents/bound-accounts
```

```json
// 响应 200
{
  "accounts": [
    { "id": "uuid", "name": "Binance 主账户", "exchange": "binance" }
  ]
}
```

#### 获取详情

```
GET /api/v1/agents/{id}
```

#### 更新

```
PATCH /api/v1/agents/{id}
```

```json
// 请求
{
  "name": "更新名称",
  "account_id": "uuid"
}
```

#### 删除

```
DELETE /api/v1/agents/{id}
```

> 删除前必须先停止 Agent。

#### 更新状态 (启动/暂停/停止)

```
POST /api/v1/agents/{id}/status
```

```json
// 请求
{ "status": "active" }  // active / paused / stopped

// 响应 200
{
  "id": "uuid",
  "status": "active",
  "message": "Agent started"
}
```

#### 手动触发 (Run Now)

立即执行一次策略周期：

```
POST /api/v1/agents/{id}/trigger
```

```json
// 响应 200
{
  "message": "Agent triggered",
  "triggered_at": "2025-01-01T12:00:00Z"
}
```

#### 获取持仓

```
GET /api/v1/agents/{id}/positions
```

```json
// 响应 200
{
  "agent_id": "uuid",
  "positions": [
    {
      "symbol": "BTC/USDT:USDT",
      "side": "long",
      "size": 0.1,
      "entry_price": 100000,
      "current_price": 102000,
      "unrealized_pnl": 200,
      "unrealized_pnl_percent": 2.0
    }
  ]
}
```

#### 获取账户状态

```
GET /api/v1/agents/{id}/account-state
```

```json
// 响应 200
{
  "equity": 10000.0,
  "available_balance": 8000.0,
  "total_margin_used": 2000.0,
  "unrealized_pnl": 150.0
}
```

#### 获取运行状态 (含心跳)

```
GET /api/v1/agents/{id}/runtime-status
```

```json
// 响应 200
{
  "status": "active",
  "worker_heartbeat_at": "2025-01-01T12:00:00Z",
  "worker_instance_id": "worker-xxx",
  "is_stale": false,
  "last_run_at": "2025-01-01T11:55:00Z",
  "error_count": 0
}
```

---

### Strategies — AI Agent 策略

策略是配置模板，Agent 是执行实例。

#### 创建策略

```
POST /api/v1/strategies
```

```json
// 请求
{
  "name": "BTC 趋势跟踪",
  "description": "基于 EMA 金叉的趋势策略",
  "prompt": "专注 BTC 趋势跟踪...",
  "trading_mode": "balanced",
  "config": {
    "symbols": ["BTC/USDT:USDT"],
    "timeframes": ["4h", "1h"],
    "risk_controls": {
      "max_leverage": 3,
      "max_position_ratio": 0.3
    },
    "indicators": {
      "ema": { "enabled": true, "short_period": 9, "long_period": 21 },
      "rsi": { "enabled": true, "period": 14 }
    }
  },
  "ai_model": "deepseek:deepseek-chat"
}
```

#### 列表

```
GET /api/v1/strategies
GET /api/v1/strategies?status=active
```

#### 获取详情

```
GET /api/v1/strategies/{strategy_id}
```

#### 更新

```
PATCH /api/v1/strategies/{strategy_id}
```

#### 删除

```
DELETE /api/v1/strategies/{strategy_id}
```

#### 预览 Prompt

生成系统 Prompt 预览，不执行策略：

```
POST /api/v1/strategies/preview-prompt
```

```json
// 请求
{
  "prompt": "BTC 趋势跟踪",
  "trading_mode": "balanced",
  "symbols": ["BTC/USDT:USDT"],
  "language": "zh",
  "indicators": { "ema": { "enabled": true } },
  "risk_controls": { "max_leverage": 3 }
}

// 响应 200
{
  "system_prompt": "你是一位专业的加密货币交易分析师...",
  "estimated_tokens": 1500,
  "sections": ["role", "trading_mode", "constraints", ...]
}
```

#### 验证辩论模型

```
POST /api/v1/strategies/validate-debate-models
```

```json
// 请求
{ "model_ids": ["deepseek:deepseek-chat", "qwen:qwen3-plus"] }

// 响应 200
{
  "valid": true,
  "models": [
    { "model_id": "deepseek:deepseek-chat", "valid": true, "error": null },
    { "model_id": "qwen:qwen3-plus", "valid": true, "error": null }
  ]
}
```

---

### Quant Strategies — 量化策略

#### 创建

```
POST /api/v1/quant-strategies
```

```json
// 请求 (网格策略)
{
  "name": "BTC 网格",
  "strategy_type": "grid",
  "symbol": "BTC/USDT:USDT",
  "config": {
    "upper_price": 105000,
    "lower_price": 95000,
    "grid_count": 20,
    "total_investment": 5000,
    "leverage": 1.0
  },
  "account_id": "uuid"
}
```

#### 列表 / 详情 / 更新 / 删除

```
GET    /api/v1/quant-strategies
GET    /api/v1/quant-strategies/{id}
PATCH  /api/v1/quant-strategies/{id}
DELETE /api/v1/quant-strategies/{id}
```

#### 更新状态

```
POST /api/v1/quant-strategies/{id}/status
```

```json
{ "status": "active" }  // active / paused / stopped
```

---

### Decisions — 决策记录

#### 最近决策

```
GET /api/v1/decisions/recent?limit=20
```

#### Agent 决策 (分页)

```
GET /api/v1/decisions/agent/{agent_id}?limit=20&offset=0
```

#### 策略决策 (分页)

```
GET /api/v1/decisions/strategy/{strategy_id}?limit=20&offset=0
```

```json
// 响应 200
{
  "items": [
    {
      "id": "uuid",
      "agent_id": "uuid",
      "strategy_id": "uuid",
      "timestamp": "2025-01-01T12:00:00Z",
      "chain_of_thought": "BTC 在 4h 级别形成金叉...",
      "market_assessment": "看多",
      "overall_confidence": 0.75,
      "decisions": [...],
      "executed": true,
      "execution_results": [...],
      "ai_model": "deepseek:deepseek-chat",
      "tokens_used": 2500,
      "latency_ms": 3200,
      "market_snapshot": {...},
      "account_snapshot": {...},
      "debate_result": {...}
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

#### 决策统计

```
GET /api/v1/decisions/agent/{agent_id}/stats
```

```json
// 响应 200
{
  "total_decisions": 150,
  "executed_decisions": 120,
  "average_confidence": 0.72,
  "average_latency_ms": 2800,
  "total_tokens": 375000,
  "action_counts": {
    "open_long": 45,
    "close_long": 30,
    "hold": 75
  }
}
```

#### 获取单条决策

```
GET /api/v1/decisions/{decision_id}
```

---

### Wallets — 钱包管理

#### 获取我的钱包

```
GET /api/v1/wallets/me
```

```json
// 响应 200
{
  "balance": 100.00,
  "currency": "USD",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### 获取交易记录

```
GET /api/v1/wallets/me/transactions?limit=50&offset=0&type=recharge
```

```json
// 响应 200
{
  "items": [
    {
      "id": "uuid",
      "type": "recharge",
      "amount": 50.00,
      "balance_after": 100.00,
      "description": "充值成功",
      "created_at": "2025-01-01T12:00:00Z"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

#### 获取交易摘要

```
GET /api/v1/wallets/me/summary
```

```json
// 响应 200
{
  "total_recharge": 200.00,
  "total_consume": 80.00,
  "total_refund": 10.00,
  "total_gift": 0.00,
  "current_balance": 130.00
}
```

#### 获取邀请信息

```
GET /api/v1/wallets/me/invite
```

```json
// 响应 200
{
  "invite_code": "ABC123",
  "total_invites": 5,
  "total_commission": 25.00
}
```

#### 赠送余额 (管理员)

```
POST /api/v1/wallets/gift
```

```json
// 请求
{
  "user_id": "uuid",
  "amount": 10.00,
  "reason": "新用户奖励"
}
```

#### 调整余额 (管理员)

```
POST /api/v1/wallets/adjust
```

```json
// 请求
{
  "user_id": "uuid",
  "amount": -5.00,  // 负数表示扣减
  "reason": "补偿调整"
}
```

---

### Channels — 通知渠道

#### 列表

```
GET /api/v1/channels
```

```json
// 响应 200
{
  "items": [
    {
      "id": "uuid",
      "channel_type": "telegram",
      "name": "我的 Telegram",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

#### 创建

```
POST /api/v1/channels
```

```json
// 请求 (Telegram)
{
  "channel_type": "telegram",
  "name": "我的 Telegram",
  "config": {
    "bot_token": "123456:ABC-DEF",
    "chat_id": "-1001234567890"
  }
}

// 请求 (Discord)
{
  "channel_type": "discord",
  "name": "Discord 通知",
  "config": {
    "webhook_url": "https://discord.com/api/webhooks/xxx/yyy"
  }
}

// 请求 (Email)
{
  "channel_type": "email",
  "name": "邮件通知",
  "config": {
    "to_email": "user@example.com"
  }
}
```

#### 获取 / 更新 / 删除

```
GET    /api/v1/channels/{id}
PATCH  /api/v1/channels/{id}
DELETE /api/v1/channels/{id}
```

#### 测试连接

```
POST /api/v1/channels/{id}/test
```

```json
// 响应 200
{
  "success": true,
  "message": "Test notification sent"
}
```

---

### Analytics — 数据分析

#### 盈亏分析

```
GET /api/v1/analytics/pnl?start_date=2025-01-01&end_date=2025-02-01
```

```json
// 响应 200
{
  "total_pnl": 1500.00,
  "realized_pnl": 1200.00,
  "unrealized_pnl": 300.00,
  "win_rate": 0.65,
  "total_trades": 100,
  "winning_trades": 65,
  "losing_trades": 35,
  "avg_win": 30.00,
  "avg_loss": -15.00,
  "profit_factor": 2.0
}
```

#### 日快照

```
GET /api/v1/analytics/daily?limit=30
```

```json
// 响应 200
{
  "items": [
    {
      "date": "2025-01-01",
      "equity": 10000.00,
      "daily_pnl": 150.00,
      "daily_pnl_percent": 1.5,
      "trades_count": 5
    }
  ]
}
```

---

### Recharge — 余额充值

#### 创建充值订单

```
POST /api/v1/recharge
```

```json
// 请求
{
  "amount": 50.00,
  "payment_method": "crypto"  // crypto / alipay / wechat
}

// 响应 200
{
  "order_id": "uuid",
  "amount": 50.00,
  "status": "pending",
  "payment_url": "https://...",
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### 查询充值状态

```
GET /api/v1/recharge/{order_id}
```

```json
// 响应 200
{
  "order_id": "uuid",
  "amount": 50.00,
  "status": "completed",  // pending / completed / failed / cancelled
  "paid_at": "2025-01-01T12:05:00Z"
}
```

#### 充值历史

```
GET /api/v1/recharge/history?limit=20
```

---

### Brand — 品牌配置

#### 获取品牌配置

```
GET /api/v1/brand
```

```json
// 响应 200
{
  "brand_name": "BitRun",
  "tagline": "AI 驱动的加密货币交易平台",
  "logo_url": "https://...",
  "favicon_url": "https://...",
  "theme": {
    "primary_color": "#3b82f6",
    "accent_color": "#10b981"
  },
  "links": {
    "terms": "/terms",
    "privacy": "/privacy"
  }
}
```

#### 更新品牌配置 (管理员)

```
PATCH /api/v1/brand
```

```json
// 请求
{
  "brand_name": "MyBrand",
  "tagline": "我的交易平台"
}
```

---

### System — 系统配置

#### 系统状态

```
GET /api/v1/system/status
```

```json
// 响应 200
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "worker": "healthy"
  }
}
```

#### 系统公告

```
GET /api/v1/system/announcements
```

```json
// 响应 200
{
  "items": [
    {
      "id": "uuid",
      "title": "系统维护通知",
      "content": "...",
      "level": "warning",  // info / warning / error
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### Backtest — 回测

#### 运行策略回测

```
POST /api/v1/backtest/run
```

```json
{
  "strategy_id": "uuid",
  "start_date": "2025-01-01",
  "end_date": "2025-06-01",
  "initial_balance": 10000,
  "timeframe": "4h",
  "exchange": "binance",
  "use_ai": true
}
```

#### 快速回测

```
POST /api/v1/backtest/quick
```

```json
{
  "symbols": ["BTC/USDT:USDT"],
  "start_date": "2025-01-01",
  "end_date": "2025-06-01",
  "initial_balance": 10000,
  "max_leverage": 3,
  "timeframe": "4h"
}
```

#### 获取可用交易对

```
GET /api/v1/backtest/symbols
```

---

### Dashboard — 仪表盘

#### 统计数据

```
GET /api/v1/dashboard/stats
```

```json
// 响应 200
{
  "total_equity": 50000.0,
  "available_balance": 35000.0,
  "unrealized_pnl": 1200.0,
  "daily_pnl": 500.0,
  "daily_pnl_percent": 1.02,
  "active_agents": 3,
  "total_agents": 5,
  "open_positions": 2,
  "positions": [...],
  "today_decisions": 12,
  "today_executed_decisions": 8,
  "accounts_connected": 2,
  "accounts_total": 3
}
```

#### 活动流

```
GET /api/v1/dashboard/activity?limit=20&offset=0
```

---

### Models — AI 模型

#### 列出所有 Provider

```
GET /api/v1/models/providers
```

#### 列出可用模型

```
GET /api/v1/models
GET /api/v1/models?provider=deepseek
```

#### 获取模型详情

```
GET /api/v1/models/{provider:model_id}
```

#### 测试模型连接

```
POST /api/v1/models/test
```

```json
{ "model_id": "deepseek:deepseek-chat" }
```

---

### Providers — AI Provider 配置

#### 列出预设 Provider

```
GET /api/v1/providers/presets
```

#### 列出用户配置的 Provider

```
GET /api/v1/providers
```

#### 创建 Provider

```
POST /api/v1/providers
```

```json
{
  "provider_type": "deepseek",
  "name": "DeepSeek",
  "api_key": "sk-xxx",
  "base_url": "https://api.deepseek.com"
}
```

#### 获取 / 更新 / 删除

```
GET    /api/v1/providers/{id}
PATCH  /api/v1/providers/{id}
DELETE /api/v1/providers/{id}
```

#### 测试连接

```
POST /api/v1/providers/{id}/test
```

#### 管理 Provider 的模型列表

```
GET    /api/v1/providers/{id}/models          # 列出模型
PUT    /api/v1/providers/{id}/models          # 替换全部模型
POST   /api/v1/providers/{id}/models          # 添加单个模型
DELETE /api/v1/providers/{id}/models/{model_id} # 删除模型
```

---

### Workers — Worker 管理

#### 获取 Worker 总状态

```
GET /api/v1/workers/status
```

```json
// 响应 200
{
  "running": true,
  "total_workers": 3,
  "workers": [
    {
      "agent_id": "uuid",
      "running": true,
      "last_run": "2025-01-01T12:00:00Z",
      "error_count": 0,
      "worker_heartbeat_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

#### 控制单个 Worker

```
POST /api/v1/workers/{agent_id}/start    # 启动
POST /api/v1/workers/{agent_id}/stop     # 停止
POST /api/v1/workers/{agent_id}/trigger  # 立即执行一次
GET  /api/v1/workers/{agent_id}/status   # 查看状态
```

---

### Data — 市场数据

#### 缓存统计

```
GET /api/v1/data/cache/stats
```

#### 预加载数据

```
POST /api/v1/data/cache/preload
POST /api/v1/data/cache/preload/common
```

#### 清除缓存

```
POST /api/v1/data/cache/invalidate
```

#### 获取可用交易对

```
GET /api/v1/data/symbols
```

---

### Notifications — 通知

#### 通知状态

```
GET /api/v1/notifications/status
```

#### 发送测试通知

```
POST /api/v1/notifications/test
```

```json
{ "message": "Hello from BITRUN!" }
```

#### 列出通知渠道

```
GET /api/v1/notifications/channels
```

---

### Metrics — 监控指标

#### Prometheus 指标

```
GET /api/v1/metrics
```

返回 Prometheus 文本格式的指标数据。

#### JSON 格式指标

```
GET /api/v1/metrics/json
```

#### 详细健康检查

```
GET /api/v1/health/detailed
```

#### 熔断器状态

```
GET /api/v1/health/circuit-breakers
```

---

### Crypto — 传输加密

> 仅当 `TRANSPORT_ENCRYPTION_ENABLED=true` 时可用。

#### 获取公钥

```
GET /api/v1/crypto/public-key
```

```json
{
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "algorithm": "RSA-OAEP",
  "key_size": 2048
}
```

#### 解密数据

```
POST /api/v1/crypto/decrypt
```

---

## WebSocket API

### 连接

```
ws://localhost:8000/api/v1/ws?token=<access_token>
```

生产环境 (Nginx + SSL):
```
wss://api.example.com/api/v1/ws?token=<access_token>
```

### 连接限制

| 限制 | 值 |
|------|------|
| 单用户最大连接数 | 5 |
| 系统最大总连接数 | 500 |

### 消息格式

所有消息均为 JSON 格式：

```json
{
  "type": "message_type",
  "channel": "optional_channel",
  "data": { ... },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### 客户端 -> 服务端消息

#### 订阅频道

```json
{ "type": "subscribe", "channel": "agent:uuid-xxx" }
```

#### 取消订阅

```json
{ "type": "unsubscribe", "channel": "agent:uuid-xxx" }
```

#### 心跳

```json
{ "type": "ping" }
```

### 服务端 -> 客户端消息

#### 订阅确认

```json
{ "type": "subscribed", "channel": "agent:uuid-xxx" }
```

#### 心跳响应

```json
{ "type": "pong" }
```

#### 交易决策

```json
{
  "type": "decision",
  "channel": "agent:uuid-xxx",
  "data": {
    "agent_id": "uuid",
    "decision": {
      "chain_of_thought": "...",
      "overall_confidence": 0.75,
      "decisions": [...]
    }
  }
}
```

#### 持仓更新

```json
{
  "type": "position_update",
  "channel": "account:uuid-xxx",
  "data": {
    "account_id": "uuid",
    "positions": [...]
  }
}
```

#### 账户更新

```json
{
  "type": "account_update",
  "data": {
    "account_id": "uuid",
    "state": {
      "equity": 10000,
      "available_balance": 8000,
      "unrealized_pnl": 150
    }
  }
}
```

#### Agent 状态变更

```json
{
  "type": "agent_status",
  "channel": "agent:uuid-xxx",
  "data": {
    "agent_id": "uuid",
    "status": "active",
    "error": null
  }
}
```

#### 通知

```json
{
  "type": "notification",
  "data": {
    "title": "策略执行完成",
    "message": "BTC 趋势 Agent 已完成一轮分析",
    "level": "info"
  }
}
```

#### 错误

```json
{
  "type": "error",
  "data": {
    "message": "Invalid JSON"
  }
}
```

### 频道列表

| 频道 | 格式 | 说明 |
|------|------|------|
| 系统 | `system` | 系统级通知 |
| Agent | `agent:{agent_id}` | Agent 决策和状态变更 |
| 账户 | `account:{account_id}` | 账户和持仓更新 |

### WebSocket 统计

```
GET /api/v1/ws/stats
```

```json
{
  "total_connections": 5,
  "channels": {
    "agent:uuid-1": 2,
    "system": 5
  }
}
```

## 错误响应格式

所有错误使用标准 HTTP 状态码，响应体：

```json
{
  "detail": "错误描述"
}
```

常见状态码：

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 失效 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

## API 文档 (Swagger)

开发环境下可访问自动生成的交互式 API 文档：

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

> 生产环境下这些端点被禁用。

## 相关文档

- [架构概览](architecture.md) — 系统设计
- [快速开始](getting-started.md) — 环境搭建
- [开发者指南](development.md) — 开发规范
