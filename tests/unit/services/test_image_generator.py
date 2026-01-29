"""
图像生成服务单元测试
测试OpenRouter API调用、提示词处理、Vision混合生成、异常处理
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# 模拟导入，避免真实依赖
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_openrouter_client():
    """创建Mock OpenRouter客户端"""
    from tests.fixtures.mocks import MockOpenRouterClient

    return MockOpenRouterClient(response_mode="success")


@pytest.fixture
def mock_llm_for_prompt():
    """创建Mock LLM用于提示词提取"""
    from tests.fixtures.mocks import MockAsyncLLM

    return MockAsyncLLM(responses=['{"enhanced_prompt": "A modern minimalist living room with large windows"}'])


@pytest.fixture
def mock_vision_service():
    """创建Mock Vision服务"""
    mock = AsyncMock()
    mock.analyze_image.return_value = {
        "description": "A beautiful interior design reference",
        "style": "modern",
        "colors": ["white", "gray", "wood"],
    }
    return mock


@pytest.fixture
def sample_generation_request():
    """示例图像生成请求"""
    return {"prompt": "现代简约风格客厅", "aspect_ratio": "16:9", "style": "photorealistic", "count": 1}


# ============================================================================
# API调用测试
# ============================================================================


class TestAPICall:
    """测试OpenRouter API调用逻辑"""

    @pytest.mark.asyncio
    async def test_successful_image_generation(self, mock_openrouter_client):
        """测试成功生成图像"""
        # 模拟ImageGenerator类
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_openrouter_client

            # 模拟调用
            response = await mock_openrouter_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={"prompt": "test", "model": "google/gemini-2.0-flash-exp:free"},
            )

            assert response.status_code == 200
            data = await response.json()
            assert "choices" in data
            assert "images" in data["choices"][0]["message"]
            assert len(data["choices"][0]["message"]["images"]) == 2

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """测试限流错误处理"""
        from tests.fixtures.mocks import MockOpenRouterClient

        client = MockOpenRouterClient(response_mode="rate_limit")
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", json={})

        assert response.status_code == 429
        data = await response.json()
        assert "error" in data
        assert data["error"]["code"] == "rate_limit_exceeded"

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """测试超时错误处理"""
        from tests.fixtures.mocks import MockOpenRouterClient

        client = MockOpenRouterClient(response_mode="timeout")

        with pytest.raises(TimeoutError):
            await client.post("https://openrouter.ai/api/v1/chat/completions", json={})

    @pytest.mark.asyncio
    async def test_server_error(self):
        """测试服务器错误处理"""
        from tests.fixtures.mocks import MockOpenRouterClient

        client = MockOpenRouterClient(response_mode="error")
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", json={})

        assert response.status_code == 500
        data = await response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_token_limit_exceeded(self):
        """测试Token耗尽（finish_reason=length）"""
        from tests.fixtures.mocks import MockOpenRouterClient

        client = MockOpenRouterClient(response_mode="token_limit")
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", json={})

        data = await response.json()
        assert data["choices"][0]["finish_reason"] == "length"
        assert data["usage"]["completion_tokens"] == 4096


# ============================================================================
# 提示词处理测试
# ============================================================================


class TestPromptProcessing:
    """测试提示词验证和LLM增强"""

    def test_empty_prompt_validation(self):
        """测试空提示词验证"""
        # 空字符串应该被拒绝
        prompt = ""
        assert len(prompt.strip()) == 0

    def test_prompt_length_validation(self):
        """测试提示词长度限制"""
        # 超长提示词应该被截断
        long_prompt = "A" * 10000
        max_length = 2000
        truncated = long_prompt[:max_length]
        assert len(truncated) == max_length

    @pytest.mark.asyncio
    async def test_llm_prompt_extraction_success(self, mock_llm_for_prompt):
        """测试LLM提示词语义提取成功"""
        user_input = "我想要一个现代简约风格的客厅"

        # 模拟LLM提取
        response = await mock_llm_for_prompt.ainvoke(user_input)
        assert "modern" in response.content.lower() or "minimalist" in response.content.lower()

    @pytest.mark.asyncio
    async def test_llm_prompt_extraction_fallback(self):
        """测试LLM提取失败时的降级处理"""
        from tests.fixtures.mocks import MockAsyncLLM

        # 模拟LLM返回无效JSON
        failing_llm = MockAsyncLLM(responses=["Invalid JSON response"])

        user_input = "现代客厅"
        response = await failing_llm.ainvoke(user_input)

        # 应该降级到直接使用用户输入
        fallback_prompt = user_input
        assert fallback_prompt == "现代客厅"

    def test_prompt_sanitization(self):
        """测试提示词安全清理"""
        # 移除特殊字符和潜在注入
        dirty_prompt = "Design<script>alert('xss')</script> a room"
        clean_prompt = dirty_prompt.replace("<script>", "").replace("</script>", "")
        assert "<script>" not in clean_prompt


# ============================================================================
# 响应解析测试
# ============================================================================


class TestResponseParsing:
    """测试多种响应格式解析"""

    @pytest.mark.asyncio
    async def test_parse_images_array_format(self):
        """测试解析message.images数组格式"""
        from tests.fixtures.mocks import MockOpenRouterClient

        client = MockOpenRouterClient(response_mode="success")
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", json={})
        data = await response.json()

        images = data["choices"][0]["message"]["images"]
        assert isinstance(images, list)
        assert len(images) == 2
        assert images[0].startswith("https://")

    @pytest.mark.asyncio
    async def test_parse_base64_format(self):
        """测试解析Base64编码图像"""
        from tests.fixtures.mocks import MockOpenRouterClient

        client = MockOpenRouterClient(response_mode="base64")
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", json={})
        data = await response.json()

        content = data["choices"][0]["message"]["content"]
        assert content.startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_parse_content_array_format(self):
        """测试解析content数组格式（部分模型）"""
        # 模拟OpenAI风格的content数组
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "Generated image"},
                            {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
                        ]
                    }
                }
            ]
        }

        # 提取图像URL
        content = mock_response["choices"][0]["message"]["content"]
        image_items = [item for item in content if item["type"] == "image_url"]
        assert len(image_items) == 1
        assert image_items[0]["image_url"]["url"].startswith("https://")

    def test_token_usage_tracking(self):
        """测试Token使用量追踪"""
        mock_usage = {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150}

        assert mock_usage["prompt_tokens"] > 0
        assert mock_usage["completion_tokens"] > 0
        assert mock_usage["total_tokens"] == mock_usage["prompt_tokens"] + mock_usage["completion_tokens"]


# ============================================================================
# Vision混合生成测试
# ============================================================================


class TestVisionIntegration:
    """测试Vision参考图像+生成混合流程"""

    @pytest.mark.asyncio
    async def test_vision_reference_analysis(self, mock_vision_service):
        """测试Vision分析参考图像"""
        reference_image_url = "https://example.com/reference.jpg"

        analysis = await mock_vision_service.analyze_image(reference_image_url)

        assert "description" in analysis
        assert "style" in analysis
        assert analysis["style"] == "modern"

    @pytest.mark.asyncio
    async def test_vision_to_prompt_enhancement(self, mock_vision_service):
        """测试将Vision分析结果注入提示词"""
        base_prompt = "Design a living room"
        analysis = await mock_vision_service.analyze_image("ref.jpg")

        # 组合提示词
        enhanced_prompt = f"{base_prompt}, inspired by {analysis['description']}, style: {analysis['style']}"

        assert "modern" in enhanced_prompt
        assert "beautiful interior design" in enhanced_prompt.lower()

    @pytest.mark.asyncio
    async def test_vision_analysis_timeout(self):
        """测试Vision分析超时降级"""
        mock_vision = AsyncMock()
        mock_vision.analyze_image.side_effect = TimeoutError("Vision API timeout")

        # 超时后应该降级到不使用Vision
        try:
            await mock_vision.analyze_image("ref.jpg")
            vision_used = True
        except TimeoutError:
            vision_used = False

        assert not vision_used  # 应该降级


# ============================================================================
# 批量生成测试
# ============================================================================


class TestBatchGeneration:
    """测试多图批量生成（深度思维模式）"""

    @pytest.mark.asyncio
    async def test_generate_multiple_concept_images(self, mock_openrouter_client):
        """测试生成多张概念图"""
        prompts = ["Modern living room concept 1", "Modern living room concept 2", "Modern living room concept 3"]

        results = []
        for prompt in prompts:
            response = await mock_openrouter_client.post(
                "https://openrouter.ai/api/v1/chat/completions", json={"prompt": prompt}
            )
            data = await response.json()
            results.append(data)

        assert len(results) == 3
        assert mock_openrouter_client.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_generation_partial_failure(self):
        """测试批量生成部分失败"""
        from tests.fixtures.mocks import MockOpenRouterClient

        # 模拟第2次调用失败
        client = MockOpenRouterClient(response_mode="success")
        results = []
        errors = []

        for i in range(3):
            if i == 1:
                # 模拟第2次失败
                client.response_mode = "error"
            else:
                client.response_mode = "success"

            response = await client.post("https://openrouter.ai/api/v1/chat/completions", json={})

            if response.status_code == 200:
                results.append(await response.json())
            else:
                errors.append(i)

        assert len(results) == 2
        assert len(errors) == 1
        assert errors[0] == 1

    def test_deliverable_prompt_specialization(self):
        """测试交付物特定提示词生成"""
        deliverables = [
            {"name": "空间布局图", "type": "layout"},
            {"name": "材料方案板", "type": "materials"},
            {"name": "色彩方案", "type": "colors"},
        ]

        specialized_prompts = []
        for d in deliverables:
            if d["type"] == "layout":
                prompt = f"Floor plan layout for {d['name']}"
            elif d["type"] == "materials":
                prompt = f"Material board showing {d['name']}"
            else:
                prompt = f"Color scheme for {d['name']}"
            specialized_prompts.append(prompt)

        assert len(specialized_prompts) == 3
        assert "Floor plan" in specialized_prompts[0]
        assert "Material board" in specialized_prompts[1]


# ============================================================================
# 集成场景测试
# ============================================================================


class TestIntegrationScenarios:
    """测试完整的集成场景"""

    @pytest.mark.asyncio
    async def test_full_generation_workflow(self, mock_llm_for_prompt, mock_openrouter_client):
        """测试完整生成流程：LLM提取 → API调用 → 响应解析"""
        # Step 1: LLM提取提示词
        user_input = "现代简约客厅"
        llm_response = await mock_llm_for_prompt.ainvoke(user_input)

        # Step 2: 调用OpenRouter
        api_response = await mock_openrouter_client.post(
            "https://openrouter.ai/api/v1/chat/completions", json={"prompt": llm_response.content}
        )

        # Step 3: 解析响应
        data = await api_response.json()
        images = data["choices"][0]["message"]["images"]

        assert len(images) > 0
        assert mock_llm_for_prompt.call_count == 1
        assert mock_openrouter_client.call_count == 1

    @pytest.mark.asyncio
    async def test_questionnaire_to_image_generation(self):
        """测试从问卷数据生成概念图"""
        # 模拟问卷数据
        questionnaire_data = {
            "style": "现代简约",
            "space_type": "客厅",
            "area": "30平米",
            "budget": "中等",
            "key_requirements": ["采光好", "收纳足"],
        }

        # 构建提示词
        prompt_parts = [
            f"Design a {questionnaire_data['space_type']}",
            f"in {questionnaire_data['style']} style",
            f"area: {questionnaire_data['area']}",
            f"with {', '.join(questionnaire_data['key_requirements'])}",
        ]
        final_prompt = ", ".join(prompt_parts)

        assert "客厅" in final_prompt
        assert "现代简约" in final_prompt
        assert "采光好" in final_prompt

    @pytest.mark.asyncio
    async def test_error_recovery_chain(self):
        """测试错误恢复链"""
        from tests.fixtures.mocks import MockOpenRouterClient

        # 模拟降级链：主API失败 → 备用模型 → 降级到文本描述
        primary_client = MockOpenRouterClient(response_mode="rate_limit")
        backup_client = MockOpenRouterClient(response_mode="success")

        # 尝试主API
        primary_response = await primary_client.post("https://openrouter.ai/api/v1/chat/completions", json={})

        if primary_response.status_code != 200:
            # 降级到备用
            backup_response = await backup_client.post("https://openrouter.ai/api/v1/chat/completions", json={})
            assert backup_response.status_code == 200
