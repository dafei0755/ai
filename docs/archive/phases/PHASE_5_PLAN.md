# Phase 5 执行计划 - Core Functionality Tests

**计划时间**: 2025-12-30 23:35
**目标覆盖率**: 11% → 20% (+9百分点)
**预计新增测试**: 80-100个
**预计工作时间**: 4-6小时

---

## 🎯 Phase 5 目标

### 核心目标

1. **提升覆盖率到20%** - 从当前11%提升到20%
2. **添加功能性测试** - 不只是import测试，要测试实际方法调用
3. **减少skip标记** - 将16个skip减少到10个以下
4. **建立功能测试模式** - 为后续Phase建立可复用的测试模式

### 为什么Phase 4只提升了1%?

**Phase 4分析**:
- 新增117个测试，但大部分是import测试
- import测试只执行`import`语句和`assert`，不执行实际代码逻辑
- agents、interaction、security模块代码量~10,000行，import测试覆盖率贡献<1%

**Phase 5改进**:
- 添加方法调用测试（如`agent.invoke()`, `guard.check()`）
- 添加数据流测试（测试输入→处理→输出）
- 添加集成测试（测试模块间交互）

---

## 📋 详细任务列表

### Task 1: Agents功能测试 (30个测试, 预计+3%覆盖率)

#### 1.1 BaseAgent核心功能 (10个测试)

**文件**: `tests/agents/test_base_agent_functionality.py`

**测试内容**:
1. ✅ test_base_agent_initialization - 测试初始化
2. ✅ test_base_agent_with_llm - 测试LLM配置
3. ✅ test_base_agent_invoke_method_exists - 测试invoke方法存在
4. ✅ test_agent_name_property - 测试agent名称属性
5. ✅ test_agent_description_property - 测试agent描述属性
6. ✅ test_agent_config_handling - 测试配置处理
7. ✅ test_agent_error_handling - 测试错误处理
8. ✅ test_agent_state_management - 测试状态管理
9. ✅ test_agent_logging - 测试日志功能
10. ✅ test_agent_metrics - 测试指标收集

**Mock策略**:
```python
@pytest.fixture
def mock_llm():
    mock = Mock()
    mock.invoke.return_value = Mock(content="测试响应")
    return mock

def test_base_agent_with_llm(mock_llm):
    from intelligent_project_analyzer.agents.base import BaseAgent

    # 可能需要创建子类，因为BaseAgent可能是抽象类
    agent = ConcreteAgent(llm_model=mock_llm)
    assert agent.llm_model is not None
```

#### 1.2 RequirementsAnalystAgent功能 (10个测试)

**文件**: `tests/agents/test_requirements_analyst_functionality.py`

**测试内容**:
1. test_requirements_analyst_initialization
2. test_analyze_requirements_basic
3. test_extract_domain_from_input
4. test_identify_project_type
5. test_structured_requirements_output
6. test_requirements_validation
7. test_handle_ambiguous_requirements
8. test_requirements_refinement
9. test_requirements_confidence_score
10. test_requirements_metadata

**重点方法**:
- `analyze()` - 分析需求
- `extract_domain()` - 提取领域
- `identify_project_type()` - 识别项目类型

#### 1.3 其他Agent功能测试 (10个测试)

**文件**: `tests/agents/test_other_agents_functionality.py`

**测试内容**:
1. test_project_director_basic_functionality
2. test_quality_monitor_check_quality
3. test_questionnaire_agent_generate
4. test_conversation_agent_process_message
5. test_followup_agent_generate_questions
6. test_analysis_review_agent_review
7. test_challenge_detection_agent_detect
8. test_feasibility_analyst_assess
9. test_agent_factory_create_agent
10. test_specialized_agent_factory_create

---

### Task 2: Security功能测试 (25个测试, 预计+2%覆盖率)

#### 2.1 ContentSafetyGuard功能 (10个测试)

**文件**: `tests/security/test_content_safety_functionality.py`

