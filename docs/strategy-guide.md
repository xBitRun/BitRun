# 策略模块文档

BITRUN 提供两种策略类型：**AI Agent 策略**（Prompt 驱动）和**量化策略**（规则驱动）。本文档详细说明两种策略的工作原理和配置方法。

## AI Agent 策略

### 工作原理

AI Agent 策略的核心思路是：用自然语言描述交易逻辑，由 AI 模型结合实时市场数据自主生成交易决策。

执行流程：

1. **市场数据采集** — `DataAccessLayer` 获取标的的实时价格、K 线、技术指标
2. **Prompt 构建** — `PromptBuilder` 将策略配置、市场数据、账户状态组装为结构化 Prompt
3. **AI 决策** — 调用配置的 AI 模型生成交易决策 (JSON 格式)
4. **决策解析** — `DecisionParser` 解析 AI 响应，校验风控规则
5. **交易执行** — `OrderManager` 通过 CCXT 将决策提交到交易所
6. **记录存储** — 完整的决策链路 (Prompt → AI 响应 → 执行结果) 存入数据库
7. **实时推送** — 通过 WebSocket 将决策和持仓变动推送到前端

### 策略工作室 (Strategy Studio)

策略工作室提供可视化的策略配置界面，包含五个配置标签页：

#### Coins — 交易标的

- 选择一个或多个交易对 (如 `BTC/USDT:USDT`, `ETH/USDT:USDT`)
- 系统会为每个标的获取实时市场数据
- 支持的交易所：Binance、Bybit、OKX、Hyperliquid

#### Indicators — 技术指标

配置 AI 分析时参考的技术指标：

| 指标 | 参数 | 说明 |
|------|------|------|
| **EMA** (指数移动平均线) | 短周期 (默认 9)、长周期 (默认 21) | 判断趋势方向，短线穿越长线为金叉/死叉信号 |
| **RSI** (相对强弱指标) | 周期 (默认 14)、超买线 (70)、超卖线 (30) | 衡量价格动量，识别超买超卖区域 |
| **MACD** (移动平均收敛散度) | 快线 (12)、慢线 (26)、信号线 (9) | 趋势动量指标，通过快慢线交叉判断趋势 |
| **ATR** (平均真实波幅) | 周期 (默认 14) | 衡量市场波动率，用于动态止损位计算 |

技术指标数据会嵌入到 User Prompt 中，辅助 AI 做出更精准的判断。

#### Risk — 风控参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_leverage` | 3 | 单个持仓最大杠杆倍数 |
| `max_position_ratio` | 0.3 | 单个持仓占账户权益最大比例 (30%) |
| `max_total_ratio` | 0.8 | 所有持仓占账户权益最大比例 (80%) |
| `max_drawdown` | 0.15 | 最大回撤限制 (15%)，触发后暂停策略 |
| `stop_loss_default` | 0.05 | 默认止损比例 (5%) |
| `take_profit_default` | 0.10 | 默认止盈比例 (10%) |

风控参数由代码层强制执行（写入 System Prompt 的 Hard Constraints 段），AI 无法绕过。

#### Prompt — 自定义策略描述

在此编写你的交易策略核心逻辑，例如：

```
专注于 BTC 的趋势跟踪策略。
在 EMA 金叉且 RSI 低于 70 时开多，在 EMA 死叉或 RSI 超过 80 时平仓。
控制仓位在账户权益的 20% 以内，使用 2 倍杠杆。
关注 4 小时和 1 小时级别的趋势一致性。
```

这段文本会被放入 System Prompt 的第 8 段（Custom Prompt），与其他 7 段系统指令共同构成完整的 AI 上下文。

#### Debate — 多模型辩论 (可选)

启用后，系统将同一 Prompt 发送给多个 AI 模型，通过投票或加权方式得出共识决策。

配置项：

| 参数 | 说明 |
|------|------|
| **参与模型** | 选择 2-5 个 AI 模型参与辩论 |
| **共识模式** | `majority_vote` (多数投票) / `highest_confidence` (最高置信度) / `weighted_average` (加权平均) / `unanimous` (全票通过) |
| **最低置信度** | 低于此阈值的决策视为弃权 |

### Prompt 构建机制

`PromptBuilder` 使用 **8 段式结构** 构建 System Prompt：

| 段落 | 内容 |
|------|------|
| 1. Role Definition | AI 角色定义 (专业加密货币交易分析师) |
| 2. Trading Mode | 交易模式特征 (保守 / 平衡 / 激进) |
| 3. Hard Constraints | 代码强制的风控规则 (杠杆上限、仓位限制) |
| 4. Trading Frequency | 交易频率约束 |
| 5. Entry Standards | 入场标准 |
| 6. Decision Process | 决策流程规范 |
| 7. Output Format | JSON 输出格式定义 |
| 8. Custom Prompt | 用户自定义策略描述 |

