"""
测试数据工厂
提供标准化的测试数据创建方法，减少代码重复
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import Mock


class TestDataFactory:
    """测试数据工厂类"""

    @staticmethod
    def create_project_state(**overrides) -> Dict[str, Any]:
        """
        创建标准测试状态

        Args:
            **overrides: 覆盖默认值的字段

        Returns:
            测试状态字典
        """
        default_state = {
            "session_id": "test-123",
            "user_id": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "user_input": "测试项目",
            "structured_requirements": None,
            "feasibility_assessment": None,
            "project_type": None,
            "strategic_analysis": None,
            "subagents": None,
            "agent_results": {},
            "agent_type": None,
            "deliverable_metadata": None,
            "deliverable_owner_map": None,
            "analysis_mode": None,
        }

        # 应用覆盖
        default_state.update(overrides)
        return default_state

    @staticmethod
    def create_mock_llm_response(content: str, **kwargs) -> Mock:
        """
        创建Mock LLM响应

        Args:
            content: 响应内容
            **kwargs: 其他属性

        Returns:
            Mock对象
        """
        mock = Mock()
        mock.content = content

        # 添加额外属性
        for key, value in kwargs.items():
            setattr(mock, key, value)

        return mock

    @staticmethod
    def create_structured_requirements(
        project_name: str = "测试项目", project_type: str = "web_application", **kwargs
    ) -> Dict[str, Any]:
        """
        创建结构化需求

        Args:
            project_name: 项目名称
            project_type: 项目类型
            **kwargs: 其他字段

        Returns:
            结构化需求字典
        """
        requirements = {
            "project_name": project_name,
            "project_type": project_type,
            "description": kwargs.get("description", "这是一个测试项目"),
            "key_features": kwargs.get("key_features", ["功能1", "功能2", "功能3"]),
            "target_audience": kwargs.get("target_audience", "测试用户"),
            "constraints": kwargs.get("constraints", []),
            "success_criteria": kwargs.get("success_criteria", []),
        }

        return requirements

    @staticmethod
    def create_complete_state(
        user_input: str = "测试项目",
        agents: Optional[List[str]] = None,
        agent_results: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建完整的测试状态（包含所有分析结果）

        Args:
            user_input: 用户输入
            agents: Agent列表
            agent_results: Agent结果字典
            **kwargs: 其他覆盖字段

        Returns:
            完整测试状态
        """
        if agents is None:
            agents = ["expert1", "expert2"]

        if agent_results is None:
            agent_results = {
                "expert1": "专家1的分析结果",
                "expert2": "专家2的分析结果",
            }

        state = TestDataFactory.create_project_state(
            user_input=user_input,
            structured_requirements=TestDataFactory.create_structured_requirements(),
            feasibility_assessment={"feasibility": "high", "risks": []},
            project_type="web_application",
            strategic_analysis={"strategy": "agile"},
            subagents=agents,
            agent_results=agent_results,
        )

        # 应用额外覆盖
        state.update(kwargs)
        return state

    @staticmethod
    def create_mock_llm(response_content: str = "测试响应") -> Mock:
        """
        创建Mock LLM对象

        Args:
            response_content: LLM响应内容

        Returns:
            Mock LLM对象
        """
        mock_llm = Mock()

        # 模拟invoke方法
        def mock_invoke(prompt, **kwargs):
            return TestDataFactory.create_mock_llm_response(response_content)

        mock_llm.invoke = Mock(side_effect=mock_invoke)
        mock_llm.ainvoke = Mock(side_effect=mock_invoke)

        return mock_llm

    @staticmethod
    def create_session_state(session_id: str = "test-session-123", **kwargs) -> Dict[str, Any]:
        """
        创建会话状态

        Args:
            session_id: 会话ID
            **kwargs: 其他字段

        Returns:
            会话状态字典
        """
        session = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "status": kwargs.get("status", "active"),
            "user_id": kwargs.get("user_id", None),
            "data": kwargs.get("data", {}),
        }

        return session


# 便捷函数
def mock_llm(content: str = "测试响应") -> Mock:
    """创建Mock LLM对象（便捷函数）"""
    return TestDataFactory.create_mock_llm(content)


def test_state(**kwargs) -> Dict[str, Any]:
    """创建测试状态（便捷函数）"""
    return TestDataFactory.create_project_state(**kwargs)


def complete_state(**kwargs) -> Dict[str, Any]:
    """创建完整状态（便捷函数）"""
    return TestDataFactory.create_complete_state(**kwargs)


def mock_response(content: str, **kwargs) -> Mock:
    """创建Mock响应（便捷函数）"""
    return TestDataFactory.create_mock_llm_response(content, **kwargs)


def structured_requirements(**kwargs) -> Dict[str, Any]:
    """创建结构化需求（便捷函数）"""
    return TestDataFactory.create_structured_requirements(**kwargs)
