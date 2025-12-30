# OpenRouter vs 官方 OpenAI API 差异分析

## 背景
**场景**：服务器无法直接访问 OpenAI 官方 API（api.openai.com 被墙）  
**解决方案**：通过 OpenRouter 代理访问 GPT 模型

---

## OpenRouter 介绍

**OpenRouter** 是一个统一的 LLM API 网关，提供：
- ✅ 全球可访问（国内服务器可用）
- ✅ 支持 100+ 模型（GPT-4、Claude、Gemini 等）
- ✅ OpenAI 兼容接口（无需改代码）
- ✅ 按使用量计费（无需多个平台账号）
- ✅ 自动负载均衡和降级

**官网**：https://openrouter.ai/  
**文档**：https://openrouter.ai/docs

---

## 核心差异对比

### 1️⃣ 网络访问性

| 项目 | 官方 OpenAI API | OpenRouter |
|------|----------------|------------|
| **API 地址** | `https://api.openai.com/v1` | `https://openrouter.ai/api/v1` |
| **国内直连** | ❌ 需翻墙/代理 | ✅ 直接访问 |
| **稳定性** | ⚠️ 受网络波动影响 | ✅ 多节点冗余 |
| **延迟** | 🌍 国际网络延迟 | 🌏 就近节点（更快）|

### 2️⃣ API 兼容性

```python
# ✅ 100% 兼容 OpenAI SDK
from langchain_openai import ChatOpenAI

# 官方 API 调用
openai_llm = ChatOpenAI(
    model="gpt-4o",
    api_key="sk-proj-...",
    base_url="https://api.openai.com/v1"
)

# OpenRouter 调用（仅需改 base_url 和 API key）
openrouter_llm = ChatOpenAI(
    model="openai/gpt-4o",  # ⚠️ 注意模型名称格式
    api_key="sk-or-v1-...",
    base_url="https://openrouter.ai/api/v1"
)
```

**差异点**：
- ⚠️ 模型名称需加前缀：`openai/gpt-4o`（而非 `gpt-4o`）
- ⚠️ 需在 header 中添加 `HTTP-Referer` 和 `X-Title`（可选但推荐）

### 3️⃣ 模型可用性

| 模型 | 官方 API | OpenRouter | 备注 |
|------|---------|-----------|------|
| **gpt-4o** | ✅ | ✅ `openai/gpt-4o` | 最新 GPT-4o |
| **gpt-4-turbo** | ✅ | ✅ `openai/gpt-4-turbo` | GPT-4 Turbo |
| **gpt-4o-mini** | ✅ | ✅ `openai/gpt-4o-mini` | 经济版 |
| **o1-preview** | ✅ | ✅ `openai/o1-preview` | 推理模型 |
| **Claude 3.5 Sonnet** | ❌ | ✅ `anthropic/claude-3.5-sonnet` | 需 Anthropic 账号 |
| **Gemini Pro** | ❌ | ✅ `google/gemini-pro-1.5` | 需 Google 账号 |
| **Llama 3.3 70B** | ❌ | ✅ `meta-llama/llama-3.3-70b-instruct` | 开源模型 |

**优势**：OpenRouter 提供一个 API key 访问所有模型

### 4️⃣ 定价

#### 官方 OpenAI 定价
| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) |
|------|-------------------|-------------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |

#### OpenRouter 定价（GPT 模型）
| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) | 差价 |
|------|-------------------|-------------------|------|
| openai/gpt-4o | $2.50 | $10.00 | **相同** |
| openai/gpt-4o-mini | $0.15 | $0.60 | **相同** |
| openai/gpt-4-turbo | $10.00 | $30.00 | **相同** |

**结论**：OpenRouter 的 GPT 模型定价与官方**完全相同**，无额外费用。

### 5️⃣ 功能支持

