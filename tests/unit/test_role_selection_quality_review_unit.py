"""
单元测试：角色选择质量审核功能

测试范围：
1. RoleSelectionQualityReviewNode 基本功能
2. 红队审核逻辑
3. 蓝队验证逻辑
4. 问题分类和路由
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.role_selection_quality_review import (
    RoleSelectionQualityReviewNode,
    role_selection_quality_review_node,
)
from intelligent_project_analyzer.review.multi_perspective_review import MultiPerspectiveReviewCoordinator
from intelligent_project_analyzer.review.review_agents import BlueTeamReviewer, RedTeamReviewer


class TestRoleSelectionQualityReviewNode:
    """测试角色选择质量审核节点"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()
        self.test_state = {
            "session_id": "test_session_001",
            "selected_roles": [
                {"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责整体设计方向和策略制定"},
                {"role_id": "V3_叙事专家_3-1", "role_name": "叙事与体验专家", "description": "负责用户体验和故事叙事"},
            ],
            "structured_requirements": {"project_task": "设计一个现代简约风格的住宅空间"},
            "project_strategy": {"strategy_summary": "采用现代简约设计理念，注重空间功能性"},
        }

    def test_node_initialization(self):
        """测试节点初始化"""
        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})
        assert RoleSelectionQualityReviewNode._review_coordinator is not None
        assert RoleSelectionQualityReviewNode._llm_model == self.mock_llm

    def test_execute_with_no_issues(self):
        """测试无问题场景"""
        # Mock LLM 返回无问题
        self.mock_llm.invoke = Mock(return_value=Mock(content='{"issues": [], "summary": "角色配置合理"}'))

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.test_state, llm_model=self.mock_llm, config={})

        # 验证结果
        assert result is not None
        assert hasattr(result, "update")
        assert hasattr(result, "goto")

        # 应该路由到 quality_preflight（无问题）
        assert result.goto == "quality_preflight"

    def test_execute_with_critical_issues(self):
        """测试发现关键问题场景"""
        # Mock 红队发现问题
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "缺少技术可行性评估角色",
                    "severity": "critical",
                    "evidence": "住宅设计需要技术评估",
                    "impact": "可能导致方案无法实施"
                }
            ],
            "summary": "发现1个关键问题"
        }
        """
        )

        # Mock 蓝队同意问题
        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "agree",
                    "reasoning": "确实缺少技术评估",
                    "improvement_suggestion": "建议添加技术架构师"
                }
            ],
            "strengths": [],
            "summary": "同意1个问题"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.test_state, llm_model=self.mock_llm, config={})

        # 应该路由到 user_question（有关键问题）
        assert result.goto == "user_question"
        assert "pending_user_question" in result.update

    def test_execute_with_warnings_only(self):
        """测试仅有警告场景"""
        # Mock 红队发现低优先级问题
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "角色职责可能有轻微重叠",
                    "severity": "low",
                    "evidence": "设计总监和叙事专家部分职责重叠",
                    "impact": "可能导致工作重复"
                }
            ],
            "summary": "发现1个低优先级问题"
        }
        """
        )

        # Mock 蓝队部分同意
        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "partially_agree",
                    "reasoning": "有轻微重叠但不影响整体",
                    "improvement_suggestion": "明确职责边界即可"
                }
            ],
            "strengths": [
                {
                    "aspect": "角色覆盖全面",
                    "evidence": "涵盖设计和体验两个维度",
                    "value": "确保方案完整性"
                }
            ],
            "summary": "部分同意，发现1个优势"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=self.test_state, llm_model=self.mock_llm, config={})

        # 应该路由到 quality_preflight（仅警告不阻塞）
        assert result.goto == "quality_preflight"

    def test_execute_skip_when_no_roles(self):
        """测试无角色时跳过审核"""
        state_no_roles = {
            "session_id": "test_session_002",
            "selected_roles": [],
            "structured_requirements": {"project_task": "测试项目"},
        }

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=state_no_roles, llm_model=self.mock_llm, config={})

        # 应该跳过审核
        assert result.goto == "quality_preflight"
        assert result.update.get("role_quality_review_result", {}).get("skipped") == True

    def test_prepare_user_question(self):
        """测试用户问题准备"""
        critical_issues = [{"issue": "缺少技术评估角色", "impact": "方案可能无法实施", "suggestion": "添加技术架构师"}]
        warnings = [{"issue": "角色职责有重叠", "details": "设计总监和叙事专家职责部分重叠"}]
        strengths = []

        question_data = RoleSelectionQualityReviewNode._prepare_user_question(critical_issues, warnings, strengths)

        assert "question_type" in question_data
        assert question_data["question_type"] == "role_quality_review"
        assert "options" in question_data
        assert len(question_data["options"]) == 3
        assert any(opt["value"] == "adjust_roles" for opt in question_data["options"])


