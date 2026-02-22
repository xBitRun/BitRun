# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Daily Summary (2026-02-22)

- feat: 增强 Dashboard 中 Agent 持仓展示；重构策略相关组件；新增策略编辑保护与复制功能；增强 Agent 删除流程与 Mock 模式 PnL 计算；新增策略/代理名称自动去重；优化排序稳定性与 Landing 页面文案。
- fix: 修复 agents 路由导入路径与市场类型枚举问题；补充 Jest `json-summary` reporter 以支持 CI 覆盖率报告；修复 CI 工作流 YAML 语法错误。
- refactor: 重构持仓服务并修复 SL/TP 逻辑；重构 PnL 计算与展示组件；统一管理员权限依赖并新增 Admin 布局组件。
- perf: 集成共享价格缓存，减少重复 API 调用开销。
- test: 新增并优化前后端单元测试套件。
- docs: 优化 README 文档格式与结构。

### Added

- AI Agent 策略引擎 - 用自然语言定义交易策略
- 多模型辩论引擎 (Debate Engine) - 多个 AI 模型并行分析、投票表决
- 量化策略引擎 - Grid (网格)、DCA (定投)、RSI 策略
- Agent 执行实例 - 策略配置与执行实例分离
- 多交易所支持 - Binance、Bybit、OKX、Bitget、KuCoin、Gate.io、Hyperliquid DEX
- 回测系统 - 基于历史数据验证策略表现
- 策略工作室 - 可视化配置交易标的、技术指标、风控参数
- 9+ AI Provider - DeepSeek、Qwen、Zhipu、MiniMax、Kimi、OpenAI、Gemini、Grok
- 钱包/支付系统 - 用户余额管理、充值消费
- 通知渠道系统 - Telegram、Discord、Email (Resend)
- 数据分析模块 - 盈亏统计、日快照、账务报表
- 品牌定制 - 白标部署支持
- 邀请/推荐系统
- 策略市场
- 国际化 - 中英文双语界面

### Technical

- 后端: FastAPI + PostgreSQL + Redis + ARQ
- 前端: Next.js 16 + React 19 + Tailwind CSS 4
- Docker 多阶段构建
- Nginx 反向代理 + SSL
- Prometheus + Sentry 监控

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | TBD | Initial release |

---

[Unreleased]: https://github.com/xBitRun/BitRun
