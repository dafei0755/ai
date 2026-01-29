#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bocha搜索工具单元测试 (v7.131)

测试覆盖:
1. API连接测试
2. 成功搜索测试
3. 错误处理测试 (无效API密钥、网络错误、超时)
4. 响应解析测试
5. LangChain工具包装测试
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from intelligent_project_analyzer.agents.bocha_search_tool import (
    BochaSearchTool,
    create_bocha_search_tool_from_settings,
)
from intelligent_project_analyzer.core.types import ToolConfig


class TestBochaSearchTool:
    """Bocha搜索工具测试类"""

    @pytest.fixture
    def bocha_tool(self):
        """创建Bocha工具实例"""
        config = ToolConfig(name="bocha_search")
        return BochaSearchTool(
            api_key="test_api_key_12345",
            base_url="https://api.bocha.cn",
            default_count=5,
            timeout=30,
            config=config,
        )

    @pytest.fixture
    def mock_success_response(self):
        """模拟成功的API响应"""
        return {
            "code": 200,
            "log_id": "test_log_id_123",
            "msg": "success",
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "测试标题1",
                            "url": "https://example.com/1",
                            "snippet": "这是测试摘要1",
                            "summary": "这是完整摘要1",
                            "siteName": "测试网站1",
                            "datePublished": "2024-01-01",
                        },
                        {
                            "name": "测试标题2",
                            "url": "https://example.com/2",
                            "snippet": "这是测试摘要2",
                            "summary": "这是完整摘要2",
                            "siteName": "测试网站2",
                            "datePublished": "2024-01-02",
                        },
                    ]
                }
            },
        }

    # ========== 测试1: 基本初始化 ==========
    def test_initialization(self, bocha_tool):
        """测试工具初始化"""
        assert bocha_tool.api_key == "test_api_key_12345"
        assert bocha_tool.base_url == "https://api.bocha.cn"
        assert bocha_tool.default_count == 5
        assert bocha_tool.timeout == 30
        assert bocha_tool.name == "bocha_search"
        assert bocha_tool.__name__ == "bocha_search"  # LangChain兼容性

    # ========== 测试2: 成功搜索 ==========
    @patch("httpx.Client")
    def test_successful_search(self, mock_client, bocha_tool, mock_success_response):
        """测试成功的搜索请求"""
        # 模拟HTTP响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_success_response

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # 执行搜索
        result = bocha_tool.search("测试查询", count=2)

        # 验证结果
        assert result["success"] is True
        assert result["query"] == "测试查询"
        assert len(result["results"]) == 2
        assert result["count"] == 2
        assert "execution_time" in result

        # 验证第一个结果
        first_result = result["results"][0]
        assert first_result["title"] == "测试标题1"
        assert first_result["url"] == "https://example.com/1"
        assert first_result["snippet"] == "这是测试摘要1"
        assert first_result["summary"] == "这是完整摘要1"

    # ========== 测试3: API错误处理 ==========
    @patch("httpx.Client")
    def test_api_error_handling(self, mock_client, bocha_tool):
        """测试API错误处理"""
        # 模拟HTTP 401错误
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # 执行搜索
        result = bocha_tool.search("测试查询")

        # 验证错误处理
        assert result["success"] is False
        assert "401" in result["message"]
        assert result["results"] == []

    # ========== 测试4: 网络错误处理 ==========
    @patch("httpx.Client")
    def test_network_error_handling(self, mock_client, bocha_tool):
        """测试网络错误处理"""
        import httpx

        # 模拟网络错误
        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # 执行搜索
        result = bocha_tool.search("测试查询")

        # 验证错误处理
        assert result["success"] is False
        assert "Network request failed" in result["message"]
        assert result["results"] == []

    # ========== 测试5: 超时处理 ==========
    @patch("httpx.Client")
    def test_timeout_handling(self, mock_client, bocha_tool):
        """测试超时处理"""
        import httpx

        # 模拟超时
        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # 执行搜索
        result = bocha_tool.search("测试查询")

        # 验证错误处理
        assert result["success"] is False
        assert result["results"] == []

    # ========== 测试6: 空结果处理 ==========
    @patch("httpx.Client")
    def test_empty_results(self, mock_client, bocha_tool):
        """测试空结果处理"""
        # 模拟空结果响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": {"webPages": {"value": []}}}

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # 执行搜索
        result = bocha_tool.search("测试查询")

        # 验证结果
        assert result["success"] is True
        assert result["results"] == []
        assert result["count"] == 0

    # ========== 测试7: 响应格式错误 ==========
    @patch("httpx.Client")
    def test_malformed_response(self, mock_client, bocha_tool):
        """测试格式错误的响应"""
        # 模拟格式错误的响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 500, "msg": "Internal error"}

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # 执行搜索
        result = bocha_tool.search("测试查询")

        # 验证结果 - 应该返回空结果但不报错
        assert result["success"] is True
        assert result["results"] == []

    # ========== 测试8: LangChain工具包装 ==========
    def test_langchain_tool_wrapping(self, bocha_tool):
        """测试LangChain工具包装"""
        langchain_tool = bocha_tool.to_langchain_tool()

        # 验证工具属性
        assert langchain_tool.name == "bocha_search"
        assert "中文" in langchain_tool.description
        assert "博查" in langchain_tool.description

        # 验证工具可调用
        assert callable(langchain_tool.func)

    # ========== 测试9: __call__方法 ==========
    @patch("httpx.Client")
    def test_call_method(self, mock_client, bocha_tool, mock_success_response):
        """测试__call__方法（LangChain接口）"""
        # 模拟HTTP响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_success_response

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        # 调用__call__方法
        result = bocha_tool("测试查询")

        # 验证返回字符串格式
        assert isinstance(result, str)
        assert "博查搜索结果" in result
        assert "测试标题1" in result
        assert "https://example.com/1" in result

    # ========== 测试10: 从设置创建工具 ==========
    @patch("intelligent_project_analyzer.agents.bocha_search_tool.settings")
    def test_create_from_settings(self, mock_settings):
        """测试从全局设置创建工具"""
        # 模拟设置
        mock_settings.bocha.enabled = True
        mock_settings.bocha.api_key = "test_key"
        mock_settings.bocha.base_url = "https://api.bocha.cn"
        mock_settings.bocha.default_count = 8
        mock_settings.bocha.timeout = 30

        # 创建工具
        tool = create_bocha_search_tool_from_settings()

        # 验证工具创建
        assert tool is not None
        assert tool.api_key == "test_key"
        assert tool.default_count == 8

    # ========== 测试11: 禁用时不创建工具 ==========
    @patch("intelligent_project_analyzer.agents.bocha_search_tool.settings")
    def test_disabled_tool_creation(self, mock_settings):
        """测试禁用时不创建工具"""
        # 模拟禁用设置
        mock_settings.bocha.enabled = False

        # 尝试创建工具
        tool = create_bocha_search_tool_from_settings()

        # 验证返回None
        assert tool is None

    # ========== 测试12: 无效API密钥时不创建工具 ==========
    @patch("intelligent_project_analyzer.agents.bocha_search_tool.settings")
    def test_invalid_api_key_creation(self, mock_settings):
        """测试无效API密钥时不创建工具"""
        # 模拟无效API密钥
        mock_settings.bocha.enabled = True
        mock_settings.bocha.api_key = "your_bocha_api_key_here"

        # 尝试创建工具
        tool = create_bocha_search_tool_from_settings()

        # 验证返回None
        assert tool is None


# ========== 集成测试（需要真实API密钥） ==========
@pytest.mark.integration
class TestBochaIntegration:
    """Bocha集成测试（需要真实API）"""

    def test_real_api_call(self):
        """测试真实API调用"""
        from intelligent_project_analyzer.settings import settings

        if not settings.bocha.enabled or settings.bocha.api_key == "your_bocha_api_key_here":
            pytest.skip("Bocha未配置或API密钥无效")

        # 创建工具
        tool = create_bocha_search_tool_from_settings()
        assert tool is not None

        # 执行真实搜索
        result = tool.search("Python编程", count=3)

        # 验证结果
        assert result["success"] is True
        assert len(result["results"]) > 0
        assert result["results"][0]["title"]
        assert result["results"][0]["url"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