**测试内容**:
1. test_content_safety_guard_check_safe_content
2. test_content_safety_guard_block_unsafe_content
3. test_content_safety_guard_keyword_detection
4. test_content_safety_guard_regex_detection
5. test_content_safety_guard_multilayer_detection
6. test_content_safety_guard_severity_levels
7. test_content_safety_guard_whitelist
8. test_content_safety_guard_logging
9. test_content_safety_guard_metrics
10. test_content_safety_guard_performance

**重点方法**:
- `check()` - 检查内容
- `_check_keywords()` - 关键词检查
- `_check_patterns()` - 模式检查

#### 2.2 DomainClassifier功能 (8个测试)

**文件**: 扩展 `tests/security/test_security_basic.py`

**测试内容**:
1. test_domain_classifier_classify_design
2. test_domain_classifier_classify_non_design
3. test_domain_classifier_confidence_score
4. test_domain_classifier_multiple_domains
5. test_domain_classifier_edge_cases
6. test_domain_classifier_keywords_matching
7. test_domain_classifier_context_analysis
8. test_domain_classifier_result_structure

#### 2.3 其他Security功能 (7个测试)

**测试内容**:
1. test_llm_safety_detector_detect
2. test_enhanced_regex_detector_detect
3. test_violation_logger_log
4. test_violation_logger_statistics
5. test_safe_llm_wrapper_wrap
6. test_input_guard_validate
7. test_domain_validator_validate

---

### Task 3: Workflow功能测试 (20个测试, 预计+2%覆盖率)

#### 3.1 MainWorkflow执行测试 (10个测试)

**文件**: 扩展 `tests/workflow/test_main_workflow.py`

**测试内容**:
1. test_workflow_run_with_mock_state
2. test_workflow_invoke_requirements_analyst
3. test_workflow_invoke_project_director
4. test_workflow_state_transitions
5. test_workflow_error_recovery
6. test_workflow_node_execution_order
7. test_workflow_conditional_routing
8. test_workflow_context_building
9. test_workflow_agent_result_aggregation
10. test_workflow_completion_detection

**Mock策略**:
```python
def test_workflow_run_with_mock_state(mock_llm):
    workflow = MainWorkflow(llm_model=mock_llm)

    # 创建最小化状态
    initial_state = {
        "session_id": "test-123",
        "user_input": "设计咖啡馆",
        # ... 其他必需字段
    }

    # Mock节点方法返回值
    with patch.object(workflow, '_requirements_analyst_node') as mock_node:
        mock_node.return_value = {
            "structured_requirements": {"domain": "interior_design"}
        }

        # 运行workflow（可能需要Mock整个graph.invoke）
        # result = workflow.run("测试", "session-123")
```

#### 3.2 Workflow节点功能测试 (10个测试)

**测试内容**:
1. test_requirements_analyst_node_invoke
2. test_project_director_node_invoke
3. test_calibration_questionnaire_node_invoke
4. test_requirements_confirmation_node_invoke
5. test_analysis_review_node_invoke
6. test_progressive_questionnaire_node_invoke
7. test_quality_preflight_node_invoke
8. test_user_question_node_invoke
9. test_final_review_node_invoke
10. test_manual_review_node_invoke

---

### Task 4: Interaction功能测试 (15个测试, 预计+1.5%覆盖率)

#### 4.1 问卷生成功能 (8个测试)

**文件**: 扩展 `tests/interaction/test_interaction_basic.py`

**测试内容**:
1. test_question_adjuster_adjust_questions
2. test_question_adjuster_priority_sorting
3. test_question_adjuster_trim_by_length
4. test_question_adjuster_conflict_handling
5. test_strategy_generator_generate
6. test_strategy_generator_context_aware
7. test_calibration_questionnaire_generate
8. test_progressive_questionnaire_generate

#### 4.2 Review节点功能 (7个测试)

**测试内容**:
1. test_analysis_review_node_review
2. test_manual_review_node_process
3. test_final_review_node_finalize
4. test_quality_preflight_node_check
5. test_user_question_node_ask
6. test_requirements_confirmation_node_confirm
7. test_review_node_base_functionality

