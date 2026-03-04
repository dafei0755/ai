"""
需求分析师 两阶段执行 Mixin
由 scripts/refactor/_split_mt14_analyst.py 自动生成 (MT-14)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.store.base import BaseStore
    from ..workflow.state import ProjectAnalysisState


class AnalystPhaseMixin:
    """Mixin — 需求分析师 两阶段执行 Mixin"""
    async def _execute_two_phase(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: BaseStore | None = None
    ) -> AnalysisResult:
        """ v7.17: 两阶段执行模式
         v7.502 P0优化: 改为async函数支持并行执行
        
        Phase1: 快速定性 + 交付物识别（~1.5s）
        - L0 项目定性（信息充足/不足判断）
        - 交付物识别 + 能力边界判断
        - 输出: info_status, primary_deliverables, recommended_next_step
        
        Phase2: 深度分析 + 专家接口（~3s，仅当 Phase1 判断信息充足时）
        - L1-L5 深度分析
        - 专家接口构建
        - 输出: 完整的 structured_data + expert_handoff
        """
        start_time = time.time()
        session_id = state.get("session_id", "unknown")
        
        logger.info(f" [v7.17] 启动两阶段需求分析 (session: {session_id})")
        
        try:
            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: user input is too short or empty")
            
            user_input = state.get("user_input", "")
            
            #  v7.155: 提取视觉参考
            visual_references = state.get("uploaded_visual_references", None)
            if visual_references:
                logger.info(f"️ [v7.155] 检测到 {len(visual_references)} 个视觉参考，将注入需求分析")

            # ═══════════════════════════════════════════════════════════════
            #  P0优化 (v7.502): Precheck + Phase1 并行执行
            # 旧架构: precheck → Phase1 (串行, 1.5s总耗时)
            # 新架构: precheck || Phase1 (并行, 1.1s总耗时, 27%加速)
            # ═══════════════════════════════════════════════════════════════
            parallel_start = time.time()
            logger.info(" [P0优化] 开始 Precheck + Phase1 并行执行...")
            
            # 创建异步任务
            import asyncio
            
            # 确保有event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 创建并行任务
            precheck_task = asyncio.create_task(self._execute_precheck_async(user_input))
            phase1_task = asyncio.create_task(self._execute_phase1_async(user_input, visual_references))
            
            #  并行执行
            capability_precheck, phase1_result = await asyncio.gather(precheck_task, phase1_task)
            
            parallel_elapsed = time.time() - parallel_start
            logger.info(f" [P0优化] Precheck + Phase1 并行完成，总耗时 {parallel_elapsed:.2f}s")
            logger.info("   - 预期串行耗时: ~1.5s")
            logger.info(f"   -  加速比: {1.5/parallel_elapsed:.1f}x")
            logger.info(f"   - Precheck结果: 信息充足={capability_precheck['info_sufficiency']['is_sufficient']}")
            logger.info(f"   - Phase1结果: info_status={phase1_result.get('info_status')}")
            
            # 合并 precheck 洞察到 Phase1 结果（如果Phase1没有考虑）
            if 'capability_precheck' not in phase1_result:
                phase1_result['capability_precheck'] = capability_precheck
            
            # 判断是否需要执行 Phase2
            info_status = phase1_result.get("info_status", "insufficient")
            recommended_next = phase1_result.get("recommended_next_step", "questionnaire_first")
            
            if info_status == "insufficient" or recommended_next == "questionnaire_first":
                # 信息不足，跳过 Phase2，直接返回 Phase1 结果
                logger.info("️ [Phase1] 信息不足，跳过 Phase2，建议先收集问卷")
                
                structured_data = self._build_phase1_only_result(phase1_result, user_input)
                structured_data["analysis_mode"] = "phase1_only"
                structured_data["skip_phase2_reason"] = phase1_result.get("info_status_reason", "信息不足")
                
                result = self.create_analysis_result(
                    content=json.dumps(phase1_result, ensure_ascii=False, indent=2),
                    structured_data=structured_data,
                    confidence=0.5,  # Phase1 only 的置信度较低
                    sources=["user_input", "phase1_analysis"]
                )
                
                end_time = time.time()
                self._track_execution_time(start_time, end_time)
                logger.info(f" [v7.17] 两阶段分析完成（仅Phase1），总耗时 {end_time - start_time:.2f}s")
                
                return result
            
            # ═══════════════════════════════════════════════════════════════
            # Phase 2: 深度分析 + 专家接口
            # ═══════════════════════════════════════════════════════════════
            phase2_start = time.time()
            logger.info(" [Phase2] 开始深度分析 + 专家接口构建...")
            
            phase2_result = self._execute_phase2(user_input, phase1_result)
            
            phase2_elapsed = time.time() - phase2_start
            logger.info(f" [Phase2] 完成，耗时 {phase2_elapsed:.2f}s")
            
            # 合并 Phase1 和 Phase2 结果
            structured_data = self._merge_phase_results(phase1_result, phase2_result)
            structured_data["analysis_mode"] = "two_phase"
            structured_data["phase1_elapsed_s"] = round(parallel_elapsed, 2)  # precheck+phase1 并行耗时
            structured_data["phase2_elapsed_s"] = round(phase2_elapsed, 2)

            # 后处理：字段规范化、项目类型推断
            self._normalize_jtbd_fields(structured_data)
            structured_data["project_type"] = self._infer_project_type(structured_data)

            #  v7.270: Enhanced post-processing
            logger.info(" [v7.270] Starting enhanced post-processing...")

            # 1. Validate Phase 2 output quality
            validation_result = self.requirements_validator.validate_phase2_output(phase2_result)
            structured_data["validation_result"] = validation_result.to_dict()

            if not validation_result.is_valid:
                logger.warning("️ [v7.270] Phase 2 validation failed, attempting fixes...")
                # Attempt to fix missing L6/L7
                phase2_result = self._fix_validation_issues(phase2_result, validation_result, user_input)
                # Re-merge after fixes
                structured_data = self._merge_phase_results(phase1_result, phase2_result)

            # 2. Extract entities
            logger.info(" [v7.270] Extracting entities...")
            entity_result = self.entity_extractor.extract_entities(
                structured_data=structured_data,
                user_input=user_input
            )
            structured_data["entities"] = entity_result.to_dict()
            logger.info(f" [v7.270] Extracted {entity_result.total_entities()} entities")

            # 3. Identify motivation types
            logger.info(" [v7.270] Identifying motivation types...")
            try:
                # Create task dict for motivation engine
                task = {
                    "project_overview": structured_data.get("project_overview", ""),
                    "core_objectives": structured_data.get("core_objectives", []),
                    "target_users": structured_data.get("target_users", "")
                }

                # Call async infer method synchronously
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                motivation_result = loop.run_until_complete(
                    self.motivation_engine.infer(
                        task=task,
                        user_input=user_input,
                        structured_data=structured_data
                    )
                )

                structured_data["motivation_types"] = {
                    "primary": motivation_result.primary,
                    "primary_label": motivation_result.primary_label,
                    "secondary": motivation_result.secondary or [],
                    "confidence": motivation_result.confidence,
                    "reasoning": motivation_result.reasoning,
                    "method": motivation_result.method
                }
                logger.info(f" [v7.270] Primary motivation: {motivation_result.primary} ({motivation_result.primary_label})")
            except Exception as e:
                logger.warning(f"️ [v7.270] Motivation identification failed: {e}, using fallback")
                structured_data["motivation_types"] = {
                    "primary": "mixed",
                    "primary_label": "综合",
                    "secondary": [],
                    "confidence": 0.5,
                    "reasoning": "自动识别失败，使用默认值",
                    "method": "fallback"
                }

            # 4. Generate problem-solving approach
            logger.info(" [v7.270] Generating problem-solving approach...")
            problem_solving_approach = self._generate_problem_solving_approach(
                user_input=user_input,
                phase2_result=phase2_result
            )
            if problem_solving_approach:
                structured_data["problem_solving_approach"] = problem_solving_approach.to_dict()
                logger.info(f" [v7.270] Generated {len(problem_solving_approach.solution_steps)} solution steps")

            logger.info(" [v7.270] Enhanced post-processing complete")

            # 创建分析结果
            confidence = self._calculate_two_phase_confidence(phase1_result, phase2_result)

            result = self.create_analysis_result(
                content=json.dumps(phase2_result, ensure_ascii=False, indent=2),
                structured_data=structured_data,
                confidence=confidence,
                sources=["user_input", "phase1_analysis", "phase2_analysis"]
            )

            end_time = time.time()
            self._track_execution_time(start_time, end_time)
            logger.info(f" [v7.17] 两阶段分析完成，总耗时 {end_time - start_time:.2f}s")

            return result
            
        except Exception as e:
            error = self.handle_error(e, "two-phase requirements analysis")
            raise error

    # ═══════════════════════════════════════════════════════════════════════════
    #  P0优化 (v7.502): 异步包装方法 - Phase1 + Precheck 并行执行
    # ═══════════════════════════════════════════════════════════════════════════

    async def _execute_precheck_async(self, user_input: str) -> Dict[str, Any]:
        """
         P0优化: 异步执行程序化能力边界预检测

        Args:
            user_input: 用户输入文本

        Returns:
            预检测结果字典
        """
        import asyncio
        
        logger.info(" [Precheck-Async] 开始程序化能力边界检测...")
        start = time.time()
        
        # check_capability 是同步函数，在线程池中运行以避免阻塞
        loop = asyncio.get_event_loop()
        capability_precheck = await loop.run_in_executor(None, check_capability, user_input)
        
        elapsed = time.time() - start
        logger.info(f" [Precheck-Async] 完成，耗时 {elapsed:.3f}s")
        logger.info(f"   - 信息充足: {capability_precheck['info_sufficiency']['is_sufficient']}")
        logger.info(f"   - 能力匹配: {capability_precheck['deliverable_capability']['capability_score']:.0%}")
        
        return capability_precheck

    async def _execute_phase1_async(
        self, 
        user_input: str, 
        visual_references: List[Dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """
         P0优化: 异步执行Phase1快速定性

        注意: 此版本不依赖precheck结果，precheck将在外部并行执行并后续合并

        Args:
            user_input: 用户输入文本
            visual_references: 视觉参考（可选）

        Returns:
            Phase1结果字典
        """
        import asyncio
        
        logger.info(" [Phase1-Async] 开始快速定性...")
        start = time.time()
        
        # _execute_phase1 内部调用 LLM，已经是异步的（通过 invoke_llm）
        # 我们在线程池中运行同步版本，或者创建一个真正的异步版本
        loop = asyncio.get_event_loop()
        
        # 使用 partial 传递None作为 capability_precheck 参数（将在外部合并）
        from functools import partial
        phase1_func = partial(self._execute_phase1, user_input, None, visual_references)
        phase1_result = await loop.run_in_executor(None, phase1_func)
        
        elapsed = time.time() - start
        logger.info(f" [Phase1-Async] 完成，耗时 {elapsed:.2f}s")
        logger.info(f"   - info_status: {phase1_result.get('info_status')}")
        logger.info(f"   - deliverables: {len(phase1_result.get('primary_deliverables', []))}个")
        
        return phase1_result

    # ═══════════════════════════════════════════════════════════════════════════
    # 原有Phase执行方法
    # ═══════════════════════════════════════════════════════════════════════════

    def _execute_phase1(
        self,
        user_input: str,
        capability_precheck: Dict[str, Any] | None = None,
        visual_references: List[Dict[str, Any]] | None = None,  #  v7.155: 视觉参考
    ) -> Dict[str, Any]:
        """执行 Phase1: 快速定性 + 交付物识别

        Args:
            user_input: 用户输入文本
            capability_precheck: 程序化预检测结果（v7.17 P2）
            visual_references: 用户上传的视觉参考列表（v7.155）
        """
        # 加载 Phase1 专用提示词
        phase1_config = self.prompt_manager.get_prompt("requirements_analyst_phase1", return_full_config=True)

        if not phase1_config:
            logger.warning("[Phase1] 未找到专用配置，使用默认定性逻辑")
            return self._fallback_phase1(user_input, capability_precheck)

        system_prompt = phase1_config.get("system_prompt", "")
        task_template = phase1_config.get("task_description_template", "")

        # 构建任务描述
        from datetime import datetime
        datetime_info = f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}。"
        task_description = task_template.replace("{datetime_info}", datetime_info).replace("{user_input}", user_input)

        #  v7.17 P2: 将预检测结果注入到任务描述中
        if capability_precheck:
            precheck_hints = self._format_precheck_hints(capability_precheck)
            task_description = f"{precheck_hints}\n\n{task_description}"

        #  v7.155: 将视觉参考注入到任务描述中
        if visual_references:
            visual_context = self._build_visual_reference_context(visual_references)
            task_description = f"{visual_context}\n\n{task_description}"
            logger.info(f"  ️ [v7.155] 已注入 {len(visual_references)} 个视觉参考到需求分析")

        # 调用 LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_description}
        ]

        response = self.invoke_llm(messages)

        # 解析 JSON
        try:
            result = self._parse_phase_response(response.content)
            result["phase"] = 1
            return result
        except Exception as e:
            logger.error(f"[Phase1] JSON解析失败: {e}")
            return self._fallback_phase1(user_input, capability_precheck)

    def _execute_phase2(self, user_input: str, phase1_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Phase2: 深度分析 + 专家接口构建"""
        # 加载 Phase2 专用提示词
        phase2_config = self.prompt_manager.get_prompt("requirements_analyst_phase2", return_full_config=True)
        
        if not phase2_config:
            logger.warning("[Phase2] 未找到专用配置，使用默认分析逻辑")
            return self._fallback_phase2(user_input, phase1_result)
        
        system_prompt = phase2_config.get("system_prompt", "")
        task_template = phase2_config.get("task_description_template", "")
        
        # 构建任务描述（包含 Phase1 输出）
        from datetime import datetime
        datetime_info = f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}。"
        phase1_output_str = json.dumps(phase1_result, ensure_ascii=False, indent=2)
        
        task_description = (
            task_template
            .replace("{datetime_info}", datetime_info)
            .replace("{user_input}", user_input)
            .replace("{phase1_output}", phase1_output_str)
        )
        
        # 调用 LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_description}
        ]
        
        response = self.invoke_llm(messages)
        
        # 解析 JSON
        try:
            result = self._parse_phase_response(response.content)
            result["phase"] = 2
            return result
        except Exception as e:
            logger.error(f"[Phase2] JSON解析失败: {e}")
            return self._fallback_phase2(user_input, phase1_result)

    def _parse_phase_response(self, response: str) -> Dict[str, Any]:
        """解析阶段响应的 JSON"""
        # 复用已有的 JSON 提取逻辑
        json_str = self._extract_balanced_json(response)
        if json_str:
            return json.loads(json_str)
        
        # 尝试首尾括号提取
        first_brace = response.find('{')
        last_brace = response.rfind('}')
        if first_brace != -1 and last_brace != -1:
            return json.loads(response[first_brace:last_brace+1])
        
        raise ValueError("无法从响应中提取 JSON")

    def _fallback_phase1(self, user_input: str, capability_precheck: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Phase1 降级逻辑 - 使用程序化预检测结果（v7.17 P2 增强）"""
        
        # 如果有预检测结果，优先使用
        if capability_precheck:
            info_suff = capability_precheck.get("info_sufficiency", {})
            capability_precheck.get("deliverable_capability", {})
            capable_deliverables = capability_precheck.get("capable_deliverables", [])
            transformations = capability_precheck.get("transformations", [])
            
            info_sufficient = info_suff.get("is_sufficient", False)
            
            # 构建交付物列表
            primary_deliverables = []
            
            # 添加能力范围内的交付物
            for i, d in enumerate(capable_deliverables[:3]):
                primary_deliverables.append({
                    "deliverable_id": f"D{i+1}",
                    "type": d.get("type", "design_strategy"),
                    "description": f"基于关键词 {d.get('keywords', [])} 识别",
                    "priority": "MUST_HAVE",
                    "capability_check": {"within_capability": True}
                })
            
            # 添加需要转化的交付物
            for i, t in enumerate(transformations[:2]):
                primary_deliverables.append({
                    "deliverable_id": f"D{len(capable_deliverables)+i+1}",
                    "type": t.get("transformed_to", "design_strategy"),
                    "description": t.get("reason", ""),
                    "priority": "NICE_TO_HAVE",
                    "capability_check": {
                        "within_capability": False,
                        "original_request": t.get("original", ""),
                        "transformed_to": t.get("transformed_to", "")
                    }
                })
            
            # 确保至少有一个交付物
            if not primary_deliverables:
                primary_deliverables.append({
                    "deliverable_id": "D1",
                    "type": "design_strategy",
                    "description": "设计策略文档",
                    "priority": "MUST_HAVE",
                    "capability_check": {"within_capability": True}
                })
            
            return {
                "phase": 1,
                "info_status": "sufficient" if info_sufficient else "insufficient",
                "info_status_reason": info_suff.get("reason", "基于程序化检测"),
                "info_gaps": info_suff.get("missing_elements", []),
                "project_type_preliminary": "personal_residential",
                "project_summary": user_input[:50] + "...",
                "primary_deliverables": primary_deliverables,
                "recommended_next_step": capability_precheck.get("recommended_action", "questionnaire_first"),
                "precheck_based": True,
                "fallback": True
            }
        
        # 兜底：简单规则判断（无预检测结果时）
        word_count = len(user_input)
        has_numbers = any(c.isdigit() for c in user_input)
        has_location = any(kw in user_input for kw in ["平米", "㎡", "房间", "卧室", "客厅"])
        
        info_sufficient = word_count > 100 and (has_numbers or has_location)
        
        return {
            "phase": 1,
            "info_status": "sufficient" if info_sufficient else "insufficient",
            "info_status_reason": "基于规则判断" if info_sufficient else "信息量不足，建议补充",
            "info_gaps": [] if info_sufficient else ["项目类型", "空间约束", "预算范围"],
            "project_type_preliminary": "personal_residential",
            "project_summary": user_input[:50] + "...",
            "primary_deliverables": [{
                "deliverable_id": "D1",
                "type": "design_strategy",
                "description": "设计策略文档",
                "priority": "MUST_HAVE",
                "capability_check": {"within_capability": True}
            }],
            "recommended_next_step": "phase2_analysis" if info_sufficient else "questionnaire_first",
            "fallback": True
        }

    def _format_precheck_hints(self, capability_precheck: Dict[str, Any]) -> str:
        """
        格式化程序化预检测结果为 LLM 提示
        
        v7.17 P2: 将预检测结果注入到 Phase1 任务描述中，
        减少 LLM 的判断负担，提高一致性
        """
        hints = ["###  程序化预检测结果（已完成，请参考）"]
        
        # 信息充足性提示
        info_suff = capability_precheck.get("info_sufficiency", {})
        if info_suff.get("is_sufficient"):
            hints.append(f" **信息充足性**: 充足（得分 {info_suff.get('score', 0):.2f}）")
            hints.append(f"   - 已识别: {', '.join(info_suff.get('present_elements', []))}")
        else:
            hints.append(f"️ **信息充足性**: 不足（得分 {info_suff.get('score', 0):.2f}）")
            hints.append(f"   - 缺少: {', '.join(info_suff.get('missing_elements', [])[:5])}")
        
        # 能力匹配提示
        deliv_cap = capability_precheck.get("deliverable_capability", {})
        cap_score = deliv_cap.get("capability_score", 1.0)
        hints.append(f" **能力匹配度**: {cap_score:.0%}")
        
        # 在能力范围内的交付物
        capable = capability_precheck.get("capable_deliverables", [])
        if capable:
            deliverable_types = [d.get("type", "") for d in capable[:3]]
            hints.append(f"   - 可交付: {', '.join(deliverable_types)}")
        
        # 需要转化的需求
        transformations = capability_precheck.get("transformations", [])
        if transformations:
            hints.append("️ **需要转化的需求**:")
            for t in transformations[:3]:
                hints.append(f"   - '{t.get('original')}' → '{t.get('transformed_to')}' ({t.get('reason', '')[:50]})")
        
        # 推荐行动
        recommended = capability_precheck.get("recommended_action", "proceed_analysis")
        action_map = {
            "proceed_analysis": "建议继续深度分析",
            "questionnaire_first": "建议先收集问卷补充信息",
            "clarify_expectations": "建议与用户澄清期望（部分需求超出能力）"
        }
        hints.append(f" **建议行动**: {action_map.get(recommended, recommended)}")
        
        hints.append("")
        hints.append("请基于以上预检测结果完成 Phase1 分析，重点验证和补充预检测的判断。")

        return "\n".join(hints)

    def _build_visual_reference_context(self, visual_references: List[Dict[str, Any]]) -> str:
        """
         v7.155: 构建视觉参考上下文字符串

        将用户上传的参考图的结构化特征转换为文本描述，
        用于注入到需求分析提示词中，帮助 LLM 理解用户的视觉偏好。

        Args:
            visual_references: 视觉参考列表

        Returns:
            格式化的视觉参考上下文字符串
        """
        if not visual_references:
            return ""

        hints = ["### ️ 用户提供的视觉参考（请在分析中考虑这些视觉偏好）"]
        hints.append("")

        for idx, ref in enumerate(visual_references, 1):
            features = ref.get("structured_features", {})

            hints.append(f"**参考图 {idx}**:")

            # 风格关键词
            style_keywords = features.get("style_keywords", [])
            if style_keywords:
                hints.append(f"- 风格: {', '.join(style_keywords)}")

            # 主色调
            dominant_colors = features.get("dominant_colors", [])
            if dominant_colors:
                hints.append(f"- 主色调: {', '.join(dominant_colors)}")

            # 材质
            materials = features.get("materials", [])
            if materials:
                hints.append(f"- 材质: {', '.join(materials)}")

            # 氛围
            mood_atmosphere = features.get("mood_atmosphere", "")
            if mood_atmosphere:
                hints.append(f"- 氛围: {mood_atmosphere}")

            # 空间布局
            spatial_layout = features.get("spatial_layout", "")
            if spatial_layout:
                hints.append(f"- 空间布局: {spatial_layout}")

            # 用户追加描述（优先级最高）
            user_description = ref.get("user_description")
            if user_description:
                hints.append(f"- **用户说明**: {user_description}")

            hints.append("")

        hints.append("请在需求分析中充分考虑用户的视觉偏好，这些参考图反映了用户期望的设计风格和氛围。")
        hints.append("")

        return "\n".join(hints)

    def _fallback_phase2(self, user_input: str, phase1_result: Dict[str, Any]) -> Dict[str, Any]:
        """Phase2 降级逻辑"""
        return {
            "phase": 2,
            "analysis_layers": {
                "L1_facts": [f"用户输入: {user_input[:100]}..."],
                "L2_user_model": {"psychological": "待分析", "sociological": "待分析", "aesthetic": "待分析"},
                "L3_core_tension": "待识别核心矛盾",
                "L4_project_task": user_input[:200],
                "L5_sharpness": {"score": 50, "note": "降级模式"}
            },
            "structured_output": {
                "project_task": user_input[:200],
                "character_narrative": "待进一步分析",
                "physical_context": "待明确",
                "resource_constraints": "待明确",
                "regulatory_requirements": "待明确",
                "inspiration_references": "待补齐",
                "experience_behavior": "待补齐",
                "design_challenge": "待识别",
                "emotional_landscape": "待问卷补充后分析",
                "spiritual_aspirations": "待深入挖掘",
                "psychological_safety_needs": "待识别",
                "ritual_behaviors": "待观察",
                "memory_anchors": "待补齐"
            },
            "expert_handoff": {
                "critical_questions_for_experts": {},
                "design_challenge_spectrum": {},
                "permission_to_diverge": {}
            },
            "fallback": True
        }

    def _build_phase1_only_result(self, phase1_result: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """构建仅 Phase1 的结果结构"""
        return {
            "project_task": phase1_result.get("project_summary", user_input[:200]),
            "character_narrative": "待问卷补充后分析",
            "physical_context": "待明确",
            "resource_constraints": "待明确",
            "regulatory_requirements": "待明确",
            "inspiration_references": "待补齐",
            "experience_behavior": "待补齐",
            "design_challenge": "待识别",
            "emotional_landscape": "待问卷补充后分析",
            "spiritual_aspirations": "待深入挖掘",
            "psychological_safety_needs": "待识别",
            "ritual_behaviors": "待观察",
            "memory_anchors": "待补齐",
            "primary_deliverables": phase1_result.get("primary_deliverables", []),
            "info_status": phase1_result.get("info_status"),
            "info_gaps": phase1_result.get("info_gaps", []),
            "project_type_preliminary": phase1_result.get("project_type_preliminary"),
            "project_overview": phase1_result.get("project_summary", user_input[:200]),
            "core_objectives": [],
            "project_tasks": []
        }

    def _merge_phase_results(self, phase1: Dict[str, Any], phase2: Dict[str, Any]) -> Dict[str, Any]:
        """合并 Phase1 和 Phase2 结果

         v7.18.0: 新增L6假设审计、L7系统性影响分析和扩展L2视角支持
        """
        structured_output = phase2.get("structured_output", {})
        analysis_layers = phase2.get("analysis_layers", {})

        result = {
            # 来自 Phase2 的核心字段
            "project_task": structured_output.get("project_task", ""),
            "character_narrative": structured_output.get("character_narrative", ""),
            "physical_context": structured_output.get("physical_context", ""),
            "resource_constraints": structured_output.get("resource_constraints", ""),
            "regulatory_requirements": structured_output.get("regulatory_requirements", ""),
            "inspiration_references": structured_output.get("inspiration_references", ""),
            "experience_behavior": structured_output.get("experience_behavior", ""),
            "design_challenge": structured_output.get("design_challenge", ""),

            #  v7.141.5: 人性维度字段（情感/精神/心理/仪式/记忆）
            "emotional_landscape": structured_output.get("emotional_landscape", ""),
            "spiritual_aspirations": structured_output.get("spiritual_aspirations", ""),
            "psychological_safety_needs": structured_output.get("psychological_safety_needs", ""),
            "ritual_behaviors": structured_output.get("ritual_behaviors", ""),
            "memory_anchors": structured_output.get("memory_anchors", ""),

            # 来自 Phase1 的交付物识别
            "primary_deliverables": phase1.get("primary_deliverables", []),
            "info_status": phase1.get("info_status"),
            "project_type_preliminary": phase1.get("project_type_preliminary"),

            # 来自 Phase2 的分析层
            "analysis_layers": analysis_layers,

            #  v7.18.0: 提取L2扩展视角到顶层（便于前端访问）
            "l2_extended_perspectives": self._extract_l2_extended_perspectives(analysis_layers),

            #  v7.18.0: 提取L6假设审计到顶层
            "assumption_audit": analysis_layers.get("L6_assumption_audit", {}),

            #  v7.18.0: 提取L7系统性影响到顶层
            "systemic_impact": analysis_layers.get("L7_systemic_impact", {}),

            # 来自 Phase2 的专家接口
            "expert_handoff": phase2.get("expert_handoff", {}),

            # 兼容旧格式
            "project_overview": structured_output.get("project_task", ""),
            "core_objectives": [],
            "project_tasks": []
        }

        # 从 project_task 提取目标和任务
        project_task = result["project_task"]
        if project_task:
            result["core_objectives"] = [project_task[:100]]
            result["project_tasks"] = [project_task]

        return result

    def _extract_l2_extended_perspectives(self, analysis_layers: Dict[str, Any]) -> Dict[str, str]:
        """提取L2扩展视角（商业/技术/生态/文化/政治）

         v7.18.0: 从L2_user_model中提取扩展视角，便于前端展示
        """
        l2_model = analysis_layers.get("L2_user_model", {})
        extended = {}

        extended_perspective_keys = ["business", "technical", "ecological", "cultural", "political"]

        for key in extended_perspective_keys:
            value = l2_model.get(key, "")
            if value and value.strip() and not value.startswith("（如激活）"):
                extended[key] = value

        return extended

    def _calculate_two_phase_confidence(self, phase1: Dict[str, Any], phase2: Dict[str, Any]) -> float:
        """计算两阶段分析的置信度

         v7.18.0: 新增L6假设审计和L7系统性影响质量评估
        """
        confidence = 0.5  # 基础置信度

        # Phase1 贡献
        if phase1.get("info_status") == "sufficient":
            confidence += 0.1
        if len(phase1.get("primary_deliverables", [])) > 0:
            confidence += 0.1

        # Phase2 贡献
        analysis_layers = phase2.get("analysis_layers", {})

        # L5 锐度测试
        sharpness = analysis_layers.get("L5_sharpness", {})
        if isinstance(sharpness, dict):
            score = sharpness.get("score", 0)
            confidence += min(score / 200, 0.2)  # 最多 +0.2

        #  v7.18.0: L6 假设审计质量
        assumption_audit = analysis_layers.get("L6_assumption_audit", {})
        if isinstance(assumption_audit, dict):
            assumptions = assumption_audit.get("identified_assumptions", [])
            if len(assumptions) >= 3:
                confidence += 0.05  # 完成假设审计 +0.05

        #  v7.18.0: L7 系统性影响分析质量
        systemic_impact = analysis_layers.get("L7_systemic_impact", {})
        if isinstance(systemic_impact, dict):
            # 检查是否覆盖三个时间维度
            has_short = bool(systemic_impact.get("short_term"))
            has_medium = bool(systemic_impact.get("medium_term"))
            has_long = bool(systemic_impact.get("long_term"))
            if has_short and has_medium and has_long:
                confidence += 0.05  # 完成系统性影响分析 +0.05

        # 专家接口完整性
        if phase2.get("expert_handoff", {}).get("critical_questions_for_experts"):
            confidence += 0.1

        return min(confidence, 1.0)

    # ═══════════════════════════════════════════════════════════════════════════
    #  v7.270: Enhanced validation and generation methods
    # ═══════════════════════════════════════════════════════════════════════════

