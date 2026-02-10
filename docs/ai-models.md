# AI 模型配置指南

BITRUN 支持 9+ AI Provider，用户可在应用内配置 API Key 并选择模型。本文档说明所有支持的 Provider、配置方法和模型选择建议。

## Provider 级别配置架构

BITRUN 采用 **Provider 级别** 的配置架构：

```
Provider (服务商)
├── API Key (一个 Provider 一个 Key)
├── Base URL (可自定义端点)
└── Models (模型列表)
    ├── Model A
    ├── Model B
    └── ...
```

### 数据模型

每个 Provider 配置存储在 `AIProviderConfigDB` 表中：

| 字段 | 说明 |
|------|------|
| `provider_type` | Provider 类型标识 |
| `name` | 自定义显示名称 |
| `api_key` | API Key (AES-256-GCM 加密存储) |
| `base_url` | API 端点 URL |
| `api_format` | API 格式 (openai / custom) |
| `models` | 该 Provider 下的可用模型列表 (JSON) |
| `is_enabled` | 是否启用 |

### 模型 ID 格式

模型通过 `provider:model_id` 格式唯一标识，例如：
- `deepseek:deepseek-chat`
- `openai:gpt-4o`
- `gemini:gemini-2.5-flash`

## 支持的 AI Provider

### DeepSeek

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `deepseek-chat` | 64K | 通用对话模型，性价比极高 |
| `deepseek-reasoner` | 64K | 推理增强模型，适合复杂分析 |

