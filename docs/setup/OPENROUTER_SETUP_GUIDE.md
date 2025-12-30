# OpenRouter 快速配置指南

## 🚀 5 分钟配置 OpenRouter（解决国内无法访问 OpenAI 问题）

### 步骤 1：注册 OpenRouter 账号（2分钟）

1. 访问 https://openrouter.ai/
2. 点击右上角 **Sign In**
3. 选择 **Google** 或 **GitHub** 登录（推荐）
4. 完成注册

### 步骤 2：获取 API Key（1分钟）

1. 登录后访问 https://openrouter.ai/keys
2. 点击 **Create Key**
3. 输入 Key 名称（如 `intelligent-project-analyzer`）
4. 复制生成的 API Key（格式：`sk-or-v1-xxxxxxxx`）

⚠️ **重要**：API Key 只显示一次，请立即保存！

### 步骤 3：充值余额（2分钟）

1. 访问 https://openrouter.ai/credits
2. 点击 **Add Credits**
3. 最低充值 **$5**（约 ¥35）
4. 支持信用卡支付（支持国内双币卡）

💡 **提示**：$5 可用于约 500 次 GPT-4o 对话（项目分析约 2-3 次）

### 步骤 4：修改项目配置（30秒）

#### 方法 A：仅使用 OpenRouter（推荐）

打开 `.env` 文件，修改以下行：

```bash
# 切换到 OpenRouter
LLM_PROVIDER=openrouter

# 填入你的 API Key
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here

# 选择模型（推荐 GPT-4o）
OPENROUTER_MODEL=openai/gpt-4o

# 可选：标识你的应用（提高优先级）
OPENROUTER_APP_NAME=Intelligent Project Analyzer
OPENROUTER_SITE_URL=https://github.com/your-repo
```

#### 方法 B：OpenRouter + 自动降级（最稳定）

```bash
# 主提供商：OpenRouter
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
OPENROUTER_MODEL=openai/gpt-4o

# 启用自动降级
LLM_AUTO_FALLBACK=true

# 降级链：OpenRouter → DeepSeek → Qwen
# 当 OpenRouter 失败时，自动切换到国内模型
DEEPSEEK_API_KEY=your_deepseek_api_key_here  # 保持原配置
QWEN_API_KEY=your_qwen_api_key_here      # 保持原配置
```

### 步骤 5：测试配置（30秒）

运行测试脚本：

```bash
python test_openrouter.py
```

**预期输出**：
```
✅ OpenRouter 配置成功!
💬 回复内容:
  OpenRouter 是一个统一的 LLM API 网关，提供访问 GPT-4、Claude、Gemini 等 100+ 模型的服务。
```

---

## 🎯 常见问题

### Q1: OpenRouter 比官方 API 贵吗？

**A**: **不贵！价格完全相同。**

| 模型 | OpenRouter | 官方 API |
|------|-----------|---------|
| gpt-4o | $2.5/$10 | $2.5/$10 |
| gpt-4o-mini | $0.15/$0.6 | $0.15/$0.6 |

### Q2: OpenRouter 速度慢吗？

**A**: **国内访问反而更快！**

- 官方 API（需翻墙）：~2.5s
- OpenRouter：~1.8s（快 30%）

### Q3: OpenRouter 支持哪些模型？

**A**: 100+ 模型，包括：

- ✅ GPT-4o、GPT-4o-mini、o1-preview
- ✅ Claude 3.5 Sonnet、Claude 3 Opus
- ✅ Gemini Pro 1.5
- ✅ Llama 3.3 70B（免费开源模型）
- ✅ Qwen、DeepSeek（中文优化）

**完整列表**：https://openrouter.ai/models

### Q4: 模型名称格式是什么？

**A**: 必须加提供商前缀：

```bash
# ❌ 错误
OPENROUTER_MODEL=gpt-4o

# ✅ 正确
OPENROUTER_MODEL=openai/gpt-4o
```

### Q5: 如何查看余额和使用情况？

**A**: 访问 https://openrouter.ai/activity

- 查看每次请求的成本、延迟、模型
- 设置预算上限（避免超支）
- 实时余额显示

### Q6: 支持 Function Calling 吗？

**A**: ✅ 完全支持！

OpenRouter 与官方 API **100% 兼容**，支持：
- Function Calling
- Streaming
- Structured Output
- Vision（图像输入）

### Q7: 安全吗？会保存我的数据吗？

**A**: 
- ✅ OpenRouter 不存储请求内容
- ✅ 使用 HTTPS 加密传输
- ✅ 符合 GDPR/SOC2 标准
- 📖 隐私政策：https://openrouter.ai/privacy

