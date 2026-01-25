"""
Serper搜索工具单元测试

测试Serper API集成和功能正确性
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from intelligent_project_analyzer.core.types import ToolConfig
from intelligent_project_analyzer.tools.serper_search import SerperSearchTool


class TestSerperSearchTool:
    """Serper搜索工具测试类"""

    @pytest.fixture
    def serper_tool(self):
        """创建测试用的Serper工具实例"""
        return SerperSearchTool(api_key="test_api_key_123", config=ToolConfig(name="serper_search"))

    def test_init(self, serper_tool):
        """测试工具初始化"""
        assert serper_tool.api_key == "test_api_key_123"
        assert serper_tool.base_url == "https://google.serper.dev"
        assert serper_tool.name == "serper_search"
        assert serper_tool.default_params["num"] == 10
        assert serper_tool.default_params["gl"] == "us"
        assert serper_tool.default_params["hl"] == "en"

    def test_process_search_response(self, serper_tool):
        """测试搜索响应处理"""
        mock_response = {
            "organic": [
                {
                    "title": "Test Result 1",
                    "link": "https://example.com/1",
                    "snippet": "This is test result 1",
                    "position": 1,
                },
                {
                    "title": "Test Result 2",
                    "link": "https://example.com/2",
                    "snippet": "This is test result 2",
                    "position": 2,
                },
            ],
            "answerBox": {"answer": "This is the answer"},
        }

        result = serper_tool._process_search_response(mock_response, 0.5, "test query")

        assert result["success"] is True
        assert result["query"] == "test query"
        assert result["answer"] == "This is the answer"
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "Test Result 1"
        assert result["results"][0]["url"] == "https://example.com/1"
        assert result["results"][0]["position"] == 1
        assert result["execution_time"] == 0.5

    @patch("intelligent_project_analyzer.tools.serper_search.httpx.Client")
    def test_search_success(self, mock_httpx, serper_tool):
        """测试成功的搜索调用"""
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Design Trends 2024",
                    "link": "https://example.com/trends",
                    "snippet": "Latest design trends",
                    "position": 1,
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        # 执行搜索
        result = serper_tool.search(query="design trends 2024", num_results=5)

        # 验证结果
        assert result["success"] is True
        assert result["query"] == "design trends 2024"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Design Trends 2024"

        # 验证API调用
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/search" in call_args[0][0]
        assert call_args[1]["json"]["q"] == "design trends 2024"
        assert call_args[1]["json"]["num"] == 5

    @patch("intelligent_project_analyzer.tools.serper_search.httpx.Client")
    def test_search_with_custom_params(self, mock_httpx, serper_tool):
        """测试自定义参数搜索"""
        mock_response = Mock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        # 使用中文和中国地区参数
        serper_tool.search(query="设计趋势", num_results=10, gl="cn", hl="zh-cn")

        # 验证参数
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["q"] == "设计趋势"
        assert payload["num"] == 10
        assert payload["gl"] == "cn"
        assert payload["hl"] == "zh-cn"

    @patch("intelligent_project_analyzer.tools.serper_search.httpx.Client")
    def test_search_api_error(self, mock_httpx, serper_tool):
        """测试API错误处理"""
        import httpx

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "API Error", request=Mock(), response=Mock(status_code=401, text="Unauthorized")
        )
        mock_httpx.return_value = mock_client

        result = serper_tool.search(query="test")

        assert result["success"] is False
        assert "error" in result
        assert result["results"] == []

    @patch("intelligent_project_analyzer.tools.serper_search.httpx.Client")
    def test_search_for_deliverable(self, mock_httpx, serper_tool):
        """测试针对交付物的精准搜索"""
        # Mock搜索结果（确保snippet足够长以通过质量控制）
        mock_response = Mock()
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "用户画像最佳实践 - 如何构建完整的用户画像体系",
                    "link": "https://example.com/persona",
                    "snippet": "如何构建完整的用户画像：用户画像是指根据用户社会属性、生活习惯、消费行为等信息抽象出来的标签化用户模型。本文详细介绍了用户画像的构建方法、数据来源、应用场景和最佳实践案例。",
                    "position": 1,
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        # 交付物数据
        deliverable = {"name": "用户画像", "description": "构建目标用户的详细画像", "format": "persona"}

        # 执行搜索
        result = serper_tool.search_for_deliverable(
            deliverable=deliverable, project_type="commercial_space", max_results=5
        )

        # 验证结果
        assert result["success"] is True
        assert result["deliverable_name"] == "用户画像"
        assert "precise_query" in result
        assert len(result["results"]) > 0
        # 检查是否添加了reference_number
        if len(result["results"]) > 0:
            assert result["results"][0]["reference_number"] == 1

    def test_to_langchain_tool(self, serper_tool):
        """测试转换为LangChain工具"""
        try:
            from langchain_core.tools import StructuredTool

            langchain_tool = serper_tool.to_langchain_tool()

            assert isinstance(langchain_tool, StructuredTool)
            assert langchain_tool.name == "serper_search"
            assert "Google" in langchain_tool.description or "Serper" in langchain_tool.description
        except ImportError:
            pytest.skip("LangChain not available")


@pytest.mark.integration
class TestSerperIntegration:
    """Serper工具集成测试（需要真实API密钥）"""

    @pytest.fixture
    def real_serper_tool(self):
        """创建使用真实API密钥的工具实例"""
        from intelligent_project_analyzer.settings import settings

        if not settings.serper.api_key or settings.serper.api_key == "your_serper_api_key_here":
            pytest.skip("未配置Serper API密钥")

        return SerperSearchTool(api_key=settings.serper.api_key, config=ToolConfig(name="serper_search"))

    def test_real_search(self, real_serper_tool):
        """测试真实搜索（需要API密钥）"""
        result = real_serper_tool.search(query="Python programming", num_results=3)

        assert result["success"] is True
        assert "results" in result
        assert len(result["results"]) > 0
        assert result["results"][0]["title"] != ""
        assert result["results"][0]["url"].startswith("http")

    def test_real_search_deliverable(self, real_serper_tool):
        """测试真实的deliverable搜索"""
        deliverable = {
            "name": "Market Research",
            "description": "Comprehensive market analysis for retail design",
            "format": "report",
        }

        result = real_serper_tool.search_for_deliverable(deliverable=deliverable, project_type="retail", max_results=5)

        assert result["success"] is True
        assert result["deliverable_name"] == "Market Research"
        assert len(result["results"]) > 0


class TestToolFactory:
    """测试ToolFactory中的Serper工具创建"""

    def test_create_serper_tool_from_factory(self):
        """测试从工厂创建Serper工具"""
        from intelligent_project_analyzer.services.tool_factory import ToolFactory
        from intelligent_project_analyzer.settings import settings

        if not settings.serper.enabled or not settings.serper.api_key:
            pytest.skip("Serper未启用或未配置API密钥")

        tool = ToolFactory.create_serper_tool()

        assert tool is not None
        assert tool.name == "serper_search"

    def test_create_all_tools_includes_serper(self):
        """测试create_all_tools包含Serper"""
        from intelligent_project_analyzer.services.tool_factory import ToolFactory
        from intelligent_project_analyzer.settings import settings

        tools = ToolFactory.create_all_tools()

        # 如果Serper已启用且配置，应该在tools中
        if settings.serper.enabled and settings.serper.api_key:
            assert "serper" in tools
            assert tools["serper"].name == "serper_search"