**API Key 获取**：
1. 访问 [DeepSeek Platform](https://platform.deepseek.com)
2. 注册并登录
3. 进入 API Keys 页面创建密钥

**API 端点**: `https://api.deepseek.com`

---

### Qwen (通义千问)

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `qwen3-turbo` | 131K | 快速推理，适合实时交易决策 |
| `qwen3-plus` | 131K | 平衡性能和质量 |
| `qwen3-max` | 131K | 最高质量，适合复杂分析 |

**API Key 获取**：
1. 访问 [阿里云百炼](https://bailian.console.aliyun.com)
2. 开通模型服务
3. 创建 API Key

**API 端点**: `https://dashscope.aliyuncs.com/compatible-mode/v1`

---

### Zhipu (智谱)

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `glm-4.6` | 128K | GLM-4 系列，综合能力强 |
| `glm-4.7` | 128K | 最新版本，性能提升 |

**API Key 获取**：
1. 访问 [智谱 AI 开放平台](https://open.bigmodel.cn)
2. 注册并创建 API Key

**API 端点**: `https://open.bigmodel.cn/api/paas/v4`

---

### MiniMax

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `MiniMax-M2.1` | 1000K | 超大上下文，适合长周期分析 |
| `MiniMax-M2.1-lightning` | 1000K | 快速版本，牺牲少量质量换取速度 |

**API Key 获取**：
1. 访问 [MiniMax 开放平台](https://platform.minimaxi.com)
2. 注册并创建 API Key

**API 端点**: `https://api.minimaxi.chat/v1`

---

### Kimi (月之暗面)

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `kimi-k2.5` | 131K | 最新一代，综合能力强 |
| `kimi-k2` | 131K | 上一代，性价比高 |

**API Key 获取**：
1. 访问 [Moonshot AI 开放平台](https://platform.moonshot.cn)
2. 注册并创建 API Key

**API 端点**: `https://api.moonshot.cn/v1`

---

### OpenAI

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `gpt-4o` | 128K | 旗舰多模态模型 |
| `gpt-4o-mini` | 128K | 轻量版，成本低 |
| `o4-mini` | 128K | 推理模型，适合复杂分析 |

**API Key 获取**：
1. 访问 [OpenAI Platform](https://platform.openai.com)
2. 注册并创建 API Key

**API 端点**: `https://api.openai.com/v1`

> 需要海外网络环境，或使用兼容代理服务。

---

### Google Gemini

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `gemini-2.5-flash` | 1000K | 超大上下文，快速响应 |
| `gemini-2.5-pro` | 1000K | 最高质量，适合复杂推理 |

**API Key 获取**：
1. 访问 [Google AI Studio](https://aistudio.google.com)
2. 创建 API Key

**API 端点**: 由 Google Generative AI SDK 自动处理

> 需要海外网络环境。

---

### xAI Grok

| 模型 | 上下文窗口 | 说明 |
|------|-----------|------|
| `grok-4` | 131K | 旗舰模型 |
| `grok-3-mini-beta` | 131K | 轻量版 |

**API Key 获取**：
1. 访问 [xAI Console](https://console.x.ai)
2. 注册并创建 API Key

**API 端点**: `https://api.x.ai/v1`

---

### Custom (自定义 OpenAI 兼容端点)

支持任何兼容 OpenAI API 格式的端点，包括：
- 本地部署的 LLM (如 Ollama, vLLM, llama.cpp)
- 第三方代理服务
- 私有部署的模型

配置时填写自定义的 Base URL 和模型名称即可。

## 在 BITRUN 中配置 Provider

### 通过界面配置

1. 进入 **「模型管理」** 页面
2. 点击「添加 Provider」
3. 选择预设 Provider 或自定义
4. 填入 API Key
5. 可选修改 Base URL（使用代理时）
6. 添加要使用的模型
7. 点击「测试连接」验证
8. 保存配置

### 通过 API 配置

```bash
# 创建 Provider
POST /api/v1/providers
{
  "provider_type": "deepseek",
  "name": "DeepSeek",
  "api_key": "sk-xxx",
  "base_url": "https://api.deepseek.com"
}

# 添加模型
POST /api/v1/providers/{provider_id}/models
{
  "id": "deepseek-chat",
  "name": "DeepSeek Chat",
  "context_window": 64000,
  "max_output_tokens": 8192,
  "supports_json_mode": true
}

# 测试连接
POST /api/v1/providers/{provider_id}/test
```

## 模型选择建议

### 按场景推荐

| 场景 | 推荐模型 | 理由 |
|------|---------|------|
| **日常交易决策** | `deepseek:deepseek-chat` | 性价比最高，响应快 |
| **复杂策略分析** | `deepseek:deepseek-reasoner` 或 `openai:o4-mini` | 推理能力强 |
| **超长上下文** | `minimax:MiniMax-M2.1` 或 `gemini:gemini-2.5-flash` | 1000K 上下文窗口 |
| **多模型辩论** | DeepSeek + Qwen + Gemini | 不同架构模型组合，提高多样性 |
| **高频决策** | `qwen:qwen3-turbo` 或 `minimax:MiniMax-M2.1-lightning` | 低延迟 |
| **成本敏感** | `deepseek:deepseek-chat` 或 `qwen:qwen3-turbo` | 价格最低 |

### 按维度对比

| 维度 | 推荐 Provider |
|------|--------------|
| **性价比** | DeepSeek > Qwen > Kimi > MiniMax > Zhipu |
| **响应速度** | Qwen Turbo > DeepSeek > MiniMax Lightning > Grok |
| **推理质量** | OpenAI o4 > DeepSeek Reasoner > Gemini Pro > GPT-4o |
| **上下文长度** | MiniMax / Gemini (1000K) > Qwen / Kimi (131K) > OpenAI (128K) > DeepSeek (64K) |
| **国内访问** | DeepSeek / Qwen / Zhipu / MiniMax / Kimi (无需代理) |

### Debate Engine 模型组合建议

选择不同架构的模型以获得最大多样性：

```
推荐组合 1 (高性价比):
  DeepSeek Chat + Qwen Plus + Kimi K2.5

推荐组合 2 (高质量):
  GPT-4o + DeepSeek Reasoner + Gemini Pro

推荐组合 3 (国内可用):
  DeepSeek Chat + Qwen Max + Zhipu GLM-4.7
```

## 注意事项

- API Key 在数据库中使用 **AES-256-GCM** 加密存储，不以明文形式保存
- 每个用户可以独立配置自己的 Provider 和 API Key
- 部分 Provider (OpenAI, Gemini, Grok) 需要海外网络环境
- 模型的可用性和定价可能会随 Provider 更新而变化
- 建议定期检查 Provider 的模型列表是否有新模型可用

## 相关文档

- [快速开始](getting-started.md) — 首次配置 AI Provider
- [策略模块](strategy-guide.md) — 在策略中使用 AI 模型
- [回测模块](backtest-guide.md) — 回测中的 AI 调用
- [API 参考](api-reference.md) — Provider 和 Model 管理 API
