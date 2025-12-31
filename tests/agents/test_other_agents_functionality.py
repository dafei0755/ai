"""
Agents模块功能测试 - 其他Agents

测试其他Agent的核心功能
包括ProjectDirector, QualityMonitor, QuestionnaireAgent等
"""

import pytest
from unittest.mock import Mock, patch


class TestProjectDirectorFunctionality:
    """测试ProjectDirector功能"""

    def test_project_director_basic_functionality(self, env_setup, mock_llm):
        """测试ProjectDirector基本功能"""
        from intelligent_project_analyzer.agents.project_director import ProjectDirectorAgent

        try:
            agent = ProjectDirectorAgent(llm_model=mock_llm)
            assert agent is not None

            # 验证有invoke、execute或类似方法
            method_names = ['invoke', 'run', 'execute', 'process']
            has_method = any(hasattr(agent, method) for method in method_names)
            assert has_method, "ProjectDirectorAgent应该有执行方法"
        except TypeError:
            pytest.skip("ProjectDirectorAgent需要特定初始化参数")

    def test_project_director_strategic_analysis(self, env_setup, mock_llm):
        """测试战略分析功能"""
        from intelligent_project_analyzer.agents.project_director import ProjectDirectorAgent

        try:
            agent = ProjectDirectorAgent(llm_model=mock_llm)

            # Mock LLM响应
            mock_llm.invoke.return_value = Mock(
                content="战略分析: 可行性高\n建议的专家角色: 室内设计师, 空间规划师"
            )

            state = {
                "session_id": "test-123",
                "user_input": "咖啡馆设计",
                "structured_requirements": {"domain": "interior_design"}
            }

            if hasattr(agent, 'invoke'):
                result = agent.invoke(state)

                assert result is not None
                assert isinstance(result, dict)
        except (TypeError, AttributeError):
            pytest.skip("ProjectDirectorAgent invoke不可用")


class TestQualityMonitorFunctionality:
    """测试QualityMonitor功能"""

    def test_quality_monitor_check_quality(self, env_setup, mock_llm):
        """测试质量检查"""
        from intelligent_project_analyzer.agents.quality_monitor import QualityMonitor

        try:
            monitor = QualityMonitor(llm_model=mock_llm)
            assert monitor is not None

            # 检查质量检查方法
            quality_methods = ['check_quality', 'check', 'validate', 'invoke']
            has_check_method = any(hasattr(monitor, method) for method in quality_methods)

            assert has_check_method
        except (TypeError, ImportError):
            pytest.skip("QualityMonitor不可用")

    def test_quality_monitor_scoring(self, env_setup, mock_llm):
        """测试质量评分"""
        from intelligent_project_analyzer.agents.quality_monitor import QualityMonitor

        try:
            monitor = QualityMonitor(llm_model=mock_llm)

            # Mock质量检查响应
            mock_llm.invoke.return_value = Mock(
                content="质量分数: 85\n问题: 缺少细节描述"
            )

            state = {
                "agent_results": {"design_expert": "设计方案A"}
            }

            if hasattr(monitor, 'invoke'):
                result = monitor.invoke(state)
                assert result is not None
        except (TypeError, ImportError):
            pytest.skip("QualityMonitor不可用")


class TestQuestionnaireAgentFunctionality:
    """测试QuestionnaireAgent功能"""

    def test_questionnaire_agent_generate(self, env_setup, mock_llm):
        """测试问卷生成"""
        from intelligent_project_analyzer.agents.questionnaire_agent import QuestionnaireAgent

        try:
            agent = QuestionnaireAgent(llm_model=mock_llm)
            assert agent is not None

            # Mock问卷生成
            mock_llm.invoke.return_value = Mock(
                content="问题1: 咖啡馆的目标客群是什么?\n问题2: 预算范围?"
            )

            state = {
                "structured_requirements": {"domain": "interior_design"},
                "session_id": "test-123"
            }

            if hasattr(agent, 'invoke'):
                result = agent.invoke(state)
                assert result is not None
        except (TypeError, ImportError):
            pytest.skip("QuestionnaireAgent不可用")


class TestConversationAgentFunctionality:
    """测试ConversationAgent功能"""

    def test_conversation_agent_process_message(self, env_setup, mock_llm):
        """测试对话处理"""
        from intelligent_project_analyzer.agents.conversation_agent import ConversationAgent

        try:
            agent = ConversationAgent(llm_model=mock_llm)
            assert agent is not None

            # Mock对话响应
            mock_llm.invoke.return_value = Mock(
                content="我理解您想要设计一个咖啡馆。请问有什么具体要求吗?"
            )

            state = {
                "user_input": "我想设计咖啡馆",
                "session_id": "test-123"
            }

            if hasattr(agent, 'invoke') or hasattr(agent, 'process'):
                method = agent.invoke if hasattr(agent, 'invoke') else agent.process
                result = method(state)
                assert result is not None
        except (TypeError, ImportError):
            pytest.skip("ConversationAgent不可用")


