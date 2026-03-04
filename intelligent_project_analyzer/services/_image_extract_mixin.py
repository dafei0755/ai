"""
图片生成器 视觉提取/提示词 Mixin
由 scripts/refactor/_split_mt20_image_generator.py 自动生成 (MT-20)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class ImageExtractMixin:
    """Mixin — 图片生成器 视觉提取/提示词 Mixin"""
    async def _extract_visual_brief(
        self,
        deliverable_content: str,
        role_id: str,
        profile_label: str = "",
        project_type: str = "",  #  v7.154: 添加项目类型参数
        visual_references: List[Dict[str, Any]] | None = None,  #  v7.155: 视觉参考
    ) -> Tuple[str, str]:
        """
         v7.153: 第一阶段LLM - 从交付物content中提取视觉简报

        核心改进：
        1. 以交付物content为唯一信息源（已融合问卷+需求+搜索+任务）
        2. 根据角色配置的extraction_focus定制提取维度
        3. 同时生成style_anchor确保多图一致性
        4.  v7.154: 根据项目类型选择合适的视觉类型
        5.  v7.155: 支持用户上传的视觉参考注入

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
        logger.info(" [v7.153 第一阶段] 开始视觉简报提取...")
        logger.debug(f"   角色: {role_id}, 风格标签: {profile_label}")
        logger.debug(f"   内容长度: {len(deliverable_content)} 字符")

        # 从配置加载角色视觉身份
        role_config = get_role_visual_identity(role_id)
        extraction_focus = role_config.get("extraction_focus", [])
        #  v7.154: 使用项目类型感知的视觉类型选择
        visual_type = get_role_visual_type_for_project(role_id, project_type)
        role_perspective = role_config.get("perspective", "设计专家")

        logger.info(f"   视觉类型: {visual_type} (项目类型: {project_type})")
        logger.info(f"   提取焦点: {extraction_focus[:3]}...")

        #  v7.155: 构建视觉参考上下文
        visual_reference_context = ""
        if visual_references:
            visual_reference_context = self._build_visual_reference_context(visual_references)
            logger.info(f"  ️ [v7.155] 注入 {len(visual_references)} 个视觉参考")

        # 获取视觉类型配置
        visual_type_config = get_visual_type_config(visual_type)
        global_config = get_global_config()
        max_length = global_config.get("visual_brief_max_length", 800)

        # 构建提取焦点描述
        focus_list = "\n".join(f"- {f}" for f in extraction_focus) if extraction_focus else "- 空间效果\n- 材质色彩\n- 氛围表现"

        #  v7.155: 在 system_prompt 中注入视觉参考
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
            logger.info(f"  ️ LLM响应时间: {elapsed:.2f}秒")

            if response.status_code != 200:
                logger.warning(f"️ [第一阶段] API错误: {response.status_code}")
                return self._fallback_visual_brief(deliverable_content, role_config, profile_label)

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not content:
                logger.warning("️ [第一阶段] LLM返回空内容")
                return self._fallback_visual_brief(deliverable_content, role_config, profile_label)

            # 解析输出
            if "---STYLE_ANCHOR---" in content:
                parts = content.split("---STYLE_ANCHOR---")
                visual_brief = parts[0].strip()
                style_anchor = parts[1].strip() if len(parts) > 1 else ""
            else:
                visual_brief = content
                style_anchor = self._extract_style_anchor_fallback(content, role_config)

            logger.info(" [v7.153 第一阶段] 视觉简报提取成功")
            logger.info(f"   简报长度: {len(visual_brief)} 字符")
            logger.info(f"   风格锚点: {style_anchor[:50]}...")

            return visual_brief, style_anchor

        except Exception as e:
            logger.error(f" [第一阶段] 异常: {e}")
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

        logger.info(f"  ️ 使用降级视觉简报 ({len(visual_brief)} 字符)")
        return visual_brief, style_anchor

    def _extract_style_anchor_fallback(self, content: str, role_config: Dict[str, Any]) -> str:
        """从内容中提取风格锚点的降级方法"""
        style_prefs = role_config.get("style_preferences", [])[:3]
        return ", ".join(style_prefs) if style_prefs else "professional design"

    # ========================================================================
    #  v7.155: 视觉参考上下文构建
    # ========================================================================

    def _build_visual_reference_context(self, visual_references: List[Dict[str, Any]]) -> str:
        """
         v7.155: 构建视觉参考上下文字符串

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
    #  v7.153: 两阶段LLM精炼 - 第二阶段：结构化英文Prompt生成
    # ========================================================================

    async def _generate_structured_prompt(
        self,
        visual_brief: str,
        style_anchor: str,
        role_id: str,
        deliverable_name: str = "",
        project_type: str = "",  #  v7.154: 添加项目类型参数
    ) -> str:
        """
         v7.153: 第二阶段LLM - 从视觉简报生成结构化英文Prompt

        Args:
            visual_brief: 第一阶段提取的视觉简报
            style_anchor: 风格锚点（确保一致性）
            role_id: 角色ID
            deliverable_name: 交付物名称
            project_type: 项目类型（用于选择合适的视觉类型）

        Returns:
            结构化英文Prompt (150-200 words)
        """
        logger.info(" [v7.153 第二阶段] 开始结构化Prompt生成...")

        # 加载配置
        role_config = get_role_visual_identity(role_id)
        #  v7.154: 使用项目类型感知的视觉类型选择
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
            logger.info(f"  ️ LLM响应时间: {elapsed:.2f}秒")

            if response.status_code != 200:
                logger.warning(f"️ [第二阶段] API错误: {response.status_code}")
                return self._fallback_structured_prompt(visual_brief, style_anchor, role_config)

            result = response.json()
            prompt = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not prompt or len(prompt) < 50:
                logger.warning("️ [第二阶段] Prompt过短或为空")
                return self._fallback_structured_prompt(visual_brief, style_anchor, role_config)

            # 校验必保留关键词
            prompt = self._validate_and_enhance_prompt(prompt, required_keywords, style_anchor, quality_suffix)

            logger.info(f" [v7.153 第二阶段] 结构化Prompt生成成功 ({len(prompt)} 字符)")
            logger.debug(f"   Prompt: {prompt[:150]}...")

            return prompt

        except Exception as e:
            logger.error(f" [第二阶段] 异常: {e}")
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
        re.findall(r"[\u4e00-\u9fff]{2,4}", visual_brief)[:10]

        prompt = f"{style_anchor}, {' '.join(english_words)}, professional design visualization, {quality_suffix}"

        logger.info(f"  ️ 使用降级Prompt ({len(prompt)} 字符)")
        return prompt

    def _validate_and_enhance_prompt(
        self, prompt: str, required_keywords: List[str], style_anchor: str, quality_suffix: str
    ) -> str:
        """校验并增强Prompt，确保必要关键词存在"""
        prompt_lower = prompt.lower()

        # 检查必保留关键词
        missing_keywords = [kw for kw in required_keywords if kw.lower() not in prompt_lower]

        if missing_keywords:
            logger.info(f"   追加缺失关键词: {missing_keywords}")
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
         v7.50: 使用 LLM 从专家报告中提取高质量图像生成提示词

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
        logger.info(" [LLM提示词提取] 开始处理...")
        logger.debug(f"   专家名称: {expert_name}")
        logger.debug(f"  ️  项目类型: {project_type}")
        logger.debug(f"   专家内容长度: {len(expert_content)} 字符")

        #  v7.128: 增加输入长度限制至5000字符（支持完整专家分析）
        content_preview = expert_content[:5000] if len(expert_content) > 5000 else expert_content
        if len(expert_content) > 5000:
            logger.info(f"  ️  内容截断: {len(expert_content)} → 5000 字符")

        # 项目类型到场景描述的映射
        type_context = {
            "interior": "interior design / residential space",
            "architecture": "architectural / building exterior",
            "product": "product design / industrial design",
            "branding": "brand identity / visual design",
        }.get(project_type, "design concept")
        logger.debug(f"   场景上下文: {type_context}")

        #  v7.129: 优化系统提示词，强化角色身份差异化
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
            logger.info(f"   调用LLM (model={self.prompt_extraction_model})...")
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
                logger.info(f"  ️  LLM响应时间: {elapsed_time:.2f}秒")

                if response.status_code != 200:
                    logger.warning(f"️  [LLM提示词提取] API返回错误: {response.status_code}")
                    logger.debug(f"  错误响应: {response.text[:200]}")
                    return ""

                result = response.json()
                extracted_prompt = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                if extracted_prompt:
                    logger.info(f" [LLM提示词提取] 成功 ({len(extracted_prompt)} 字符)")
                    logger.info(f"   提取的提示词: {extracted_prompt[:200]}...")
                    return extracted_prompt
                else:
                    logger.warning("️  [LLM提示词提取] LLM返回空内容")
                    return ""

        except Exception as e:
            logger.error(f" [LLM提示词提取] 发生异常: {e}")
            logger.exception(e)
            return ""

    async def _enhance_prompt_with_user_input(
        self,
        user_prompt: str,
        expert_context: str = "",
        conversation_history: str = "",
        project_constraints: str = "",
        vision_analysis: str | None = None,
    ) -> str:
        """
         v7.50: 为编辑环节优化用户输入的提示词
         v7.61: 添加 Vision 分析结果集成

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
        #  v7.61: Vision 分析优先级最高（如果有参考图）
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
                    logger.warning(f"️ Prompt enhancement failed: {response.status_code}")
                    return user_prompt  # 失败时返回原始提示词

                result = response.json()
                enhanced = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                if enhanced and len(enhanced) > len(user_prompt):
                    logger.info(f" [v7.50] 用户提示词增强成功: {len(user_prompt)} → {len(enhanced)} 字符")
                    return enhanced
                else:
                    return user_prompt

        except Exception as e:
            logger.warning(f"️ Prompt enhancement error: {e}, using original")
            return user_prompt

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头 - v7.200: 每次请求通过负载均衡器轮询 Key"""
        api_key = self._load_balancer._select_key()
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }

    def _enhance_prompt(
        self, prompt: str, style: str | None = None, aspect_ratio: ImageAspectRatio = ImageAspectRatio.LANDSCAPE
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

        logger.debug(f" Enhanced prompt: {enhanced[:100]}...")
        return enhanced

