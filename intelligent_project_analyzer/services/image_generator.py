"""
图像生成服务 - Gemini Nano Banana Pro 集成

通过 OpenRouter 调用 Gemini 2.5 Flash 的图像生成能力。

🔥 v7.153 优化:
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

import base64
import json
import os
import time
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger
from pydantic import BaseModel, Field

# 🆕 v7.153: 导入配置加载器
from ..utils.visual_config_loader import get_role_visual_type_for_project  # 🆕 v7.154: 项目类型感知的视觉类型选择
from ..utils.visual_config_loader import (
    build_role_visual_context,
    get_global_config,
    get_role_visual_identity,
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
    style: Optional[str] = Field(default=None, description="风格提示，如 'architectural rendering', 'watercolor'")
    negative_prompt: Optional[str] = Field(default=None, description="负面提示词（不希望出现的元素）")


class ImageGenerationResult(BaseModel):
    """图像生成结果"""

    success: bool
    image_url: Optional[str] = Field(default=None, description="Base64 Data URL 或远程 URL")
    image_data: Optional[bytes] = Field(default=None, description="原始图像字节数据")
    revised_prompt: Optional[str] = Field(default=None, description="模型修订后的提示词")
    error: Optional[str] = Field(default=None, description="错误信息")
    model_used: Optional[str] = Field(default=None, description="实际使用的模型")  # 🔥 v7.60.5: Token追踪字段（后置Token追踪）
    prompt_tokens: int = Field(default=0, description="提示词Token数")
    completion_tokens: int = Field(default=0, description="生成Token数")
    total_tokens: int = Field(default=0, description="总Token数")


class ImageGeneratorService:
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
        api_key: Optional[str] = None,
        model: Optional[str] = None,
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
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Missing OPENROUTER_API_KEY environment variable")

        self.model = model or os.getenv("IMAGE_GENERATION_MODEL", self.DEFAULT_MODEL)
        self.base_url = base_url
        self.timeout = timeout

        # OpenRouter 需要的 headers
        self.app_name = os.getenv("OPENROUTER_APP_NAME", "Intelligent Project Analyzer")
        self.site_url = os.getenv("OPENROUTER_SITE_URL", "https://github.com/your-repo")

        # 🆕 v7.50: LLM 提示词提取模型（使用轻量模型降低成本）
        self.prompt_extraction_model = os.getenv(
            "PROMPT_EXTRACTION_MODEL", "openai/gpt-4o-mini"  # 默认使用 gpt-4o-mini，成本低且速度快
        )

        logger.info(f"🎨 ImageGeneratorService initialized: model={self.model}")

    # ========================================================================
    # 🆕 v7.153: 两阶段LLM精炼 - 第一阶段：视觉简报提取
    # ========================================================================

    async def _extract_visual_brief(
        self,
        deliverable_content: str,
        role_id: str,
        profile_label: str = "",
        project_type: str = "",  # 🆕 v7.154: 添加项目类型参数
        visual_references: Optional[List[Dict[str, Any]]] = None,  # 🆕 v7.155: 视觉参考
    ) -> Tuple[str, str]:
        """
        🆕 v7.153: 第一阶段LLM - 从交付物content中提取视觉简报

        核心改进：
        1. 以交付物content为唯一信息源（已融合问卷+需求+搜索+任务）
        2. 根据角色配置的extraction_focus定制提取维度
        3. 同时生成style_anchor确保多图一致性
        4. 🆕 v7.154: 根据项目类型选择合适的视觉类型
        5. 🆕 v7.155: 支持用户上传的视觉参考注入

        Args:
            deliverable_content: 交付物完整内容（唯一信息源）
            role_id: 角色ID，如 "V3", "2-1"
            profile_label: 风格标签（硬性约束）
            project_type: 项目类型（用于选择合适的视觉类型）
            visual_references: 用户上传的视觉参考列表

        Returns:
            Tuple[visual_brief, style_anchor]:
            - visual_brief: 500-800字中文视觉简报
            - style_anchor: 3-8词英文风格锚点
        """
        logger.info(f"🧠 [v7.153 第一阶段] 开始视觉简报提取...")
        logger.debug(f"  📋 角色: {role_id}, 风格标签: {profile_label}")
        logger.debug(f"  📏 内容长度: {len(deliverable_content)} 字符")

        # 从配置加载角色视觉身份
        role_config = get_role_visual_identity(role_id)
        extraction_focus = role_config.get("extraction_focus", [])
        # 🆕 v7.154: 使用项目类型感知的视觉类型选择
        visual_type = get_role_visual_type_for_project(role_id, project_type)
        role_perspective = role_config.get("perspective", "设计专家")

        logger.info(f"  🎨 视觉类型: {visual_type} (项目类型: {project_type})")
        logger.info(f"  🔍 提取焦点: {extraction_focus[:3]}...")

        # 🆕 v7.155: 构建视觉参考上下文
        visual_reference_context = ""
        if visual_references:
            visual_reference_context = self._build_visual_reference_context(visual_references)
            logger.info(f"  🖼️ [v7.155] 注入 {len(visual_references)} 个视觉参考")

        # 获取视觉类型配置
        visual_type_config = get_visual_type_config(visual_type)
        global_config = get_global_config()
        max_length = global_config.get("visual_brief_max_length", 800)

        # 构建提取焦点描述
        focus_list = "\n".join(f"- {f}" for f in extraction_focus) if extraction_focus else "- 空间效果\n- 材质色彩\n- 氛围表现"

        # 🆕 v7.155: 在 system_prompt 中注入视觉参考
        visual_ref_section = ""
        if visual_reference_context:
            visual_ref_section = f"""
**用户提供的视觉参考**（必须参考这些风格特征）:
{visual_reference_context}

"""

        system_prompt = f"""你是专业的设计视觉化专家。你的任务是从设计交付物内容中提取可视化的核心要素。

**你的专业视角**: {role_perspective}
**目标视觉类型**: {visual_type_config.get('description', '专业设计可视化')}
{visual_ref_section}
**提取焦点维度**（按优先级）:
{focus_list}

**输出要求**:
1. 输出两部分，用 "---STYLE_ANCHOR---" 分隔
2. 第一部分：视觉简报（500-{max_length}字中文）
   - 聚焦可视化、可表达的具体元素
   - 包含：空间描述、材料质感、色彩方案、光线氛围、风格元素
   - 排除：抽象概念、理论分析、无法可视化的内容
   - {"**重要**：必须融合用户提供的视觉参考特征" if visual_references else ""}
3. 第二部分：风格锚点（3-8个英文关键词）
   - 用于确保多张图片风格一致
   - 格式：逗号分隔的英文词组
   - {"**重要**：风格锚点必须体现用户参考图的风格特征" if visual_references else ""}

**示例输出格式**:
视觉简报内容...描述空间布局、材料、色彩、光线、氛围等可视化元素...
---STYLE_ANCHOR---
Scandinavian minimalist, warm wood tones, natural lighting, soft textiles"""

        # 风格标签作为硬性约束
        style_constraint = f"\n**风格标签（必须体现）**: {profile_label}" if profile_label else ""

        user_prompt = f"""请从以下设计交付物内容中提取视觉简报和风格锚点：
{style_constraint}

