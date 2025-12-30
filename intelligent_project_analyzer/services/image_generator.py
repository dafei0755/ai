"""
图像生成服务 - Gemini Nano Banana Pro 集成

通过 OpenRouter 调用 Gemini 2.5 Flash 的图像生成能力。

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
import base64
import httpx
import json
from typing import Optional, Dict, Any, List
from loguru import logger
from pydantic import BaseModel, Field
from enum import Enum


class ImageAspectRatio(str, Enum):
    """支持的图像宽高比"""
    SQUARE = "1:1"          # 正方形，社交媒体
    LANDSCAPE = "16:9"      # 横向，演示文稿
    PORTRAIT = "9:16"       # 纵向，手机展示
    WIDE = "4:3"            # 传统宽屏
    ULTRAWIDE = "21:9"      # 超宽屏


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
    model_used: Optional[str] = Field(default=None, description="实际使用的模型")    # 🔥 v7.60.5: Token追踪字段（后置Token追踪）
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
        "default": "professional design concept, high quality, detailed"
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
            "PROMPT_EXTRACTION_MODEL", 
            "openai/gpt-4o-mini"  # 默认使用 gpt-4o-mini，成本低且速度快
        )
        
        logger.info(f"🎨 ImageGeneratorService initialized: model={self.model}")
    
    async def _llm_extract_visual_prompt(
        self,
        expert_content: str,
        expert_name: str = "",
        project_type: str = "interior",
        top_constraints: str = ""
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
        # 限制输入长度以控制成本
        content_preview = expert_content[:2500] if len(expert_content) > 2500 else expert_content
        
        # 项目类型到场景描述的映射
        type_context = {
            "interior": "interior design / residential space",
            "architecture": "architectural / building exterior",
            "product": "product design / industrial design",
            "branding": "brand identity / visual design",
        }.get(project_type, "design concept")
        
        system_prompt = """You are a professional image prompt engineer specializing in design visualization.

Your task is to extract visual elements from design analysis reports and create high-quality prompts for AI image generation (like Midjourney, DALL-E, Gemini).

Output Requirements:
1. Write in English only
2. 100-150 words, no more
3. Focus on VISUAL elements: materials, colors, lighting, atmosphere, spatial relationships
4. Include specific design details that make the concept unique
5. Use professional architectural/interior photography terminology
6. End with quality descriptors like "professional rendering, photorealistic, high detail"

