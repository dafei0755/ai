# UCPPT v7.270 测试文档

## 概述

本文档描述 UCPPT v7.270 的完整测试策略，包括单元测试、集成测试、端到端测试和回归测试。

## 测试文件清单

| 测试类型 | 文件路径 | 测试内容 | 运行时间 |
|---------|---------|---------|---------|
| 单元测试 | `tests/test_ucppt_v7270_unit.py` | 数据结构、Prompt生成、辅助方法 | ~5秒 |
| 集成测试 | `tests/test_ucppt_v7270_integration.py` | 两步流程、事件流、错误处理 | ~30秒 |
| 端到端测试 | `tests/test_ucppt_v7270_e2e.py` | 完整流程、真实场景、性能 | ~2分钟 |
| 回归测试 | `tests/test_ucppt_v7270_regression.py` | 向后兼容性、现有功能 | ~20秒 |

## 快速开始

### 运行所有测试

```bash
cd tests
run_v7270_tests.bat
```

### 运行单个测试套件

```bash
# 单元测试
pytest test_ucppt_v7270_unit.py -v

# 集成测试
pytest test_ucppt_v7270_integration.py -v

# 端到端测试（跳过慢速测试）
pytest test_ucppt_v7270_e2e.py -v -m "not slow"

# 回归测试
pytest test_ucppt_v7270_regression.py -v
```

### 运行特定测试

```bash
# 运行特定测试类
pytest test_ucppt_v7270_unit.py::TestProblemSolvingApproach -v

# 运行特定测试方法
pytest test_ucppt_v7270_unit.py::TestProblemSolvingApproach::test_create_instance -v
```

## 测试详解

### 1. 单元测试 (test_ucppt_v7270_unit.py)

#### 测试类：TestProblemSolvingApproach

**目的**: 测试 `ProblemSolvingApproach` 数据结构

**测试用例**:
- `test_create_instance`: 测试创建实例
- `test_to_dict`: 测试转换为字典
- `test_from_dict`: 测试从字典创建实例
- `test_to_plain_text`: 测试生成纯文本格式
- `test_serialization_roundtrip`: 测试序列化往返
- `test_empty_optional_fields`: 测试可选字段为空的情况

**示例**:
```python
def test_create_instance(self):
    approach = ProblemSolvingApproach(
        task_type="design",
        complexity_level="complex",
        solution_steps=[...],
        # ...
    )
    assert approach.task_type == "design"
```

#### 测试类：TestStep2PromptGeneration

**目的**: 测试 Step2 Prompt 生成

**测试用例**:
- `test_build_step2_prompt_structure`: 测试 Prompt 结构
- `test_build_step2_prompt_keyword_requirements`: 测试关键词生成要求
- `test_build_step2_prompt_output_format`: 测试输出格式要求
- `test_build_step2_prompt_with_minimal_data`: 测试最小数据生成

**示例**:
```python
def test_build_step2_prompt_structure(self, engine, ...):
    prompt = engine._build_step2_search_framework_prompt(...)
    assert "## 用户问题" in prompt
    assert "### 解题路径" in prompt
```

#### 测试类：TestHelperMethods

**目的**: 测试辅助方法

**测试用例**:
- `test_build_default_problem_solving_approach`: 测试构建默认解题思路
- `test_generate_framework_checklist`: 测试生成框架清单
- `test_generate_framework_checklist_with_many_targets`: 测试多目标清单生成

### 2. 集成测试 (test_ucppt_v7270_integration.py)

#### 测试类：TestTwoStepFlowIntegration

**目的**: 测试两步流程的完整集成

**测试用例**:
- `test_step1_generates_problem_solving_approach`: 测试第一步生成解题思路
- `test_step1_provides_step2_context`: 测试第一步提供 step2_context
- `test_step2_generates_search_framework`: 测试第二步生成搜索框架
- `test_complete_two_step_flow`: 测试完整的两步流程