---交付物内容开始---
{deliverable_content[:5000]}
---交付物内容结束---

请按要求格式输出视觉简报和风格锚点："""

        try:
            start_time = time.time()

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json={
                        "model": self.prompt_extraction_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.6,
                        "max_tokens": 1000,
                    },
                )

            elapsed = time.time() - start_time
            logger.info(f"  ⏱️ LLM响应时间: {elapsed:.2f}秒")

            if response.status_code != 200:
                logger.warning(f"⚠️ [第一阶段] API错误: {response.status_code}")
                return self._fallback_visual_brief(deliverable_content, role_config, profile_label)

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not content:
                logger.warning("⚠️ [第一阶段] LLM返回空内容")
                return self._fallback_visual_brief(deliverable_content, role_config, profile_label)

            # 解析输出
            if "---STYLE_ANCHOR---" in content:
                parts = content.split("---STYLE_ANCHOR---")
                visual_brief = parts[0].strip()
                style_anchor = parts[1].strip() if len(parts) > 1 else ""
            else:
                visual_brief = content
                style_anchor = self._extract_style_anchor_fallback(content, role_config)

            logger.info(f"✅ [v7.153 第一阶段] 视觉简报提取成功")
            logger.info(f"  📝 简报长度: {len(visual_brief)} 字符")
            logger.info(f"  🎨 风格锚点: {style_anchor[:50]}...")

            return visual_brief, style_anchor

        except Exception as e:
            logger.error(f"❌ [第一阶段] 异常: {e}")
            return self._fallback_visual_brief(deliverable_content, role_config, profile_label)

    def _fallback_visual_brief(self, content: str, role_config: Dict[str, Any], profile_label: str) -> Tuple[str, str]:
        """降级的视觉简报生成"""
        # 截取内容前800字作为简报
        visual_brief = content[:800] if len(content) > 800 else content

        # 从配置生成风格锚点
        style_prefs = role_config.get("style_preferences", [])[:3]
        style_anchor = ", ".join(style_prefs) if style_prefs else "professional design visualization"

        if profile_label:
            style_anchor = f"{profile_label}, {style_anchor}"

        logger.info(f"  ⚠️ 使用降级视觉简报 ({len(visual_brief)} 字符)")
        return visual_brief, style_anchor

    def _extract_style_anchor_fallback(self, content: str, role_config: Dict[str, Any]) -> str:
        """从内容中提取风格锚点的降级方法"""
        style_prefs = role_config.get("style_preferences", [])[:3]
        return ", ".join(style_prefs) if style_prefs else "professional design"

    # ========================================================================
    # 🆕 v7.155: 视觉参考上下文构建
    # ========================================================================

    def _build_visual_reference_context(self, visual_references: List[Dict[str, Any]]) -> str:
        """
        🆕 v7.155: 构建视觉参考上下文字符串

        将用户上传的参考图的结构化特征转换为文本描述，
        用于注入到 LLM 提示词中。

        Args:
            visual_references: 视觉参考列表

        Returns:
            格式化的视觉参考上下文字符串
        """
        if not visual_references:
            return ""

        context_parts = []

        for idx, ref in enumerate(visual_references, 1):
            features = ref.get("structured_features", {})

            # 构建单个参考图的描述
            part_lines = [f"### 参考图 {idx}"]

            # 风格关键词
            style_keywords = features.get("style_keywords", [])
            if style_keywords:
                part_lines.append(f"- 风格: {', '.join(style_keywords)}")

            # 主色调
            dominant_colors = features.get("dominant_colors", [])
            if dominant_colors:
                part_lines.append(f"- 主色调: {', '.join(dominant_colors)}")

            # 材质
            materials = features.get("materials", [])
            if materials:
                part_lines.append(f"- 材质: {', '.join(materials)}")

            # 氛围
            mood_atmosphere = features.get("mood_atmosphere", "")
            if mood_atmosphere:
                part_lines.append(f"- 氛围: {mood_atmosphere}")

            # 空间布局
            spatial_layout = features.get("spatial_layout", "")
            if spatial_layout:
                part_lines.append(f"- 空间布局: {spatial_layout}")

            # 设计元素
            design_elements = features.get("design_elements", [])
            if design_elements:
                part_lines.append(f"- 设计元素: {', '.join(design_elements)}")

            # 用户追加描述（优先级最高）
            user_description = ref.get("user_description")
            if user_description:
                part_lines.append(f"- **用户说明**: {user_description}")

            # 参考类型
            reference_type = ref.get("reference_type", "general")
            if reference_type != "general":
                type_labels = {
                    "style": "风格参考",
                    "layout": "布局参考",
                    "color": "色彩参考",
                }
                part_lines.append(f"- 参考类型: {type_labels.get(reference_type, reference_type)}")

            context_parts.append("\n".join(part_lines))

        return "\n\n".join(context_parts)

    # ========================================================================
    # 🆕 v7.153: 两阶段LLM精炼 - 第二阶段：结构化英文Prompt生成
    # ========================================================================

    async def _generate_structured_prompt(
        self,
        visual_brief: str,
        style_anchor: str,
        role_id: str,
        deliverable_name: str = "",
        project_type: str = "",  # 🆕 v7.154: 添加项目类型参数
    ) -> str:
        """
        🆕 v7.153: 第二阶段LLM - 从视觉简报生成结构化英文Prompt

        Args:
            visual_brief: 第一阶段提取的视觉简报
            style_anchor: 风格锚点（确保一致性）
            role_id: 角色ID
            deliverable_name: 交付物名称
            project_type: 项目类型（用于选择合适的视觉类型）

        Returns:
            结构化英文Prompt (150-200 words)
        """
        logger.info(f"🧠 [v7.153 第二阶段] 开始结构化Prompt生成...")

        # 加载配置
        role_config = get_role_visual_identity(role_id)
        # 🆕 v7.154: 使用项目类型感知的视觉类型选择
        visual_type = get_role_visual_type_for_project(role_id, project_type)
        visual_type_config = get_visual_type_config(visual_type)
        avoid_patterns = role_config.get("avoid_patterns", [])
        required_keywords = role_config.get("required_keywords", [])

        # 获取质量后缀和负面提示词
        quality_suffix = visual_type_config.get("quality_suffix", "high quality, professional")
        type_keywords = visual_type_config.get("keywords_en", [])

        system_prompt = f"""You are an expert image prompt engineer for AI image generation (Midjourney, DALL-E, Gemini).

**Target Visual Type**: {visual_type_config.get('description_en', 'Professional design visualization')}
**Style Anchor (MUST maintain)**: {style_anchor}

**Output Requirements**:
1. Write in English only, 150-200 words
2. Structure: Scene description → Materials & textures → Colors → Lighting → Mood/atmosphere
3. MUST include style anchor keywords to ensure consistency
4. MUST include these type-specific keywords: {', '.join(type_keywords[:5])}
5. End with: {quality_suffix}

**AVOID generating**:
{chr(10).join(f'- {p}' for p in avoid_patterns[:5]) if avoid_patterns else '- Low quality rendering'}

**MUST include keywords**: {', '.join(required_keywords) if required_keywords else 'design, space'}