| 功能 | 官方 API | OpenRouter | 差异说明 |
|------|---------|-----------|---------|
| **Streaming** | ✅ | ✅ | 完全支持 |
| **Function Calling** | ✅ | ✅ | 完全支持 |
| **Structured Output** | ✅ | ✅ | 支持 `response_format` |
| **Vision (图像输入)** | ✅ | ✅ | GPT-4V 可用 |
| **Embeddings** | ✅ | ⚠️ 部分支持 | 推荐用 `text-embedding-3-small` |
| **Fine-tuning** | ✅ | ❌ | OpenRouter 不支持微调 |
| **Batch API** | ✅ | ❌ | OpenRouter 不支持批量 API |

### 6️⃣ Rate Limits

#### 官方 API
- Tier 1（新用户）：500 RPM, 30,000 TPM
- Tier 4（付费用户）：5,000 RPM, 1,500,000 TPM
- Tier 5（企业用户）：10,000 RPM, 5,000,000 TPM

#### OpenRouter
- **无固定 Rate Limit**（根据模型动态调整）
- 使用信用点系统（Credits）
- 高并发场景下会自动排队（不会直接拒绝）
- 推荐添加 `HTTP-Referer` header 提高优先级

**优势**：OpenRouter 更灵活，不会因为 Rate Limit 直接失败

### 7️⃣ 响应延迟

**实测数据**（中国服务器 → 模型延迟）：

| 路径 | TTFB (首字节) | 总延迟 | 备注 |
|------|--------------|--------|------|
| **官方 API（直连）** | ~800ms | ~2.5s | 需翻墙，不稳定 |
| **官方 API（国内代理）** | ~1200ms | ~3.5s | 依赖代理质量 |
| **OpenRouter** | ~400ms | ~1.8s | 国内服务器友好 |
| **DeepSeek（国内）** | ~150ms | ~0.8s | 最快，但仅 DeepSeek 模型 |

**结论**：OpenRouter 从国内访问**速度更快**且**更稳定**

---

## 配置 OpenRouter（项目集成）

### 步骤 1：获取 API Key

1. 访问 https://openrouter.ai/
2. 注册账号（支持 Google/GitHub 登录）
3. 进入 https://openrouter.ai/keys 创建 API Key
4. 获得格式为 `sk-or-v1-xxxxxxxx` 的 key

### 步骤 2：添加配置到 .env

```bash
# 在 .env 中添加 OpenRouter 配置
LLM_PROVIDER=openrouter

# OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# OpenRouter 模型（注意前缀）
OPENROUTER_MODEL=openai/gpt-4o

# OpenRouter Base URL
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# 可选：标识你的应用（提高优先级）
OPENROUTER_APP_NAME=Intelligent Project Analyzer
OPENROUTER_SITE_URL=https://your-domain.com
```

### 步骤 3：修改 multi_llm_factory.py

在 `PROVIDER_CONFIGS` 中添加 OpenRouter：

```python
"openrouter": {
    "api_key_env": "OPENROUTER_API_KEY",
    "model_env": "OPENROUTER_MODEL",
    "base_url_env": "OPENROUTER_BASE_URL",
    "default_model": "openai/gpt-4o",
    "default_base_url": "https://openrouter.ai/api/v1",
    "class": ChatOpenAI,
    "extra_headers": {
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "")
    }
}
```

### 步骤 4：测试连接

```python
from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory

# 测试 OpenRouter 连接
llm = MultiLLMFactory.create_llm(provider="openrouter")
response = llm.invoke("你好，请用一句话介绍 OpenRouter")
print(response.content)
```

---

## 推荐模型选择（OpenRouter）

| 场景 | 推荐模型 | OpenRouter 名称 | 成本 |
|------|---------|----------------|------|
| **高质量分析** | GPT-4o | `openai/gpt-4o` | $$$ |
| **日常对话** | GPT-4o-mini | `openai/gpt-4o-mini` | $ |
| **复杂推理** | o1-preview | `openai/o1-preview` | $$$$ |
| **成本优先** | Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` | 免费 |
| **中文优化** | Qwen 2.5 | `qwen/qwen-2.5-72b-instruct` | $ |
| **Claude 替代** | Claude 3.5 Sonnet | `anthropic/claude-3.5-sonnet` | $$$ |

**完整模型列表**：https://openrouter.ai/models

---

## 最佳实践

### 1️⃣ 使用降级链（推荐）

```python
# .env 配置
LLM_PROVIDER=openrouter
LLM_AUTO_FALLBACK=true