**示例**:
```python
@pytest.mark.asyncio
async def test_step1_generates_problem_solving_approach(self, engine, sample_query):
    events = []
    async for event in engine._unified_analysis_stream(sample_query):
        events.append(event)

    event_types = [e.get("type") for e in events]
    assert "problem_solving_approach_ready" in event_types
```

#### 测试类：TestEventFlow

**目的**: 测试事件流的正确性

**测试用例**:
- `test_event_order`: 测试事件顺序
- `test_event_data_completeness`: 测试事件数据完整性

#### 测试类：TestErrorHandling

**目的**: 测试错误处理和降级

**测试用例**:
- `test_step1_failure_fallback`: 测试第一步失败时的降级
- `test_step2_failure_fallback`: 测试第二步失败时的降级
- `test_default_problem_solving_approach`: 测试默认解题思路的生成

#### 测试类：TestBackwardCompatibility

**目的**: 测试向后兼容性

**测试用例**:
- `test_old_flow_still_works`: 测试旧流程仍然可用
- `test_new_flow_detection`: 测试新流程检测

#### 测试类：TestDataConsistency

**目的**: 测试数据一致性

**测试用例**:
- `test_step2_context_consistency`: 测试 step2_context 的一致性
- `test_search_target_field_consistency`: 测试 SearchTarget 字段的一致性

### 3. 端到端测试 (test_ucppt_v7270_e2e.py)

#### 测试类：TestHAYMinsuCase

**目的**: 测试HAY民宿案例（完整流程）

**测试用例**:
- `test_hay_minsu_complete_flow`: 测试HAY民宿案例的完整流程（标记为 slow）
- `test_hay_minsu_solution_steps_quality`: 测试HAY民宿案例的解题步骤质量

**示例**:
```python
@pytest.mark.asyncio
@pytest.mark.slow
async def test_hay_minsu_complete_flow(self, engine, hay_minsu_query):
    # 完整流程测试，包含详细的日志输出
    print(f"\n{'='*80}")
    print(f"🧪 测试案例: HAY民宿概念设计")
    # ...
```

#### 测试类：TestRealWorldScenarios

**目的**: 测试真实场景

**测试用例**:
- `test_different_query_types`: 参数化测试不同类型的查询
  - 决策型查询
  - 研究型查询
  - 设计型查询
  - 探索型查询

#### 测试类：TestPerformance

**目的**: 性能测试

**测试用例**:
- `test_step1_performance`: 测试第一步的性能（标记为 slow）
- `test_memory_usage`: 测试内存使用

#### 测试类：TestEdgeCases

**目的**: 边界情况测试

**测试用例**:
- `test_very_short_query`: 测试非常短的查询
- `test_very_long_query`: 测试非常长的查询
- `test_special_characters_query`: 测试包含特殊字符的查询
- `test_multilingual_query`: 测试多语言查询

#### 测试类：TestConcurrency

**目的**: 并发测试

**测试用例**:
- `test_concurrent_requests`: 测试并发请求（标记为 slow）

### 4. 回归测试 (test_ucppt_v7270_regression.py)

#### 测试类：TestBackwardCompatibility

**目的**: 测试向后兼容性

**测试用例**:
- `test_old_search_framework_format_still_works`: 测试旧的搜索框架格式仍然可用
- `test_mixed_format_handling`: 测试混合格式处理

#### 测试类：TestExistingFeaturesUnaffected

**目的**: 测试现有功能未受影响

**测试用例**:
- `test_search_target_creation`: 测试 SearchTarget 创建（旧方式）
- `test_search_target_to_dict`: 测试 SearchTarget.to_dict() 向后兼容
- `test_search_framework_creation`: 测试 SearchFramework 创建
- `test_search_framework_get_next_target`: 测试 SearchFramework.get_next_target() 方法

#### 测试类：TestDataFormatCompatibility

**目的**: 测试数据格式兼容性

