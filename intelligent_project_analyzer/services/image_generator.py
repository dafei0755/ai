"""
图像生成服务 - Gemini Nano Banana Pro 集成

通过 OpenRouter 调用 Gemini 2.5 Flash 的图像生成能力。

 v7.153 优化:
- 配置驱动的角色差异化视觉生成
- 两阶段LLM精炼：视觉简报提取 → 结构化英文Prompt
- Style Anchor机制确保多图一致性
- 以交付物content为唯一信息源

支持模型:
- google/gemini-2.5-flash-preview-image-generation (推荐，性价比高)
- google/gemini-2.0-flash-exp:free (免费版，质量稍低)

使用方式:
    from services.image_generator import ImageGeneratorService

    generator = ImageGeneratorService()
    result = await generator.generate_image(
        prompt="现代简约风格客厅概念图，自然光线，木质家具",
        aspect_ratio="16:9"
    )
    # result = {"image_url": "data:image/png;base64,...", "revised_prompt": "..."}
"""

import os
import time
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import httpx
from loguru import logger
from pydantic import BaseModel, Field

#  v7.153: 导入配置加载器
from ._image_extract_mixin import ImageExtractMixin
from ._image_generate_mixin import ImageGenerateMixin, generate_concept_image  # noqa: F401
from ..utils.visual_config_loader import (
    get_global_config,
    get_role_visual_identity,
    get_role_visual_type_for_project,  # v7.154: 项目类型感知的视觉类型选择
    get_visual_type_config,
)

if TYPE_CHECKING:
    from ..models.image_metadata import ImageMetadata


class ImageAspectRatio(str, Enum):
    """支持的图像宽高比"""

    SQUARE = "1:1"  # 正方形，社交媒体
    LANDSCAPE = "16:9"  # 横向，演示文稿
    PORTRAIT = "9:16"  # 纵向，手机展示
    WIDE = "4:3"  # 传统宽屏
    ULTRAWIDE = "21:9"  # 超宽屏


class ImageGenerationRequest(BaseModel):
    """图像生成请求"""

    prompt: str = Field(..., description="图像生成提示词")
    aspect_ratio: ImageAspectRatio = Field(default=ImageAspectRatio.LANDSCAPE, description="宽高比")
    style: str | None = Field(default=None, description="风格提示，如 'architectural rendering', 'watercolor'")
    negative_prompt: str | None = Field(default=None, description="负面提示词（不希望出现的元素）")


class ImageGenerationResult(BaseModel):
    """图像生成结果"""

    success: bool
    image_url: str | None = Field(default=None, description="Base64 Data URL 或远程 URL")
    image_data: bytes | None = Field(default=None, description="原始图像字节数据")
    revised_prompt: str | None = Field(default=None, description="模型修订后的提示词")
    error: str | None = Field(default=None, description="错误信息")
    model_used: str | None = Field(default=None, description="实际使用的模型")  #  v7.60.5: Token追踪字段（后置Token追踪）
    prompt_tokens: int = Field(default=0, description="提示词Token数")
    completion_tokens: int = Field(default=0, description="生成Token数")
    total_tokens: int = Field(default=0, description="总Token数")


class ImageGeneratorService(ImageExtractMixin, ImageGenerateMixin):
    """
    图像生成服务 - 通过 OpenRouter 调用 Gemini Nano Banana Pro

    特点:
    - 支持 Gemini 3 Pro 图像生成 (Nano Banana Pro)
    - 自动构建设计领域专业提示词
    - 返回 Base64 Data URL 便于前端直接显示
    - 支持多种宽高比
    - 价格: $2/M input, $12/M output
    """

    # 默认模型 - Nano Banana Pro (Gemini 3 Pro Image Preview)
    DEFAULT_MODEL = "google/gemini-3-pro-image-preview"
    # 备选模型 - Nano Banana (Gemini 2.5 Flash Image)
    FALLBACK_MODEL = "google/gemini-2.5-flash-image"

    # 设计领域风格增强提示词
    DESIGN_STYLE_ENHANCERS = {
        "interior": "professional interior design visualization, photorealistic rendering, natural lighting",
        "product": "product design concept, clean background, studio lighting, high-end commercial photography",
        "branding": "brand identity design, clean vector style, modern minimalist aesthetic",
        "architecture": "architectural visualization, professional rendering, dramatic lighting",
        "default": "professional design concept, high quality, detailed",
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 120,
    ):
        """
        初始化图像生成服务

        Args:
            api_key: OpenRouter API Key (默认从环境变量读取)
            model: 使用的模型 (默认使用 Gemini 2.5 Flash)
            base_url: OpenRouter API 地址
            timeout: 请求超时时间 (图像生成较慢，默认 120 秒)
        """
        #  v7.200: 接入负载均衡器，图像生成消费均摊到多个账号
        try:
            from .openrouter_load_balancer import OpenRouterLoadBalancer

            self._load_balancer = OpenRouterLoadBalancer(api_keys=[api_key] if api_key else None)
            logger.info(f" ImageGeneratorService: 负载均衡已启用 ({len(self._load_balancer.api_keys)} 个 Key)")
        except ValueError as e:
            raise ValueError(f" Missing OPENROUTER_API_KEY(S) for image generation: {e}")

        self.model = model or os.getenv("IMAGE_GENERATION_MODEL", self.DEFAULT_MODEL)
        self.base_url = base_url
        self.timeout = timeout

        # OpenRouter 需要的 headers
        self.app_name = os.getenv("OPENROUTER_APP_NAME", "Intelligent Project Analyzer")
        self.site_url = os.getenv("OPENROUTER_SITE_URL", "https://github.com/your-repo")

        #  v7.50: LLM 提示词提取模型（使用轻量模型降低成本）
        self.prompt_extraction_model = os.getenv(
            "PROMPT_EXTRACTION_MODEL", "openai/gpt-4o-mini"  # 默认使用 gpt-4o-mini，成本低且速度快
        )

        logger.info(f" ImageGeneratorService initialized: model={self.model}")

    # ========================================================================
    #  v7.153: 两阶段LLM精炼 - 第一阶段：视觉简报提取
    # ========================================================================

