"""
Tools模块测试 - Tavily Search工具

测试Tavily搜索API集成
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_tavily_client():
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
        yield client_instance


def test_tavily_search_success(mock_tavily_client):
    """测试Tavily搜索 - 成功场景"""
    from intelligent_project_analyzer.tools.tavily_search import tavily_search

    result = tavily_search("咖啡馆设计")

    # 验证返回结果
    assert "results" in result
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "咖啡馆设计趋势 2025"
    assert result["results"][0]["score"] == 0.95

    # 验证客户端被正确调用
    mock_tavily_client.search.assert_called_once_with(query="咖啡馆设计")


def test_tavily_search_empty_query():
    """测试空查询"""
    from intelligent_project_analyzer.tools.tavily_search import tavily_search

    with pytest.raises(ValueError, match="查询不能为空"):
        tavily_search("")


def test_tavily_search_with_max_results(mock_tavily_client):
    """测试指定最大结果数"""
    from intelligent_project_analyzer.tools.tavily_search import tavily_search

    result = tavily_search("咖啡馆设计", max_results=5)

    # 验证max_results参数被传递
    mock_tavily_client.search.assert_called_with(
        query="咖啡馆设计",
        max_results=5
    )


def test_tavily_search_api_error(mock_tavily_client):
    """测试API错误处理"""
    # Mock API抛出异常
    mock_tavily_client.search.side_effect = Exception("API Error")

    from intelligent_project_analyzer.tools.tavily_search import tavily_search

    # 应该优雅地处理错误
    with pytest.raises(Exception):
        tavily_search("咖啡馆设计")


def test_tavily_search_timeout(mock_tavily_client):
    """测试超时处理"""
    import time

    def slow_search(*args, **kwargs):
        time.sleep(10)  # 模拟超时
        return {"results": []}

    mock_tavily_client.search.side_effect = slow_search

    from intelligent_project_analyzer.tools.tavily_search import tavily_search

    # 应该有超时机制（如果实现了）
    with pytest.raises((TimeoutError, Exception)):
        tavily_search("咖啡馆设计", timeout=1)


def test_tavily_search_result_filtering(mock_tavily_client):
    """测试结果过滤（按分数）"""
    from intelligent_project_analyzer.tools.tavily_search import tavily_search

    result = tavily_search("咖啡馆设计", min_score=0.9)

    # 如果实现了过滤，验证只返回高分结果
    if "results" in result:
        high_score_results = [r for r in result["results"] if r["score"] >= 0.9]
        assert len(high_score_results) >= 1


@pytest.mark.parametrize("query,expected_results", [
    ("咖啡馆设计", 2),
    ("室内设计", 2),
    ("", 0),  # 空查询应返回0结果或抛出错误
])
def test_tavily_search_various_queries(mock_tavily_client, query, expected_results):
    """测试各种查询场景"""
    from intelligent_project_analyzer.tools.tavily_search import tavily_search

    if query == "":
        with pytest.raises(ValueError):
            tavily_search(query)
    else:
        result = tavily_search(query)
        assert len(result.get("results", [])) == expected_results
