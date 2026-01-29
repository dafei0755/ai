"""
Bocha搜索质量集成测试 (v7.155)

测试Bocha搜索工具的端到端质量控制流程，包括：
1. 模拟Bocha API响应
2. 质量控制管道应用
3. 与Tavily/Serper的对等性
"""

from unittest.mock import Mock, patch

import pytest

from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool


@pytest.mark.integration
def test_bocha_search_with_quality_control():
    """测试Bocha搜索应用质量控制"""
    # Mock Bocha API response with fake URLs
    mock_response = {
        "code": 200,
        "data": {
            "webPages": {
                "value": [
                    {
                        "name": "Valid Article",
                        "url": "https://archdaily.com/article",
                        "snippet": "Real content about architecture design" * 10,
                        "datePublished": "2025-01-01",
                    },
                    {
                        "name": "Fake Article",
                        "url": "https://example.com/fake",
                        "snippet": "Fake content about design" * 10,
                        "datePublished": "2027-01-01",  # 未来日期
                    },
                    {
                        "name": "Placeholder Article",
                        "url": "https://test.com/placeholder",
                        "snippet": "Placeholder content" * 10,
                        "datePublished": "2025-06-01",
                    },
                ]
            }
        },
    }

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        tool = BochaSearchTool(api_key="test_key")
        results = tool.search("test query")

        # 应该只返回有效结果
        assert results["success"]
        assert len(results["results"]) == 1, f"Expected 1 result, got {len(results['results'])}"
        assert "archdaily.com" in results["results"][0]["url"]
        assert results["quality_controlled"] == True


@pytest.mark.integration
def test_bocha_search_for_deliverable():
    """测试Bocha的search_for_deliverable方法"""
    # 需要真实API密钥，跳过
    pytest.skip("Requires real Bocha API key")

    tool = BochaSearchTool(api_key="real_key")
    deliverable = {"name": "用户画像", "description": "分析目标用户群体特征", "format": "persona"}

    results = tool.search_for_deliverable(deliverable=deliverable, project_type="commercial_space", max_results=5)

    assert results["success"]
    assert len(results["results"]) <= 5
    assert results["quality_controlled"] == True
    # 验证没有占位符URL
    for result in results["results"]:
        assert "example.com" not in result["url"]


@pytest.mark.integration
def test_bocha_handles_empty_results():
    """测试Bocha处理空结果"""
    mock_response = {"code": 200, "data": {"webPages": {"value": []}}}

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        tool = BochaSearchTool(api_key="test_key")
        results = tool.search("test query")

        assert results["success"]
        assert len(results["results"]) == 0
        assert results["quality_controlled"] == False  # 没有结果，不需要QC


@pytest.mark.integration
def test_bocha_handles_api_error():
    """测试Bocha处理API错误"""
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"

        tool = BochaSearchTool(api_key="test_key")
        results = tool.search("test query")

        assert results["success"] == False
        assert "error" in results["message"].lower() or "500" in results["message"]


@pytest.mark.integration
def test_bocha_filters_all_invalid_results():
    """测试Bocha过滤所有无效结果"""
    # 所有结果都是无效的
    mock_response = {
        "code": 200,
        "data": {
            "webPages": {
                "value": [
                    {
                        "name": "Fake 1",
                        "url": "https://example.com/1",
                        "snippet": "Fake content" * 10,
                        "datePublished": "2025-01-01",
                    },
                    {
                        "name": "Fake 2",
                        "url": "https://test.com/2",
                        "snippet": "Test content" * 10,
                        "datePublished": "2025-01-01",
                    },
                    {
                        "name": "Future",
                        "url": "https://archdaily.com/future",
                        "snippet": "Future content" * 10,
                        "datePublished": "2028-01-01",
                    },
                ]
            }
        },
    }

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        tool = BochaSearchTool(api_key="test_key")
        results = tool.search("test query")

        # 所有结果都应该被过滤
        assert results["success"]
        assert len(results["results"]) == 0


@pytest.mark.integration
def test_bocha_preserves_valid_results():
    """测试Bocha保留有效结果"""
    mock_response = {
        "code": 200,
        "data": {
            "webPages": {
                "value": [
                    {
                        "name": "Valid 1",
                        "url": "https://archdaily.com/article1",
                        "snippet": "Architecture design content" * 10,
                        "datePublished": "2024-01-01",
                    },
                    {
                        "name": "Valid 2",
                        "url": "https://dezeen.com/article2",
                        "snippet": "Design trends content" * 10,
                        "datePublished": "2024-06-01",
                    },
                    {
                        "name": "Valid 3",
                        "url": "https://designboom.com/article3",
                        "snippet": "Creative design content" * 10,
                        "datePublished": "2025-01-01",
                    },
                ]
            }
        },
    }

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        tool = BochaSearchTool(api_key="test_key")
        results = tool.search("test query")

        # 所有有效结果都应该保留
        assert results["success"]
        assert len(results["results"]) == 3
        assert results["quality_controlled"] == True

        # 验证所有结果都有质量分数
        for result in results["results"]:
            assert "quality_score" in result
            assert result["quality_score"] > 0


@pytest.mark.integration
def test_bocha_chinese_query_building():
    """测试Bocha中文查询构建"""
    tool = BochaSearchTool(api_key="test_key")

    deliverable = {"name": "用户画像", "description": "分析目标用户的行为特征和需求", "format": "persona"}

    # 测试中文查询构建
    query = tool._build_chinese_query(deliverable, "commercial_space")

    # 查询应该包含中文关键词
    assert len(query) > 0
    # 应该包含项目类型
    assert "商业空间设计" in query or "用户" in query or "画像" in query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
