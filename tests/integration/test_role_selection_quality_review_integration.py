"""
集成测试：角色选择质量审核工作流集成

测试范围：
1. 工作流节点集成
2. 状态传递和更新
3. 路由逻辑
4. 用户交互流程
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from langgraph.types import Command

from intelligent_project_analyzer.core.state import AnalysisStage, ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.role_selection_quality_review import (
    RoleSelectionQualityReviewNode,
    role_selection_quality_review_node,
)


class TestWorkflowIntegration:
    """测试工作流集成"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()
        self.base_state = {
            "session_id": "integration_test_001",
            "user_id": "test_user",
            "created_at": "2026-01-26T10:00:00",
            "updated_at": "2026-01-26T10:00:00",
            "user_input": "设计一个现代住宅",
            "current_stage": AnalysisStage.ROLE_SELECTION.value,
            "selected_roles": [
                {"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责整体设计方向"},
                {"role_id": "V3_叙事专家_3-1", "role_name": "叙事与体验专家", "description": "负责用户体验"},
                {"role_id": "V6_总工程师_6-1", "role_name": "总工程师", "description": "负责技术实施"},
            ],
            "structured_requirements": {"project_task": "设计一个现代简约风格的住宅空间，面积120平米"},
            "project_strategy": {"strategy_summary": "采用现代简约设计理念，注重空间功能性和美观性"},
            "conversation_history": [],
            "active_agents": [],
            "completed_agents": [],
            "failed_agents": [],
            "errors": [],
            "retry_count": 0,
        }

    def test_workflow_routing_no_issues(self):
        """测试无问题时的工作流路由"""
        # Mock LLM 返回无问题
        red_response = Mock(content='{"issues": [], "summary": "角色配置合理"}')
        blue_response = Mock(content='{"validations": [], "strengths": [{"aspect": "覆盖全面"}], "summary": "优秀"}')

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.base_state, llm_model=self.mock_llm, config={})

        # 验证路由
        assert isinstance(result, Command)
        assert result.goto == "quality_preflight"

        # 验证状态更新
        assert "role_quality_review_result" in result.update
        assert result.update["role_quality_review_completed"] == True

        review_result = result.update["role_quality_review_result"]
        assert len(review_result["critical_issues"]) == 0

    def test_workflow_routing_with_critical_issues(self):
        """测试有关键问题时的工作流路由"""
        # Mock LLM 返回关键问题
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "缺少设计研究角色",
                    "severity": "critical",
                    "evidence": "需要案例研究和灵感参考",
                    "impact": "设计方案可能缺乏创新性"
                }
            ],
            "summary": "发现1个关键问题"
        }
        """
        )

        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "agree",
                    "reasoning": "确实需要设计研究支持",
                    "improvement_suggestion": "建议添加设计研究员角色"
                }
            ],
            "strengths": [],
            "summary": "同意1个问题"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.base_state, llm_model=self.mock_llm, config={})

        # 验证路由到用户问题
        assert result.goto == "user_question"

        # 验证用户问题数据
        assert "pending_user_question" in result.update
        user_question = result.update["pending_user_question"]
        assert user_question["question_type"] == "role_quality_review"
        assert len(user_question["options"]) == 3

    def test_workflow_routing_with_warnings_only(self):
        """测试仅有警告时的工作流路由"""
        # Mock LLM 返回警告
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "设计总监和叙事专家职责可能有轻微重叠",
                    "severity": "low",
                    "evidence": "两者都涉及用户体验设计",
                    "impact": "可能导致工作重复"
                }
            ],
            "summary": "发现1个低优先级问题"
        }
        """
        )

        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "partially_agree",
                    "reasoning": "有轻微重叠但不影响整体效率",
                    "improvement_suggestion": "明确职责边界即可"
                }
            ],
            "strengths": [
                {
                    "aspect": "角色配置全面",
                    "evidence": "涵盖设计、体验、技术三个维度",
                    "value": "确保方案完整性和可实施性"
                }
            ],
            "summary": "部分同意，发现1个优势"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.base_state, llm_model=self.mock_llm, config={})

        # 验证路由到 quality_preflight（警告不阻塞）
        assert result.goto == "quality_preflight"

        # 验证警告被记录
        review_result = result.update["role_quality_review_result"]
        assert len(review_result["warnings"]) > 0
        assert len(review_result["critical_issues"]) == 0

    def test_state_persistence(self):
        """测试状态持久化"""
        red_response = Mock(content='{"issues": [], "summary": "良好"}')
        blue_response = Mock(content='{"validations": [], "strengths": [], "summary": "良好"}')

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.base_state, llm_model=self.mock_llm, config={})

        # 验证状态字段
        assert "role_quality_review_result" in result.update
        assert "role_quality_review_completed" in result.update
        assert "current_stage" in result.update

        # 验证审核结果结构
        review_result = result.update["role_quality_review_result"]
        assert "critical_issues" in review_result
        assert "warnings" in review_result
        assert "strengths" in review_result
        assert "overall_assessment" in review_result
        assert "red_review" in review_result
        assert "blue_review" in review_result

    def test_user_question_format(self):
        """测试用户问题格式"""
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "缺少场景专家",
                    "severity": "critical",
                    "evidence": "需要场景分析",
                    "impact": "方案可能不符合实际使用场景"
                },
                {
                    "id": "R2",
                    "description": "缺少成本评估",
                    "severity": "high",
                    "evidence": "需要预算控制",
                    "impact": "可能超出预算"
                }
            ],
            "summary": "发现2个问题"
        }
        """
        )

        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "agree",
                    "reasoning": "确实需要场景分析",
                    "improvement_suggestion": "添加场景专家"
                },
                {
                    "red_issue_id": "R2",
                    "stance": "agree",
                    "reasoning": "成本控制很重要",
                    "improvement_suggestion": "添加成本分析师"
                }
            ],
            "strengths": [],
            "summary": "同意2个问题"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.base_state, llm_model=self.mock_llm, config={})

        # 验证用户问题格式
        user_question = result.update["pending_user_question"]

        assert "question_type" in user_question
        assert "question_text" in user_question
        assert "options" in user_question
        assert "context" in user_question

        # 验证选项
        options = user_question["options"]
        assert len(options) == 3
        option_values = [opt["value"] for opt in options]
        assert "adjust_roles" in option_values
        assert "proceed_anyway" in option_values
        assert "provide_context" in option_values

        # 验证上下文
        context = user_question["context"]
        assert "critical_issues" in context
        assert len(context["critical_issues"]) == 2


class TestEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()

    def test_empty_roles_list(self):
        """测试空角色列表"""
        state = {
            "session_id": "edge_test_001",
            "selected_roles": [],
            "structured_requirements": {"project_task": "测试"},
            "project_strategy": {},
        }

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 应该跳过审核
        assert result.goto == "quality_preflight"
        assert result.update["role_quality_review_result"]["skipped"] == True

    def test_missing_requirements(self):
        """测试缺少需求信息"""
        state = {
            "session_id": "edge_test_002",
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监"}],
            "structured_requirements": {},
            "project_strategy": {},
        }

        red_response = Mock(content='{"issues": [], "summary": "无法评估"}')
        blue_response = Mock(content='{"validations": [], "strengths": [], "summary": "无法评估"}')

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 应该能够处理，不抛出异常
        assert result is not None

    def test_llm_error_handling(self):
        """测试LLM错误处理"""
        state = {
            "session_id": "edge_test_003",
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监"}],
            "structured_requirements": {"project_task": "测试"},
            "project_strategy": {},
        }

        # Mock LLM 抛出异常
        self.mock_llm.invoke = Mock(side_effect=Exception("LLM服务异常"))

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 应该优雅降级，跳过审核
        assert result.goto == "quality_preflight"
        assert "skipped" in result.update["role_quality_review_result"]

    def test_malformed_json_response(self):
        """测试格式错误的JSON响应"""
        state = {
            "session_id": "edge_test_004",
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监"}],
            "structured_requirements": {"project_task": "测试"},
            "project_strategy": {},
        }

        # Mock LLM 返回格式错误的JSON
        red_response = Mock(content='{"issues": [{"id": "R1", "description": "测试",}], "summary": "错误"}')  # 多余逗号
        blue_response = Mock(content='{"validations": [], "strengths": []}')  # 缺少summary

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 应该能够处理，使用文本提取回退
        assert result is not None


class TestPerformance:
    """测试性能"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()

    def test_review_time_limit(self):
        """测试审核时间限制"""
        import time

        state = {
            "session_id": "perf_test_001",
            "selected_roles": [{"role_id": f"V{i}_角色_{i}", "role_name": f"角色{i}"} for i in range(1, 6)],  # 5个角色
            "structured_requirements": {"project_task": "复杂项目"},
            "project_strategy": {"strategy_summary": "多维度策略"},
        }

        red_response = Mock(content='{"issues": [], "summary": "良好"}')
        blue_response = Mock(content='{"validations": [], "strengths": [], "summary": "良好"}')

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        start_time = time.time()
        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})
        elapsed_time = time.time() - start_time

        # 验证执行时间（不包括实际LLM调用，应该很快）
        assert elapsed_time < 1.0  # 本地处理应该在1秒内完成
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
