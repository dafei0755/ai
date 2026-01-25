# LLM服务调用重试机制实施报告

**版本**: v7.131
**日期**: 2026-01-04
**作者**: Design Beyond Team

## 📋 实施背景

### 问题描述
- **现象**: LLM调用偶发 `Connection error`，导致 Gap Question Generator 失败
- **影响**: 首次尝试失败时，系统直接降级到硬编码问题，降低用户体验
- **根本原因**: 网络不稳定、API服务波动，缺乏自动重试机制

### 目标
增加重试逻辑和超时配置，提高LLM调用成功率，减少因临时网络问题导致的失败。

---

## 🛠️ 实施方案

### 1. 创建通用重试工具模块

**文件**: `intelligent_project_analyzer/utils/llm_retry.py`

#### 核心功能
```python
# 同步调用（带重试）
response = invoke_llm_with_retry(llm, messages, config=retry_config)

# 异步调用（带重试）
response = await ainvoke_llm_with_retry(llm, messages, config=retry_config)

# 装饰器方式（同步）
@llm_retry(max_attempts=3, timeout=30)
def call_llm():
    return llm.invoke(messages)

# 装饰器方式（异步）
@async_llm_retry(max_attempts=3, timeout=30)
async def call_llm():
    return await llm.ainvoke(messages)
```

#### 重试特性
- **指数退避策略**: 等待时间按 1s, 2s, 4s, 8s... 递增（最大10s）
- **可配置参数**:
  - `max_attempts`: 最大尝试次数（默认3次）
  - `min_wait`: 最小等待时间（默认1秒）
  - `max_wait`: 最大等待时间（默认10秒）
  - `timeout`: 单次调用超时时间（默认30秒）
- **智能重试**: 只对可重试的错误进行重试
  - `httpcore.ConnectError` - 连接错误
  - `httpcore.ConnectTimeout` - 连接超时
  - `httpcore.ReadTimeout` - 读取超时
  - `openai.APIConnectionError` - API连接错误
  - `openai.APITimeoutError` - API超时
  - `openai.RateLimitError` - 速率限制
  - `ConnectionError` - 通用连接错误
  - `TimeoutError` / `asyncio.TimeoutError` - 超时错误
- **详细日志**: 记录每次重试的尝试次数、错误类型、等待时间

#### 示例日志输出
```
🚀 [LLM调用] 开始异步调用 | 最大尝试次数: 3
🔄 [LLM重试] 第 1 次重试 | 错误: ConnectError | 等待 1.0s
🔄 [LLM重试] 第 2 次重试 | 错误: ConnectError | 等待 2.0s
✅ [LLM调用] 成功 | 尝试次数: 3
```

---

### 2. 应用到关键LLM调用点

#### 2.1 LLMGapQuestionGenerator

**文件**: `intelligent_project_analyzer/services/llm_gap_question_generator.py`

**修改内容**:
```python
# 导入重试工具
from ..utils.llm_retry import LLMRetryConfig, ainvoke_llm_with_retry

# 在 generate 方法中使用重试
retry_config = LLMRetryConfig(
    max_attempts=self.generation_config.get("max_retry_attempts", 3),
    min_wait=self.generation_config.get("retry_min_wait", 1.0),
    max_wait=self.generation_config.get("retry_max_wait", 10.0),
    timeout=self.generation_config.get("llm_timeout", 30.0),
)

response = await ainvoke_llm_with_retry(llm, messages, config=retry_config)
```

**效果**: Gap Question Generator 现在能自动处理临时网络错误，提高问题生成成功率。

#### 2.2 LLMQuestionGenerator

**文件**: `intelligent_project_analyzer/interaction/questionnaire/llm_generator.py`

**修改内容**:
```python
# 导入重试工具
from ...utils.llm_retry import LLMRetryConfig, invoke_llm_with_retry

# 在 generate 方法中使用重试
retry_config = LLMRetryConfig(
    max_attempts=3,
    min_wait=1.0,
    max_wait=10.0,
    timeout=timeout,  # 使用传入的 timeout 参数
)

response = invoke_llm_with_retry(llm_model, messages, config=retry_config)
```

**效果**: 校准问卷生成器现在能自动处理临时网络错误。

---

### 3. 添加配置支持

#### 配置文件更新

**文件**: `intelligent_project_analyzer/config/prompts/gap_question_generator.yaml`

```yaml
generation_config:
  # 🆕 v7.131: LLM重试配置
  max_retry_attempts: 3     # 最大重试次数（包含首次尝试）
  retry_min_wait: 1.0       # 最小等待时间（秒）
  retry_max_wait: 10.0      # 最大等待时间（秒）
  llm_timeout: 30.0         # 单次调用超时时间（秒）
```

**优势**:
- 可通过配置文件调整重试参数，无需修改代码
- 不同场景可使用不同的重试策略
- 便于运维团队根据网络状况调优

---

## ✅ 测试验证

### 测试文件
**文件**: `tests/test_llm_retry.py`

