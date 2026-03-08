"""
图片生成器 图片生成 Mixin
由 scripts/refactor/_split_mt20_image_generator.py 自动生成 (MT-20)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class ImageGenerateMixin:
    """Mixin — 图片生成器 图片生成 Mixin"""
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: "ImageAspectRatio | None" = None,
        style: str | None = None,
        negative_prompt: str | None = None,
    ) -> "ImageGenerationResult":
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
        # P1-B: 延迟导入，避免 Mixin 文件在类定义时求值未导入的 ImageAspectRatio
        from intelligent_project_analyzer.services.image_generator import ImageAspectRatio, ImageGenerationResult  # noqa: F401
        if aspect_ratio is None:
            aspect_ratio = ImageAspectRatio.LANDSCAPE
        # 验证prompt不为空
        if not prompt or not prompt.strip():
            logger.error(" [图像生成API] prompt不能为空")
            raise ValueError("Prompt cannot be empty")

        # 验证aspect_ratio类型
        if not isinstance(aspect_ratio, ImageAspectRatio):
            logger.error(f" [图像生成API] 无效的宽高比类型: {type(aspect_ratio)}")
            raise ValueError(f"aspect_ratio must be ImageAspectRatio enum, got {type(aspect_ratio).__name__}")

        logger.info(" [图像生成API] 开始生成图像...")
        logger.info(f"   原始提示词: {prompt[:100]}...")
        logger.info(f"   宽高比: {aspect_ratio.value}")
        logger.info(f"   风格: {style or 'default'}")
        logger.info(f"   负面提示词: {negative_prompt or 'None'}")

        try:
            # 增强提示词
            logger.info("   增强提示词...")
            enhanced_prompt = self._enhance_prompt(prompt, style, aspect_ratio)
            logger.info(f"   增强后提示词: {enhanced_prompt[:150]}...")

            # 构建请求体 - 使用 Gemini 的 multimodal 格式
            # Gemini 图像生成通过 chat completion with responseModalities
            request_body = {
                "model": self.model,
                "messages": [{"role": "user", "content": enhanced_prompt}],
                # Gemini 特定参数 - 请求图像输出
                "modalities": ["text", "image"],  # 允许图像输出
                "max_tokens": 4096,  #  v7.60.3: 增加到4096以支持图像生成 (原1024不足，所有token被reasoning消耗)
                "temperature": 0.8,  # 图像生成需要一定创造性
            }

            # 添加负面提示词（如果支持）
            if negative_prompt:
                request_body["messages"][0]["content"] += f"\n\nDo NOT include: {negative_prompt}"
                logger.info("   添加负面提示词")

            logger.info(f"   调用图像生成API (model={self.model})...")
            logger.debug(f"   请求体: {str(request_body)[:300]}...")

            start_time = __import__("time").time()

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=self._build_headers(), json=request_body
                )

                elapsed_time = __import__("time").time() - start_time
                logger.info(f"  ️  API响应时间: {elapsed_time:.2f}秒")

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f" [图像生成API] HTTP错误: {response.status_code}")
                    logger.error(f"  错误详情: {error_text[:500]}")
                    return ImageGenerationResult(
                        success=False,
                        error=f"API error {response.status_code}: {error_text[:200]}",
                        model_used=self.model,
                    )

                result = response.json()
                logger.info(" [图像生成API] 收到响应，开始解析...")
                logger.debug(f"  响应体: {str(result)[:500]}...")

                # 解析响应 - Gemini 返回的图像在 content 中
                parsed_result = self._parse_response(result, enhanced_prompt)

                if parsed_result.success:
                    logger.info(" [图像生成API] 图像生成成功")
                    logger.info(
                        f"   图像URL类型: {'data URI' if parsed_result.image_url and parsed_result.image_url.startswith('data:') else 'URL'}"
                    )
                    logger.info(f"   使用模型: {parsed_result.model_used}")
                else:
                    logger.error(f" [图像生成API] 解析失败: {parsed_result.error}")

                return parsed_result

        except httpx.TimeoutException:
            logger.error(f" [图像生成API] 请求超时 (timeout={self.timeout}秒)")
            return ImageGenerationResult(
                success=False, error=f"Request timeout after {self.timeout} seconds", model_used=self.model
            )
        except Exception as e:
            logger.error(f" [图像生成API] 发生异常: {e}")
            logger.exception(e)
            return ImageGenerationResult(success=False, error=str(e), model_used=self.model)

    async def generate_with_vision_reference(
        self,
        user_prompt: str,
        reference_image: str,
        aspect_ratio: "ImageAspectRatio | None" = None,
        style: str | None = None,
        vision_weight: float = 0.7,
    ) -> "ImageGenerationResult":
        """
         v7.61: 使用 Vision 分析参考图后生成新图像

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
            # P1-B: 延迟导入，aspect_ratio 默认值不能在类定义时引用未导入的枚举
            from intelligent_project_analyzer.services.image_generator import ImageAspectRatio, ImageGenerationResult  # noqa: F401
            if aspect_ratio is None:
                aspect_ratio = ImageAspectRatio.LANDSCAPE
            logger.info(" [v7.61] 开始 Vision + 生成混合流程")

            # Stage 1: Vision 分析参考图
            from .vision_service import get_vision_service

            vision_service = get_vision_service()

            logger.info(" Stage 1: Vision 分析参考图...")
            vision_result = await vision_service.analyze_design_image(
                image_data=reference_image, analysis_type="comprehensive"
            )

            if not vision_result.success:
                logger.warning(f"️ Vision 分析失败: {vision_result.error}")
                logger.info("️ 降级到纯文本生成模式")
                # 降级：不使用 Vision 特征
                return await self.generate_image(prompt=user_prompt, aspect_ratio=aspect_ratio, style=style)

            logger.info(f" Vision 分析成功: {len(vision_result.features or {})} 个特征")

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

            logger.info(" Stage 2: 混合提示词（Vision + 用户指令）...")

            # 使用 _enhance_prompt_with_user_input 进行混合
            # vision_analysis 会被优先注入到 context
            enhanced_prompt = await self._enhance_prompt_with_user_input(
                user_prompt=user_prompt, vision_analysis=vision_analysis_text
            )

            logger.info(" Stage 3: 生成新图像...")
            # 使用增强后的提示词生成图像
            result = await self.generate_image(prompt=enhanced_prompt, aspect_ratio=aspect_ratio, style=style)

            # 在结果中标记使用了 Vision
            if result.success:
                logger.info(" Vision + 生成流程完成")

            return result

        except Exception as e:
            logger.error(f" Vision + 生成流程失败: {e}")
            return ImageGenerationResult(success=False, error=f"Vision generation failed: {e}", model_used=self.model)

    def _parse_response(self, response: Dict[str, Any], prompt: str) -> ImageGenerationResult:
        """
        解析 OpenRouter/Gemini 响应

         v7.38.1: OpenRouter 图像生成正确响应格式 (来自官方文档):
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
            #  v7.60.5: 提取Token使用信息（后置Token追踪）
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            if total_tokens > 0:
                logger.info(
                    f" [Token提取-图像生成] usage -> {total_tokens} tokens (prompt: {prompt_tokens}, completion: {completion_tokens})"
                )

            choices = response.get("choices", [])
            if not choices:
                return ImageGenerationResult(
                    success=False,
                    error="No choices in response",
                    model_used=self.model,
                    #  v7.60.5
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )

            #  v7.60.3: 检测Token耗尽情况
            finish_reason = choices[0].get("finish_reason", "")
            if finish_reason in ("length", "MAX_TOKENS"):
                logger.warning(
                    f"️ Token limit reached (finish_reason={finish_reason}). Consider increasing max_tokens."
                )

            message = choices[0].get("message", {})
            content = message.get("content", "")

            #  v7.38.1: 首先检查 message.images 字段 (OpenRouter 标准响应格式)
            images = message.get("images", [])
            if images:
                for img in images:
                    if isinstance(img, dict):
                        # 格式: {"type": "image_url", "image_url": {"url": "data:..."}}
                        image_url = img.get("image_url", {}).get("url")
                        if image_url:
                            logger.info(" Image generated successfully via message.images")
                            #  v7.40.1: 优先使用传入的 prompt（实际使用的提示词），而非 API 返回的 content
                            final_prompt = prompt
                            if isinstance(content, str) and content.strip() and len(content) > len(prompt):
                                final_prompt = content  # 只有当 content 更详细时才使用
                            return ImageGenerationResult(
                                success=True,
                                image_url=image_url,
                                revised_prompt=final_prompt,
                                model_used=self.model,
                                #  v7.60.5
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
                    logger.info(" Image generated successfully via content array")
                    #  v7.40.1: 优先使用传入的 prompt
                    return ImageGenerationResult(
                        success=True,
                        image_url=image_url,
                        revised_prompt=text_content if text_content.strip() else prompt,
                        model_used=self.model,
                        #  v7.60.5
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
                        logger.info(" Image extracted from content string")
                        return ImageGenerationResult(
                            success=True,
                            image_url=match.group(1),
                            revised_prompt=prompt,  # 使用传入的详细 prompt
                            model_used=self.model,
                            #  v7.60.5
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                        )

            # 没有找到图像
            logger.warning(f"️ No image in response: {str(content)[:200]}")
            return ImageGenerationResult(
                success=False,
                error="No image found in response",
                revised_prompt=prompt,  #  v7.40.1: 即使失败也保留详细 prompt
                model_used=self.model,
                #  v7.60.5
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        except Exception as e:
            logger.error(f" Error parsing response: {e}")
            return ImageGenerationResult(
                success=False,
                error=f"Response parsing error: {e}",
                model_used=self.model,
                #  v7.60.5
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

         v7.50: 支持 LLM 语义提取，大幅提升提示词质量

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
        logger.info(" [概念图生成] 开始生成概念图")
        logger.info(f"   参数: project_type={project_type}, num_images={num_images}, expert_name={expert_name}")
        logger.info(f"   专家摘要长度: {len(expert_summary)} 字符")
        logger.info(f"  ️  使用LLM提取: {use_llm_extraction}")

        prompts = []

        #  v7.50: 优先使用 LLM 语义提取
        if use_llm_extraction:
            logger.info(" [提示词提取] 尝试使用LLM语义提取提示词...")
            llm_prompt = await self._llm_extract_visual_prompt(
                expert_content=expert_summary,
                expert_name=expert_name,
                project_type=project_type,
                top_constraints=top_constraints,
            )
            if llm_prompt:
                prompts = [llm_prompt]
                logger.info(f" [提示词提取] LLM提取成功，提示词长度: {len(llm_prompt)} 字符")
                logger.debug(f"   提示词内容: {llm_prompt}")
            else:
                logger.warning("️  [提示词提取] LLM提取失败，将使用正则提取")

        # Fallback: 正则提取（如果 LLM 失败或禁用）
        if not prompts:
            logger.info(" [提示词提取] 使用正则表达式提取提示词...")
            prompts = self._extract_visual_concepts(expert_summary, project_type)
            logger.info(f" [提示词提取] 正则提取完成，得到 {len(prompts)} 个提示词")

        # 限制数量
        original_count = len(prompts)
        prompts = prompts[:num_images]
        if original_count > num_images:
            logger.info(f" [提示词调整] 提示词从 {original_count} 个截断至 {num_images} 个")

        logger.info(f" [图像生成] 开始生成 {len(prompts)} 张概念图...")

        results = []
        for i, prompt in enumerate(prompts):
            logger.info(f"️  [图像生成 {i+1}/{len(prompts)}] 开始生成...")
            logger.info(f"   使用提示词: {prompt[:150]}...")

            try:
                result = await self.generate_image(
                    prompt=prompt, style=project_type, aspect_ratio=ImageAspectRatio.LANDSCAPE
                )

                #  v7.40.1: 如果 API 没有返回 revised_prompt，使用原始 prompt
                if result.success and not result.revised_prompt:
                    result.revised_prompt = prompt
                    logger.debug("   使用原始 prompt 作为 revised_prompt")

                if result.success:
                    logger.info(f" [图像生成 {i+1}/{len(prompts)}] 生成成功")
                    logger.info(f"   图像URL长度: {len(result.image_url) if result.image_url else 0} 字符")
                    logger.info(f"   使用模型: {result.model_used}")
                else:
                    logger.error(f" [图像生成 {i+1}/{len(prompts)}] 生成失败: {result.error}")

                results.append(result)

            except Exception as e:
                logger.error(f" [图像生成 {i+1}/{len(prompts)}] 发生异常: {e}")
                logger.exception(e)
                # 创建失败结果
                results.append(ImageGenerationResult(success=False, error=f"生成异常: {str(e)}", model_used=self.model))

        success_count = sum(1 for r in results if r.success)
        logger.info(f" [概念图生成] 完成，成功 {success_count}/{len(results)} 张")

        return results

    def _extract_visual_concepts(self, text: str, project_type: str) -> List[str]:
        """
         v7.39.5: 从专家分析文本中智能提取可视化概念

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

        logger.debug(f" 从专家内容提取的设计概念: {unique_concepts[:8]}")

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
        questionnaire_data: dict | None = None,
        visual_references: List[Dict[str, Any]] | None = None,  #  v7.155: 视觉参考
        global_style_anchor: str | None = None,  #  v7.155: 全局风格锚点
    ) -> "List[ImageMetadata]":
        """
         v7.153: 重构为两阶段LLM精炼流程
         v7.155: 支持用户上传的视觉参考

        核心改进：
        1. 以交付物content(expert_analysis)为唯一信息源
        2. 第一阶段：提取视觉简报 + 生成style_anchor
        3. 第二阶段：生成结构化英文Prompt
        4. 配置驱动的角色差异化视觉生成
        5. Style Anchor确保多图一致性
        6.  v7.155: 支持用户上传的视觉参考注入

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

        logger.info(f" [v7.153] 为交付物生成概念图: {deliverable_name}")
        logger.info(f"   角色: {owner_role}, 交付物ID: {deliverable_id}")

        #  v7.155: 记录视觉参考信息
        if visual_references:
            logger.info(f"  ️ [v7.155] 使用 {len(visual_references)} 个视觉参考")
        if global_style_anchor:
            logger.info(f"   [v7.155] 全局风格锚点: {global_style_anchor[:50]}...")

        # 读取 concept_image_config 配置
        concept_image_config = deliverable_metadata.get("concept_image_config", {})
        image_count = concept_image_config.get("count", 1)
        logger.info(f"  ️ 计划生成 {image_count} 张概念图")

        try:
            # ================================================================
            #  v7.153 核心改进：两阶段LLM精炼
            # ================================================================

            # 提取风格标签作为硬性约束（唯一从questionnaire_data提取的信息）
            profile_label = ""
            if questionnaire_data:
                profile_label = questionnaire_data.get("profile_label", "")
                logger.info(f"   风格标签（硬性约束）: {profile_label or '未指定'}")

            # 标准化角色ID
            role_id = owner_role
            if "-" in owner_role:
                role_id = f"V{owner_role.split('-')[0]}"

            # 加载角色配置
            role_config = get_role_visual_identity(role_id)
            #  v7.154: 使用项目类型感知的视觉类型
            actual_visual_type = get_role_visual_type_for_project(role_id, project_type)
            logger.info(f"   角色视觉类型: {actual_visual_type} (项目类型: {project_type})")

            # ================================================================
            # 第一阶段：从交付物content提取视觉简报 + style_anchor
            #  v7.155: 注入视觉参考
            # ================================================================
            logger.info("   [第一阶段] 提取视觉简报...")

            visual_brief, style_anchor = await self._extract_visual_brief(
                deliverable_content=expert_analysis,
                role_id=role_id,
                profile_label=profile_label,
                project_type=project_type,  #  v7.154: 传入项目类型
                visual_references=visual_references,  #  v7.155: 传入视觉参考
            )

            if not visual_brief:
                logger.warning("  ️ 视觉简报提取失败，使用原始内容")
                visual_brief = expert_analysis[:800]
                style_anchor = ", ".join(role_config.get("style_preferences", [])[:3])

            #  v7.155: 如果有全局风格锚点，优先合并
            if global_style_anchor:
                style_anchor = f"{global_style_anchor}, {style_anchor}"
                logger.info("   [v7.155] 合并全局风格锚点")

            logger.info(f"   视觉简报: {len(visual_brief)} 字符")
            logger.info(f"   Style Anchor: {style_anchor[:60]}...")

            # ================================================================
            # 第二阶段：生成结构化英文Prompt
            # ================================================================
            logger.info("   [第二阶段] 生成结构化Prompt...")

            visual_prompt = await self._generate_structured_prompt(
                visual_brief=visual_brief,
                style_anchor=style_anchor,
                role_id=role_id,
                deliverable_name=deliverable_name,
                project_type=project_type,  #  v7.154: 传入项目类型
            )

            # 校验Prompt质量
            global_config = get_global_config()
            min_length = global_config.get("final_prompt_min_length", 80)

            if len(visual_prompt) < min_length:
                logger.warning(f"  ️ Prompt过短 ({len(visual_prompt)} < {min_length})，使用降级Prompt")
                visual_type_config = get_visual_type_config(role_config.get("visual_type", "photorealistic_rendering"))
                visual_prompt = (
                    f"{style_anchor}, {deliverable_name}, {visual_type_config.get('quality_suffix', 'high quality')}"
                )

            logger.info(f"   最终Prompt: {visual_prompt[:100]}...")
            logger.debug(f"   完整Prompt ({len(visual_prompt)} chars): {visual_prompt}")

            # ================================================================
            # 第三阶段：循环生成多张图片（使用相同Prompt + Style Anchor）
            # ================================================================
            from ..services.image_storage_manager import ImageStorageManager

            generated_images: List[ImageMetadata] = []
            failed_count = 0

            for attempt in range(image_count):
                try:
                    logger.info(f"  ️ [图片 {attempt + 1}/{image_count}] 开始生成...")

                    # 多图生成时，追加视角差异（可选）
                    current_prompt = visual_prompt
                    if image_count > 1 and attempt > 0:
                        # 为后续图片添加视角变化
                        view_variations = ["detail view", "wide angle view", "atmospheric view"]
                        variation = view_variations[attempt % len(view_variations)]
                        current_prompt = f"{visual_prompt}, {variation}"
                        logger.debug(f"     添加视角变化: {variation}")

                    # 调用图片生成API
                    generation_result = await self.generate_image(
                        prompt=current_prompt, aspect_ratio=ImageAspectRatio(aspect_ratio)
                    )

                    if not generation_result.success:
                        logger.error(f"     生成失败: {generation_result.error}")
                        failed_count += 1
                        continue

                    logger.info("     图片生成成功！")

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
                    logger.info(f"     已保存: {filename}")

                except Exception as img_error:
                    logger.error(f"     [图片 {attempt + 1}] 生成失败: {img_error}")
                    logger.exception(img_error)
                    failed_count += 1

            # 处理生成结果
            if not generated_images:
                logger.error(f"   全部 {image_count} 张图片生成失败")
                raise Exception(f"全部 {image_count} 张图片生成失败")

            if failed_count > 0:
                logger.warning(f"  ️ 生成 {len(generated_images)}/{image_count} 张图片（{failed_count} 张失败）")
            else:
                logger.info(f" [v7.153] 成功生成全部 {len(generated_images)} 张概念图")

            return generated_images

        except Exception as e:
            logger.error(f" [v7.153] 生成交付物概念图失败: {e}")
            logger.exception(e)
            raise

    async def edit_image_with_mask(
        self,
        original_image: str,
        mask_image: str,
        prompt: str,
        aspect_ratio: ImageAspectRatio | None = None,
        style: str | None = None,
        inpainting_service=None,
    ) -> ImageGenerationResult:
        """
         v7.62: 使用 Mask 编辑图像（双模式架构）

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
        logger.info(" [v7.62 Dual-Mode] 接收图像处理请求")

        # 1. 检查是否有 Mask（决定模式）
        if mask_image and inpainting_service and inpainting_service.is_available():
            logger.info(" [Inpainting Mode] 使用 DALL-E 2 Edit API（Option D）")

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
                    logger.info(" [Inpainting Mode] 图像编辑成功")
                    return ImageGenerationResult(
                        success=True,
                        image_url=inpainting_result.edited_image_url,
                        revised_prompt=inpainting_result.original_prompt,
                        model_used=inpainting_result.model_used or "dall-e-2-edit",
                    )
                else:
                    # Inpainting 失败，记录错误并回退
                    logger.warning(f"️ [Inpainting Mode] 失败: {inpainting_result.error}")
                    logger.warning(" 回退到 Vision+生成 模式（Option C）")

            except Exception as e:
                logger.error(f" [Inpainting Mode] 异常: {e}")
                logger.warning(" 回退到 Vision+生成 模式（Option C）")

        # 2. 回退到 Vision+生成 模式（Option C）
        logger.info(" [Generation Mode] 使用 Vision+生成（Option C）")

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