class TestRedTeamReviewer:
    """测试红队审核器"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()
        self.reviewer = RedTeamReviewer(self.mock_llm)

    def test_review_role_selection_basic(self):
        """测试基本角色选择审核"""
        selected_roles = [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责设计"}]
        requirements = {"project_task": "设计住宅"}
        strategy = {"strategy_summary": "现代简约"}

        # Mock LLM 响应
        self.mock_llm.invoke = Mock(
            return_value=Mock(
                content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "缺少技术角色",
                    "severity": "high",
                    "evidence": "无技术评估",
                    "impact": "方案可能不可行"
                }
            ],
            "summary": "发现1个问题"
        }
        """
            )
        )

        result = self.reviewer.review_role_selection(selected_roles, requirements, strategy)

        assert "issues" in result
        assert len(result["issues"]) > 0
        assert result["issues"][0]["id"] == "R1"

    def test_extract_role_selection_issues_json(self):
        """测试从JSON提取问题"""
        content = """
        ```json
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "测试问题",
                    "severity": "critical",
                    "evidence": "测试证据",
                    "impact": "测试影响"
                }
            ],
            "summary": "测试摘要"
        }
        ```
        """

        issues = self.reviewer._extract_role_selection_issues(content)

        assert len(issues) == 1
        assert issues[0]["id"] == "R1"
        assert issues[0]["severity"] == "critical"

    def test_extract_role_selection_issues_fallback(self):
        """测试文本提取回退"""
        content = "发现问题：缺少技术角色\n存在风险：方案可能不可行"

        issues = self.reviewer._extract_role_selection_issues(content)

        assert len(issues) > 0
        assert any("问题" in issue["description"] or "风险" in issue["description"] for issue in issues)


class TestBlueTeamReviewer:
    """测试蓝队审核器"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()
        self.reviewer = BlueTeamReviewer(self.mock_llm)

    def test_review_role_selection_with_red_review(self):
        """测试基于红队结果的验证"""
        selected_roles = [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监"}]
        requirements = {"project_task": "设计住宅"}
        strategy = {"strategy_summary": "现代简约"}
        red_review = {"issues": [{"id": "R1", "description": "缺少技术角色", "severity": "high"}]}

        # Mock LLM 响应
        self.mock_llm.invoke = Mock(
            return_value=Mock(
                content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "agree",
                    "reasoning": "确实缺少",
                    "improvement_suggestion": "添加技术角色"
                }
            ],
            "strengths": [],
            "summary": "同意1个问题"
        }
        """
            )
        )

        result = self.reviewer.review_role_selection(selected_roles, requirements, strategy, red_review)

        assert "validations" in result
        assert len(result["validations"]) > 0
        assert result["validations"][0]["stance"] == "agree"

    def test_extract_role_selection_validations_json(self):
        """测试从JSON提取验证结果"""
        content = """
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "disagree",
                    "reasoning": "误判",
                    "improvement_suggestion": ""
                }
            ],
            "strengths": [
                {
                    "aspect": "覆盖全面",
                    "evidence": "涵盖多维度",
                    "value": "确保完整性"
                }
            ],
            "summary": "不同意1个，发现1个优势"
        }
        """

        red_review = {"issues": [{"id": "R1"}]}
        validations, strengths = self.reviewer._extract_role_selection_validations(content, red_review)

        assert len(validations) == 1
        assert validations[0]["stance"] == "disagree"
        assert len(strengths) == 1


class TestMultiPerspectiveReviewCoordinator:
    """测试多视角审核协调器"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()
        self.coordinator = MultiPerspectiveReviewCoordinator(self.mock_llm, {})

    def test_conduct_role_selection_review(self):
        """测试角色选择审核协调"""
        selected_roles = [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监"}]
        requirements = {"project_task": "设计住宅"}
        strategy = {"strategy_summary": "现代简约"}

        # Mock 红队和蓝队响应
        red_response = Mock(
            content='{"issues": [{"id": "R1", "description": "测试", "severity": "high"}], "summary": "1个问题"}'
        )
        blue_response = Mock(
            content='{"validations": [{"red_issue_id": "R1", "stance": "agree"}], "strengths": [], "summary": "同意"}'
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        result = self.coordinator.conduct_role_selection_review(selected_roles, requirements, strategy)

        assert "critical_issues" in result
        assert "warnings" in result
        assert "strengths" in result
        assert "overall_assessment" in result

    def test_generate_role_review_assessment(self):
        """测试总体评估生成"""
        # 无问题
        assessment = self.coordinator._generate_role_review_assessment([], [], [])
        assert "优秀" in assessment

        # 有关键问题
        critical_issues = [{"issue": "测试问题"}]
        assessment = self.coordinator._generate_role_review_assessment(critical_issues, [], [])
        assert "关键问题" in assessment

        # 有警告
        warnings = [{"issue": f"警告{i}"} for i in range(4)]
        assessment = self.coordinator._generate_role_review_assessment([], warnings, [])
        assert "警告" in assessment or "优化" in assessment


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