Output: Just the prompt, no explanations."""

        user_prompt = f"""Design Deliverable: {deliverable_name}

Visual Brief (Chinese):
{visual_brief[:2000]}

---
Generate the structured English image prompt:"""

        try:
            start_time = time.time()

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json={
                        "model": self.prompt_extraction_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 350,
                    },
                )

            elapsed = time.time() - start_time
            logger.info(f"  ⏱️ LLM响应时间: {elapsed:.2f}秒")

            if response.status_code != 200:
                logger.warning(f"⚠️ [第二阶段] API错误: {response.status_code}")
                return self._fallback_structured_prompt(visual_brief, style_anchor, role_config)

            result = response.json()
            prompt = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not prompt or len(prompt) < 50:
                logger.warning(f"⚠️ [第二阶段] Prompt过短或为空")
                return self._fallback_structured_prompt(visual_brief, style_anchor, role_config)

            # 校验必保留关键词
            prompt = self._validate_and_enhance_prompt(prompt, required_keywords, style_anchor, quality_suffix)

            logger.info(f"✅ [v7.153 第二阶段] 结构化Prompt生成成功 ({len(prompt)} 字符)")
            logger.debug(f"  📝 Prompt: {prompt[:150]}...")

            return prompt

        except Exception as e:
            logger.error(f"❌ [第二阶段] 异常: {e}")
            return self._fallback_structured_prompt(visual_brief, style_anchor, role_config)

    def _fallback_structured_prompt(self, visual_brief: str, style_anchor: str, role_config: Dict[str, Any]) -> str:
        """降级的结构化Prompt生成"""
        visual_type_config = get_visual_type_config(role_config.get("visual_type", "photorealistic_rendering"))
        quality_suffix = visual_type_config.get("quality_suffix", "high quality")

        # 从视觉简报提取关键词
        import re

        # 提取英文词汇
        english_words = re.findall(r"[a-zA-Z]+", visual_brief)[:10]
        # 提取中文关键词并简化
        chinese_keywords = re.findall(r"[\u4e00-\u9fff]{2,4}", visual_brief)[:10]

        prompt = f"{style_anchor}, {' '.join(english_words)}, professional design visualization, {quality_suffix}"

        logger.info(f"  ⚠️ 使用降级Prompt ({len(prompt)} 字符)")
        return prompt

    def _validate_and_enhance_prompt(
        self, prompt: str, required_keywords: List[str], style_anchor: str, quality_suffix: str
    ) -> str:
        """校验并增强Prompt，确保必要关键词存在"""
        prompt_lower = prompt.lower()

        # 检查必保留关键词
        missing_keywords = [kw for kw in required_keywords if kw.lower() not in prompt_lower]

        if missing_keywords:
            logger.info(f"  📝 追加缺失关键词: {missing_keywords}")
            prompt = f"{prompt}, {', '.join(missing_keywords)}"

        # 确保style_anchor存在
        anchor_words = [w.strip() for w in style_anchor.split(",")[:2]]
        for anchor in anchor_words:
            if anchor.lower() not in prompt_lower:
                prompt = f"{anchor}, {prompt}"
                break

        # 确保质量后缀
        if quality_suffix and quality_suffix.lower() not in prompt_lower:
            prompt = f"{prompt}, {quality_suffix}"

        return prompt

    async def _llm_extract_visual_prompt(
        self, expert_content: str, expert_name: str = "", project_type: str = "interior", top_constraints: str = ""
    ) -> str:
        """
        🆕 v7.50: 使用 LLM 从专家报告中提取高质量图像生成提示词

        相比正则提取的优势：
        1. 理解语义，捕捉深层设计意图
        2. 提取完整的视觉叙事，而非碎片化关键词
        3. 自动构建符合图像生成模型期望的 prompt 结构

        Args:
            expert_content: 专家报告内容
            expert_name: 专家名称（用于上下文）
            project_type: 项目类型
            top_constraints: 项目顶层约束

        Returns:
            优化后的英文图像生成提示词 (100-150 words)
        """
        logger.info(f"🧠 [LLM提示词提取] 开始处理...")
        logger.debug(f"  👤 专家名称: {expert_name}")
        logger.debug(f"  🏷️  项目类型: {project_type}")
        logger.debug(f"  📏 专家内容长度: {len(expert_content)} 字符")

        # 🔥 v7.128: 增加输入长度限制至5000字符（支持完整专家分析）
        content_preview = expert_content[:5000] if len(expert_content) > 5000 else expert_content
        if len(expert_content) > 5000:
            logger.info(f"  ✂️  内容截断: {len(expert_content)} → 5000 字符")

        # 项目类型到场景描述的映射
        type_context = {
            "interior": "interior design / residential space",
            "architecture": "architectural / building exterior",
            "product": "product design / industrial design",
            "branding": "brand identity / visual design",
        }.get(project_type, "design concept")
        logger.debug(f"  🎯 场景上下文: {type_context}")

        # 🔥 v7.129: 优化系统提示词，强化角色身份差异化
        system_prompt = """You are a professional image prompt engineer specializing in design visualization.

Your task is to extract visual elements from design analysis reports and create high-quality prompts for AI image generation (like Midjourney, DALL-E, Gemini).

**CRITICAL REQUIREMENTS** (v7.129):
1. **RESPECT ROLE IDENTITY**: Generate images matching the expert's professional role
   - Narrative expert (叙事体验设计师) → Storyboards/mood boards, NOT architectural renderings
   - Research expert (设计研究分析师) → Infographics/charts/diagrams, NOT space visualizations
   - Technical expert (技术实施工程师) → Technical schematics/blueprints, NOT artistic renderings
   - Design Director (综合设计协调者) → Architectural sections/spatial coordination diagrams
   - Context expert (场景与行为专家) → User journey maps/behavior patterns, NOT static spaces

2. **RESPECT DELIVERABLE FORMAT**: Match the output type specified
   - "visualization" format → Infographics/charts/data visualizations
   - "narrative" format → Storyboards/mood boards/scene concepts
   - "technical_doc" format → Technical drawings/blueprints/schematics
   - "architectural_design" format → Architectural sections/coordination diagrams
   - "contextual" format → User journey maps/behavior flow diagrams

3. **AVOID SPECIFIED PATTERNS**: If the input mentions "严格避免" (strictly avoid), do NOT generate those types

4. Extract SPECIFIC details from the expert analysis (materials, spatial layouts, cultural elements)

5. Reflect user's detailed needs and emotional keywords

6. Include precise technical specifications mentioned in the analysis

Output Requirements:
1. Write in English only
2. 150-200 words with rich details
3. Focus on VISUAL elements: materials, colors, lighting, atmosphere, spatial relationships
4. Include specific design details that make the concept unique
5. Use professional terminology matching the role identity and deliverable format
6. End with quality descriptors appropriate to the visual type (e.g., "infographic style" for research, "technical drawing" for engineering)

Do NOT include:
- Generic descriptions like "modern minimalist" without specifics
- Abstract concepts that can't be visualized
- Chinese characters
- Explanations or meta-commentary
- Client names or personal information

Output format: Just the prompt, nothing else."""

        user_prompt = f"""Design Context: {type_context}
Expert Role: {expert_name if expert_name else "Design Expert"}

