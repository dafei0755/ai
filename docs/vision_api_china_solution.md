# Vision API 国内访问解决方案

**更新日期**: 2025-11-30
**问题**: Gemini/OpenAI Vision API 在国内无法直接访问
**解决方案**: 通过 OpenRouter 中转，实现国内直接可用

---

## 🚀 推荐方案：GPT-4o Vision via OpenRouter

### ✅ 方案优势

| 特性 | GPT-4o via OpenRouter |
|------|----------------------|
| 国内可用 | ✅ 直接可用，无需翻墙 |
| 分析质量 | ✅✅✅ 最优（OpenAI GPT-4o） |
| 响应速度 | ⚡ ~3-4秒 |
| 中文支持 | ✅ 原生支持 |
| 稳定性 | ✅✅ 生产环境可用 |
| 费用 | 💰 ~$0.005/图片 |

### 📝 配置步骤

#### 1. 确认 OpenRouter API Key

在 `.env` 文件中已有配置：
```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

#### 2. 设置 Vision 提供商

在 `.env` 文件中设置：
```bash
# Vision API 提供商选择
VISION_PROVIDER=openai-openrouter  # 推荐国内用户

# 启用 Vision API
ENABLE_VISION_API=true
```

#### 3. 测试配置

运行测试脚本验证：
```bash
python test_openai_openrouter.py
```

**预期输出**：
```
✅ GPT-4o Vision (via OpenRouter) 配置成功!
  国内直接可用，无需翻墙
  OpenAI GPT-4o，最强视觉理解能力
  响应速度快 (~3-4秒)
  支持中文，深度分析设计元素
```

---

## 🔄 所有可选方案对比

| 方案 | 国内可用 | 费用 | 质量 | 速度 | 推荐度 |
|------|---------|------|------|------|--------|
| **openai-openrouter** | ✅ | 💰💰 | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ 推荐 |
| openai | ❌ | 💰💰 | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | ⭐ 需翻墙 |
| gemini | ❌ | 免费 | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | ⭐ 需翻墙 |
| gemini-openrouter | ✅ | 免费 | ⭐⭐⭐ | ⚡⚡⚡ | ⭐⭐ 支持有限 |

### 方案详情

#### 1. openai-openrouter (推荐) ✅

**配置**：
```bash
VISION_PROVIDER=openai-openrouter
OPENROUTER_API_KEY=sk-or-v1-...
```

**特点**：
- ✅ **国内直接可用**，无需任何代理
- ✅ 使用 OpenAI GPT-4o，分析质量最优
- ✅ 响应速度 ~3-4秒
- ✅ 完美支持中文
- ✅ 生产环境推荐
- 💰 费用: ~$0.005/图片

**适用场景**：
- 商业项目
- 对分析质量要求高
- 国内部署环境
- 生产环境

#### 2. openai (官方)

**配置**：
```bash
VISION_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**特点**：
- ❌ **需要翻墙**访问
- ✅ OpenAI 官方，质量最优
- ✅ 响应速度 ~3-4秒
- 💰 费用: ~$0.005/图片

**适用场景**：
- 海外部署
- 有稳定翻墙环境

#### 3. gemini (官方)

**配置**：
```bash
VISION_PROVIDER=gemini
GOOGLE_API_KEY=AIzaS...
```

**特点**：
- ❌ **需要翻墙**访问 Google 服务
- ✅ 免费配额: 15次/分钟, 1500次/天
- ✅ 响应速度 ~2-3秒
- ✅ 质量优秀

**适用场景**：
- 海外部署
- 开发测试（免费）

#### 4. gemini-openrouter

**配置**：
```bash
VISION_PROVIDER=gemini-openrouter
OPENROUTER_API_KEY=sk-or-v1-...
```

**特点**：
- ✅ 国内直接可用
- ✅ 免费（OpenRouter 提供）
- ⚠️ 支持有限（模型可能不稳定）
- ⚠️ 质量不如 GPT-4o

**适用场景**：
- 预算极其有限
- 开发测试

---

## 💡 使用示例

### 完整的 .env 配置示例

```bash
# ============================================================================
# 🖼️ Vision API 配置 (用于图片内容分析)
# ============================================================================

# Vision API 提供商选择（推荐国内用户）
VISION_PROVIDER=openai-openrouter

# OpenRouter API Key (国内直接可用)
OPENROUTER_API_KEY=sk-or-v1-your_key_here

# 是否启用Vision API
ENABLE_VISION_API=true

# 可选: Google Gemini API Key (如需使用 gemini 方案)
GOOGLE_API_KEY=AIzaS...

# 可选: OpenAI 官方 API Key (如需使用 openai 方案)
OPENAI_API_KEY=sk-...
```