Do NOT include:
- Abstract concepts or emotions that can't be visualized
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
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json={
                        "model": self.prompt_extraction_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 300,
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ LLM prompt extraction failed: {response.status_code}")
                    return ""
                
                result = response.json()
                extracted_prompt = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                
                if extracted_prompt:
                    logger.info(f"✅ [v7.50] LLM 提取提示词成功 ({len(extracted_prompt)} 字符)")
                    logger.debug(f"📝 提取的提示词: {extracted_prompt[:200]}...")
                    return extracted_prompt
                else:
                    logger.warning("⚠️ LLM 返回空提示词")
                    return ""
                    
        except Exception as e:
            logger.warning(f"⚠️ LLM prompt extraction error: {e}")
            return ""
    
    async def _enhance_prompt_with_user_input(
        self,
        user_prompt: str,
        expert_context: str = "",
        conversation_history: str = "",
        project_constraints: str = "",
        vision_analysis: Optional[str] = None
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
            context_block += f"\nReference Image Analysis (high priority, maintain these features):\n{vision_analysis[:800]}\n"
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
                            {"role": "user", "content": user_message}
                        ],
                        "temperature": 0.6,
                        "max_tokens": 250,
                    }
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
        self, 
        prompt: str, 
        style: Optional[str] = None,
        aspect_ratio: ImageAspectRatio = ImageAspectRatio.LANDSCAPE
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
        try:
            # 增强提示词
            enhanced_prompt = self._enhance_prompt(prompt, style, aspect_ratio)
            
            # 构建请求体 - 使用 Gemini 的 multimodal 格式
            # Gemini 图像生成通过 chat completion with responseModalities
            request_body = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ],
                # Gemini 特定参数 - 请求图像输出
                "modalities": ["text", "image"],  # 允许图像输出
                "max_tokens": 4096,  # 🔥 v7.60.3: 增加到4096以支持图像生成 (原1024不足，所有token被reasoning消耗)
                "temperature": 0.8,  # 图像生成需要一定创造性
            }
            
            # 添加负面提示词（如果支持）
            if negative_prompt:
                request_body["messages"][0]["content"] += f"\n\nDo NOT include: {negative_prompt}"
            
            logger.info(f"🎨 Generating image with {self.model}...")
            logger.debug(f"📤 Request: {request_body}")
            
            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json=request_body
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Image generation failed: {response.status_code} - {error_text}")
                    return ImageGenerationResult(
                        success=False,
                        error=f"API error {response.status_code}: {error_text[:200]}",
                        model_used=self.model
                    )
                
                result = response.json()
                logger.debug(f"📥 Response: {str(result)[:500]}...")
                
                # 解析响应 - Gemini 返回的图像在 content 中
                return self._parse_response(result, enhanced_prompt)
                
        except httpx.TimeoutException:
            logger.error(f"❌ Image generation timeout after {self.timeout}s")
            return ImageGenerationResult(
                success=False,
                error=f"Request timeout after {self.timeout} seconds",
                model_used=self.model
            )
        except Exception as e:
            logger.error(f"❌ Image generation error: {e}")
            return ImageGenerationResult(
                success=False,
                error=str(e),
                model_used=self.model
            )
    
    async def generate_with_vision_reference(
        self,
        user_prompt: str,
        reference_image: str,
        aspect_ratio: ImageAspectRatio = ImageAspectRatio.LANDSCAPE,
        style: Optional[str] = None,
        vision_weight: float = 0.7
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
                image_data=reference_image,
                analysis_type="comprehensive"
            )
            
            if not vision_result.success:
                logger.warning(f"⚠️ Vision 分析失败: {vision_result.error}")
                logger.info("➡️ 降级到纯文本生成模式")
                # 降级：不使用 Vision 特征
                return await self.generate_image(
                    prompt=user_prompt,
                    aspect_ratio=aspect_ratio,
                    style=style
                )
            
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
                user_prompt=user_prompt,
                vision_analysis=vision_analysis_text
            )
            
            logger.info("🎨 Stage 3: 生成新图像...")
            # 使用增强后的提示词生成图像
            result = await self.generate_image(
                prompt=enhanced_prompt,
                aspect_ratio=aspect_ratio,
                style=style
            )
            
            # 在结果中标记使用了 Vision
            if result.success:
                logger.info("✅ Vision + 生成流程完成")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Vision + 生成流程失败: {e}")
            return ImageGenerationResult(
                success=False,
                error=f"Vision generation failed: {e}",
                model_used=self.model
            )
    
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
                logger.info(f"✅ [Token提取-图像生成] usage -> {total_tokens} tokens (prompt: {prompt_tokens}, completion: {completion_tokens})")
            
            choices = response.get("choices", [])
            if not choices:
                return ImageGenerationResult(
                    success=False,
                    error="No choices in response",
                    model_used=self.model,
                    # 🔥 v7.60.5
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
            
            # 🔥 v7.60.3: 检测Token耗尽情况
            finish_reason = choices[0].get("finish_reason", "")
            if finish_reason in ("length", "MAX_TOKENS"):
                logger.warning(f"⚠️ Token limit reached (finish_reason={finish_reason}). Consider increasing max_tokens.")
            
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
                                total_tokens=total_tokens
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
                        total_tokens=total_tokens
                    )
            
            # 备用方案2: 纯文本响应 - 可能包含 base64 图像
            elif isinstance(content, str):
                if "data:image" in content:
                    import re
                    match = re.search(r'(data:image/[^;]+;base64,[A-Za-z0-9+/=]+)', content)
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
                            total_tokens=total_tokens
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
                total_tokens=total_tokens
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
                total_tokens=0
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
        prompts = []
        
        # 🆕 v7.50: 优先使用 LLM 语义提取
        if use_llm_extraction:
            llm_prompt = await self._llm_extract_visual_prompt(
                expert_content=expert_summary,
                expert_name=expert_name,
                project_type=project_type,
                top_constraints=top_constraints
            )
            if llm_prompt:
                prompts = [llm_prompt]
                logger.info(f"🧠 [v7.50] 使用 LLM 语义提取的提示词")
        
        # Fallback: 正则提取（如果 LLM 失败或禁用）
        if not prompts:
            prompts = self._extract_visual_concepts(expert_summary, project_type)
            logger.info(f"📐 [v7.50] Fallback 到正则提取的提示词")
        
        # 限制数量
        prompts = prompts[:num_images]
        
        results = []
        for i, prompt in enumerate(prompts):
            logger.info(f"🎨 Generating concept image {i+1}/{len(prompts)}...")
            logger.info(f"📝 使用提示词: {prompt[:100]}...")
            result = await self.generate_image(
                prompt=prompt,
                style=project_type,
                aspect_ratio=ImageAspectRatio.LANDSCAPE
            )
            # 🔥 v7.40.1: 如果 API 没有返回 revised_prompt，使用原始 prompt
            if result.success and not result.revised_prompt:
                result.revised_prompt = prompt
                logger.debug(f"📝 使用原始 prompt 作为 revised_prompt")
            results.append(result)
        
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
            r'(?:风格|理念|概念|主题|氛围|调性)[:：]?\s*([^，。,.\n]{3,30})',
            r'([^，。\n]{2,15}(?:风格|理念|设计|空间|氛围|体验))',
            r'(?:打造|营造|呈现|展现)\s*([^，。,.\n]{5,40})',
        ]
        for pattern in style_patterns:
            matches = re.findall(pattern, text[:1000])
            design_concepts.extend(matches[:3])
        
        # 3. 提取材料/色彩/元素描述
        material_patterns = [
            r'(?:材料|材质|用材)[:：]?\s*([^，。,.\n]{3,30})',
            r'(?:色彩|配色|颜色)[:：]?\s*([^，。,.\n]{3,30})',
            r'([^，。\n]{2,10}(?:大理石|木|金属|玻璃|皮革|布艺|石材))',
        ]
        for pattern in material_patterns:
            matches = re.findall(pattern, text[:1000])
            design_concepts.extend(matches[:2])
        
        # 4. 提取空间/功能描述
        space_patterns = [
            r'([^，。\n]{3,15}(?:区域|空间|区|厅|室|台))',
            r'(?:包括|设有|设置)\s*([^，。,.\n]{5,40})',
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
        text_preview = text[:200].replace('\n', ' ').strip()
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
        aspect_ratio: str = "16:9"
    ):
        """
        🆕 v7.108: 为交付物生成精准的概念图（注入约束）

        与现有的generate_concept_images不同，本方法：
        1. 基于具体交付物的元数据（keywords, constraints）
        2. 注入交付物约束到Prompt中
        3. 返回ImageMetadata对象（支持文件存储）

        Args:
            deliverable_metadata: 交付物元数据字典
                {
                    "id": "2-1_1_143022_abc",
                    "name": "空间功能分区方案",
                    "keywords": ["现代", "简约"],
                    "constraints": {
                        "must_include": ["自然光", "木质元素"],
                        "style_preferences": "professional rendering"
                    },
                    "owner_role": "2-1"
                }
            expert_analysis: 专家分析内容（摘要）
            session_id: 会话ID（用于文件存储路径）
            project_type: 项目类型 (interior/product/branding/architecture)
            aspect_ratio: 宽高比 (16:9, 9:16, 1:1)

        Returns:
            ImageMetadata对象（包含文件路径和URL）
        """
        from ..models.image_metadata import ImageMetadata
        from datetime import datetime

        logger.info(f"🎨 [v7.108] 为交付物生成概念图: {deliverable_metadata.get('name', 'Unknown')}")

        try:
            # 1. 构建增强Prompt（注入交付物约束）
            deliverable_name = deliverable_metadata.get("name", "设计交付物")
            keywords = deliverable_metadata.get("keywords", [])
            constraints = deliverable_metadata.get("constraints", {})

            # 中文提示词（给LLM语义提取用）
            enhanced_prompt = f"""
设计可视化需求：{deliverable_name}

【交付物核心关键词】
{', '.join(keywords) if keywords else '现代设计'}

【必须包含的设计元素】
{', '.join(constraints.get('must_include', [])) if constraints.get('must_include') else '无特殊要求'}

【风格偏好】
{constraints.get('style_preferences', 'professional design rendering')}

【专家分析摘要】
{expert_analysis[:500] if expert_analysis else '专业设计分析'}

请基于以上交付物要求和专家分析，提取视觉化提示词。
"""

            logger.debug(f"  📝 构建的增强Prompt:\n{enhanced_prompt[:200]}...")

            # 2. 使用现有的LLM语义提取方法
            logger.info("  🔍 调用LLM提取视觉Prompt...")
            visual_prompts = await self._llm_extract_visual_prompt(
                enhanced_prompt,
                project_type
            )

            if not visual_prompts:
                logger.warning("  ⚠️ LLM提取失败，使用基础Prompt")
                visual_prompt = f"{deliverable_name}, {', '.join(keywords)}, professional rendering"
            else:
                visual_prompt = visual_prompts[0]

            logger.info(f"  ✅ 提取的视觉Prompt: {visual_prompt[:100]}...")

            # 3. 生成图片
            logger.info(f"  🖼️ 调用图片生成API (宽高比: {aspect_ratio})...")
            generation_result = await self.generate_image(
                prompt=visual_prompt,
                aspect_ratio=ImageAspectRatio(aspect_ratio),
                num_outputs=1
            )

            if not generation_result.success:
                logger.error(f"  ❌ 图片生成失败: {generation_result.error}")
                raise Exception(f"图片生成失败: {generation_result.error}")

            logger.info("  ✅ 图片生成成功！")

            # 4. 保存到文件系统（Phase 3新增）
            from ..services.image_storage_manager import ImageStorageManager

            deliverable_id = deliverable_metadata.get("id", "unknown")
            owner_role = deliverable_metadata.get("owner_role", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{deliverable_id}_{project_type}_{timestamp}.png"

            # 保存到文件系统
            saved_metadata = await ImageStorageManager.save_image(
                base64_data=generation_result.image_url,
                session_id=session_id,
                deliverable_id=deliverable_id,
                owner_role=owner_role,
                filename=filename,
                visual_prompt=visual_prompt,
                aspect_ratio=aspect_ratio
            )

            # 创建ImageMetadata对象（不含Base64）
            from ..models.image_metadata import ImageMetadata
            metadata = ImageMetadata(**saved_metadata)

            logger.info(f"✅ [v7.108] 概念图已保存: {filename}")
            return metadata

        except Exception as e:
            logger.error(f"❌ [v7.108] 生成交付物概念图失败: {e}")
            logger.exception(e)
            # 返回None或抛出异常由调用方处理
            raise

    async def edit_image_with_mask(
        self,
        original_image: str,
        mask_image: str,
        prompt: str,
        aspect_ratio: Optional[ImageAspectRatio] = None,
        style: Optional[str] = None,
        inpainting_service = None
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
                    n=1
                )
                
                if inpainting_result.success:
                    logger.info("✅ [Inpainting Mode] 图像编辑成功")
                    return ImageGenerationResult(
                        success=True,
                        image_url=inpainting_result.edited_image_url,
                        revised_prompt=inpainting_result.original_prompt,
                        model_used=inpainting_result.model_used or "dall-e-2-edit"
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
                vision_weight=0.7  # Vision 特征权重 70%
            )
        else:
            # 无参考图像，直接生成
            result = await self.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio or ImageAspectRatio.LANDSCAPE,
                style=style
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