Project Constraints:
{top_constraints if top_constraints else "Not specified"}

Expert Analysis Content:
{content_preview}

---
Generate an optimized image prompt based on the above design analysis:"""

        try:
            logger.info(f"  📤 调用LLM (model={self.prompt_extraction_model})...")
            start_time = __import__("time").time()

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json={
                        "model": self.prompt_extraction_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 300,
                    },
                )

                elapsed_time = __import__("time").time() - start_time
                logger.info(f"  ⏱️  LLM响应时间: {elapsed_time:.2f}秒")

                if response.status_code != 200:
                    logger.warning(f"⚠️  [LLM提示词提取] API返回错误: {response.status_code}")
                    logger.debug(f"  错误响应: {response.text[:200]}")
                    return ""

                result = response.json()
                extracted_prompt = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                if extracted_prompt:
                    logger.info(f"✅ [LLM提示词提取] 成功 ({len(extracted_prompt)} 字符)")
                    logger.info(f"  📝 提取的提示词: {extracted_prompt[:200]}...")
                    return extracted_prompt
                else:
                    logger.warning("⚠️  [LLM提示词提取] LLM返回空内容")
                    return ""

        except Exception as e:
            logger.error(f"❌ [LLM提示词提取] 发生异常: {e}")
            logger.exception(e)
            return ""

    async def _enhance_prompt_with_user_input(
        self,
        user_prompt: str,
        expert_context: str = "",
        conversation_history: str = "",
        project_constraints: str = "",
        vision_analysis: Optional[str] = None,
    ) -> str:
        """
        🆕 v7.50: 为编辑环节优化用户输入的提示词
        🔥 v7.61: 添加 Vision 分析结果集成

        将用户的简短描述扩展为专业的图像生成提示词，
        同时保持与专家报告内容和对话历史的连贯性。

        Args:
            user_prompt: 用户输入的描述
            expert_context: 相关专家报告摘要
            conversation_history: 之前的对话记录
            project_constraints: 项目约束
            vision_analysis: Vision 模型分析的参考图特征（可选）

        Returns:
            优化后的英文图像生成提示词
        """
        system_prompt = """You are a professional image prompt engineer.
Enhance the user's brief description into a detailed, professional image generation prompt.

Requirements:
1. Write in English only, 80-120 words
2. Preserve the user's core intent and specific requests
3. Add professional visual details: materials, lighting, composition, atmosphere
4. Incorporate relevant context from conversation history
5. Maintain design coherence with the expert's analysis
6. End with quality descriptors

Output: Just the enhanced prompt, no explanations."""

        context_block = ""
        # 🔥 v7.61: Vision 分析优先级最高（如果有参考图）
        if vision_analysis:
            context_block += (
                f"\nReference Image Analysis (high priority, maintain these features):\n{vision_analysis[:800]}\n"
            )
        if expert_context:
            context_block += f"\nExpert Analysis Context (for reference):\n{expert_context[:800]}\n"
        if conversation_history:
            context_block += f"\nConversation History:\n{conversation_history[-500:]}\n"
        if project_constraints:
            context_block += f"\nProject Constraints:\n{project_constraints[:300]}\n"

        user_message = f"""{context_block}
User's current request:
{user_prompt}