### Q8: 余额用完了怎么办？

**A**: 
1. 访问 https://openrouter.ai/credits
2. 点击 **Add Credits** 充值
3. 支持信用卡/PayPal

💡 **提示**：可以设置自动充值（余额低于 $1 时自动充值 $5）

---

## 🔥 推荐配置（不同场景）

### 场景 1：高质量项目分析

```bash
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=openai/gpt-4o
TEMPERATURE=0.7
MAX_TOKENS=32000
```

**成本**：约 $1-2 / 次分析

### 场景 2：成本优先

```bash
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=openai/gpt-4o-mini  # 便宜 10 倍
TEMPERATURE=0.7
MAX_TOKENS=16000
```

**成本**：约 $0.1-0.2 / 次分析

### 场景 3：免费测试

```bash
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct  # 完全免费
TEMPERATURE=0.8
MAX_TOKENS=8000
```

**成本**：免费！

### 场景 4：最稳定（生产环境）

```bash
# 主提供商：OpenRouter（国内快）
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=openai/gpt-4o

# 自动降级：OpenRouter → DeepSeek → Qwen
LLM_AUTO_FALLBACK=true
```

**优势**：
- OpenRouter 正常时使用 GPT-4o（高质量）
- OpenRouter 失败时自动切换到 DeepSeek（国内快）
- 所有提供商都失败才报错（可用性 99.9%+）

---

## 📊 成本估算

### 单次工作流消耗（GPT-4o）

| 阶段 | Tokens | 成本 |
|------|--------|------|
| 需求分析 | ~8,000 | $0.02 |
| 角色选择 | ~5,000 | $0.01 |
| 质量预检 | ~15,000 | $0.04 |
| Agent 执行 | ~80,000 | $0.20 |
| 审核流程 | ~25,000 | $0.06 |
| 报告生成 | ~45,000 | $0.11 |
| **总计** | **~178,000** | **$0.44** |

**每月 100 次分析**：约 $44（¥310）

### 降本策略

| 策略 | 节省 | 方法 |
|------|------|------|
| 使用 gpt-4o-mini | 90% | `OPENROUTER_MODEL=openai/gpt-4o-mini` |
| 减少 max_tokens | 30% | `MAX_TOKENS=16000`（仅影响长输出） |
| 降低 temperature | 10% | `TEMPERATURE=0.5`（减少重复生成） |
| 使用免费模型（Llama） | 100% | `OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct` |

---

## ✅ 配置检查清单

完成以下检查后，OpenRouter 就可以正常使用了：

- [ ] 已注册 OpenRouter 账号
- [ ] 已获取 API Key（`sk-or-v1-...`）
- [ ] 已充值至少 $5
- [ ] 已修改 `.env`：`LLM_PROVIDER=openrouter`
- [ ] 已填写 `OPENROUTER_API_KEY`
- [ ] 模型名称格式正确（如 `openai/gpt-4o`）
- [ ] 运行 `python test_openrouter.py` 测试成功

---

## 🆘 遇到问题？

### 错误：`Missing or invalid API key`

**原因**：API Key 未配置或格式错误

**解决**：
```bash
# 检查 .env 文件
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here  # 必须是 sk-or-v1- 开头
```

### 错误：`Model not found`

**原因**：模型名称格式错误

**解决**：
```bash
# ❌ 错误
OPENROUTER_MODEL=gpt-4o

# ✅ 正确
OPENROUTER_MODEL=openai/gpt-4o
```

### 错误：`Insufficient credits`

**原因**：余额不足

**解决**：访问 https://openrouter.ai/credits 充值

### 错误：`Rate limit exceeded`

**原因**：请求频率过高

**解决**：
1. 添加 `HTTP-Referer` header（已自动配置）
2. 降低并发数：`MAX_CONCURRENT_AGENTS=3`

---

## 📚 更多资源

- 官网：https://openrouter.ai/
- 文档：https://openrouter.ai/docs
- 模型列表：https://openrouter.ai/models
- 使用统计：https://openrouter.ai/activity
- Discord 社区：https://discord.gg/openrouter

---

**配置完成后，立即运行：**

```bash
# 1. 测试 OpenRouter
python test_openrouter.py

# 2. 启动服务
python intelligent_project_analyzer/api/server.py

# 3. 运行前端（新终端）
python intelligent_project_analyzer/frontend/run_frontend.py
```

🎉 **现在你可以在国内服务器上流畅使用 GPT-4 了！**
