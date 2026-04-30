# Vision API 配置指南

**版本**: v3.8
**更新日期**: 2025-11-30

---

## 概述

系统支持两种Vision API提供商用于图片内容分析：

1. **OpenAI GPT-4o Vision** - 高质量，需付费
2. **Google Gemini Vision** - 高质量，有免费配额

---

## 提供商对比

| 特性 | OpenAI GPT-4o | Google Gemini |
|------|--------------|---------------|
| **模型名称** | `gpt-4o` | `gemini-1.5-flash` / `gemini-1.5-pro` |
| **免费配额** | ❌ 无免费配额 | ✅ 15次/分钟（免费） |
| **付费价格** | $0.005/图片 | $0.001/图片（Flash） |
| **响应速度** | ~3-4秒 | ~2-3秒 |
| **分析质量** | 优秀 | 优秀 |
| **中文支持** | ✅ 原生支持 | ✅ 原生支持 |
| **适用场景** | 高精度商业项目 | 快速原型、开发测试 |

**推荐选择**：
- 🆓 **开发/测试阶段**：使用 Google Gemini（免费）
- 💼 **生产环境**：根据预算选择 OpenAI 或 Gemini Pro

---

## 配置方案 1: OpenAI GPT-4o Vision（默认）

### 步骤 1: 获取 OpenAI API Key

1. 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 登录或注册账号
3. 创建新的API Key
4. 复制API Key（格式：`sk-...`）

### 步骤 2: 配置环境变量

在项目根目录创建或编辑 `.env` 文件：

```bash
# OpenAI配置
OPENAI_API_KEY=sk-your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1  # 可选，使用国内代理时修改
```

### 步骤 3: 启用 OpenAI Vision（默认配置）

不需要额外配置，系统默认使用 OpenAI。如果需要显式指定：

```bash
# .env
VISION_PROVIDER=openai  # 默认值，可省略
```

### 步骤 4: 验证配置

运行测试脚本：

```bash
python test_phase2.py
```

预期输出：
```
✅ Vision API已启用 (OpenAI GPT-4V)
✅ 图片Vision API分析
  - Vision分析: 已启用
```

---

## 配置方案 2: Google Gemini Vision（推荐）🆕

### 步骤 1: 获取 Gemini API Key（免费）

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 使用Google账号登录
3. 点击 **"Create API Key"**
4. 选择或创建 Google Cloud 项目
5. 复制生成的API Key

**提示**：Gemini 免费配额为 **每分钟15次请求**，足够开发和测试使用。

### 步骤 2: 安装依赖

```bash
pip install langchain-google-genai
```

### 步骤 3: 配置环境变量

在 `.env` 文件中添加：

```bash
# Gemini配置
VISION_PROVIDER=gemini
GOOGLE_API_KEY=your_gemini_api_key_here
```

**完整配置示例**：
```bash
# .env - 完整示例

# 选择Vision API提供商
VISION_PROVIDER=gemini  # 或 openai

# OpenAI配置（如果使用OpenAI）
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1

# Gemini配置（如果使用Gemini）
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 步骤 4: 重启服务

```bash
# 后端服务
uvicorn intelligent_project_analyzer.api.server:app --reload

# 或使用启动脚本
python -m intelligent_project_analyzer.api.server
```

### 步骤 5: 验证配置

运行测试脚本：

```bash
python test_phase2.py
```

预期输出：
```
✅ Vision API已启用 (Google Gemini)
✅ 图片Vision API分析
  - Vision分析: 已启用
```

---

## 禁用 Vision API

如果不需要图片分析功能（仅提取图片基本信息）：

### 方法 1: 环境变量

```bash
# .env
ENABLE_VISION_API=false
```

### 方法 2: 代码配置

修改 `file_processor.py`:

```python
file_processor = FileProcessor(enable_vision_api=False)
```

**效果**：上传图片时仅返回基本信息（尺寸、格式），不进行AI分析。

---

## 故障排查

### 1. OpenAI API 错误

#### 错误信息: `Error code: 401 - Incorrect API key`
**原因**：API Key无效或未配置
**解决方案**：
```bash
# 检查.env文件
cat .env | grep OPENAI_API_KEY

