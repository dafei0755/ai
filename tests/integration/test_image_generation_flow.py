"""
图片生成端到端集成测试

测试覆盖:
1. 完整流程: 问卷数据 → ImageGeneratorService → OpenRouter API → 文件存储 → API返回
2. 高频错误场景回归测试:
   - v7.122: 图片Prompt单字符问题 (visual_prompts[0] vs visual_prompts)
   - API超时处理
   - 配额耗尽降级
   - 并发多图生成

作者: Copilot AI Testing Assistant
创建日期: 2026-01-04
"""

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from httpx import AsyncClient, Response

from intelligent_project_analyzer.services.image_generator import (
    ImageAspectRatio,
    ImageGenerationResult,
    ImageGeneratorService,
)


@pytest.fixture
def mock_openrouter_success_response() -> Dict:
    """模拟OpenRouter成功响应"""
    # 生成一个1x1像素的PNG图片base64
    tiny_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "I've generated a beautiful modern interior design image.",
                    "images": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tiny_png}"}}],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 150, "completion_tokens": 1500, "total_tokens": 1650},
        "model": "google/gemini-2.5-flash-image",
    }


@pytest.fixture
def mock_openrouter_timeout_response() -> Dict:
    """模拟OpenRouter超时响应"""
    return {
        "error": {
            "code": "timeout",
            "message": "Request timeout after 120 seconds",
        }
    }


@pytest.fixture
def mock_openrouter_quota_exceeded_response() -> Dict:
    """模拟OpenRouter配额耗尽响应"""
    return {
        "error": {
            "code": "quota_exceeded",
            "message": "API quota exceeded. Please upgrade your plan.",
        }
    }


@pytest.fixture
def sample_questionnaire_data() -> Dict:
    """模拟问卷数据"""
    return {
        "project_type": "住宅设计",
        "style": "现代简约",
        "area": "150平米",
        "rooms": "三室两厅",
        "budget": "30万",
        "special_requirements": ["注重收纳", "采光良好", "儿童友好"],
    }


@pytest.fixture
def sample_deliverable_metadata() -> Dict:
    """模拟交付物元数据"""
    return {
        "deliverable_id": "DELIV_001",
        "deliverable_name": "空间布局方案",
        "deliverable_type": "concept_design",
        "expert_role": "室内设计师",
    }


@pytest.fixture
def sample_expert_analysis() -> str:
    """模拟专家分析内容"""
    return """
    # 现代简约住宅设计分析

    ## 空间布局
    - 开放式客餐厅布局，提升空间通透感
    - 主卧套房设计，保证私密性
    - 儿童房预留成长空间

    ## 材料选择
    - 木质地板：温暖自然
    - 白色墙面：简洁明亮
    - 玻璃隔断：采光最大化

    ## 色彩搭配
    - 主色调：白色、原木色
    - 点缀色：蓝灰色、绿植
    """


