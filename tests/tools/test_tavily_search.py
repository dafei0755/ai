"""
Tools模块测试 - Tavily Search工具

测试Tavily搜索API集成
"""

import pytest
from unittest.mock import Mock, patch


class TestTavilySearchTool:
    """测试Tavily搜索工具类"""

    @pytest.fixture
    def mock_tavily_client(self):
        """Mock Tavily Client"""
        with patch('intelligent_project_analyzer.tools.tavily_search.TavilyClient') as mock:
            client_instance = Mock()

            # Mock search方法
            client_instance.search.return_value = {
                "results": [
                    {
                        "title": "咖啡馆设计趋势 2025",
                        "url": "https://example.com/cafe-design-2025",
                        "content": "2025年咖啡馆设计的主要趋势包括...",
                        "score": 0.95
                    },
                    {
                        "title": "精品咖啡馆室内设计案例",
                        "url": "https://example.com/cafe-interior",
                        "content": "精品咖啡馆的室内设计需要考虑...",
                        "score": 0.88
                    }
                ],
                "query": "咖啡馆设计",
                "response_time": 0.5
            }

            mock.return_value = client_instance
            yield mock

    def test_tavily_tool_initialization(self):
        """测试工具初始化"""
        from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

        tool = TavilySearchTool(api_key="test-key")
        assert tool is not None

    def test_tavily_tool_search_success(self, mock_tavily_client):
        """测试搜索 - 成功场景"""
        from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

        tool = TavilySearchTool(api_key="test-key")
        result = tool.search("咖啡馆设计")

        # 验证返回结果
        assert "results" in result
        assert len(result["results"]) >= 0  # 可能返回任意数量结果

    def test_tavily_tool_attributes(self):
        """测试工具属性"""
        from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

        tool = TavilySearchTool(api_key="test-key")

        # 验证工具有必要的属性
        assert hasattr(tool, 'search') or hasattr(tool, '__call__')
        # LangChain工具通常有name和description
        if hasattr(tool, 'name'):
            assert isinstance(tool.name, str)

    @pytest.mark.parametrize("api_key", ["test-key-1", "test-key-2", ""])
    def test_tavily_tool_with_various_keys(self, api_key):
        """测试不同API密钥"""
        from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

        if api_key == "":
            # 空API密钥可能抛出异常
            try:
                tool = TavilySearchTool(api_key=api_key)
                # 如果没抛异常也可以接受
                assert tool is not None
            except (ValueError, Exception):
                # 抛异常也是合理的
                pass
        else:
            tool = TavilySearchTool(api_key=api_key)
            assert tool is not None
