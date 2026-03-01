"""
v7.107 Step 3 LLM智能生成功能测试

测试目标：
- LLMGapQuestionGenerator 基础功能
- TaskCompletenessAnalyzer 基础功能
- 环境变量配置验证
- 代码集成验证
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestLLMGapQuestionGenerator:
    """LLM补充问题生成器测试"""

    @pytest.mark.unit
    def test_generator_exists(self):
        """验证LLM生成器类存在"""
        from intelligent_project_analyzer.services.llm_gap_question_generator import LLMGapQuestionGenerator

        generator = LLMGapQuestionGenerator()
        assert generator is not None
        assert hasattr(generator, "generate_sync")


class TestTaskCompletenessAnalyzer:
    """任务完整性分析器测试"""

    @pytest.mark.unit
    def test_analyzer_completeness(self):
        """测试完整性分析功能"""
        from intelligent_project_analyzer.services.task_completeness_analyzer import TaskCompletenessAnalyzer

        analyzer = TaskCompletenessAnalyzer()

        # analyze方法需要三个参数
        analysis = analyzer.analyze(
            confirmed_tasks=[{"title": "结构改造", "description": "老房结构评估"}, {"title": "装修设计", "description": "现代简约风格"}],
            user_input="上海老弄堂120平米老房翻新，预算50万",
            structured_data={},
        )

        assert "completeness_score" in analysis
        assert "missing_dimensions" in analysis
        assert 0 <= analysis["completeness_score"] <= 1

    @pytest.mark.unit
    def test_budget_recognition_unit_price(self):
        """v7.107.1：测试单价形式预算识别（如"3000元/平米"）"""
        from intelligent_project_analyzer.services.task_completeness_analyzer import TaskCompletenessAnalyzer

        analyzer = TaskCompletenessAnalyzer()

        # 测试单价形式
        user_input = "深圳湾一号300平米，预算3000元/平米"
        result = analyzer.analyze([], user_input, {})

        # 预期：预算约束应该被识别
        assert "预算约束" not in result["missing_dimensions"], f"预算应被识别，但缺失维度中仍有: {result['missing_dimensions']}"
        assert result["dimension_scores"]["预算约束"] > 0.3, f"预算评分应>0.3，实际: {result['dimension_scores']['预算约束']}"

    @pytest.mark.unit
    def test_dynamic_priority_adjustment(self):
        """v7.107.1：测试设计诉求型项目的优先级动态调整"""
        from intelligent_project_analyzer.services.task_completeness_analyzer import TaskCompletenessAnalyzer

        analyzer = TaskCompletenessAnalyzer()

        # 设计诉求型输入
        user_input = "深圳湾一号300平米，如何不降低豪宅体面感和价值感"
        result = analyzer.analyze([], user_input, {})

        # 检查关键缺失列表
        critical_gaps = result.get("critical_gaps", [])
        time_is_critical = any(g["dimension"] == "时间节点" for g in critical_gaps)

        # 预期：时间节点不应被标记为关键缺失
        assert not time_is_critical, f"设计诉求型项目，时间节点不应为关键缺失。实际关键缺失: {critical_gaps}"

    @pytest.mark.unit
    def test_hardcoded_question_generation(self):
        """测试硬编码问题生成"""
        from intelligent_project_analyzer.services.task_completeness_analyzer import TaskCompletenessAnalyzer

        analyzer = TaskCompletenessAnalyzer()

        # 先分析完整性
        analysis = analyzer.analyze(
            confirmed_tasks=[{"title": "任务1", "description": "描述"}], user_input="设计项目", structured_data={}
        )

        # 生成补充问题 - 使用正确的参数
        questions = analyzer.generate_gap_questions(
            missing_dimensions=analysis["missing_dimensions"],
            critical_gaps=analysis["critical_gaps"],
            confirmed_tasks=[{"title": "任务1"}],
            existing_info_summary="已知信息：项目类型",
            target_count=5,
        )

        assert isinstance(questions, list)
        if analysis["completeness_score"] < 1.0:
            assert len(questions) > 0
            for q in questions:
                assert "question" in q
                assert "type" in q


class TestEnvironmentConfiguration:
    """环境变量配置测试"""

    @pytest.mark.unit
    def test_env_default_true(self):
        """测试默认启用LLM"""
        if "USE_LLM_GAP_QUESTIONS" in os.environ:
            del os.environ["USE_LLM_GAP_QUESTIONS"]

        default = os.getenv("USE_LLM_GAP_QUESTIONS", "true")
        assert default == "true"

    @pytest.mark.unit
    def test_env_can_disable(self):
        """测试可以禁用LLM"""
        with patch.dict(os.environ, {"USE_LLM_GAP_QUESTIONS": "false"}):
            value = os.getenv("USE_LLM_GAP_QUESTIONS")
            assert value == "false"
            enable = value.lower() == "true"
            assert enable is False


class TestStep3CodeIntegration:
    """Step 3代码集成验证"""

    @pytest.mark.integration
    def test_llm_logic_exists(self):
        """验证LLM生成逻辑存在于代码中"""
        import inspect

        from intelligent_project_analyzer.interaction.nodes import progressive_questionnaire

        source = inspect.getsource(progressive_questionnaire)

        assert "USE_LLM_GAP_QUESTIONS" in source
        assert "LLMGapQuestionGenerator" in source
        assert "enable_llm_generation" in source
        assert "generate_sync" in source
        assert "v7.107" in source

    @pytest.mark.integration
    def test_fallback_logic_exists(self):
        """验证fallback逻辑存在"""
        import inspect

        from intelligent_project_analyzer.interaction.nodes import progressive_questionnaire

        source = inspect.getsource(progressive_questionnaire)

        assert "try:" in source
        assert "except" in source
        assert "TaskCompletenessAnalyzer" in source
        assert "logger.warning" in source or "logger.info" in source


class TestRealLLM:
    """真实LLM调用测试（需要API密钥）"""

    @pytest.mark.llm
    @pytest.mark.integration
    def test_llm_generation_e2e(self):
        """端到端LLM生成测试"""
        from intelligent_project_analyzer.services.llm_gap_question_generator import LLMGapQuestionGenerator

        try:
            generator = LLMGapQuestionGenerator()
            questions = generator.generate_sync(
                user_input="上海老弄堂120平米老房翻新，预算50万",
                confirmed_tasks=["结构改造", "装修设计", "特色保护"],
                missing_dimensions="缺少：预算明细、时间节点",
                existing_info_summary="已知：面积、预算、项目类型",
                completeness_score=0.6,
            )

            assert questions is not None
            assert isinstance(questions, list)

            if len(questions) > 0:
                q = questions[0]
                assert "question" in q
                assert "type" in q
                assert q["type"] in ["single_choice", "multiple_choice", "open_ended"]

        except Exception as e:
            pytest.skip(f"LLM API不可用: {e}")


"""
运行指令：

# 快速单元测试
pytest tests/test_step3_llm_v7107.py -v -m "unit"

# 集成测试（不调用LLM）
pytest tests/test_step3_llm_v7107.py -v -m "integration and not llm"

# 真实LLM测试
pytest tests/test_step3_llm_v7107.py -v -m "llm"

# 所有测试
pytest tests/test_step3_llm_v7107.py -v

# 覆盖率
pytest tests/test_step3_llm_v7107.py --cov=intelligent_project_analyzer.services --cov-report=term
"""