### 代码中使用

系统会自动根据 `VISION_PROVIDER` 配置选择提供商，无需修改代码：

```python
from intelligent_project_analyzer.services.file_processor import file_processor

# 上传图片并分析
result = await file_processor.extract_content(
    file_path=Path("design.jpg"),
    content_type="image/jpeg"
)

# 获取 AI 分析结果
print(result['vision_analysis'])
```

---

## 🧪 测试脚本

我们提供了3个测试脚本：

### 1. test_openai_openrouter.py (推荐)
测试 GPT-4o via OpenRouter（国内最佳方案）

```bash
python test_openai_openrouter.py
```

### 2. test_gemini_vision.py
测试 Google Gemini 官方（需翻墙）

```bash
python test_gemini_vision.py
```

### 3. test_gemini_openrouter.py
测试 Gemini via OpenRouter（备选方案）

```bash
python test_gemini_openrouter.py
```

---

## 🔧 故障排查

### 问题1：API 调用超时

**可能原因**：
- 网络连接问题
- OpenRouter 服务暂时不可用

**解决方案**：
```bash
# 1. 测试网络连接
curl https://openrouter.ai/api/v1/models

# 2. 检查 API Key 是否有效
echo $OPENROUTER_API_KEY
```

### 问题2：Vision API 未启用

**错误信息**：`Vision API未启用`

**解决方案**：
```bash
# 检查 .env 配置
ENABLE_VISION_API=true
VISION_PROVIDER=openai-openrouter
```

### 问题3：API Key 无效

**错误信息**：`Error code: 401`

**解决方案**：
1. 访问 [OpenRouter Keys](https://openrouter.ai/keys)
2. 确认 API Key 有效且有余额
3. 更新 `.env` 文件

### 问题4：模型不支持

**错误信息**：`Error code: 404 - No endpoints found`

**解决方案**：
- 确保使用 `VISION_PROVIDER=openai-openrouter`
- 模型名称为 `openai/gpt-4o`（已在代码中配置）

---

## 💰 费用说明

### OpenRouter 定价

| 服务 | 价格 | 说明 |
|------|------|------|
| GPT-4o Vision | $0.005/图片 | 与OpenAI官方相同 |
| 充值方式 | 信用卡/加密货币 | 支持国际信用卡 |
| 最低充值 | $5 | 可分析约1000张图片 |

### 费用估算

| 使用场景 | 图片数量 | 月费用 |
|---------|---------|--------|
| 小型项目 | ~100张/月 | $0.5 |
| 中型项目 | ~500张/月 | $2.5 |
| 大型项目 | ~2000张/月 | $10 |

---

## 📝 最佳实践

### 1. 开发环境

**推荐配置**：
```bash
VISION_PROVIDER=openai-openrouter
```

**理由**：
- 国内直接可用
- 稳定可靠
- 费用可控

### 2. 生产环境

**推荐配置**：
```bash
VISION_PROVIDER=openai-openrouter
```

**理由**：
- 无需翻墙，稳定性高
- GPT-4o 质量最优
- 适合商业项目

### 3. 成本优化

如果预算有限，可以考虑：

1. **限制调用频率**
   - 仅对用户主动上传的图片分析
   - 缓存常见图片的分析结果

2. **按场景选择**
   - 重要图片：使用 GPT-4o
   - 一般图片：使用 gemini-openrouter（免费）

3. **批量处理**
   - 收集图片批量分析
   - 利用OpenRouter的批量折扣

---

## 🎯 总结

### 国内用户最佳方案

✅ **推荐配置**：
```bash
VISION_PROVIDER=openai-openrouter
OPENROUTER_API_KEY=sk-or-v1-...
ENABLE_VISION_API=true
```

### 核心优势

| 特性 | 说明 |
|------|------|
| 🌐 国内可用 | 无需翻墙，直接访问 |
| 🎯 质量最优 | OpenAI GPT-4o，业界最强 |
| ⚡ 响应快速 | ~3-4秒完成分析 |
| 💰 费用透明 | $0.005/图片，可控 |
| 🛡️ 生产级 | 稳定可靠，适合商用 |

---

**相关文档**：
- [Vision API 配置指南](./vision_api_setup.md)
- [Phase 2: 增强文件提取功能](./phase2_enhanced_extraction.md)
- [多模态输入实现文档](./multimodal_input_implementation.md)

**测试脚本**：
- `test_openai_openrouter.py` - 推荐方案测试
- `test_gemini_vision.py` - Gemini 官方测试
- `test_gemini_openrouter.py` - Gemini via OpenRouter 测试
