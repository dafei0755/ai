"""
需求重组 综合/合成 Mixin
由 scripts/refactor/_split_mt18_restructuring.py 自动生成 (MT-18)
"""
from __future__ import annotations

from typing import Any, Dict, List


class RestructuringSynthesisMixin:
    """Mixin — 需求重组 综合/合成 Mixin"""
    @staticmethod
    def _prepare_synthesis_context(
        questionnaire_data: "Dict[str, Any]",
        ai_analysis: "Dict[str, Any]",
        analysis_layers: "Dict[str, Any]",
        user_input: str,
    ) -> "Dict[str, Any]":
        """Phase A: 收集整理原始数据为结构化 context"""

        context: Dict[str, Any] = {"user_input": user_input or ""}

        # Step 1: 核心任务
        tasks = questionnaire_data.get("core_tasks", [])
        context["core_tasks"] = [
            {
                "title": t.get("title", ""),
                "description": t.get("description", "")[:120],
                "priority": t.get("priority", ""),
                "motivation_label": t.get("motivation_label", ""),
                "type": t.get("type", ""),
            }
            for t in tasks[:8]
        ]

        # Step 2: 信息补全答案
        gap_filling = questionnaire_data.get("gap_filling", {})
        context["gap_filling_raw"] = {
            k: str(v)[:200] for k, v in gap_filling.items() if v and k not in ["timestamp", "submitted_at", "_meta"]
        }

        # Step 3: 雷达维度 + 权重
        dimensions = questionnaire_data.get("dimensions", {})
        selected_dims = dimensions.get("selected", [])
        weights = dimensions.get("weights", {}) or {}
        dimension_labels = {
            "functionality": "功能性",
            "aesthetics": "美学",
            "sustainability": "可持续性",
            "cost": "成本控制",
            "timeline": "时间管理",
            "quality": "品质感",
            "innovation": "创新性",
        }
        dim_list = []
        for dim in selected_dims[:8]:
            if isinstance(dim, dict):
                dim_id = dim.get("id", "")
                dim_name = dim.get("name", dim_id)
            else:
                dim_id = str(dim)
                dim_name = dimension_labels.get(str(dim), str(dim))
            weight = weights.get(dim_id, 0.5) if isinstance(weights, dict) else 0.5
            dim_list.append({"id": dim_id, "name": dim_name, "weight": weight})
        context["dimensions"] = dim_list

        # AI分析层（L1-L5）
        context["l1_facts"] = analysis_layers.get("L1_facts", []) if analysis_layers else []
        context["l2_user_model"] = analysis_layers.get("L2_user_model", {}) if analysis_layers else {}
        context["l3_core_tension"] = analysis_layers.get("L3_core_tension", "") if analysis_layers else ""
        context["l4_project_task"] = analysis_layers.get("L4_project_task", "") if analysis_layers else ""
        context["l5_sharpness"] = analysis_layers.get("L5_sharpness", {}) if analysis_layers else {}

        return context

    # ==================== v3.0: Phase B - LLM综合分析 ====================

    @staticmethod
    def _build_synthesis_prompt(context: "Dict[str, Any]") -> str:
        """构建综合分析 prompt（以下游需求为导向）"""
        import json as _json

        # 格式化核心任务
        tasks_text = (
            "\n".join(
                [
                    f"- {t['title']}"
                    + (f"（{t['motivation_label']}）" if t.get("motivation_label") else "")
                    + (f": {t['description']}" if t.get("description") else "")
                    for t in context.get("core_tasks", [])
                ]
            )
            or "未提供"
        )

        # 格式化补充信息
        gap_items = "\n".join([f"- {k}: {v}" for k, v in context.get("gap_filling_raw", {}).items()]) or "未提供"

        # 格式化维度偏好（含权重和ID）
        dims = context.get("dimensions", [])
        dim_items = "\n".join([f"- {d['name']}（ID: {d['id']}）: 权重{int(d['weight'] * 100)}%" for d in dims]) or "未选择"

        # AI分析参考
        l3 = context.get("l3_core_tension", "")
        l4 = context.get("l4_project_task", "")
        l2 = context.get("l2_user_model", {})
        ai_section = ""
        if l3 or l4 or l2:
            ai_parts = []
            if l4:
                ai_parts.append(f"- JTBD任务: {l4[:200]}")
            if l3:
                ai_parts.append(f"- 核心张力: {l3[:200]}")
            if l2:
                ai_parts.append(f"- 用户画像: {_json.dumps(l2, ensure_ascii=False)[:200]}")
            ai_section = "\n【AI初步分析（参考，可修正）】\n" + "\n".join(ai_parts) + "\n"

        dim_ids = [d["id"] for d in dims]

        user_input = context.get("user_input", "")[:800]

        return f"""你是一位有15年经验的室内设计需求分析师。你刚完成了与客户的三轮深度访谈，现在需要撰写一份"需求洞察报告"。

这份报告的读者是：后续的设计专家团队。他们需要从你的报告中快速理解：这个客户到底要什么、为什么要、有什么限制、重点在哪。

**你的分析方法**：
1. 交叉验证：将三轮信息互相印证，找出一致性和矛盾点
2. 读出言外之意：用户说"简约"可能意味着"好打理"，说"有品质"可能意味着"给客人看"
3. 专业重构：用设计行业的专业框架重新组织信息，而非按问卷顺序罗列
4. 具体化：所有描述必须针对这个具体项目，禁止使用"满足需求""提升品质"等万能废话

=== 三轮访谈记录 ===

【客户原始描述】
{user_input}

【第一轮：客户确认的核心任务】
{tasks_text}

【第二轮：客户补充的详细信息】
{gap_items}

【第三轮：客户的设计偏好维度及权重】
{dim_items}
{ai_section}
=== 输出要求 ===

请输出JSON格式的需求洞察报告。注意：
- project_essence: 不是功能描述，而是"这个项目对客户意味着什么"（1-2句，要有洞察力）
- executive_summary.one_sentence: 30-50字，后续所有专家第一眼看到的就是这句话，必须精准概括
- primary_goal: JTBD格式（"通过...实现..."或"为...打造..."），50-80字
- understanding_comparison: user_expression摘录客户原话，ai_understanding是你的专业改写
- constraints: 只填客户明确提到的，未提及的设为null
- design_priorities: 必须使用客户选择的维度ID（{dim_ids}），key_requirements是你从三轮数据中综合提炼的该维度具体需求
- core_tension: 这个项目最核心的矛盾是什么？必须是具体的（如"30万预算 vs 全屋定制品质追求"），不要泛泛而谈
- identified_risks: 针对这个项目的具体风险，不要写"预算可能超支"这种废话，要写"客户期望的全屋智能系统（约5万）可能挤压软装预算"
- key_conflicts: 需要设计团队在方案中明确取舍的矛盾点
- implicit_requirements: 客户没说但你从访谈中推断出的需求，必须给出推断依据

```json
{{
    "project_essence": "string",
    "executive_summary": {{
        "one_sentence": "string (30-50字)",
        "what": "string",
        "why": "string (深层动机，不是表面需求)",
        "how": "string (策略方向)",
        "constraints_summary": "string (关键约束一句话)"
    }},
    "project_objectives": {{
        "primary_goal": "string (JTBD格式，50-80字)",
        "primary_goal_source": "synthesis",
        "secondary_goals": ["string"],
        "success_criteria": ["string (具体可验证的标准)"],
        "understanding_comparison": {{
            "user_expression": "string (摘录原话)",
            "ai_understanding": "string (专业改写)",
            "alignment_note": "string (分析说明)"
        }}
    }},
    "constraints": {{
        "budget": {{"type": "hard_constraint", "total": "string|null", "flexibility": "high/medium/low", "source": "questionnaire_step2"}} ,
        "timeline": {{"type": "hard_constraint", "duration": "string|null", "flexibility": "high/medium/low", "source": "questionnaire_step2"}},
        "space": {{"type": "hard_constraint", "area": "string|null", "layout": "string|null", "flexibility": "none", "source": "questionnaire_step2"}}
    }},
    "design_priorities": [
        {{
            "rank": 1,
            "dimension": "维度ID",
            "label": "维度中文名",
            "weight": 0.35,
            "key_requirements": ["从三轮数据综合提炼的该维度具体需求"],
            "rationale": "为什么这个维度对这个客户特别重要（结合访谈内容）"
        }}
    ],
    "core_tension": {{
        "description": "string (必须包含具体的 A vs B)",
        "strategic_options": [
            {{"stance": "策略名", "approach": "具体方法50-80字", "risk": "风险", "benefit": "收益"}}
        ],
        "recommended_stance": "string"
    }},
    "identified_risks": [
        {{"risk_id": "R1", "risk": "string (具体风险)", "severity": "high/medium/low", "type": "strategic/resource/execution", "mitigation": "string (具体措施)"}}
    ],
    "implicit_requirements": [
        {{"requirement": "string", "evidence": "string (从哪句话推断)", "priority": "high/medium/low"}}
    ],
    "key_conflicts": [
        {{"conflict": "string", "sides": ["string", "string"], "recommended_approach": "string", "trade_off": "string"}}
    ],
    "special_requirements": [
        {{"requirement": "string", "emphasis_level": "high/medium", "source": "string", "context": "string"}}
    ],
    "task_corrections": [
        {{
            "task_id": "string (已有任务ID，新增任务为null)",
            "action": "enhance|reprioritize|invalidate|add",
            "title": "string (仅action=add时必填，新任务标题)",
            "description": "string (仅action=add时必填，新任务描述)",
            "new_priority": "high|medium|low (仅reprioritize时必填)",
            "enhance_note": "string (仅enhance时必填，补充到描述的约束/上下文)",
            "reason": "string (必填，引用具体的补充信息或偏好维度名+数值作为校正依据)",
            "source": "gap_filling|radar|cross_validation (校正来源)"
        }}
    ],
    "radar_response_map": [
        {{
            "dimension_id": "string (维度ID，必须与design_priorities中的维度ID一致)",
            "dimension_label": "string (维度中文名)",
            "design_driver": "string (一句话设计驱动意图，如'极致实用是核心驱动，功能分区需深入到方案级')",
            "responses": [
                {{
                    "action_type": "material_constraint|spatial_strategy|task_boost|reference_injection|budget_hint|technology_requirement",
                    "action_detail": "string (具体设计响应动作)"
                }}
            ],
            "coverage_reason": "string (若responses为空，解释为什么此维度无需具体响应动作)"
        }}
    ]
}}
```

**关于 task_corrections**:
- enhance: 基于补充信息为已有任务添加更具体的约束条件或执行上下文（如明确预算、工期、材料要求）
- reprioritize: 基于偏好雷达权重调整任务优先级（高权重相关任务提升，低权重相关任务降级）
- invalidate: 当补充信息揭示某任务前提不成立或已被其他任务覆盖时标记为无效
- add: 三轮信息综合后发现的重要遗漏任务（最多3个），必须说明为什么原任务列表未覆盖
- 每条 reason 必须包含维度ID标识（如「function_intensity」），便于精确回溯
- 每条 reason 必须引用具体信号（如"用户补充预算30万""功能性偏好权重85"），禁止泛泛而谈

**关于 radar_response_map（🆕 v14.0 设计驱动响应映射）**:
- 每个在 design_priorities 中出现的维度，都必须在 radar_response_map 中有一条记录
- design_driver 是一句话的设计意图翻译，不要只写权重数字，要写出设计含义
- responses 是具体的设计响应动作（材料约束、空间策略、技术要求等），允许为空
- 若 responses 为空，必须在 coverage_reason 中解释原因（如"此维度调整幅度极小，无需特殊响应"）
- design_priorities 中每个维度的 weight 不得偏离用户滑块归一化值（滑块值/100）超过 ±0.15

**禁止事项**：
- 禁止复制粘贴用户原话作为分析结论
- 禁止使用"满足用户需求""提升空间品质""打造理想家居"等空洞表述
- 禁止编造用户未提及的约束条件（设为null）
- 禁止使用通用风险模板，每条风险必须与本项目具体情况相关
- design_priorities的维度ID必须从{dim_ids}中选择
- 🚫 v8.1: 禁止对未知信息使用"待进一步明确""有待确认""需进一步了解""暂不明确"等占位词；对用户未提及的维度，应基于已知信息作出语义化推断，用具体的设计假设替代占位符"""

    @staticmethod
    def _llm_synthesize_insight(context: "Dict[str, Any]") -> "Dict[str, Any]":
        """Phase B: 单次LLM综合分析调用"""
        import json
        import re

        from ...utils.llm_retry import LLMRetryConfig, invoke_llm_with_retry

        llm = LLMFactory.create_llm(temperature=0.6, max_tokens=4000)
        prompt = RequirementsRestructuringEngine._build_synthesis_prompt(context)

        retry_config = LLMRetryConfig(max_attempts=2, min_wait=1.0, max_wait=5.0, multiplier=2.0, timeout=45.0)

        logger.info("🧠 [Phase B] 调用LLM进行综合分析...")
        response = invoke_llm_with_retry(llm, prompt, config=retry_config)
        content = response.content.strip() if hasattr(response, "content") else str(response).strip()

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            result = json.loads(json_match.group())
            logger.info("✅ [Phase B] JSON解析成功")
            return result

        raise ValueError("LLM响应未包含有效JSON")

    @staticmethod
    def _validate_synthesis_result(result: "Dict[str, Any]") -> bool:
        """校验LLM综合分析结果的完整性"""
        required_fields = [
            "project_essence",
            "executive_summary",
            "project_objectives",
            "design_priorities",
            "identified_risks",
        ]

        for field in required_fields:
            if field not in result or not result[field]:
                logger.warning(f"⚠️ [校验] 缺少必要字段: {field}")
                return False

        objectives = result.get("project_objectives", {})
        if not objectives.get("primary_goal") or len(objectives["primary_goal"]) < 10:
            logger.warning("⚠️ [校验] primary_goal 过短或缺失")
            return False

        exec_summary = result.get("executive_summary", {})
        if not exec_summary.get("one_sentence") or len(exec_summary["one_sentence"]) < 10:
            logger.warning("⚠️ [校验] executive_summary.one_sentence 过短或缺失")
            return False

        if len(result.get("project_essence", "")) < 15:
            logger.warning("⚠️ [校验] project_essence 过短")
            return False

        logger.info("✅ [校验] LLM输出通过完整性校验")
        return True

    @staticmethod
    def _format_synthesis_output(result: "Dict[str, Any]", context: "Dict[str, Any]") -> "Dict[str, Any]":
        """将LLM综合分析结果格式化为 RestructuredRequirements 格式"""

        # insight_summary 从 analysis_layers 提取（非LLM生成）
        insight_summary = RequirementsRestructuringEngine._extract_insight_summary_from_context(context)

        # 清理 constraints 中的 null 值
        constraints = result.get("constraints", {}) or {}
        constraints = {k: v for k, v in constraints.items() if v is not None}

        # 确保 design_priorities 字段与前端 TypeScript 类型匹配
        priorities = result.get("design_priorities", [])
        for idx, p in enumerate(priorities):
            p["rank"] = idx + 1
            if isinstance(p.get("weight"), str):
                try:
                    p["weight"] = float(p["weight"])
                except (ValueError, TypeError):
                    p["weight"] = 0.5
            # 前端读 dimension_id，LLM 输出 dimension
            if "dimension" in p and "dimension_id" not in p:
                p["dimension_id"] = p.pop("dimension")
            # 前端读 tendency，LLM 输出 key_requirements
            if "tendency" not in p:
                key_reqs = p.get("key_requirements", [])
                p["tendency"] = "、".join(key_reqs) if isinstance(key_reqs, list) else str(key_reqs)

        # 确保 identified_risks 同时有 description 和 risk 字段（前端优先读 description）
        risks = result.get("identified_risks", [])
        for r in risks:
            if "risk" in r and "description" not in r:
                r["description"] = r["risk"]
            elif "description" in r and "risk" not in r:
                r["risk"] = r["description"]

        # 确保 core_tension 字段与前端类型匹配
        core_tension = result.get("core_tension", {}) or {}
        if "description" in core_tension and "tension_statement" not in core_tension:
            core_tension["tension_statement"] = core_tension["description"]

        return {
            "metadata": {
                "document_version": "3.0",
                "generated_at": datetime.now().isoformat(),
                "generation_method": "llm_synthesis_v3",
                "data_sources": ["user_questionnaire", "ai_analysis_L1-L5", "original_input"],
                "llm_enhanced": True,
            },
            "project_objectives": result.get("project_objectives", {}),
            "constraints": constraints,
            "design_priorities": priorities,
            "core_tension": core_tension,
            "special_requirements": result.get("special_requirements", []),
            "identified_risks": risks,
            "insight_summary": insight_summary,
            "project_essence": result.get("project_essence", ""),
            "implicit_requirements": result.get("implicit_requirements", []),
            "key_conflicts": result.get("key_conflicts", []),
            "deliverable_expectations": ["设计策略文档", "空间布局建议", "材料选择指导", "预算分配框架"],
            "executive_summary": result.get("executive_summary", {}),
            # 🆕 v13.0: 任务校正指令（供 questionnaire_summary 应用）
            "task_corrections": result.get("task_corrections", []),
        }

    @staticmethod
    def _extract_insight_summary_from_context(context: "Dict[str, Any]") -> "Dict[str, Any]":
        """从 context 中提取 L1-L5 洞察摘要"""
        l1_facts = context.get("l1_facts", [])
        l2_model = context.get("l2_user_model", {})
        l3_tension = context.get("l3_core_tension", "")
        l4_task = context.get("l4_project_task", "")
        l5_sharpness = context.get("l5_sharpness", {})

        if not any([l1_facts, l2_model, l3_tension, l4_task]):
            return {
                "L1_key_facts": ["基于问卷数据分析"],
                "L2_user_profile": {"psychological": "追求品质与舒适", "aesthetic": "注重空间美感", "sociological": "重视家庭互动"},
                "L3_core_tension": "在有限条件下实现最优设计效果",
                "L4_project_task_jtbd": "打造满足核心需求的理想空间",
                "L5_sharpness_score": 60,
                "L5_sharpness_note": "基于问卷数据的基础洞察分析",
                "_status": "degraded",
            }

        return {
            "L1_key_facts": l1_facts[:3] if isinstance(l1_facts, list) else [],
            "L2_user_profile": {
                "psychological": str(l2_model.get("psychological", ""))[:100] if isinstance(l2_model, dict) else "",
                "aesthetic": str(l2_model.get("aesthetic", ""))[:100] if isinstance(l2_model, dict) else "",
                "sociological": str(l2_model.get("sociological", ""))[:100] if isinstance(l2_model, dict) else "",
            },
            "L3_core_tension": l3_tension[:200] if isinstance(l3_tension, str) else "",
            "L4_project_task_jtbd": l4_task[:200] if isinstance(l4_task, str) else "",
            "L5_sharpness_score": l5_sharpness.get("score", 0) if isinstance(l5_sharpness, dict) else 0,
            "L5_sharpness_note": l5_sharpness.get("note", "待分析") if isinstance(l5_sharpness, dict) else "待分析",
        }

    # ==================== v3.0: Fallback - 规则降级 ====================

    @staticmethod
    def _rule_based_fallback(
        questionnaire_data: "Dict[str, Any]",
        ai_analysis: "Dict[str, Any]",
        analysis_layers: "Dict[str, Any]",
        user_input: str,
        weight_interpretations: "Dict[str, Any] | None" = None,
    ) -> "Dict[str, Any]":
        """Fallback: 规则降级方案（复用现有 Step 1-8 逻辑，不使用LLM）"""
        logger.info("🔄 [Fallback] 执行规则降级重构")

        E = RequirementsRestructuringEngine

        objectives = E._extract_objectives_with_jtbd(
            questionnaire_data.get("core_tasks", []),
            analysis_layers.get("L4_project_task", "") if analysis_layers else "",
            user_input,
            use_llm=False,
        )
        constraints = E._identify_constraints(questionnaire_data.get("gap_filling", {}))
        priorities = E._build_priorities_with_insights(
            questionnaire_data.get("dimensions", {}),
            analysis_layers.get("L2_user_model", {}) if analysis_layers else {},
            analysis_layers.get("L3_core_tension", "") if analysis_layers else "",
            questionnaire_data.get("gap_filling", {}),
        )
        core_tension = E._extract_core_tension(
            analysis_layers.get("L3_core_tension", "") if analysis_layers else "",
            use_llm=False,
        )
        special_reqs = E._extract_special_requirements(user_input, questionnaire_data)
        risks = E._identify_risks_with_tension(constraints, priorities, objectives, core_tension)
        insight_summary = E._extract_insight_summary(analysis_layers if analysis_layers else {})
        executive_summary = E._generate_executive_summary(objectives, constraints, priorities, use_llm=False)
        deep_insights = E._fallback_deep_insights(user_input, questionnaire_data, objectives, constraints)

        # 🆕 v13.0: 规则降级的任务校正生成
        # 🆕 v14.0: 直接使用方法参数 weight_interpretations
        task_corrections = E._rule_based_task_corrections(
            questionnaire_data.get("core_tasks", []),
            questionnaire_data.get("gap_filling", {}),
            questionnaire_data.get("dimensions", {}),
            priorities,
            weight_interpretations=weight_interpretations,
        )

        # 规范化字段名以匹配前端类型定义
        for p in priorities:
            if "dimension" in p and "dimension_id" not in p:
                p["dimension_id"] = p.pop("dimension")
            if "tendency" not in p:
                key_reqs = p.get("key_requirements", [])
                p["tendency"] = "、".join(key_reqs) if isinstance(key_reqs, list) else str(key_reqs)
        for r in risks:
            if "risk" in r and "description" not in r:
                r["description"] = r["risk"]
            elif "description" in r and "risk" not in r:
                r["risk"] = r["description"]
        if core_tension and "description" in core_tension and "tension_statement" not in core_tension:
            core_tension["tension_statement"] = core_tension["description"]

        return {
            "metadata": {
                "document_version": "3.0-fallback",
                "generated_at": datetime.now().isoformat(),
                "generation_method": "rule_based_fallback",
                "data_sources": ["user_questionnaire", "ai_analysis_L1-L5", "original_input"],
                "llm_enhanced": False,
            },
            "project_objectives": objectives,
            "constraints": constraints,
            "design_priorities": priorities,
            "core_tension": core_tension,
            "special_requirements": special_reqs,
            "identified_risks": risks,
            "insight_summary": insight_summary,
            "project_essence": deep_insights.get("project_essence", ""),
            "implicit_requirements": deep_insights.get("implicit_requirements", []),
            "key_conflicts": deep_insights.get("key_conflicts", []),
            "deliverable_expectations": ["设计策略文档", "空间布局建议", "材料选择指导", "预算分配框架"],
            "executive_summary": executive_summary,
            # 🆕 v13.0: 规则降级的任务校正
            "task_corrections": task_corrections,
        }

    # ==================== 以下为原有私有方法（供 Fallback 使用） ====================

    # ==================== 🆕 v13.0: 规则降级任务校正 ====================

    # 维度-任务关键词映射表（标准维度 + 动态维度自动提取）