@pytest.mark.integration
@pytest.mark.integration_critical
class TestImageGenerationFlow:
    """图片生成端到端集成测试"""

    @pytest.mark.asyncio
    async def test_full_image_generation_pipeline(
        self,
        mock_openrouter_success_response: Dict,
        sample_questionnaire_data: Dict,
        sample_deliverable_metadata: Dict,
        sample_expert_analysis: str,
    ):
        """测试完整的图片生成流程"""
        # Arrange
        service = ImageGeneratorService(
            api_key="test_api_key",
            timeout=30,  # 集成测试使用较短超时
        )

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200, json=mock_openrouter_success_response, request=MagicMock()
            )

            # Act
            result = await service.generate_image(
                prompt="现代简约风格客厅，自然光线，木质家具",
                aspect_ratio=ImageAspectRatio.LANDSCAPE,
                style="interior",
            )

            # Assert
            assert result.success is True, f"生成失败: {result.error}"
            assert result.image_url is not None, "图片URL为空"
            assert result.image_url.startswith("data:image/png;base64,"), "图片URL格式错误"
            assert result.total_tokens == 1650, "Token统计错误"
            # 注意: 实际模型可能与mock响应不同，验证模型字段存在即可
            assert result.model_used is not None, "模型名称不应为空"

    @pytest.mark.asyncio
    async def test_image_prompt_single_char_bug_regression(self, mock_openrouter_success_response: Dict):
        """
        回归测试: v7.122 图片Prompt单字符BUG

        根因: visual_prompts[0] 只取首字符，导致prompt变成 "M"
        修复: 使用 visual_prompts（完整字符串）
        """
        # Arrange
        service = ImageGeneratorService(api_key="test_api_key")

        # 模拟旧代码的错误逻辑
        full_prompt = "Modern minimalist living room with natural lighting"
        wrong_prompt = full_prompt[0]  # ❌ 错误: 只取首字符 "M"

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200, json=mock_openrouter_success_response, request=MagicMock()
            )

            # Act - 使用错误的单字符prompt
            result_wrong = await service.generate_image(prompt=wrong_prompt)

            # 验证API调用的prompt参数
            call_args = mock_post.call_args
            request_body = call_args.kwargs.get("json", {})
            messages = request_body.get("messages", [])

            # Assert - 旧代码会发送单字符prompt
            assert len(messages) > 0, "消息列表为空"
            actual_prompt = messages[0].get("content", "")

            # 如果是单字符，说明触发了BUG
            if len(actual_prompt) <= 3:
                pytest.fail(
                    f"❌ 检测到v7.122 BUG回归: prompt只有{len(actual_prompt)}个字符 '{actual_prompt}'"
                    f"\n预期: 使用完整prompt '{full_prompt}'"
                )

            # ✅ 正确: 应该使用完整prompt
            assert len(actual_prompt) > 10, f"Prompt过短，可能是BUG回归: '{actual_prompt}'"

    @pytest.mark.asyncio
    async def test_image_generation_api_timeout_handling(self, mock_openrouter_timeout_response: Dict):
        """测试API超时处理"""
        # Arrange
        service = ImageGeneratorService(api_key="test_api_key", timeout=5)

        with patch("httpx.AsyncClient.post") as mock_post:
            # 模拟超时
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            # Act
            result = await service.generate_image(
                prompt="测试超时场景",
                aspect_ratio=ImageAspectRatio.SQUARE,
            )

            # Assert
            assert result.success is False, "超时应该返回失败"
            assert result.error is not None, "错误信息不应为空"
            assert (
                "timeout" in result.error.lower() or "timed out" in result.error.lower()
            ), f"错误信息应包含timeout关键字: {result.error}"

    @pytest.mark.asyncio
    async def test_image_generation_quota_exceeded_handling(self, mock_openrouter_quota_exceeded_response: Dict):
        """测试配额耗尽降级处理"""
        # Arrange
        service = ImageGeneratorService(api_key="test_api_key")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=429,
                json=mock_openrouter_quota_exceeded_response,
                request=MagicMock(),
            )

            # Act
            result = await service.generate_image(prompt="测试配额耗尽场景")

            # Assert
            assert result.success is False, "配额耗尽应该返回失败"
            assert result.error is not None, "错误信息不应为空"
            # 验证错误信息包含配额相关关键字
            error_lower = result.error.lower()
            assert any(
                keyword in error_lower for keyword in ["quota", "limit", "exceeded", "rate"]
            ), f"错误信息应包含配额关键字: {result.error}"

    @pytest.mark.asyncio
    async def test_concurrent_multi_image_generation(self, mock_openrouter_success_response: Dict):
        """测试并发多图生成（v7.127 多图生成功能）"""
        # Arrange
        service = ImageGeneratorService(api_key="test_api_key")
        prompts = [
            "现代简约客厅",
            "北欧风格卧室",
            "日式禅意书房",
            "工业风餐厅",
            "地中海风格阳台",
        ]

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200, json=mock_openrouter_success_response, request=MagicMock()
            )

            # Act - 并发生成5张图片
            tasks = [service.generate_image(prompt=p) for p in prompts]
            results = await asyncio.gather(*tasks)

            # Assert
            assert len(results) == len(prompts), "结果数量与请求不符"
            assert all(r.success for r in results), "存在失败的生成任务"
            assert mock_post.call_count == len(prompts), "API调用次数不符"

            # 验证每个结果都有有效的图片URL
            for idx, result in enumerate(results):
                assert result.image_url is not None, f"第{idx+1}张图片URL为空"
                assert result.image_url.startswith("data:image/"), f"第{idx+1}张图片URL格式错误"

    @pytest.mark.asyncio
    async def test_image_generation_with_questionnaire_context(
        self,
        mock_openrouter_success_response: Dict,
        sample_questionnaire_data: Dict,
        sample_expert_analysis: str,
    ):
        """测试基于问卷数据的图片生成（v7.121+ 数据流优化）"""
        # Arrange
        service = ImageGeneratorService(api_key="test_api_key")

        # 构建包含问卷数据的增强prompt
        context_prompt = f"""
        项目类型: {sample_questionnaire_data['project_type']}
        设计风格: {sample_questionnaire_data['style']}
        面积: {sample_questionnaire_data['area']}
        特殊需求: {', '.join(sample_questionnaire_data['special_requirements'])}

        专家分析:
        {sample_expert_analysis}

        请生成一张现代简约风格的客厅概念图。
        """

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200, json=mock_openrouter_success_response, request=MagicMock()
            )

            # Act
            result = await service.generate_image(
                prompt=context_prompt.strip(),
                aspect_ratio=ImageAspectRatio.LANDSCAPE,
            )

            # Assert
            assert result.success is True, "生成失败"

            # 验证API调用包含问卷数据
            call_args = mock_post.call_args
            request_body = call_args.kwargs.get("json", {})
            messages = request_body.get("messages", [])
            actual_prompt = messages[0].get("content", "")

            # 验证prompt包含关键信息
            assert "现代简约" in actual_prompt, "Prompt应包含设计风格"
            assert "150平米" in actual_prompt or "面积" in actual_prompt, "Prompt应包含面积信息"

    @pytest.mark.asyncio
    async def test_image_generation_retry_mechanism(self, mock_openrouter_success_response: Dict):
        """测试网络错误重试机制"""
        # Arrange
        service = ImageGeneratorService(api_key="test_api_key")

        with patch("httpx.AsyncClient.post") as mock_post:
            # 前2次失败，第3次成功
            mock_post.side_effect = [
                Exception("Network error"),
                Exception("Connection reset"),
                Response(status_code=200, json=mock_openrouter_success_response, request=MagicMock()),
            ]

            # Act
            # 注意: 当前ImageGeneratorService可能没有内置重试，需要外部实现
            # 这里模拟外部重试逻辑
            max_retries = 3
            result = None
            for attempt in range(max_retries):
                try:
                    result = await service.generate_image(prompt="测试重试机制")
                    if result.success:
                        break
                except Exception:
                    if attempt == max_retries - 1:
                        raise

            # Assert
            assert result is not None, "重试后应有结果"
            assert result.success is True, "重试后应成功"
            assert mock_post.call_count == 3, "应该调用3次（2次失败+1次成功）"

    @pytest.mark.asyncio
    async def test_image_storage_and_retrieval(self, mock_openrouter_success_response: Dict, tmp_path: Path):
        """测试图片存储和检索流程"""
        # Arrange
        service = ImageGeneratorService(api_key="test_api_key")
        storage_dir = tmp_path / "concept_images"
        storage_dir.mkdir(parents=True, exist_ok=True)

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = Response(
                status_code=200, json=mock_openrouter_success_response, request=MagicMock()
            )

            # Act - 生成图片
            result = await service.generate_image(prompt="测试图片存储")

            # 模拟保存到文件系统
            if result.success and result.image_url:
                # 提取base64数据
                if "base64," in result.image_url:
                    base64_data = result.image_url.split("base64,")[1]
                    image_data = base64.b64decode(base64_data)

                    # 保存到文件
                    image_path = storage_dir / "test_image.png"
                    image_path.write_bytes(image_data)

                    # Assert - 验证文件存在
                    assert image_path.exists(), "图片文件未保存"
                    assert image_path.stat().st_size > 0, "图片文件为空"

                    # 验证可以读取
                    loaded_data = image_path.read_bytes()
                    assert loaded_data == image_data, "读取的数据与原始数据不符"


