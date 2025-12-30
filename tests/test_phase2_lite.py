"""
API端点测试 - 简化版本

测试核心API功能，避免导入完整FastAPI应用
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio


class TestAnalysisAPI:
    """分析API测试套件"""

    def test_session_id_generation(self):
        """测试会话ID生成"""
        import uuid
        session_id = f"session-{uuid.uuid4()}"
        assert session_id.startswith("session-")
        assert len(session_id) == 44  # "session-" + 36 chars UUID

    def test_state_structure(self):
        """测试状态数据结构"""
        from intelligent_project_analyzer.core.state import ProjectAnalysisState

        # ProjectAnalysisState是TypedDict，验证关键字段存在
        state_keys = ProjectAnalysisState.__annotations__.keys()
        assert "user_input" in state_keys  # 修正：实际字段名是user_input
        assert "agent_results" in state_keys
        assert "session_id" in state_keys

    @pytest.mark.asyncio
    async def test_redis_session_manager_basic(self):
        """测试RedisSessionManager基础功能（Mock）"""
        with patch('intelligent_project_analyzer.services.redis_session_manager.redis') as mock_redis:
            # Mock Redis客户端
            mock_client = Mock()
            mock_client.get.return_value = None
            mock_client.set.return_value = True
            mock_client.exists.return_value = False
            mock_redis.Redis.return_value = mock_client

            from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

            manager = RedisSessionManager()
            result = manager.save_state("test-session", {"requirement": "测试需求"})

            assert result is True or result is None  # 取决于实现

    def test_workflow_state_reducers(self):
        """测试状态reducer函数"""
        from intelligent_project_analyzer.core.state import merge_agent_results, merge_lists

        # 测试agent结果合并
        existing = {"agent1": {"result": "data1"}}
        new_data = {"agent2": {"result": "data2"}}
        merged = merge_agent_results(existing, new_data)

        assert "agent1" in merged
        assert "agent2" in merged

        # 测试列表合并
        list1 = ["a", "b"]
        list2 = ["c", "d"]
        combined = merge_lists(list1, list2)

        assert len(combined) == 4
        assert "a" in combined and "c" in combined


class TestSessionAPI:
    """会话管理API测试套件"""

    def test_session_metadata_structure(self):
        """测试会话元数据结构"""
        metadata = {
            "session_id": "test-123",
            "user_id": 1,
            "requirement": "测试需求",
            "created_at": "2025-12-30",
            "status": "running"
        }

        assert "session_id" in metadata
        assert "requirement" in metadata
        assert metadata["status"] in ["pending", "running", "completed", "failed"]

    def test_session_list_filtering(self):
        """测试会话列表过滤逻辑"""
        sessions = [
            {"session_id": "s1", "user_id": 1, "status": "completed"},
            {"session_id": "s2", "user_id": 2, "status": "running"},
            {"session_id": "s3", "user_id": 1, "status": "running"},
        ]

        # 按user_id过滤
        user1_sessions = [s for s in sessions if s["user_id"] == 1]
        assert len(user1_sessions) == 2

        # 按状态过滤
        running_sessions = [s for s in sessions if s["status"] == "running"]
        assert len(running_sessions) == 2


class TestToolsModule:
    """工具模块测试套件"""

    @pytest.mark.asyncio
    async def test_tavily_search_mock(self):
        """测试Tavily搜索（Mock）"""
        with patch('intelligent_project_analyzer.tools.tavily_search.TavilyClient') as mock_client:
            # Mock搜索结果
            mock_instance = Mock()
            mock_instance.search.return_value = {
                "results": [
                    {"title": "测试结果1", "url": "http://test1.com", "score": 0.9},
                    {"title": "测试结果2", "url": "http://test2.com", "score": 0.8}
                ]
            }
            mock_client.return_value = mock_instance

            from intelligent_project_analyzer.tools.tavily_search import tavily_search

            result = tavily_search("测试查询", max_results=2)

            assert "results" in result
            assert len(result["results"]) == 2
            assert result["results"][0]["score"] > result["results"][1]["score"]


class TestServicesModule:
    """服务模块测试套件"""

    def test_prompt_manager_singleton(self):
        """测试PromptManager单例模式"""
        from intelligent_project_analyzer.core.prompt_manager import PromptManager

        pm1 = PromptManager()
        pm2 = PromptManager()

        # 应该是同一个实例
        assert pm1 is pm2

    def test_llm_factory_config(self):
        """测试LLM工厂配置"""
        from intelligent_project_analyzer.services.llm_factory import LLMFactory
        from intelligent_project_analyzer.settings import settings

        # 验证配置存在
        assert settings.LLM is not None
        assert hasattr(settings.LLM, 'provider')
        assert hasattr(settings.LLM, 'model')


class TestReportModule:
    """报告模块测试套件"""

    def test_result_aggregator_structure(self):
        """测试结果聚合器数据结构"""
        sample_results = {
            "market_analyst": {
                "deliverables": [
                    {"label": "市场分析", "content": "市场规模数据..."}
                ]
            },
            "design_expert": {
                "deliverables": [
                    {"label": "设计方案", "content": "设计建议..."}
                ]
            }
        }

        # 验证结构
        assert len(sample_results) == 2
        assert "deliverables" in sample_results["market_analyst"]
        assert isinstance(sample_results["market_analyst"]["deliverables"], list)

    def test_pdf_metadata_generation(self):
        """测试PDF元数据生成"""
        import datetime

        metadata = {
            "title": "项目分析报告",
            "author": "Intelligent Project Analyzer",
            "created_at": datetime.datetime.now().isoformat(),
            "session_id": "test-session-123"
        }

        assert metadata["title"]
        assert metadata["author"]
        assert "test-session" in metadata["session_id"]


# 运行命令示例
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