**测试用例**:
- `test_old_json_format_parsing`: 测试旧 JSON 格式解析
- `test_new_json_format_parsing`: 测试新 JSON 格式解析

#### 测试类：TestAPIInterfaceCompatibility

**目的**: 测试 API 接口兼容性

**测试用例**:
- `test_unified_analysis_stream_signature`: 测试方法签名未变
- `test_build_search_framework_from_json_signature`: 测试方法签名未变
- `test_search_target_methods_unchanged`: 测试 SearchTarget 方法未变

#### 测试类：TestEventStreamCompatibility

**目的**: 测试事件流兼容性

**测试用例**:
- `test_old_events_still_emitted`: 测试旧事件仍然被发送
- `test_new_events_are_optional`: 测试新事件是可选的

#### 测试类：TestRegressionScenarios

**目的**: 回归场景测试

**测试用例**:
- `test_simple_query_still_works`: 测试简单查询仍然可用
- `test_complex_query_still_works`: 测试复杂查询仍然可用
- `test_default_values_unchanged`: 测试默认值未变

## 测试标记

### 标记说明

- `@pytest.mark.asyncio`: 异步测试
- `@pytest.mark.slow`: 慢速测试（通常需要调用真实的 LLM）
- `@pytest.mark.parametrize`: 参数化测试

### 跳过慢速测试

```bash
# 跳过标记为 slow 的测试
pytest -m "not slow"

# 只运行慢速测试
pytest -m "slow"
```

## 测试覆盖率

### 生成覆盖率报告

```bash
# 安装 pytest-cov
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest tests/test_ucppt_v7270_*.py --cov=intelligent_project_analyzer.services.ucppt_search_engine --cov-report=html

# 查看报告
start htmlcov/index.html
```

### 目标覆盖率

| 模块 | 目标覆盖率 | 当前覆盖率 |
|------|-----------|-----------|
| ProblemSolvingApproach | 100% | - |
| _build_step2_search_framework_prompt | 90% | - |
| _step2_generate_search_framework | 85% | - |
| _unified_analysis_stream | 80% | - |
| search_deep (两步流程部分) | 80% | - |

## 测试数据

### 示例查询

测试中使用的示例查询：

1. **HAY民宿案例**（完整测试）:
   ```
   以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计
   ```

2. **简单查询**:
   ```
   什么是北欧风格？
   ```

3. **决策型查询**:
   ```
   如何选择适合小户型的北欧风格家具？
   ```

4. **研究型查询**:
   ```
   分析2024年中国室内设计行业趋势
   ```

5. **设计型查询**:
   ```
   为咖啡馆设计一套完整的VI系统
   ```

### Mock 数据

测试中使用的 Mock 数据示例：

```python
# 旧格式响应
old_format_response = {
    "user_profile": {...},
    "analysis": {...},
    "search_framework": {
        "core_question": "...",
        "targets": [...]
    }
}

# 新格式响应
new_format_response = {
    "user_profile": {...},
    "analysis": {...},
    "problem_solving_approach": {...},
    "step2_context": {...}
}
```

## 持续集成

### GitHub Actions 配置

创建 `.github/workflows/test-v7270.yml`:

```yaml
name: UCPPT v7.270 Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov

    - name: Run unit tests
      run: pytest tests/test_ucppt_v7270_unit.py -v

    - name: Run integration tests
      run: pytest tests/test_ucppt_v7270_integration.py -v

    - name: Run regression tests
      run: pytest tests/test_ucppt_v7270_regression.py -v

    - name: Run E2E tests (fast only)
      run: pytest tests/test_ucppt_v7270_e2e.py -v -m "not slow"

    - name: Generate coverage report
      run: |
        pytest tests/test_ucppt_v7270_*.py \
          --cov=intelligent_project_analyzer.services.ucppt_search_engine \
          --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
```

## 故障排查

### 常见问题

#### 1. 测试超时

**问题**: 测试运行时间过长或超时