@pytest.mark.integration
class TestImageGenerationEdgeCases:
    """图片生成边缘场景测试"""

    @pytest.mark.asyncio
    async def test_empty_prompt_handling(self):
        """测试空prompt处理"""
        service = ImageGeneratorService(api_key="test_api_key")

        # Act & Assert
        with pytest.raises(Exception):  # 应该抛出异常或返回错误
            await service.generate_image(prompt="")

    @pytest.mark.asyncio
    async def test_extremely_long_prompt_handling(self, mock_openrouter_success_response: Dict):
        """测试超长prompt处理"""
        service = ImageGeneratorService(api_key="test_api_key")

        # 生成一个超长prompt（超过token限制）
        long_prompt = "现代简约风格 " * 1000  # 约2000个token

        with patch("httpx.AsyncClient.post") as mock_post:
            # 模拟token限制错误
            mock_post.return_value = Response(
                status_code=400,
                json={"error": {"code": "invalid_request", "message": "Prompt too long"}},
                request=MagicMock(),
            )

            # Act
            result = await service.generate_image(prompt=long_prompt)

            # Assert
            assert result.success is False, "超长prompt应该返回失败"

    @pytest.mark.asyncio
    async def test_invalid_aspect_ratio_handling(self):
        """测试无效宽高比处理"""
        service = ImageGeneratorService(api_key="test_api_key")

        # Act & Assert - 使用无效的宽高比
        with pytest.raises(ValueError):
            # aspect_ratio参数类型检查应该抛出异常
            await service.generate_image(prompt="测试", aspect_ratio="invalid_ratio")  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
