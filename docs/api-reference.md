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
| `/strategies/*/status` (POST) | 10 次/分钟/IP | 策略状态变更限制 |
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
// 请求 (CEX)
{
  "name": "Binance 主账户",
  "exchange": "binance",
  "is_testnet": false,
  "api_key": "xxx",
  "api_secret": "xxx"
}

// 请求 (DEX - Hyperliquid)
{
  "name": "Hyperliquid",
  "exchange": "hyperliquid",
  "is_testnet": false,
  "private_key": "0x..."
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

### Strategies — AI Agent 策略

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
  "account_id": "uuid",
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

#### 更新状态 (激活/暂停/停止)

```
POST /api/v1/strategies/{strategy_id}/status
```

```json
// 请求
{ "status": "active" }  // active / paused / stopped
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
      "account_snapshot": {...}
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

#### 决策统计

```
GET /api/v1/decisions/strategy/{strategy_id}/stats
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
  "active_strategies": 3,
  "total_strategies": 5,
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
  "distributed": false,
  "total_workers": 3,
  "workers": [
    {
      "strategy_id": "uuid",
      "running": true,
      "last_run": "2025-01-01T12:00:00Z",
      "error_count": 0,
      "mode": "legacy"
    }
  ]
}
```

#### 控制单个 Worker

```
POST /api/v1/workers/{strategy_id}/start    # 启动
POST /api/v1/workers/{strategy_id}/stop     # 停止
POST /api/v1/workers/{strategy_id}/trigger  # 立即执行一次
GET  /api/v1/workers/{strategy_id}/status   # 查看状态
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
GET /health/detailed
```

#### 熔断器状态

```
GET /health/circuit-breakers
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
wss://your-domain.com/api/v1/ws?token=<access_token>
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
{ "type": "subscribe", "channel": "strategy:uuid-xxx" }
```

#### 取消订阅

```json
{ "type": "unsubscribe", "channel": "strategy:uuid-xxx" }
```

#### 心跳

```json
{ "type": "ping" }
```

### 服务端 -> 客户端消息

#### 订阅确认

```json
{ "type": "subscribed", "channel": "strategy:uuid-xxx" }
```

#### 心跳响应

```json
{ "type": "pong" }
```

#### 交易决策

```json
{
  "type": "decision",
  "channel": "strategy:uuid-xxx",
  "data": {
    "strategy_id": "uuid",
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

#### 策略状态变更

```json
{
  "type": "strategy_status",
  "channel": "strategy:uuid-xxx",
  "data": {
    "strategy_id": "uuid",
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
    "message": "BTC 趋势跟踪已完成一轮分析",
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
| 策略 | `strategy:{strategy_id}` | 策略决策和状态变更 |
| 账户 | `account:{account_id}` | 账户和持仓更新 |

### WebSocket 统计

```
GET /api/v1/ws/stats
```

```json
{
  "total_connections": 5,
  "channels": {
    "strategy:uuid-1": 2,
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