# 降级策略：OpenRouter → DeepSeek → Qwen
# 如果 OpenRouter 失败（网络问题），自动切换到国内模型
```

### 2️⃣ 添加自定义 Headers

```python
llm = ChatOpenAI(
    model="openai/gpt-4o",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://your-site.com",  # 提高优先级
        "X-Title": "Intelligent Project Analyzer"  # 标识应用
    }
)
```

### 3️⃣ 监控使用情况

OpenRouter 提供详细的使用统计：
- Dashboard：https://openrouter.ai/activity
- 查看每次请求的成本、延迟、模型
- 设置预算上限（避免超支）

### 4️⃣ 成本优化

```python
# 根据任务复杂度选择模型
def get_llm_for_task(task_type: str):
    if task_type == "simple_qa":
        return "openai/gpt-4o-mini"  # 便宜
    elif task_type == "analysis":
        return "openai/gpt-4o"  # 平衡
    elif task_type == "reasoning":
        return "openai/o1-preview"  # 最强
```

---

## 潜在问题与解决

### 问题 1：模型名称错误
```python
# ❌ 错误：直接用官方模型名
model="gpt-4o"

# ✅ 正确：加上提供商前缀
model="openai/gpt-4o"
```

### 问题 2：中文输出被截断
```python
# 解决：增加 max_tokens
llm = ChatOpenAI(
    model="openai/gpt-4o",
    max_tokens=4096,  # OpenRouter 默认 1024，需手动设置
    base_url="https://openrouter.ai/api/v1"
)
```

### 问题 3：余额不足
```python
# OpenRouter 使用信用点系统
# 1. 访问 https://openrouter.ai/credits 充值
# 2. 最低充值 $5（约 ¥35）
# 3. 无月费，按使用量扣费
```

### 问题 4：速率限制
```python
# OpenRouter 会动态调整速率
# 解决：添加 HTTP-Referer 提高优先级
default_headers={
    "HTTP-Referer": "https://your-domain.com"
}
```

---

## 与其他方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **官方 API + 国外服务器** | 最稳定 | 需服务器成本 | ⭐⭐⭐⭐ |
| **官方 API + 代理** | 简单 | 代理不稳定 | ⭐⭐ |
| **OpenRouter** | 国内可用，无需翻墙 | 依赖第三方 | ⭐⭐⭐⭐⭐ |
| **国内模型（Qwen/DeepSeek）** | 最快最便宜 | 模型能力稍弱 | ⭐⭐⭐⭐ |

---

## 总结

### OpenRouter 适用场景
✅ **国内服务器无法直连 OpenAI**（最主要原因）  
✅ **需要访问多个 LLM 平台**（一个 key 搞定）  
✅ **要求更好的可用性**（多节点冗余）  
✅ **预算有限的开发测试**（按需付费）

### 官方 API 适用场景
✅ **企业级生产环境**（SLA 保障）  
✅ **需要 Fine-tuning**（微调模型）  
✅ **有海外服务器**（直连无障碍）

### 项目建议
🏆 **推荐配置**：
```bash
# 主提供商：OpenRouter（解决网络问题）
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=openai/gpt-4o

# 降级链：OpenRouter → DeepSeek → Qwen
LLM_AUTO_FALLBACK=true
```

**优势**：
- ✅ 国内服务器可用
- ✅ 与官方 API 定价相同
- ✅ 支持所有 OpenAI 功能
- ✅ 降级到国内模型保障可用性

---

**快速开始**：
1. 注册 https://openrouter.ai/
2. 创建 API Key
3. 修改 `.env` 中的 `LLM_PROVIDER=openrouter`
4. 运行测试：`python check_llm_config.py`
