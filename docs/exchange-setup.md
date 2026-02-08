# 交易所对接指南

BITRUN 通过 CCXT 统一接口支持多个中心化交易所 (CEX) 和去中心化交易所 (DEX)。本文档说明如何配置各交易所的 API 连接。

## 支持的交易所

| 交易所 | 类型 | 认证方式 | 测试网 |
|--------|------|----------|--------|
| **Binance** | CEX (合约) | API Key + Secret | 支持 |
| **Bybit** | CEX (合约) | API Key + Secret | 支持 |
| **OKX** | CEX (合约) | API Key + Secret + Passphrase | 支持 |
| **Hyperliquid** | DEX | 私钥 / 助记词 | 支持 |

所有交易所通过统一的 `CCXTTrader` 适配器驱动，交易所差异通过配置参数处理，无需为每个交易所编写不同的代码。

## API Key 获取方式

### Binance

1. 登录 [Binance](https://www.binance.com)
2. 进入 **API 管理** (头像 → API Management)
3. 点击「创建 API」，选择「系统生成」
4. 完成安全验证
5. 记录 **API Key** 和 **Secret Key**

**权限配置**（必须）：
- 启用「现货和杠杆交易」或「合约交易」
- 启用「读取信息」
- 建议：绑定 IP 白名单

**合约账户**：
- 确保已开通 USDT-M 合约交易
- 在合约账户中预存资金

### Bybit

1. 登录 [Bybit](https://www.bybit.com)
2. 进入 **API 管理** (头像 → API)
3. 点击「创建新密钥」，选择「系统生成 API 密钥」
4. 完成安全验证
5. 记录 **API Key** 和 **Secret Key**

**权限配置**（必须）：
- 合约交易：读写
- 资产：只读
- 建议：绑定 IP 白名单

> Bybit API 在中国大陆可能需要代理才能访问，参见下方「代理配置」。

### OKX

1. 登录 [OKX](https://www.okx.com)
2. 进入 **API** (头像 → API)
3. 点击「创建 API 密钥」
4. 设置 **Passphrase**（这是 OKX 特有的，相当于第三个密钥）
5. 完成安全验证
6. 记录 **API Key**、**Secret Key** 和 **Passphrase**

**权限配置**（必须）：
- 交易：启用
- 读取：启用
- 建议：绑定 IP 白名单

> OKX API 在中国大陆可能需要代理，参见下方「代理配置」。

### Hyperliquid (DEX)

Hyperliquid 是去中心化交易所，不使用 API Key，而是通过以太坊私钥签名交易。

#### 方式一：使用私钥

1. 从你的以太坊钱包 (MetaMask 等) 导出私钥
2. 在 BITRUN 中添加账户时，填入 **Private Key** 字段

#### 方式二：使用助记词

1. 准备 12 或 24 个单词的助记词
2. 在 BITRUN 中添加账户时，填入 **Mnemonic** 字段
3. 系统会自动通过 BIP-44 路径 (`m/44'/60'/0'/0/0`) 派生私钥

**安全提示**：
- 建议使用专门的交易钱包，不要用主钱包
- 私钥和助记词在数据库中使用 AES-256-GCM 加密存储
- Hyperliquid 钱包地址会自动从私钥推导

**资金准备**：
- 在 [Hyperliquid](https://app.hyperliquid.xyz) 页面将 USDC 从 Arbitrum 存入 Hyperliquid
- 确保账户有足够的 USDC 用于交易

## 在 BITRUN 中添加账户

### 通过界面添加

1. 进入 **「账户管理」** 页面
2. 点击「添加账户」
3. 填写配置：

| 字段 | 说明 |
|------|------|
| 名称 | 自定义账户名称 (如 "Binance 主账户") |
| 交易所 | 选择交易所类型 |
| 测试网 | 是否使用测试网（建议初次使用先用测试网验证） |
| API Key | CEX 交易所的 API Key |
| API Secret | CEX 交易所的 Secret Key |
| Passphrase | OKX 专用 |
| Private Key | Hyperliquid 专用 |
| Mnemonic | Hyperliquid 专用（与 Private Key 二选一） |

4. 点击「测试连接」验证配置
5. 确认无误后保存

### 通过 API 添加

```bash
POST /api/v1/accounts
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Binance 主账户",
  "exchange": "binance",
  "is_testnet": false,
  "api_key": "your-api-key",
  "api_secret": "your-api-secret"
}
```

Hyperliquid 示例：

```bash
POST /api/v1/accounts
{
  "name": "Hyperliquid 交易",
  "exchange": "hyperliquid",
  "is_testnet": false,
  "private_key": "0x..."
}
```

## 测试网 (Testnet)

强烈建议在实盘前使用测试网验证策略。

### 各交易所测试网

| 交易所 | 测试网地址 |
|--------|-----------|
| Binance | https://testnet.binancefuture.com |
| Bybit | https://testnet.bybit.com |
| OKX | https://www.okx.com (模拟交易) |
| Hyperliquid | https://app.hyperliquid-testnet.xyz |

### 使用方式

在添加账户时勾选「测试网」选项。系统会自动切换到对应的 Sandbox/Testnet API 端点。

测试网的 API Key 需要在对应的测试网平台单独申请。

## 代理配置

部分交易所 API (Bybit, OKX) 在中国大陆受地域限制，需要通过代理访问。

### 配置方式

在 `backend/.env` 中设置：

```bash
# Surge 代理 (默认端口 6152)
PROXY_URL=http://127.0.0.1:6152

# Clash 代理 (默认端口 7890)
PROXY_URL=http://127.0.0.1:7890
```

### Docker 环境

Docker 容器需要通过 `host.docker.internal` 访问宿主机的代理：

```bash
# Docker 环境使用宿主机代理
PROXY_URL=http://host.docker.internal:6152
```

### 代理工作方式

- 配置的代理仅用于交易所 API 请求
- CCXT 会自动使用配置的代理发起 HTTP 请求
- Binance 和 Hyperliquid 通常不需要代理

## CCXT 统一接口

BITRUN 使用 [CCXT](https://github.com/ccxt/ccxt) 作为交易所统一接口层。CCXT 的优势：

- **统一 API**：所有交易所使用相同的方法名和数据格式
- **异步支持**：`ccxt.async_support` 配合 FastAPI 全链路异步
- **100+ 交易所**：理论上可以扩展支持 CCXT 支持的所有交易所

### 当前支持的功能

| 功能 | 方法 | 说明 |
|------|------|------|
| 账户余额 | `fetchBalance` | 查询可用余额和权益 |
| 持仓查询 | `fetchPositions` | 查询当前所有持仓 |
| 市场数据 | `fetchTicker` | 获取实时价格 |
| K 线数据 | `fetchOHLCV` | 获取历史 K 线 |
| 下单 | `createOrder` | 市价单 / 限价单 |
| 资金费率 | `fetchFundingRate` | 查询合约资金费率 |
| 持仓量 | `fetchOpenInterest` | 查询合约持仓量 |

### 连接池 (ExchangePool)

系统使用 `ExchangePool` 管理 CCXT 实例，避免重复创建连接：

- 相同交易所 + 凭证的请求复用同一个 CCXT 实例
- 应用关闭时自动清理所有连接
- 减少交易所 API 的连接建立开销

## 安全说明

- 所有 API Key、Secret、私钥在存入数据库前使用 **AES-256-GCM** 加密
- 加密密钥通过 `DATA_ENCRYPTION_KEY` 环境变量配置
- 前端不存储任何敏感凭证，仅通过加密通道传输
- 可选启用传输加密 (RSA-OAEP + AES-GCM) 保护 API Key 在传输中的安全

## 相关文档

- [快速开始](getting-started.md) — 首次配置流程
- [策略模块](strategy-guide.md) — 创建使用账户的交易策略
- [部署指南](deployment.md) — 生产环境安全配置
- [API 参考](api-reference.md) — 账户管理 API 端点