User Prompt 包含：

- 当前时间戳
- 账户状态 (余额、当前持仓)
- 各标的市场数据 (价格、24h 涨跌、成交量)
- 技术指标计算值 (EMA、RSI、MACD、ATR)
- 最近交易记录

系统支持中英文双语 Prompt，通过策略的 `language` 字段切换。

### 交易模式

| 模式 | 特征 |
|------|------|
| **保守 (Conservative)** | 高确定性才入场，较窄止损，偏向小仓位，适合稳健型交易者 |
| **平衡 (Balanced)** | 综合考虑风险回报，适度仓位，适合大多数场景 |
| **激进 (Aggressive)** | 较低确定性即可入场，较宽止损，偏向大仓位，适合追求高收益 |

### AI 决策输出格式

AI 模型输出标准化的 JSON 决策：

```json
{
  "chain_of_thought": "BTC 在 4h 级别形成金叉，RSI 58 处于中性偏多区间...",
  "market_assessment": "看多",
  "overall_confidence": 0.75,
  "decisions": [
    {
      "symbol": "BTC/USDT:USDT",
      "action": "open_long",
      "confidence": 0.78,
      "size_ratio": 0.15,
      "leverage": 3,
      "entry_price": null,
      "stop_loss": 94500,
      "take_profit": 102000,
      "reasoning": "EMA 金叉确认，RSI 未超买，量能配合"
    }
  ]
}
```

支持的动作类型：`open_long` / `open_short` / `close_long` / `close_short` / `hold`

## Debate Engine — 多模型辩论

### 工作原理

Debate Engine 将相同的分析任务并行发送给多个 AI 模型，然后汇总各模型的决策以达成共识。

### 共识模式

| 模式 | 算法 | 适用场景 |
|------|------|----------|
| **majority_vote** | 每个标的取多数模型认同的动作 | 通用场景，民主决策 |
| **highest_confidence** | 取置信度最高的模型决策 | 信任最自信的模型 |
| **weighted_average** | 按各模型置信度加权计算 | 综合考量各方意见 |
| **unanimous** | 所有模型必须一致，否则 hold | 高确定性场景，最保守 |

### 使用建议

- 选择不同架构的 AI 模型 (如 DeepSeek + GPT-4o + Gemini) 以获得多样性
- 2-3 个模型在成本和效果之间取得最佳平衡
- 使用 `majority_vote` 作为默认共识模式
- 高风险场景 (大仓位) 使用 `unanimous` 模式

## 量化策略

量化策略不依赖 AI，通过预设的数学规则自动执行交易。

### Grid — 网格交易

在价格区间内设置等距的买卖网格，通过价格在网格间的波动获利。

| 参数 | 说明 |
|------|------|
| `upper_price` | 网格上界 |
| `lower_price` | 网格下界 |
| `grid_count` | 网格数量 |
| `total_investment` | 总投资金额 (USD) |
| `leverage` | 杠杆倍数 (默认 1.0) |

**适用场景**：价格在一定区间内震荡时盈利能力最强。

### DCA — 定投策略

按固定时间间隔定额买入，降低平均持仓成本。

| 参数 | 说明 |
|------|------|
| `amount_per_order` | 每次买入金额 (USD) |
| `interval` | 买入间隔 |
| `take_profit_percent` | 止盈比例 |

**适用场景**：长期看好某标的，通过定期买入平滑入场成本。

### RSI — RSI 均值回归

基于 RSI 指标的超买超卖信号进行交易。

| 参数 | 说明 |
|------|------|
| `rsi_period` | RSI 计算周期 (默认 14) |
| `oversold_threshold` | 超卖线 (默认 30，触发买入) |
| `overbought_threshold` | 超买线 (默认 70，触发卖出) |
| `position_size` | 单次交易金额 (USD) |

**适用场景**：震荡行情中，利用 RSI 极值信号进行反向交易。

## 策略生命周期

```
创建 (draft) → 激活 (active) → 暂停 (paused) → 停止 (stopped)
                    ↑                  ↓
                    └──────────────────┘
```

- **draft**: 策略已创建但未启动
- **active**: Worker 定时执行策略
- **paused**: 临时暂停，保留配置和状态
- **stopped**: 完全停止，不再执行

激活策略后，后台 Worker 会按配置的间隔自动执行策略循环。你也可以在策略详情页点击「立即执行」手动触发一次。

## 相关文档

- [AI 模型配置](ai-models.md) — 配置策略使用的 AI 模型
- [交易所对接](exchange-setup.md) — 连接交易所账户
- [回测模块](backtest-guide.md) — 在历史数据上验证策略
- [API 参考](api-reference.md) — 策略相关 API 端点
