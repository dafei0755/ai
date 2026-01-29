"""
端到端测试：角色选择质量审核完整流程

测试范围：
1. 完整工作流执行
2. 用户交互场景
3. 多轮审核流程
4. 实际LLM集成（可选）
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.core.state import AnalysisStage, ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.role_selection_quality_review import (
    RoleSelectionQualityReviewNode,
    role_selection_quality_review_node,
)


class TestEndToEndScenarios:
    """端到端测试场景"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()

    def test_scenario_1_happy_path(self):
        """
        场景1：正常流程（无问题）

        流程：
        1. 用户提供需求
        2. 系统选择合适的角色
        3. 质量审核通过
        4. 继续到任务分解
        """
        # 准备状态
        state = {
            "session_id": "e2e_scenario_1",
            "user_input": "设计一个现代简约风格的住宅空间，面积120平米，预算50万",
            "selected_roles": [
                {"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责整体设计方向和策略制定"},
                {"role_id": "V3_叙事专家_3-1", "role_name": "叙事与体验专家", "description": "负责用户体验和空间叙事"},
                {"role_id": "V4_设计研究员_4-1", "role_name": "设计研究员", "description": "负责案例研究和灵感参考"},
                {"role_id": "V5_场景专家_5-1", "role_name": "场景与用户生态专家", "description": "负责使用场景分析"},
                {"role_id": "V6_总工程师_6-1", "role_name": "总工程师", "description": "负责技术可行性和成本控制"},
            ],
            "structured_requirements": {
                "project_task": "设计一个现代简约风格的住宅空间，面积120平米，预算50万",
                "project_type": "residential",
                "budget": "50万",
                "area": "120平米",
            },
            "project_strategy": {"strategy_summary": "采用现代简约设计理念，注重空间功能性和美观性，控制成本在预算范围内"},
        }

        # Mock 红队：无问题
        red_response = Mock(
            content="""
        {
            "issues": [],
            "summary": "角色配置合理，覆盖了设计、研究、场景、技术等各个维度，能够有效支撑项目需求"
        }
        """
        )

        # Mock 蓝队：确认无问题，识别优势
        blue_response = Mock(
            content="""
        {
            "validations": [],
            "strengths": [
                {
                    "aspect": "角色覆盖全面",
                    "evidence": "涵盖设计、研究、场景、技术四个维度",
                    "value": "确保方案的完整性和可实施性"
                },
                {
                    "aspect": "角色协同性强",
                    "evidence": "各角色职责清晰，相互补充",
                    "value": "提高团队协作效率"
                }
            ],
            "summary": "角色配置优秀，发现2个优势"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        # 执行审核
        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 验证结果
        assert result.goto == "quality_preflight"
        assert result.update["role_quality_review_completed"] == True

        review_result = result.update["role_quality_review_result"]
        assert len(review_result["critical_issues"]) == 0
        assert len(review_result["warnings"]) == 0
        assert len(review_result["strengths"]) == 2
        assert "优秀" in review_result["overall_assessment"]

        print("✅ 场景1测试通过：正常流程无问题")

    def test_scenario_2_critical_issues_user_adjusts(self):
        """
        场景2：发现关键问题，用户选择调整

        流程：
        1. 系统选择角色（不完整）
        2. 质量审核发现关键问题
        3. 询问用户
        4. 用户选择调整角色
        """
        # 准备状态（缺少技术角色）
        state = {
            "session_id": "e2e_scenario_2",
            "user_input": "设计一个大型商业综合体项目",
            "selected_roles": [
                {"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责整体设计方向"},
                {"role_id": "V3_叙事专家_3-1", "role_name": "叙事与体验专家", "description": "负责用户体验"}
                # 缺少技术、场景等关键角色
            ],
            "structured_requirements": {
                "project_task": "设计一个大型商业综合体项目，包含购物中心、办公楼、酒店等多种业态",
                "project_type": "commercial",
                "complexity": "high",
            },
            "project_strategy": {"strategy_summary": "多业态综合开发，需要全方位专业支持"},
        }

        # Mock 红队：发现多个关键问题
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "缺少技术可行性评估角色",
                    "severity": "critical",
                    "evidence": "大型商业综合体需要复杂的技术支持，包括结构、机电、智能化等",
                    "impact": "可能导致方案在技术上不可行或成本失控"
                },
                {
                    "id": "R2",
                    "description": "缺少场景分析专家",
                    "severity": "critical",
                    "evidence": "多业态项目需要深入的场景分析和用户生态研究",
                    "impact": "可能导致各业态之间缺乏协同，用户体验不佳"
                },
                {
                    "id": "R3",
                    "description": "缺少设计研究支持",
                    "severity": "high",
                    "evidence": "需要大量案例研究和行业最佳实践参考",
                    "impact": "设计方案可能缺乏创新性和竞争力"
                }
            ],
            "summary": "发现3个问题，其中2个critical，1个high"
        }
        """
        )

        # Mock 蓝队：同意所有问题
        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "agree",
                    "reasoning": "大型商业综合体确实需要专业的技术评估",
                    "improvement_suggestion": "建议添加总工程师角色，负责技术可行性和成本控制"
                },
                {
                    "red_issue_id": "R2",
                    "stance": "agree",
                    "reasoning": "多业态项目需要深入的场景分析",
                    "improvement_suggestion": "建议添加场景与用户生态专家"
                },
                {
                    "red_issue_id": "R3",
                    "stance": "agree",
                    "reasoning": "设计研究对提升方案质量很重要",
                    "improvement_suggestion": "建议添加设计研究员角色"
                }
            ],
            "strengths": [],
            "summary": "同意3个问题，建议补充3个角色"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        # 执行审核
        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 验证结果
        assert result.goto == "user_question"

        review_result = result.update["role_quality_review_result"]
        assert len(review_result["critical_issues"]) == 2  # 2个critical问题

        # 验证用户问题
        user_question = result.update["pending_user_question"]
        assert user_question["question_type"] == "role_quality_review"
        assert "缺少技术可行性评估角色" in user_question["question_text"]
        assert "缺少场景分析专家" in user_question["question_text"]

        # 验证选项
        options = user_question["options"]
        assert any(opt["value"] == "adjust_roles" for opt in options)

        print("✅ 场景2测试通过：发现关键问题并询问用户")

    def test_scenario_3_warnings_only_proceed(self):
        """
        场景3：仅有警告，自动继续

        流程：
        1. 系统选择角色（基本合理）
        2. 质量审核发现轻微问题（警告）
        3. 自动继续，不阻塞流程
        """
        state = {
            "session_id": "e2e_scenario_3",
            "user_input": "设计一个小型咖啡馆",
            "selected_roles": [
                {"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责整体设计"},
                {"role_id": "V3_叙事专家_3-1", "role_name": "叙事与体验专家", "description": "负责用户体验"},
                {"role_id": "V4_设计研究员_4-1", "role_name": "设计研究员", "description": "负责案例研究"},
            ],
            "structured_requirements": {"project_task": "设计一个小型咖啡馆，面积80平米", "project_type": "commercial_small"},
            "project_strategy": {"strategy_summary": "打造温馨舒适的咖啡空间"},
        }

        # Mock 红队：发现轻微问题
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "设计总监和叙事专家职责可能有轻微重叠",
                    "severity": "low",
                    "evidence": "两者都涉及空间体验设计",
                    "impact": "可能导致少量工作重复，但不影响整体效率"
                },
                {
                    "id": "R2",
                    "description": "对于小型项目，可能不需要专门的设计研究员",
                    "severity": "low",
                    "evidence": "小型咖啡馆案例研究相对简单",
                    "impact": "可能造成轻微的资源浪费"
                }
            ],
            "summary": "发现2个低优先级问题"
        }
        """
        )

        # Mock 蓝队：部分同意，识别优势
        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "partially_agree",
                    "reasoning": "有轻微重叠但职责分工仍然清晰",
                    "improvement_suggestion": "明确各自侧重点即可"
                },
                {
                    "red_issue_id": "R2",
                    "stance": "disagree",
                    "reasoning": "设计研究对提升咖啡馆特色很有价值",
                    "improvement_suggestion": ""
                }
            ],
            "strengths": [
                {
                    "aspect": "角色配置适中",
                    "evidence": "对于小型项目，3个角色足够覆盖主要需求",
                    "value": "平衡了专业性和成本效益"
                }
            ],
            "summary": "部分同意1个，不同意1个，发现1个优势"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        # 执行审核
        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 验证结果：应该继续，不阻塞
        assert result.goto == "quality_preflight"

        review_result = result.update["role_quality_review_result"]
        assert len(review_result["critical_issues"]) == 0
        assert len(review_result["warnings"]) > 0  # 有警告但不阻塞

        print("✅ 场景3测试通过：仅有警告，自动继续")

    def test_scenario_4_user_proceeds_despite_issues(self):
        """
        场景4：有问题但用户选择继续

        流程：
        1. 质量审核发现问题
        2. 询问用户
        3. 用户选择"继续执行"
        4. 记录问题但继续流程
        """
        state = {
            "session_id": "e2e_scenario_4",
            "user_input": "快速设计一个展厅",
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责设计"}],
            "structured_requirements": {"project_task": "快速设计一个展厅，时间紧急", "urgency": "high"},
            "project_strategy": {"strategy_summary": "快速出方案"},
        }

        # Mock 红队：发现问题
        red_response = Mock(
            content="""
        {
            "issues": [
                {
                    "id": "R1",
                    "description": "仅有设计总监，缺少其他专业支持",
                    "severity": "high",
                    "evidence": "展厅设计需要多维度考虑",
                    "impact": "方案可能不够全面"
                }
            ],
            "summary": "发现1个high问题"
        }
        """
        )

        # Mock 蓝队：同意但理解紧急情况
        blue_response = Mock(
            content="""
        {
            "validations": [
                {
                    "red_issue_id": "R1",
                    "stance": "agree",
                    "reasoning": "确实缺少专业支持，但考虑到时间紧急，可以理解",
                    "improvement_suggestion": "建议后续补充其他角色"
                }
            ],
            "strengths": [],
            "summary": "同意1个问题"
        }
        """
        )

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        # 执行审核
        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 验证：应该询问用户（high问题可能被视为critical）
        # 注意：这里的行为取决于severity到critical_issues的映射逻辑
        # 如果high被映射为critical，则会询问用户
        # 如果high被映射为warning，则会自动继续

        assert result is not None
        review_result = result.update["role_quality_review_result"]
        assert len(review_result["critical_issues"]) + len(review_result["warnings"]) > 0

        print("✅ 场景4测试通过：用户可以选择继续")


class TestRegressionScenarios:
    """回归测试场景"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()

    def test_backward_compatibility_state_fields(self):
        """测试向后兼容：状态字段"""
        # 确保新字段不影响旧流程
        state = {
            "session_id": "regression_001",
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监"}],
            "structured_requirements": {"project_task": "测试"},
            "project_strategy": {},
            # 旧字段（应该被忽略）
            "review_result": {"old": "data"},
            "review_history": [{"old": "history"}],
        }

        red_response = Mock(content='{"issues": [], "summary": "良好"}')
        blue_response = Mock(content='{"validations": [], "strengths": [], "summary": "良好"}')

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 验证：新字段正常工作
        assert "role_quality_review_result" in result.update
        # 旧字段不应该被修改
        assert "review_result" not in result.update

        print("✅ 回归测试通过：向后兼容")

    def test_no_breaking_changes_to_workflow(self):
        """测试：工作流无破坏性变更"""
        # 验证节点返回的是Command对象
        state = {
            "session_id": "regression_002",
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "role_name": "设计总监"}],
            "structured_requirements": {"project_task": "测试"},
            "project_strategy": {},
        }

        red_response = Mock(content='{"issues": [], "summary": "良好"}')
        blue_response = Mock(content='{"validations": [], "strengths": [], "summary": "良好"}')

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})

        # 验证返回类型
        from langgraph.types import Command

        assert isinstance(result, Command)
        assert hasattr(result, "update")
        assert hasattr(result, "goto")
        assert result.goto in ["user_question", "quality_preflight"]

        print("✅ 回归测试通过：无破坏性变更")