**解决方案**:
```bash
# 增加超时时间
pytest --timeout=300

# 跳过慢速测试
pytest -m "not slow"
```

#### 2. LLM 调用失败

**问题**: 测试中 LLM 调用失败

**解决方案**:
- 检查 API 密钥配置
- 使用 Mock 替代真实 LLM 调用
- 跳过需要 LLM 的测试

```python
@pytest.mark.skipif(not has_llm_access(), reason="需要 LLM 访问")
async def test_with_llm(self, engine):
    # ...
```

#### 3. 异步测试失败

**问题**: 异步测试运行失败

**解决方案**:
```bash
# 确保安装 pytest-asyncio
pip install pytest-asyncio

# 检查 pytest.ini 配置
# [pytest]
# asyncio_mode = auto
```

#### 4. 导入错误

**问题**: 无法导入模块

**解决方案**:
```bash
# 设置 PYTHONPATH
set PYTHONPATH=%CD%

# 或在测试文件开头添加
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```

## 最佳实践

### 1. 测试隔离

每个测试应该独立运行，不依赖其他测试的状态：

```python
@pytest.fixture
def engine(self):
    """每个测试使用新的引擎实例"""
    return UcpptSearchEngine()
```

### 2. 使用 Fixture

使用 pytest fixture 共享测试数据：

```python
@pytest.fixture
def sample_query(self):
    return "测试查询"

def test_something(self, engine, sample_query):
    # 使用 fixture
    pass
```

### 3. 参数化测试

使用参数化减少重复代码：

```python
@pytest.mark.parametrize("query,expected_type", [
    ("设计民宿", "design"),
    ("分析趋势", "research"),
])
def test_query_types(self, engine, query, expected_type):
    # ...
```

### 4. 清晰的断言消息

提供清晰的断言消息：

```python
assert len(steps) >= 5, \
    f"解题步骤应该至少5步，实际: {len(steps)}"
```

### 5. 测试文档

为复杂测试添加文档字符串：

```python
def test_complex_scenario(self):
    """
    测试复杂场景：
    1. 第一步生成解题思路
    2. 第二步生成搜索框架
    3. 验证数据一致性
    """
    # ...
```

## 性能基准

### 基准测试结果

| 测试 | 平均耗时 | 最大耗时 | 内存使用 |
|------|---------|---------|---------|
| 单元测试（全部） | 5秒 | 10秒 | <50MB |
| 集成测试（全部） | 30秒 | 60秒 | <100MB |
| E2E测试（快速） | 1分钟 | 2分钟 | <200MB |
| E2E测试（完整） | 5分钟 | 10分钟 | <500MB |
| 回归测试（全部） | 20秒 | 40秒 | <100MB |

### 性能优化建议

1. **并行运行测试**:
   ```bash
   pytest -n auto  # 需要 pytest-xdist
   ```

2. **缓存 LLM 响应**:
   ```python
   @pytest.fixture(scope="session")
   def cached_llm_response():
       # 缓存 LLM 响应
       pass
   ```

3. **使用更快的模型**:
   ```python
   # 测试时使用更快的模型
   engine.eval_model = "deepseek-chat"  # 而非 gpt-4
   ```

## 下一步

1. **运行测试**: 使用 `run_v7270_tests.bat` 运行所有测试
2. **查看报告**: 检查测试输出和覆盖率报告
3. **修复失败**: 修复任何失败的测试
4. **持续集成**: 配置 CI/CD 自动运行测试
5. **监控**: 监控测试性能和覆盖率趋势

## 参考资料

- [pytest 文档](https://docs.pytest.org/)
- [pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [后端实现文档](../UCPPT_STEP_SEPARATION_IMPLEMENTATION_v7.270.md)
- [前端集成指南](../frontend-nextjs/UCPPT_V7270_FRONTEND_INTEGRATION_GUIDE.md)

---

**版本**: v7.270
**更新日期**: 2026-01-25
**维护者**: Claude Code