---
Generate an enhanced, professional image prompt:"""

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json={
                        "model": self.prompt_extraction_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": 0.6,
                        "max_tokens": 250,
                    },
                )

                if response.status_code != 200:
                    logger.warning(f"⚠️ Prompt enhancement failed: {response.status_code}")
                    return user_prompt  # 失败时返回原始提示词

                result = response.json()
                enhanced = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                if enhanced and len(enhanced) > len(user_prompt):
                    logger.info(f"✅ [v7.50] 用户提示词增强成功: {len(user_prompt)} → {len(enhanced)} 字符")
                    return enhanced
                else:
                    return user_prompt

        except Exception as e:
            logger.warning(f"⚠️ Prompt enhancement error: {e}, using original")
            return user_prompt

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }

    def _enhance_prompt(
        self, prompt: str, style: Optional[str] = None, aspect_ratio: ImageAspectRatio = ImageAspectRatio.LANDSCAPE
    ) -> str:
        """
        增强提示词，添加设计领域专业描述

        Args:
            prompt: 原始提示词
            style: 风格类型 (interior/product/branding/architecture)
            aspect_ratio: 宽高比

        Returns:
            增强后的提示词
        """
        # 选择风格增强器
        style_key = style.lower() if style else "default"
        enhancer = self.DESIGN_STYLE_ENHANCERS.get(style_key, self.DESIGN_STYLE_ENHANCERS["default"])

        # 添加宽高比说明（某些模型需要）
        ratio_hint = f"aspect ratio {aspect_ratio.value}"

        # 组合最终提示词
        enhanced = f"{prompt}. {enhancer}, {ratio_hint}"

        logger.debug(f"🎨 Enhanced prompt: {enhanced[:100]}...")
        return enhanced

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: ImageAspectRatio = ImageAspectRatio.LANDSCAPE,
        style: Optional[str] = None,
        negative_prompt: Optional[str] = None,
    ) -> ImageGenerationResult:
        """
        生成图像

        Args:
            prompt: 图像描述提示词
            aspect_ratio: 宽高比
            style: 风格类型 (interior/product/branding/architecture)
            negative_prompt: 负面提示词

        Returns:
            ImageGenerationResult 包含图像 URL 或错误信息
        """
        # 验证prompt不为空
        if not prompt or not prompt.strip():
            logger.error("❌ [图像生成API] prompt不能为空")
            raise ValueError("Prompt cannot be empty")

        # 验证aspect_ratio类型
        if not isinstance(aspect_ratio, ImageAspectRatio):
            logger.error(f"❌ [图像生成API] 无效的宽高比类型: {type(aspect_ratio)}")
            raise ValueError(f"aspect_ratio must be ImageAspectRatio enum, got {type(aspect_ratio).__name__}")

        logger.info(f"🎨 [图像生成API] 开始生成图像...")
        logger.info(f"  📝 原始提示词: {prompt[:100]}...")
        logger.info(f"  📐 宽高比: {aspect_ratio.value}")
        logger.info(f"  🎭 风格: {style or 'default'}")
        logger.info(f"  🚫 负面提示词: {negative_prompt or 'None'}")

        try:
            # 增强提示词
            logger.info(f"  🔧 增强提示词...")
            enhanced_prompt = self._enhance_prompt(prompt, style, aspect_ratio)
            logger.info(f"  ✅ 增强后提示词: {enhanced_prompt[:150]}...")

            # 构建请求体 - 使用 Gemini 的 multimodal 格式
            # Gemini 图像生成通过 chat completion with responseModalities
            request_body = {
                "model": self.model,
                "messages": [{"role": "user", "content": enhanced_prompt}],
                # Gemini 特定参数 - 请求图像输出
                "modalities": ["text", "image"],  # 允许图像输出
                "max_tokens": 4096,  # 🔥 v7.60.3: 增加到4096以支持图像生成 (原1024不足，所有token被reasoning消耗)
                "temperature": 0.8,  # 图像生成需要一定创造性
            }

            # 添加负面提示词（如果支持）
            if negative_prompt:
                request_body["messages"][0]["content"] += f"\n\nDo NOT include: {negative_prompt}"
                logger.info(f"  ➕ 添加负面提示词")

            logger.info(f"  📤 调用图像生成API (model={self.model})...")
            logger.debug(f"  📋 请求体: {str(request_body)[:300]}...")

            start_time = __import__("time").time()

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=self._build_headers(), json=request_body
                )

                elapsed_time = __import__("time").time() - start_time
                logger.info(f"  ⏱️  API响应时间: {elapsed_time:.2f}秒")

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ [图像生成API] HTTP错误: {response.status_code}")
                    logger.error(f"  错误详情: {error_text[:500]}")
                    return ImageGenerationResult(
                        success=False,
                        error=f"API error {response.status_code}: {error_text[:200]}",
                        model_used=self.model,
                    )

                result = response.json()
                logger.info(f"✅ [图像生成API] 收到响应，开始解析...")
                logger.debug(f"  响应体: {str(result)[:500]}...")

                # 解析响应 - Gemini 返回的图像在 content 中
                parsed_result = self._parse_response(result, enhanced_prompt)

                if parsed_result.success:
                    logger.info(f"✅ [图像生成API] 图像生成成功")
                    logger.info(
                        f"  🔗 图像URL类型: {'data URI' if parsed_result.image_url and parsed_result.image_url.startswith('data:') else 'URL'}"
                    )
                    logger.info(f"  🎯 使用模型: {parsed_result.model_used}")
                else:
                    logger.error(f"❌ [图像生成API] 解析失败: {parsed_result.error}")

                return parsed_result

        except httpx.TimeoutException:
            logger.error(f"❌ [图像生成API] 请求超时 (timeout={self.timeout}秒)")
            return ImageGenerationResult(
                success=False, error=f"Request timeout after {self.timeout} seconds", model_used=self.model
            )
        except Exception as e:
            logger.error(f"❌ [图像生成API] 发生异常: {e}")
            logger.exception(e)
            return ImageGenerationResult(success=False, error=str(e), model_used=self.model)

    async def generate_with_vision_reference(
        self,
        user_prompt: str,
        reference_image: str,
        aspect_ratio: ImageAspectRatio = ImageAspectRatio.LANDSCAPE,
        style: Optional[str] = None,
        vision_weight: float = 0.7,
    ) -> ImageGenerationResult:
        """
        🔥 v7.61: 使用 Vision 分析参考图后生成新图像

        两阶段流程：
        1. Vision 模型分析参考图 → 提取视觉特征
        2. 将 Vision 特征 + 用户指令混合 → 生成新图像

        Args:
            user_prompt: 用户修改指令（如"保留其他，只取消办公桌"）
            reference_image: 参考图像（base64 或 URL）
            aspect_ratio: 宽高比
            style: 风格类型
            vision_weight: Vision 特征权重 (0-1)，默认 0.7

        Returns:
            ImageGenerationResult 包含生成的图像
        """
        try:
            logger.info(f"🎨 [v7.61] 开始 Vision + 生成混合流程")

            # Stage 1: Vision 分析参考图
            from .vision_service import get_vision_service

            vision_service = get_vision_service()

            logger.info("🔍 Stage 1: Vision 分析参考图...")
            vision_result = await vision_service.analyze_design_image(
                image_data=reference_image, analysis_type="comprehensive"
            )

            if not vision_result.success:
                logger.warning(f"⚠️ Vision 分析失败: {vision_result.error}")
                logger.info("➡️ 降级到纯文本生成模式")
                # 降级：不使用 Vision 特征
                return await self.generate_image(prompt=user_prompt, aspect_ratio=aspect_ratio, style=style)

            logger.info(f"✅ Vision 分析成功: {len(vision_result.features or {})} 个特征")

            # Stage 2: 混合提示词（Vision 特征 + 用户指令）
            vision_analysis_text = vision_result.analysis or ""

            # 提取结构化特征作为补充
            features = vision_result.features or {}
            if features.get("colors"):
                vision_analysis_text += f"\n主色调: {', '.join(features['colors'][:3])}"
            if features.get("styles"):
                vision_analysis_text += f"\n风格: {', '.join(features['styles'][:3])}"
            if features.get("materials"):
                vision_analysis_text += f"\n材质: {', '.join(features['materials'][:3])}"

            logger.info("🔀 Stage 2: 混合提示词（Vision + 用户指令）...")

            # 使用 _enhance_prompt_with_user_input 进行混合
            # vision_analysis 会被优先注入到 context
            enhanced_prompt = await self._enhance_prompt_with_user_input(
                user_prompt=user_prompt, vision_analysis=vision_analysis_text
            )

            logger.info("🎨 Stage 3: 生成新图像...")
            # 使用增强后的提示词生成图像
            result = await self.generate_image(prompt=enhanced_prompt, aspect_ratio=aspect_ratio, style=style)

            # 在结果中标记使用了 Vision
            if result.success:
                logger.info("✅ Vision + 生成流程完成")

            return result

        except Exception as e:
            logger.error(f"❌ Vision + 生成流程失败: {e}")
            return ImageGenerationResult(success=False, error=f"Vision generation failed: {e}", model_used=self.model)

    def _parse_response(self, response: Dict[str, Any], prompt: str) -> ImageGenerationResult:
        """
        解析 OpenRouter/Gemini 响应

        🔥 v7.38.1: OpenRouter 图像生成正确响应格式 (来自官方文档):
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "I've generated a beautiful sunset image for you.",
                    "images": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
                            }
                        }
                    ]
                }
            }],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 1500,
                "total_tokens": 1650
            }
        }
        """
        try:
            # 🔥 v7.60.5: 提取Token使用信息（后置Token追踪）
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            if total_tokens > 0:
                logger.info(
                    f"✅ [Token提取-图像生成] usage -> {total_tokens} tokens (prompt: {prompt_tokens}, completion: {completion_tokens})"
                )

            choices = response.get("choices", [])
            if not choices:
                return ImageGenerationResult(
                    success=False,
                    error="No choices in response",
                    model_used=self.model,
                    # 🔥 v7.60.5
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )

            # 🔥 v7.60.3: 检测Token耗尽情况
            finish_reason = choices[0].get("finish_reason", "")
            if finish_reason in ("length", "MAX_TOKENS"):
                logger.warning(
                    f"⚠️ Token limit reached (finish_reason={finish_reason}). Consider increasing max_tokens."
                )

            message = choices[0].get("message", {})
            content = message.get("content", "")

            # 🔥 v7.38.1: 首先检查 message.images 字段 (OpenRouter 标准响应格式)
            images = message.get("images", [])
            if images:
                for img in images:
                    if isinstance(img, dict):
                        # 格式: {"type": "image_url", "image_url": {"url": "data:..."}}
                        image_url = img.get("image_url", {}).get("url")
                        if image_url:
                            logger.info(f"✅ Image generated successfully via message.images")
                            # 🔥 v7.40.1: 优先使用传入的 prompt（实际使用的提示词），而非 API 返回的 content
                            final_prompt = prompt
                            if isinstance(content, str) and content.strip() and len(content) > len(prompt):
                                final_prompt = content  # 只有当 content 更详细时才使用
                            return ImageGenerationResult(
                                success=True,
                                image_url=image_url,
                                revised_prompt=final_prompt,
                                model_used=self.model,
                                # 🔥 v7.60.5
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                                total_tokens=total_tokens,
                            )

            # 备用方案1: 检查 content 是否为多模态数组
            if isinstance(content, list):
                image_url = None
                text_content = ""

                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "image_url":
                            image_url = item.get("image_url", {}).get("url")
                        elif item.get("type") == "text":
                            text_content = item.get("text", "")

                if image_url:
                    logger.info(f"✅ Image generated successfully via content array")
                    # 🔥 v7.40.1: 优先使用传入的 prompt
                    return ImageGenerationResult(
                        success=True,
                        image_url=image_url,
                        revised_prompt=text_content if text_content.strip() else prompt,
                        model_used=self.model,
                        # 🔥 v7.60.5
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                    )

            # 备用方案2: 纯文本响应 - 可能包含 base64 图像
            elif isinstance(content, str):
                if "data:image" in content:
                    import re

                    match = re.search(r"(data:image/[^;]+;base64,[A-Za-z0-9+/=]+)", content)
                    if match:
                        logger.info(f"✅ Image extracted from content string")
                        return ImageGenerationResult(
                            success=True,
                            image_url=match.group(1),
                            revised_prompt=prompt,  # 使用传入的详细 prompt
                            model_used=self.model,
                            # 🔥 v7.60.5
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                        )

            # 没有找到图像
            logger.warning(f"⚠️ No image in response: {str(content)[:200]}")
            return ImageGenerationResult(
                success=False,
                error="No image found in response",
                revised_prompt=prompt,  # 🔥 v7.40.1: 即使失败也保留详细 prompt
                model_used=self.model,
                # 🔥 v7.60.5
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        except Exception as e:
            logger.error(f"❌ Error parsing response: {e}")
            return ImageGenerationResult(
                success=False,
                error=f"Response parsing error: {e}",
                model_used=self.model,
                # 🔥 v7.60.5
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )

    async def generate_concept_images(
        self,
        expert_summary: str,
        project_type: str = "interior",
        num_images: int = 2,
        expert_name: str = "",
        top_constraints: str = "",
        use_llm_extraction: bool = True,
    ) -> List[ImageGenerationResult]:
        """
        基于专家分析摘要生成概念图

        🆕 v7.50: 支持 LLM 语义提取，大幅提升提示词质量

        Args:
            expert_summary: 专家分析摘要文本
            project_type: 项目类型 (interior/product/branding/architecture)
            num_images: 生成图像数量
            expert_name: 专家名称（用于 LLM 上下文）
            top_constraints: 项目顶层约束
            use_llm_extraction: 是否使用 LLM 语义提取（默认 True）

        Returns:
            ImageGenerationResult 列表
        """
        logger.info(f"📸 [概念图生成] 开始生成概念图")
        logger.info(f"  📊 参数: project_type={project_type}, num_images={num_images}, expert_name={expert_name}")
        logger.info(f"  📄 专家摘要长度: {len(expert_summary)} 字符")
        logger.info(f"  ⚙️  使用LLM提取: {use_llm_extraction}")

        prompts = []

        # 🆕 v7.50: 优先使用 LLM 语义提取
        if use_llm_extraction:
            logger.info(f"🧠 [提示词提取] 尝试使用LLM语义提取提示词...")
            llm_prompt = await self._llm_extract_visual_prompt(
                expert_content=expert_summary,
                expert_name=expert_name,
                project_type=project_type,
                top_constraints=top_constraints,
            )
            if llm_prompt:
                prompts = [llm_prompt]
                logger.info(f"✅ [提示词提取] LLM提取成功，提示词长度: {len(llm_prompt)} 字符")
                logger.debug(f"  📝 提示词内容: {llm_prompt}")
            else:
                logger.warning(f"⚠️  [提示词提取] LLM提取失败，将使用正则提取")

        # Fallback: 正则提取（如果 LLM 失败或禁用）
        if not prompts:
            logger.info(f"📐 [提示词提取] 使用正则表达式提取提示词...")
            prompts = self._extract_visual_concepts(expert_summary, project_type)
            logger.info(f"✅ [提示词提取] 正则提取完成，得到 {len(prompts)} 个提示词")

        # 限制数量
        original_count = len(prompts)
        prompts = prompts[:num_images]
        if original_count > num_images:
            logger.info(f"🔧 [提示词调整] 提示词从 {original_count} 个截断至 {num_images} 个")

        logger.info(f"🎨 [图像生成] 开始生成 {len(prompts)} 张概念图...")

        results = []
        for i, prompt in enumerate(prompts):
            logger.info(f"🖼️  [图像生成 {i+1}/{len(prompts)}] 开始生成...")
            logger.info(f"  📝 使用提示词: {prompt[:150]}...")

            try:
                result = await self.generate_image(
                    prompt=prompt, style=project_type, aspect_ratio=ImageAspectRatio.LANDSCAPE
                )

                # 🔥 v7.40.1: 如果 API 没有返回 revised_prompt，使用原始 prompt
                if result.success and not result.revised_prompt:
                    result.revised_prompt = prompt
                    logger.debug(f"  📝 使用原始 prompt 作为 revised_prompt")

                if result.success:
                    logger.info(f"✅ [图像生成 {i+1}/{len(prompts)}] 生成成功")
                    logger.info(f"  🔗 图像URL长度: {len(result.image_url) if result.image_url else 0} 字符")
                    logger.info(f"  🎯 使用模型: {result.model_used}")
                else:
                    logger.error(f"❌ [图像生成 {i+1}/{len(prompts)}] 生成失败: {result.error}")

                results.append(result)

            except Exception as e:
                logger.error(f"❌ [图像生成 {i+1}/{len(prompts)}] 发生异常: {e}")
                logger.exception(e)
                # 创建失败结果
                results.append(ImageGenerationResult(success=False, error=f"生成异常: {str(e)}", model_used=self.model))

        success_count = sum(1 for r in results if r.success)
        logger.info(f"📸 [概念图生成] 完成，成功 {success_count}/{len(results)} 张")

        return results

    def _extract_visual_concepts(self, text: str, project_type: str) -> List[str]:
        """
        🔧 v7.39.5: 从专家分析文本中智能提取可视化概念

        改进：
        1. 真正分析专家内容，提取关键设计元素
        2. 构建与专家分析相关的具体 prompt
        3. 使用中英混合 prompt 提高生成质量
        """
        import re

        # 提取专家分析中的关键设计概念
        design_concepts = []

        # 1. 提取引号中的关键词/设计理念
        quoted_terms = re.findall(r'[「""]([^「""]{2,20})[」""]', text)
        design_concepts.extend(quoted_terms[:5])

        # 2. 提取"风格/理念/概念/主题"相关描述
        style_patterns = [
            r"(?:风格|理念|概念|主题|氛围|调性)[:：]?\s*([^，。,.\n]{3,30})",
            r"([^，。\n]{2,15}(?:风格|理念|设计|空间|氛围|体验))",
            r"(?:打造|营造|呈现|展现)\s*([^，。,.\n]{5,40})",
        ]
        for pattern in style_patterns:
            matches = re.findall(pattern, text[:1000])
            design_concepts.extend(matches[:3])

        # 3. 提取材料/色彩/元素描述
        material_patterns = [
            r"(?:材料|材质|用材)[:：]?\s*([^，。,.\n]{3,30})",
            r"(?:色彩|配色|颜色)[:：]?\s*([^，。,.\n]{3,30})",
            r"([^，。\n]{2,10}(?:大理石|木|金属|玻璃|皮革|布艺|石材))",
        ]
        for pattern in material_patterns:
            matches = re.findall(pattern, text[:1000])
            design_concepts.extend(matches[:2])

        # 4. 提取空间/功能描述
        space_patterns = [
            r"([^，。\n]{3,15}(?:区域|空间|区|厅|室|台))",
            r"(?:包括|设有|设置)\s*([^，。,.\n]{5,40})",
        ]
        for pattern in space_patterns:
            matches = re.findall(pattern, text[:800])
            design_concepts.extend(matches[:3])

        # 去重并过滤太短的概念
        unique_concepts = []
        seen = set()
        for concept in design_concepts:
            concept = concept.strip()
            if concept and len(concept) >= 3 and concept not in seen:
                seen.add(concept)
                unique_concepts.append(concept)

        logger.debug(f"🎨 从专家内容提取的设计概念: {unique_concepts[:8]}")

        # 构建最终 prompt
        if unique_concepts:
            # 组合前 6 个概念
            concepts_str = ", ".join(unique_concepts[:6])

            # 根据项目类型选择风格描述
            style_desc = {
                "interior": "interior design visualization, professional architectural rendering",
                "architecture": "architectural concept rendering, photorealistic exterior view",
                "product": "product design concept, studio photography, clean background",
                "branding": "brand identity visualization, modern graphic design",
            }.get(project_type, "professional design visualization")

            # 构建完整 prompt
            prompt = f"{concepts_str}. {style_desc}, high quality, detailed"
            return [prompt]

        # 如果没提取到概念，使用文本前 200 字符作为基础
        text_preview = text[:200].replace("\n", " ").strip()
        if text_preview:
            style_desc = {
                "interior": "interior design concept",
                "architecture": "architectural visualization",
                "product": "product design rendering",
                "branding": "brand design concept",
            }.get(project_type, "design concept")

            prompt = f"Design visualization based on: {text_preview[:150]}. {style_desc}, professional quality"
            return [prompt]

        # 最终兜底
        return ["modern design concept visualization with professional rendering quality"]

    async def generate_deliverable_image(
        self,
        deliverable_metadata: dict,
        expert_analysis: str,
        session_id: str,
        project_type: str = "interior",
        aspect_ratio: str = "16:9",
        questionnaire_data: Optional[dict] = None,
        visual_references: Optional[List[Dict[str, Any]]] = None,  # 🆕 v7.155: 视觉参考
        global_style_anchor: Optional[str] = None,  # 🆕 v7.155: 全局风格锚点
    ) -> "List[ImageMetadata]":
        """
        🆕 v7.153: 重构为两阶段LLM精炼流程
        🆕 v7.155: 支持用户上传的视觉参考

        核心改进：
        1. 以交付物content(expert_analysis)为唯一信息源
        2. 第一阶段：提取视觉简报 + 生成style_anchor
        3. 第二阶段：生成结构化英文Prompt
        4. 配置驱动的角色差异化视觉生成
        5. Style Anchor确保多图一致性
        6. 🆕 v7.155: 支持用户上传的视觉参考注入

        Args:
            deliverable_metadata: 交付物元数据字典
            expert_analysis: 专家分析内容（唯一信息源，已融合问卷+需求+搜索+任务）
            session_id: 会话ID（用于文件存储路径）
            project_type: 项目类型 (interior/product/branding/architecture)
            aspect_ratio: 宽高比 (16:9, 9:16, 1:1)
            questionnaire_data: 问卷数据（仅提取profile_label作为硬性约束）
            visual_references: 用户上传的视觉参考列表
            global_style_anchor: 全局风格锚点（从所有参考图提取）

        Returns:
            List[ImageMetadata]: 生成的图片列表
        """
        from datetime import datetime

        from ..models.image_metadata import ImageMetadata

        deliverable_name = deliverable_metadata.get("name", "设计交付物")
        owner_role = deliverable_metadata.get("owner_role", "unknown")
        deliverable_id = deliverable_metadata.get("id", "unknown")

        logger.info(f"🎨 [v7.153] 为交付物生成概念图: {deliverable_name}")
        logger.info(f"  📋 角色: {owner_role}, 交付物ID: {deliverable_id}")

        # 🆕 v7.155: 记录视觉参考信息
        if visual_references:
            logger.info(f"  🖼️ [v7.155] 使用 {len(visual_references)} 个视觉参考")
        if global_style_anchor:
            logger.info(f"  🎨 [v7.155] 全局风格锚点: {global_style_anchor[:50]}...")

        # 读取 concept_image_config 配置
        concept_image_config = deliverable_metadata.get("concept_image_config", {})
        image_count = concept_image_config.get("count", 1)
        logger.info(f"  🖼️ 计划生成 {image_count} 张概念图")

        try:
            # ================================================================
            # 🆕 v7.153 核心改进：两阶段LLM精炼
            # ================================================================

            # 提取风格标签作为硬性约束（唯一从questionnaire_data提取的信息）
            profile_label = ""
            if questionnaire_data:
                profile_label = questionnaire_data.get("profile_label", "")
                logger.info(f"  🎨 风格标签（硬性约束）: {profile_label or '未指定'}")

            # 标准化角色ID
            role_id = owner_role
            if "-" in owner_role:
                role_id = f"V{owner_role.split('-')[0]}"

            # 加载角色配置
            role_config = get_role_visual_identity(role_id)
            # 🆕 v7.154: 使用项目类型感知的视觉类型
            actual_visual_type = get_role_visual_type_for_project(role_id, project_type)
            logger.info(f"  📊 角色视觉类型: {actual_visual_type} (项目类型: {project_type})")

            # ================================================================
            # 第一阶段：从交付物content提取视觉简报 + style_anchor
            # 🆕 v7.155: 注入视觉参考
            # ================================================================
            logger.info(f"  🔍 [第一阶段] 提取视觉简报...")

            visual_brief, style_anchor = await self._extract_visual_brief(
                deliverable_content=expert_analysis,
                role_id=role_id,
                profile_label=profile_label,
                project_type=project_type,  # 🆕 v7.154: 传入项目类型
                visual_references=visual_references,  # 🆕 v7.155: 传入视觉参考
            )

            if not visual_brief:
                logger.warning("  ⚠️ 视觉简报提取失败，使用原始内容")
                visual_brief = expert_analysis[:800]
                style_anchor = ", ".join(role_config.get("style_preferences", [])[:3])

            # 🆕 v7.155: 如果有全局风格锚点，优先合并
            if global_style_anchor:
                style_anchor = f"{global_style_anchor}, {style_anchor}"
                logger.info(f"  🎨 [v7.155] 合并全局风格锚点")

            logger.info(f"  ✅ 视觉简报: {len(visual_brief)} 字符")
            logger.info(f"  🎨 Style Anchor: {style_anchor[:60]}...")

            # ================================================================
            # 第二阶段：生成结构化英文Prompt
            # ================================================================
            logger.info(f"  🔍 [第二阶段] 生成结构化Prompt...")

            visual_prompt = await self._generate_structured_prompt(
                visual_brief=visual_brief,
                style_anchor=style_anchor,
                role_id=role_id,
                deliverable_name=deliverable_name,
                project_type=project_type,  # 🆕 v7.154: 传入项目类型
            )

            # 校验Prompt质量
            global_config = get_global_config()
            min_length = global_config.get("final_prompt_min_length", 80)

            if len(visual_prompt) < min_length:
                logger.warning(f"  ⚠️ Prompt过短 ({len(visual_prompt)} < {min_length})，使用降级Prompt")
                visual_type_config = get_visual_type_config(role_config.get("visual_type", "photorealistic_rendering"))
                visual_prompt = (
                    f"{style_anchor}, {deliverable_name}, {visual_type_config.get('quality_suffix', 'high quality')}"
                )

            logger.info(f"  ✅ 最终Prompt: {visual_prompt[:100]}...")
            logger.debug(f"  📝 完整Prompt ({len(visual_prompt)} chars): {visual_prompt}")

            # ================================================================
            # 第三阶段：循环生成多张图片（使用相同Prompt + Style Anchor）
            # ================================================================
            from ..services.image_storage_manager import ImageStorageManager

            generated_images: List[ImageMetadata] = []
            failed_count = 0

            for attempt in range(image_count):
                try:
                    logger.info(f"  🖼️ [图片 {attempt + 1}/{image_count}] 开始生成...")

                    # 多图生成时，追加视角差异（可选）
                    current_prompt = visual_prompt
                    if image_count > 1 and attempt > 0:
                        # 为后续图片添加视角变化
                        view_variations = ["detail view", "wide angle view", "atmospheric view"]
                        variation = view_variations[attempt % len(view_variations)]
                        current_prompt = f"{visual_prompt}, {variation}"
                        logger.debug(f"    📐 添加视角变化: {variation}")

                    # 调用图片生成API
                    generation_result = await self.generate_image(
                        prompt=current_prompt, aspect_ratio=ImageAspectRatio(aspect_ratio)
                    )

                    if not generation_result.success:
                        logger.error(f"    ❌ 生成失败: {generation_result.error}")
                        failed_count += 1
                        continue

                    logger.info("    ✅ 图片生成成功！")

                    # 保存到文件系统
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"{deliverable_id}_{project_type}_{timestamp}_v{attempt + 1}.png"

                    saved_metadata = await ImageStorageManager.save_image(
                        base64_data=generation_result.image_url,
                        session_id=session_id,
                        deliverable_id=deliverable_id,
                        owner_role=owner_role,
                        filename=filename,
                        visual_prompt=current_prompt,
                        aspect_ratio=aspect_ratio,
                    )

                    metadata = ImageMetadata(**saved_metadata)
                    generated_images.append(metadata)
                    logger.info(f"    💾 已保存: {filename}")

                except Exception as img_error:
                    logger.error(f"    ❌ [图片 {attempt + 1}] 生成失败: {img_error}")
                    logger.exception(img_error)
                    failed_count += 1

            # 处理生成结果
            if not generated_images:
                logger.error(f"  ❌ 全部 {image_count} 张图片生成失败")
                raise Exception(f"全部 {image_count} 张图片生成失败")

            if failed_count > 0:
                logger.warning(f"  ⚠️ 生成 {len(generated_images)}/{image_count} 张图片（{failed_count} 张失败）")
            else:
                logger.info(f"✅ [v7.153] 成功生成全部 {len(generated_images)} 张概念图")

            return generated_images

        except Exception as e:
            logger.error(f"❌ [v7.153] 生成交付物概念图失败: {e}")
            logger.exception(e)
            raise

    async def edit_image_with_mask(
        self,
        original_image: str,
        mask_image: str,
        prompt: str,
        aspect_ratio: Optional[ImageAspectRatio] = None,
        style: Optional[str] = None,
        inpainting_service=None,
    ) -> ImageGenerationResult:
        """
        🔥 v7.62: 使用 Mask 编辑图像（双模式架构）

        模式选择逻辑：
        - 有 mask_image 且 inpainting_service 可用 → Inpainting模式（Option D）
        - 无 mask 或 Inpainting 不可用 → 回退到 Vision+生成（Option C）

        Args:
            original_image: 原始图像 Base64
            mask_image: Mask 图像 Base64（可选）
            prompt: 编辑提示词
            aspect_ratio: 输出宽高比
            style: 风格提示
            inpainting_service: InpaintingService 实例（可选）

        Returns:
            ImageGenerationResult 对象
        """
        logger.info("🎨 [v7.62 Dual-Mode] 接收图像处理请求")

        # 1. 检查是否有 Mask（决定模式）
        if mask_image and inpainting_service and inpainting_service.is_available():
            logger.info("✅ [Inpainting Mode] 使用 DALL-E 2 Edit API（Option D）")

            try:
                # 调用 Inpainting 服务
                inpainting_result = await inpainting_service.edit_image_with_mask(
                    original_image=original_image,
                    mask_image=mask_image,
                    prompt=prompt,
                    size="1024x1024",  # 固定使用最高质量
                    n=1,
                )

                if inpainting_result.success:
                    logger.info("✅ [Inpainting Mode] 图像编辑成功")
                    return ImageGenerationResult(
                        success=True,
                        image_url=inpainting_result.edited_image_url,
                        revised_prompt=inpainting_result.original_prompt,
                        model_used=inpainting_result.model_used or "dall-e-2-edit",
                    )
                else:
                    # Inpainting 失败，记录错误并回退
                    logger.warning(f"⚠️ [Inpainting Mode] 失败: {inpainting_result.error}")
                    logger.warning("🔄 回退到 Vision+生成 模式（Option C）")

            except Exception as e:
                logger.error(f"❌ [Inpainting Mode] 异常: {e}")
                logger.warning("🔄 回退到 Vision+生成 模式（Option C）")

        # 2. 回退到 Vision+生成 模式（Option C）
        logger.info("✅ [Generation Mode] 使用 Vision+生成（Option C）")

        # 如果有参考图像，使用 Vision 分析
        if original_image:
            result = await self.generate_with_vision_reference(
                user_prompt=prompt,
                reference_image=original_image,
                aspect_ratio=aspect_ratio or ImageAspectRatio.LANDSCAPE,
                style=style or "interior",
                vision_weight=0.7,  # Vision 特征权重 70%
            )
        else:
            # 无参考图像，直接生成
            result = await self.generate_image(
                prompt=prompt, aspect_ratio=aspect_ratio or ImageAspectRatio.LANDSCAPE, style=style
            )

        return result


# 便捷函数
async def generate_concept_image(prompt: str, style: str = "interior") -> ImageGenerationResult:
    """
    便捷函数：快速生成概念图

    Example:
        result = await generate_concept_image("现代简约风格客厅")
        if result.success:
            print(result.image_url)
    """
    generator = ImageGeneratorService()
    return await generator.generate_image(prompt=prompt, style=style)