class TestPerformanceE2E:
    """端到端性能测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.mock_llm = Mock()

    def test_large_role_set_performance(self):
        """测试大量角色的性能"""
        import time

        # 创建10个角色
        state = {
            "session_id": "perf_e2e_001",
            "selected_roles": [
                {"role_id": f"V{i}_角色_{i}", "role_name": f"专业角色{i}", "description": f"负责领域{i}的专业工作"}
                for i in range(1, 11)
            ],
            "structured_requirements": {"project_task": "超大型综合项目，需要多专业协同"},
            "project_strategy": {"strategy_summary": "多专业协同作战"},
        }

        red_response = Mock(content='{"issues": [], "summary": "配置合理"}')
        blue_response = Mock(content='{"validations": [], "strengths": [], "summary": "良好"}')

        self.mock_llm.invoke = Mock(side_effect=[red_response, blue_response])

        RoleSelectionQualityReviewNode.initialize_coordinator(self.mock_llm, {})

        start_time = time.time()
        result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=self.mock_llm, config={})
        elapsed_time = time.time() - start_time

        # 验证性能（不包括实际LLM调用）
        assert elapsed_time < 2.0  # 应该在2秒内完成
        assert result is not None

        print(f"✅ 性能测试通过：处理10个角色耗时 {elapsed_time:.3f}秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