# 确保API Key格式正确（以sk-开头）
OPENAI_API_KEY=sk-...
```

#### 错误信息: `Error code: 429 - You exceeded your current quota`
**原因**：账户配额不足或余额为0
**解决方案**：
- 访问 [OpenAI Billing](https://platform.openai.com/account/billing) 充值
- 或切换到 Google Gemini（免费配额）

#### 错误信息: `Connection timeout`
**原因**：网络连接问题或被墙
**解决方案**：
```bash
# 使用代理
OPENAI_API_BASE=https://your-proxy.com/v1
```

---

### 2. Google Gemini API 错误

#### 错误信息: `Invalid API key`
**原因**：API Key无效或未启用
**解决方案**：
1. 检查API Key是否正确复制
2. 确认 [Google AI Studio](https://makersuite.google.com/app/apikey) 中API Key状态为"Active"
3. 检查环境变量配置：
```bash
echo $GOOGLE_API_KEY
```

#### 错误信息: `Resource has been exhausted (e.g. check quota)`
**原因**：超过免费配额（15次/分钟）
**解决方案**：
- 等待1分钟后重试
- 或升级到付费计划

#### 错误信息: `langchain_google_genai module not found`
**原因**：缺少依赖包
**解决方案**：
```bash
pip install langchain-google-genai
```

---

### 3. Vision API 功能未生效

#### 症状：上传图片后没有AI分析内容

**排查步骤**：

1. **检查Vision API是否启用**
```bash
# 查看日志
tail -f logs/app.log | grep "Vision API"
```

预期输出：
```
✅ Vision API已启用 (OpenAI GPT-4V)
# 或
✅ Vision API已启用 (Google Gemini)
```

2. **检查环境变量**
```bash
cat .env | grep VISION_PROVIDER
cat .env | grep GOOGLE_API_KEY
```

3. **检查是否优雅降级**
如果API调用失败，系统会自动降级返回基本信息。查看日志：
```bash
tail -f logs/app.log | grep "Vision API调用失败"
```

---

## 切换提供商

### 从 OpenAI 切换到 Gemini

```bash
# .env
VISION_PROVIDER=gemini  # 修改这一行
GOOGLE_API_KEY=your_gemini_api_key  # 添加这一行
```

重启服务即可。

### 从 Gemini 切换到 OpenAI

```bash
# .env
VISION_PROVIDER=openai  # 修改这一行
OPENAI_API_KEY=sk-...  # 确保已配置
```

重启服务即可。

---

## 最佳实践

### 1. 开发环境

**推荐配置**：
```bash
# .env
VISION_PROVIDER=gemini
GOOGLE_API_KEY=your_gemini_api_key
```

**理由**：
- ✅ 免费配额（15次/分钟）
- ✅ 快速响应（~2-3秒）
- ✅ 适合开发和测试

### 2. 生产环境

#### 方案A：低成本（推荐中小项目）
```bash
VISION_PROVIDER=gemini
GOOGLE_API_KEY=your_gemini_api_key
```
- 成本：$0.001/图片（Flash）
- 适用：日均<1000张图片的项目

#### 方案B：高精度（推荐大型商业项目）
```bash
VISION_PROVIDER=openai
OPENAI_API_KEY=sk-...
```
- 成本：$0.005/图片
- 适用：对分析质量要求极高的场景

### 3. 高并发场景

如果使用Gemini免费配额遇到限流，建议：

1. **升级付费计划**（更高配额）
2. **实现请求队列**（平滑流量）
3. **缓存常见图片**（减少重复请求）

---

## 代码示例

### 手动调用 Vision API

```python
from intelligent_project_analyzer.services.file_processor import file_processor
from pathlib import Path

# 提取图片内容（自动使用配置的提供商）
result = await file_processor.extract_content(
    file_path=Path("./uploads/design.jpg"),
    content_type="image/jpeg"
)

print(result['vision_analysis'])  # AI分析内容
```

### 切换提供商（代码方式）

```python
from intelligent_project_analyzer.services.file_processor import FileProcessor

# 使用 Gemini
processor = FileProcessor(
    enable_vision_api=True,
    vision_provider="gemini"
)

# 使用 OpenAI
processor = FileProcessor(
    enable_vision_api=True,
    vision_provider="openai"
)
```

---

## 总结

### OpenAI GPT-4o Vision
- ✅ 优点：分析深度好，稳定性高
- ❌ 缺点：需要付费，成本较高
- 🎯 适用：商业项目、高精度需求

### Google Gemini Vision
- ✅ 优点：免费配额，响应快，成本低
- ❌ 缺点：免费配额有限（15次/分钟）
- 🎯 适用：开发测试、中小项目

**最佳实践**：开发阶段使用 Gemini，生产环境根据预算和需求选择。

---

**相关文档**：
- [Phase 2: 增强文件提取功能](./phase2_enhanced_extraction.md)
- [多模态输入实现文档](./multimodal_input_implementation.md)
- [用户使用指南](./multimodal_usage_guide.md)