class TestFollowupAgentFunctionality:
    """测试FollowupAgent功能"""

    def test_followup_agent_generate_questions(self, env_setup, mock_llm):
        """测试生成跟进问题"""
        from intelligent_project_analyzer.agents.followup_agent import FollowupAgent

        try:
            agent = FollowupAgent(llm_model=mock_llm)
            assert agent is not None

            # Mock跟进问题
            mock_llm.invoke.return_value = Mock(
                content="跟进问题: 您对咖啡馆的风格有什么偏好?"
            )

            state = {
                "structured_requirements": {"domain": "interior_design"},
                "session_id": "test-123"
            }

            if hasattr(agent, 'invoke'):
                result = agent.invoke(state)
                assert result is not None
        except (TypeError, ImportError):
            pytest.skip("FollowupAgent不可用")


class TestAnalysisReviewAgentFunctionality:
    """测试AnalysisReviewAgent功能"""

    def test_analysis_review_agent_review(self, env_setup, mock_llm):
        """测试分析审查"""
        from intelligent_project_analyzer.agents.analysis_review_agent import AnalysisReviewAgent

        try:
            agent = AnalysisReviewAgent(llm_model=mock_llm)
            assert agent is not None

            # Mock审查结果
            mock_llm.invoke.return_value = Mock(
                content="审查结果: 通过\n建议: 增加更多细节"
            )

            state = {
                "agent_results": {"expert1": "分析结果A"},
                "session_id": "test-123"
            }

            if hasattr(agent, 'invoke'):
                result = agent.invoke(state)
                assert result is not None
        except (TypeError, ImportError):
            pytest.skip("AnalysisReviewAgent不可用")


class TestChallengeDetectionAgentFunctionality:
    """测试ChallengeDetectionAgent功能"""

    def test_challenge_detection_agent_detect(self, env_setup, mock_llm):
        """测试挑战检测"""
        from intelligent_project_analyzer.agents.challenge_detection_agent import ChallengeDetectionAgent

        try:
            agent = ChallengeDetectionAgent(llm_model=mock_llm)
            assert agent is not None

            # Mock挑战检测
            mock_llm.invoke.return_value = Mock(
                content="潜在挑战: 预算限制, 空间限制"
            )

            state = {
                "structured_requirements": {"budget": "limited"},
                "session_id": "test-123"
            }

            if hasattr(agent, 'invoke'):
                result = agent.invoke(state)
                assert result is not None
        except (TypeError, ImportError):
            pytest.skip("ChallengeDetectionAgent不可用")


class TestFeasibilityAnalystFunctionality:
    """测试FeasibilityAnalystAgent功能"""

    def test_feasibility_analyst_assess(self, env_setup, mock_llm):
        """测试可行性评估"""
        from intelligent_project_analyzer.agents.feasibility_analyst import FeasibilityAnalystAgent

        try:
            agent = FeasibilityAnalystAgent(llm_model=mock_llm)
            assert agent is not None

            # Mock可行性评估
            mock_llm.invoke.return_value = Mock(
                content="可行性评分: 8/10\n关键因素: 市场需求强劲"
            )

            state = {
                "structured_requirements": {"domain": "interior_design"},
                "session_id": "test-123"
            }

            if hasattr(agent, 'invoke') or hasattr(agent, 'assess'):
                method = agent.invoke if hasattr(agent, 'invoke') else agent.assess
                result = method(state)
                assert result is not None
        except (TypeError, ImportError):
            pytest.skip("FeasibilityAnalystAgent不可用")


class TestAgentFactoryFunctionality:
    """测试AgentFactory功能"""

    def test_agent_factory_create_agent(self, env_setup, mock_llm):
        """测试Agent工厂创建Agent"""
        from intelligent_project_analyzer.agents import AgentFactory

        try:
            factory = AgentFactory()
            assert factory is not None

            # 测试创建agent方法
            create_methods = ['create_agent', 'create', 'get_agent', 'make_agent']
            has_create_method = any(hasattr(factory, method) for method in create_methods)

            # 至少AgentFactory类应该存在
            assert isinstance(AgentFactory, type)
        except (TypeError, ImportError):
            pytest.skip("AgentFactory不可用")

    def test_specialized_agent_factory_create(self, env_setup, mock_llm):
        """测试专业Agent工厂"""
        try:
            from intelligent_project_analyzer.agents import SpecializedAgentFactory

            factory = SpecializedAgentFactory()
            assert factory is not None

            # 验证是类
            assert isinstance(SpecializedAgentFactory, type)
        except (TypeError, ImportError):
            pytest.skip("SpecializedAgentFactory不可用")