---

### Task 5: 修复Skip测试 (减少6个skip)

#### 5.1 调研并修复interaction skip (目标: -4 skip)

**当前skip列表**:
1. test_llm_generator_import (调研实际类名)
2. test_generators_import (调研实际类名)
3. test_parsers_import (调研实际类名)
4. test_context_builder_import (调研实际类名)
5. test_role_selection_review_import (调研模块位置)
6. test_role_task_unified_review_import (调研模块位置)
7. test_task_assignment_review_import (调研模块位置)
8. test_second_batch_strategy_review_import (调研模块位置)
9. test_interaction_agent_base_import (调研实际位置)
10. test_interaction_agent_base_is_class (调研实际位置)

**行动**:
1. 使用Grep搜索实际类名
2. 修正import路径
3. 或确认类确实不存在，保留skip但更新原因

#### 5.2 调研并修复agents skip (目标: -2 skip)

**当前skip列表**:
1. test_tool_callback_import
2. test_search_strategy_import
3. test_requirements_analyst_agent_import
4. test_result_aggregator_agent_import

---

## 🔧 技术策略

### Mock策略升级

**Phase 4**: 只测试import和类型
```python
def test_agent_import(self, env_setup):
    from module import Agent
    assert Agent is not None
```

**Phase 5**: 测试方法调用和数据流
```python
def test_agent_functionality(self, env_setup, mock_llm):
    from module import Agent

    agent = Agent(llm_model=mock_llm)
    result = agent.invoke({"input": "测试"})

    assert result is not None
    assert "output" in result
    mock_llm.invoke.assert_called_once()
```

### 轻量级集成测试

**原则**: 测试真实方法调用，但Mock外部依赖

```python
@pytest.fixture
def agent_with_mock_dependencies():
    with patch('module.external_service') as mock_service:
        mock_service.return_value = "mocked response"
        agent = RealAgent()
        yield agent

def test_agent_real_logic(agent_with_mock_dependencies):
    # 测试真实逻辑，但外部依赖被Mock
    result = agent_with_mock_dependencies.process("input")
    assert result.status == "success"
```

### 数据驱动测试

使用`@pytest.mark.parametrize`测试多种场景:

```python
@pytest.mark.parametrize("input_text,expected_domain", [
    ("设计咖啡馆", "interior_design"),
    ("开发网站", "software_development"),
    ("市场调研", "business_consulting"),
])
def test_domain_extraction(input_text, expected_domain):
    result = extract_domain(input_text)
    assert result == expected_domain
```

---

## 📊 预期覆盖率提升

### 模块级预期

| 模块 | 当前覆盖率 | 目标覆盖率 | 提升 | 测试数 |
|------|-----------|-----------|------|-------|
| agents.base | 0% | 30% | +30% | 10 |
| agents.requirements_analyst | 0% | 40% | +40% | 10 |
| agents.others | 0% | 15% | +15% | 10 |
| security.content_safety_guard | 5% | 50% | +45% | 10 |
| security.domain_classifier | 10% | 60% | +50% | 8 |
| security.others | 0% | 20% | +20% | 7 |
| workflow.main_workflow | 19% | 35% | +16% | 20 |
| interaction.questionnaire | 0% | 30% | +30% | 8 |
| interaction.review_nodes | 0% | 25% | +25% | 7 |

### 总体预期

- **当前总覆盖率**: 11%
- **目标总覆盖率**: 20%
- **预期提升**: +9百分点
- **新增测试**: 90个
- **已有测试**: 137个
- **总测试数**: 227个

---

## ⚠️ 风险与应对

### 风险1: Mock复杂度过高

**问题**: 某些Agent依赖太多外部服务，Mock困难

**应对**:
1. 先测试简单场景，复杂场景标记为skip
2. 创建test-specific的简化Agent子类
3. 使用fixture管理复杂Mock

### 风险2: 覆盖率提升不达预期