### 测试覆盖
1. ✅ **成功调用不触发重试** - 验证正常情况下不会有性能损失
2. ✅ **网络错误触发重试** - 验证重试机制生效
3. ✅ **达到最大重试次数** - 验证最终失败时抛出正确异常
4. ✅ **超时配置生效** - 验证超时保护机制
5. ✅ **装饰器方式工作正常** - 验证两种使用方式都可用
6. ✅ **异步调用重试** - 验证异步场景下的重试
7. ✅ **配置集成验证** - 验证配置文件加载正确

### 测试结果
```
========================================= 13 passed in 8.75s =========================================
```

**所有测试通过** ✅

---

## 📊 预期效果

### 成功率提升
- **之前**: 首次连接失败 → 直接降级到硬编码问题
- **之后**: 首次连接失败 → 自动重试（最多3次）→ 成功率显著提升

### 性能影响
- **正常情况**: 无额外延迟（不触发重试）
- **网络波动**: 增加 1-10 秒延迟（自动重试）
- **完全失败**: 增加约 15 秒延迟（3次重试 + 超时）

### 用户体验改善
- 减少因临时网络问题导致的"降级"体验
- 更稳定的问题生成质量
- 更详细的错误日志，便于运维排查

---

## 🎯 使用示例

### 基础用法
```python
from intelligent_project_analyzer.utils.llm_retry import ainvoke_llm_with_retry, LLMRetryConfig
from intelligent_project_analyzer.services.llm_factory import LLMFactory

# 创建LLM
llm = LLMFactory.create_llm()

# 配置重试参数
config = LLMRetryConfig(
    max_attempts=3,
    min_wait=1.0,
    max_wait=10.0,
    timeout=30.0
)

# 调用（自动重试）
response = await ainvoke_llm_with_retry(llm, messages, config=config)
```

### 装饰器用法
```python
from intelligent_project_analyzer.utils.llm_retry import async_llm_retry

@async_llm_retry(max_attempts=3, timeout=30)
async def generate_report(llm, prompt):
    """生成报告（自动重试）"""
    return await llm.ainvoke(prompt)
```

### 自定义配置
```python
# 高优先级任务：更多重试次数
high_priority_config = LLMRetryConfig(
    max_attempts=5,
    min_wait=0.5,
    max_wait=15.0,
    timeout=60.0
)

# 低优先级任务：快速失败
low_priority_config = LLMRetryConfig(
    max_attempts=2,
    min_wait=1.0,
    max_wait=5.0,
    timeout=10.0
)
```

---

## 🔧 其他可应用的位置

当前已应用：
- ✅ `LLMGapQuestionGenerator.generate()`
- ✅ `LLMQuestionGenerator.generate()`

建议后续应用：
- 📋 `CoreTaskDecomposer` - 任务拆解
- 📋 `MotivationEngine` - 动机识别
- 📋 `DynamicDimensionGenerator` - 动态维度生成
- 📋 所有使用 `llm.invoke()` / `llm.ainvoke()` 的地方

**应用方式**: 在这些组件的LLM调用处使用 `invoke_llm_with_retry` 或 `ainvoke_llm_with_retry` 替换直接调用。

---

## 📝 注意事项

1. **不要滥用重试**: 只对临时性错误（网络问题、超时）重试，对逻辑错误（参数错误、权限问题）不应重试
2. **合理设置超时**: 超时时间应根据任务复杂度设置，避免过长或过短
3. **监控重试频率**: 如果重试频率过高，说明存在系统性问题，需要排查根本原因
4. **日志级别**: 重试日志使用 WARNING 级别，便于监控但不会淹没日志

---

## 🎉 总结

本次实施为LLM服务调用添加了完善的重试机制，具有以下特点：

✅ **通用性**: 创建了可复用的重试工具模块
✅ **灵活性**: 支持同步/异步、函数/装饰器多种使用方式
✅ **可配置**: 通过配置文件控制重试策略
✅ **智能化**: 只对可重试的错误进行重试
✅ **可观测**: 详细的日志记录每次重试
✅ **已测试**: 13个测试用例全部通过

**预期成果**: 显著提升LLM调用成功率，减少因临时网络问题导致的失败，改善用户体验。

---

## 📚 相关文件

### 新增文件
- `intelligent_project_analyzer/utils/llm_retry.py` - 重试工具模块
- `tests/test_llm_retry.py` - 测试文件
- `docs/LLM_RETRY_IMPLEMENTATION_v7.131.md` - 本文档

### 修改文件
- `intelligent_project_analyzer/services/llm_gap_question_generator.py`
- `intelligent_project_analyzer/interaction/questionnaire/llm_generator.py`
- `intelligent_project_analyzer/config/prompts/gap_question_generator.yaml`

### 依赖项
- ✅ `tenacity>=8.2.0` - 已存在于 `requirements.txt`

---

**实施完成时间**: 2026-01-04
**测试状态**: ✅ 全部通过
**部署状态**: 🟢 准备就绪
