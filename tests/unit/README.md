# 单元测试指南

本目录包含Intelligent Project Analyzer的单元测试套件。

## 📁 目录结构

```
tests/
├── fixtures/           # 测试fixtures和工具
│   ├── mocks.py       # 统一Mock对象（LLM、Redis、Workflow等）
│   ├── test_data.py   # 测试数据样本
│   └── data_factory.py
├── unit/              # 单元测试（不依赖外部服务）
│   ├── test_workflow_main.py      # 主工作流节点测试
│   ├── test_core_state.py         # 状态管理测试
│   ├── test_api_endpoints.py      # API端点测试
│   └── test_utils.py              # 工具函数测试
├── integration/       # 集成测试（需要真实组件）
├── regression/        # 回归测试（防止已知bug复现）
└── conftest.py        # Pytest全局配置
```

## 🚀 快速开始

### 运行所有单元测试

```bash
# 仅运行单元测试（快速）
pytest tests/unit/ -v

# 运行所有测试
pytest -v

# 带覆盖率报告
pytest tests/unit/ --cov=intelligent_project_analyzer --cov-report=html
```

### 按标记运行测试

```bash
# 仅运行工作流测试
pytest -m workflow -v

# 仅运行API测试
pytest -m api -v

# 排除慢速测试
pytest -m "not slow" -v

# 运行P0核心测试
pytest -m "unit and (workflow or api)" -v
```

### 按模块运行测试

```bash
# 测试workflow模块
pytest tests/unit/test_workflow_main.py -v

# 测试单个测试函数
pytest tests/unit/test_core_state.py::test_merge_agent_results_both_dicts -v
```

## 🏷️ 测试标记(Markers)

| 标记 | 说明 |
|-----|------|
| `unit` | 单元测试（不依赖外部服务） |
| `integration` | 集成测试（需要真实Redis/LLM） |
| `workflow` | 工作流模块测试 |
| `api` | API端点测试 |
| `agents` | Agent模块测试 |
| `security` | 安全模块测试 |
| `slow` | 慢速测试（>5秒） |
| `llm` | 需要真实LLM调用（需要API key） |

## 📊 覆盖率目标

- **整体覆盖率**: 80%+
- **核心模块（P0）**: 90%+
  - workflow/main_workflow.py
  - core/state.py
  - api/server.py (关键端点)
  - services/redis_session_manager.py

## 🧪 编写测试指南

### 使用统一Mock对象

```python
from tests.fixtures.mocks import (
    create_mock_llm,
    create_mock_redis,
    create_mock_workflow_components
)

def test_example():
    # 创建Mock LLM
    mock_llm = create_mock_llm(responses=["测试响应"])

    # 创建Mock Redis
    mock_redis = create_mock_redis()
    await mock_redis.set("key", "value")

    # 创建Mock工作流组件
    components = create_mock_workflow_components()
    state = components["state"]
    checkpointer = components["checkpointer"]
```

### 使用测试数据

```python
from tests.fixtures.test_data import (
    SAMPLE_USER_INPUTS,
    SAMPLE_EXPERT_POOL,
    SAMPLE_LLM_RESPONSES
)

def test_with_sample_data():
    user_input = SAMPLE_USER_INPUTS["detailed"]
    experts = SAMPLE_EXPERT_POOL
    # 使用样本数据进行测试
```

### 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Mock外部依赖

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.unit
def test_with_mock_llm():
    with patch('module.LLMClient') as mock_llm:
        mock_llm.return_value.ainvoke.return_value = "Mock响应"
        result = function_under_test()
        assert "Mock响应" in result
```

## 🔍 调试测试

```bash
# 显示print输出
pytest -s tests/unit/test_workflow_main.py

# 进入pdb调试器
pytest --pdb tests/unit/test_workflow_main.py

# 显示详细日志
pytest --log-cli-level=DEBUG tests/unit/

# 只运行失败的测试
pytest --lf
```

## ⚡ 性能优化

### 并行执行测试

```bash
# 安装pytest-xdist
pip install pytest-xdist

# 使用多核并行执行
pytest -n auto tests/unit/
```

### 跳过慢速测试

```bash
# 跳过标记为slow的测试
pytest -m "not slow" tests/unit/
```

## 📝 测试覆盖已实现的模块

### ✅ 已覆盖（P0核心）

- [x] workflow/main_workflow.py - 16个节点函数测试
- [x] core/state.py - 状态管理和reducer函数测试
- [x] api/server.py - 关键端点测试（/analyze、/health）
- [x] utils/ - 工具函数测试（json_parser、llm_retry等）

### 🚧 待补充（P1）

- [ ] services/image_generator.py - 图片生成服务
- [ ] services/file_processor.py - 文件处理
- [ ] services/llm_factory.py - LLM工厂
- [ ] security/unified_input_validator_node.py - 安全验证

### 📋 待实现（P2-P3）

- [ ] agents/requirements_analyst.py - 需求分析师
- [ ] agents/project_director.py - 项目总监
- [ ] interaction/questionnaire/ - 问卷系统
- [ ] tools/ - 搜索工具

## 🐛 已知问题

1. **WebSocket测试**: 需要特殊的测试客户端配置，当前部分测试被跳过
2. **LangGraph集成**: 某些LangGraph特性（如Command对象）的Mock需要进一步完善
3. **异步事件循环**: pytest-asyncio配置为`asyncio_mode=auto`，确保所有异步测试自动标记

## 📚 参考资源

- [Pytest文档](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)

## 🤝 贡献测试

### 添加新测试的步骤

1. **选择合适的测试类型**：
   - 单元测试 → `tests/unit/`
   - 集成测试 → `tests/integration/`
   - 回归测试 → `tests/regression/`

2. **使用统一Mock对象**：
   - 从`tests/fixtures/mocks.py`导入
   - 避免在测试中重复创建Mock

3. **添加适当的标记**：
   ```python
   @pytest.mark.unit
   @pytest.mark.workflow
   def test_new_feature():
       pass
   ```

4. **编写清晰的测试文档**：
   ```python
   def test_feature():
       """测试功能X - 具体场景描述"""
       # Arrange: 准备测试数据
       # Act: 执行被测试功能
       # Assert: 验证结果
   ```

5. **运行测试并检查覆盖率**：
   ```bash
   pytest tests/unit/test_new_module.py --cov=intelligent_project_analyzer.new_module
   ```

## 📞 需要帮助？

- 查看 `tests/fixtures/mocks.py` 了解可用的Mock对象
- 查看 `tests/fixtures/test_data.py` 了解可用的测试数据
- 参考现有测试文件作为示例
- 提交Issue反馈测试问题

---

**最后更新**: 2026-01-06
**测试覆盖率**: 单元测试基础框架已建立，持续补充中