**问题**: 可能无法达到20%目标

**应对**:
1. 如果只到18%，也接受（+7%已经很好）
2. 调整Phase 6目标
3. 记录哪些模块难以测试，供参考

### 风险3: 测试执行时间过长

**问题**: 功能测试比import测试慢

**应对**:
1. 使用`@pytest.mark.slow`标记慢测试
2. CI中可以跳过slow测试
3. 优化Mock，减少真实I/O

---

## 📝 执行步骤

### Step 1: 创建Agents功能测试文件 (1小时)

```bash
# 创建文件
touch tests/agents/test_base_agent_functionality.py
touch tests/agents/test_requirements_analyst_functionality.py
touch tests/agents/test_other_agents_functionality.py

# 运行验证
pytest tests/agents/test_base_agent_functionality.py -v
```

### Step 2: 创建Security功能测试 (1小时)

```bash
# 创建文件
touch tests/security/test_content_safety_functionality.py

# 扩展现有文件
# 编辑 tests/security/test_security_basic.py

# 运行验证
pytest tests/security/ -v --cov=intelligent_project_analyzer.security
```

### Step 3: 扩展Workflow测试 (1小时)

```bash
# 编辑现有文件
# 编辑 tests/workflow/test_main_workflow.py

# 运行验证
pytest tests/workflow/test_main_workflow.py -v
```

### Step 4: 扩展Interaction测试 (1小时)

```bash
# 编辑现有文件
# 编辑 tests/interaction/test_interaction_basic.py

# 运行验证
pytest tests/interaction/ -v
```

### Step 5: 修复Skip测试 (30分钟)

```bash
# 调研类名
rg "class.*Generator" intelligent_project_analyzer/interaction/
rg "class.*Review" intelligent_project_analyzer/interaction/

# 修正import路径
# 编辑相关测试文件
```

### Step 6: 运行完整测试套件 (30分钟)

```bash
# 运行所有测试
pytest tests/ -v --cov=intelligent_project_analyzer --cov-report=html --cov-report=term

# 分析覆盖率
# 查看 htmlcov/index.html

# 生成Phase 5完成报告
```

---

## 📈 成功指标

### 必须达成 (Must Have)

- ✅ 覆盖率 ≥ 18% (目标20%)
- ✅ 新增测试 ≥ 70个 (目标90个)
- ✅ 测试通过率 = 100%
- ✅ Skip测试 ≤ 12个 (从16减少)

### 期望达成 (Should Have)

- 🎯 覆盖率 = 20%
- 🎯 新增测试 = 90个
- 🎯 Skip测试 ≤ 10个
- 🎯 至少3个模块覆盖率 > 30%

### 可选达成 (Nice to Have)

- ⭐ 覆盖率 > 20%
- ⭐ 建立性能基准测试
- ⭐ 创建测试文档模板

---

## 📚 参考资料

### 内部文档
- [PHASE_4_COMPLETION_REPORT.md](PHASE_4_COMPLETION_REPORT.md) - Phase 4经验
- [COVERAGE_100_PLAN.md](COVERAGE_100_PLAN.md) - 整体计划
- [tests/conftest.py](tests/conftest.py) - Fixture参考

### 测试模式参考
- `tests/test_content_safety.py` - 功能测试示例
- `tests/services/test_redis_session_manager.py` - async测试示例
- `tests/tools/test_tavily_search.py` - Mock策略示例

### 技术文档
- pytest文档: https://docs.pytest.org/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

---

## 🎯 下一步 (Phase 6预览)

**Phase 6目标**: 覆盖率从20%提升到35%

**重点**:
- API endpoints深度测试
- Services完整测试
- Tools工具调用测试
- 更多集成测试

**预计工作量**: 6-8小时

---

**计划创建时间**: 2025-12-30 23:35
**计划作者**: AI Assistant
**开始执行**: 立即
**预计完成**: 2025-12-31 05:35 (6小时后)

**让我们开始Phase 5，向20%覆盖率迈进！** 🚀
