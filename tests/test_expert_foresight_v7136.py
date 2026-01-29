"""
v7.136 专家视角风险预判单元测试

测试范围：
1. TaskCompletenessAnalyzer.analyze_with_expert_foresight()
2. ProgressiveQuestionnaireNode._predict_expert_roles()
3. ProgressiveQuestionnaireNode._extract_expert_questions()
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import ProgressiveQuestionnaireNode
from intelligent_project_analyzer.services.task_completeness_analyzer import TaskCompletenessAnalyzer


class TestTaskCompletenessAnalyzer:
    """测试 TaskCompletenessAnalyzer 的专家视角分析功能"""

    def test_analyze_basic(self):
        """测试基础分析功能（无专家视角）"""
        analyzer = TaskCompletenessAnalyzer()

        confirmed_tasks = [{"title": "空间规划", "description": "设计空间布局"}, {"title": "风格定位", "description": "确定设计风格"}]
        user_input = "我需要设计一个150平米的现代简约住宅"
        structured_data = {"project_type": "住宅设计", "area": "150平米", "style": "现代简约"}

        result = analyzer.analyze(confirmed_tasks, user_input, structured_data)

        # 验证返回结构
        assert "completeness_score" in result
        assert "covered_dimensions" in result
        assert "missing_dimensions" in result
        assert "critical_gaps" in result
        assert isinstance(result["completeness_score"], float)
        assert 0 <= result["completeness_score"] <= 1

    @patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm")
    def test_analyze_with_expert_foresight_no_roles(self, mock_llm_factory):
        """测试增强版分析（无预测角色）"""
        analyzer = TaskCompletenessAnalyzer()

        confirmed_tasks = [{"title": "空间规划", "description": "设计空间布局"}]
        user_input = "我需要设计一个现代简约住宅"
        structured_data = {"project_type": "住宅设计"}

        # 不提供预测角色
        result = analyzer.analyze_with_expert_foresight(
            confirmed_tasks=confirmed_tasks,
            user_input=user_input,
            structured_data=structured_data,
            predicted_roles=None,
        )

        # 应该只包含基础分析
        assert "completeness_score" in result
        assert "expert_perspective_gaps" not in result
        assert "high_risk_roles" not in result

    @patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm")
    def test_analyze_with_expert_foresight_with_roles(self, mock_llm_factory):
        """测试增强版分析（有预测角色）"""
        # Mock LLM响应
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """{
            "risk_score": 65,
            "missing_info": ["用户画像数据", "场景细节"],
            "suggested_questions": ["目标用户群体是谁？", "主要使用场景有哪些？"],
            "reason": "需要更多用户和场景信息"
        }"""
        mock_llm.invoke.return_value = mock_response
        mock_llm_factory.return_value = mock_llm

        analyzer = TaskCompletenessAnalyzer()

        confirmed_tasks = [{"title": "用户研究", "description": "分析目标用户"}]
        user_input = "我需要设计一个电商平台"
        structured_data = {"project_type": "电商平台"}
        predicted_roles = ["V3_叙事专家", "V4_设计专家"]

        result = analyzer.analyze_with_expert_foresight(
            confirmed_tasks=confirmed_tasks,
            user_input=user_input,
            structured_data=structured_data,
            predicted_roles=predicted_roles,
        )

        # 验证包含专家视角分析
        assert "expert_perspective_gaps" in result
        assert "high_risk_roles" in result
        assert isinstance(result["expert_perspective_gaps"], dict)
        assert isinstance(result["high_risk_roles"], list)

    def test_summarize_structured_data(self):
        """测试结构化数据摘要"""
        analyzer = TaskCompletenessAnalyzer()

        structured_data = {"project_type": "住宅设计", "budget": "30万", "timeline": "3个月", "scale": "150平米"}

        summary = analyzer._summarize_structured_data(structured_data)

        assert "类型:住宅设计" in summary
        assert "预算:30万" in summary
        assert "时间:3个月" in summary
        assert "规模:150平米" in summary

    def test_summarize_structured_data_empty(self):
        """测试空结构化数据摘要"""
        analyzer = TaskCompletenessAnalyzer()

        summary = analyzer._summarize_structured_data({})

        assert summary == "信息不足"

    def test_get_default_expert_gap(self):
        """测试默认专家缺口分析"""
        analyzer = TaskCompletenessAnalyzer()

        default_gap = analyzer._get_default_expert_gap()

        assert default_gap["risk_score"] == 50
        assert "missing_info" in default_gap
        assert isinstance(default_gap["missing_info"], list)
        assert isinstance(default_gap["suggested_questions"], list)
        assert "reason" in default_gap


class TestProgressiveQuestionnaireNode:
    """测试 ProgressiveQuestionnaireNode 的角色预测和问题提取功能"""

    @patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm")
    def test_predict_expert_roles_success(self, mock_llm_factory):
        """测试角色预测成功"""
        # Mock LLM响应
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "V3_叙事专家, V4_设计专家, V5_技术专家"
        mock_llm.invoke.return_value = mock_response
        mock_llm_factory.return_value = mock_llm

        user_input = "我需要设计一个电商网站，包括UI设计和技术实现"
        confirmed_tasks = [{"title": "UI设计", "description": "设计界面"}, {"title": "技术开发", "description": "实现功能"}]
        structured_data = {"project_type": "电商网站"}

        roles = ProgressiveQuestionnaireNode._predict_expert_roles(
            user_input=user_input, confirmed_tasks=confirmed_tasks, structured_data=structured_data
        )

        # 验证返回的角色列表
        assert isinstance(roles, list)
        assert len(roles) > 0
        assert all(r.startswith("V") for r in roles)
        assert len(roles) <= 5  # 最多5个角色

    @patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm")
    def test_predict_expert_roles_failure(self, mock_llm_factory):
        """测试角色预测失败时的降级"""
        # Mock LLM抛出异常
        mock_llm_factory.side_effect = Exception("LLM调用失败")

        user_input = "我需要设计一个网站"
        confirmed_tasks = [{"title": "网站设计"}]
        structured_data = {}

        roles = ProgressiveQuestionnaireNode._predict_expert_roles(
            user_input=user_input, confirmed_tasks=confirmed_tasks, structured_data=structured_data
        )

        # 应该返回默认角色列表
        assert isinstance(roles, list)
        assert len(roles) == 3
        assert "V3_叙事专家" in roles
        assert "V4_设计专家" in roles
        assert "V5_技术专家" in roles

    def test_extract_expert_questions_empty(self):
        """测试提取专家问题（无高风险角色）"""
        expert_gaps = {"V3_叙事专家": {"risk_score": 50, "missing_info": ["用户画像"], "suggested_questions": ["用户是谁？"]}}  # 低风险
        high_risk_roles = []  # 无高风险角色

        questions = ProgressiveQuestionnaireNode._extract_expert_questions(
            expert_gaps=expert_gaps, high_risk_roles=high_risk_roles
        )

        # 无高风险角色，应该返回空列表
        assert isinstance(questions, list)
        assert len(questions) == 0

    def test_extract_expert_questions_with_risks(self):
        """测试提取专家问题（有高风险角色）"""
        expert_gaps = {
            "V3_叙事专家": {
                "risk_score": 85,
                "missing_info": ["用户画像数据", "场景细节"],
                "suggested_questions": ["目标用户群体是谁？", "主要使用场景有哪些？"],
            },
            "V4_设计专家": {"risk_score": 75, "missing_info": ["设计风格偏好"], "suggested_questions": ["您偏好哪种设计风格？"]},
        }
        high_risk_roles = ["V3_叙事专家", "V4_设计专家"]

        questions = ProgressiveQuestionnaireNode._extract_expert_questions(
            expert_gaps=expert_gaps, high_risk_roles=high_risk_roles
        )

        # 验证提取的问题
        assert isinstance(questions, list)
        assert len(questions) == 3  # 2个角色共3个问题

        # 验证问题格式
        for q in questions:
            assert "question" in q
            assert "dimension" in q
            assert q["dimension"] == "专家视角"
            assert "weight" in q
            assert q["weight"] == 8  # 高权重
            assert "priority" in q
            assert q["priority"] == 1  # 高优先级
            assert "is_required" in q
            assert q["is_required"] is False
            assert "expert_role" in q
            assert q["expert_role"] in high_risk_roles


class TestQualityPreflightIntegration:
    """测试质量预检节点的简化逻辑（集成测试）"""

    def test_extreme_risk_detection(self):
        """测试极端风险检测"""
        # 模拟问卷分析结果
        completeness_analysis = {
            "completeness_score": 0.45,
            "expert_perspective_gaps": {
                "V3_叙事专家": {
                    "risk_score": 95,  # 极端风险
                    "missing_info": ["用户画像", "场景细节", "竞品分析"],
                    "suggested_questions": ["用户是谁？", "使用场景？"],
                    "reason": "缺少关键的用户和场景信息",
                },
                "V4_设计专家": {
                    "risk_score": 60,  # 中等风险
                    "missing_info": ["设计风格"],
                    "suggested_questions": ["设计风格偏好？"],
                    "reason": "需要明确设计方向",
                },
            },
            "high_risk_roles": ["V3_叙事专家"],
        }

        # 提取极端风险（score>90）
        extreme_risks = [
            (role_id, gaps)
            for role_id, gaps in completeness_analysis["expert_perspective_gaps"].items()
            if gaps.get("risk_score", 0) > 90
        ]

        assert len(extreme_risks) == 1
        assert extreme_risks[0][0] == "V3_叙事专家"
        assert extreme_risks[0][1]["risk_score"] == 95


# 运行标记
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
