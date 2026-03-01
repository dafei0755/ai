"""
需求重构引擎 (Requirements Restructuring Engine)

职责：
将问卷数据 + AI洞察 + 用户原始输入重构为结构化的项目需求文档

核心理念：
不是机械回顾问卷答案，而是智能生成专业的需求文档，融合：
- 问卷数据（用户显性表达）
- L1-L5 AI洞察（深层理解）
- 原始输入（情感基调）

v7.135: 首次实现
v7.151: 升级为"需求洞察"模块
  - 新增 _llm_comprehensive_analysis: LLM深度分析生成项目本质、隐性需求、关键冲突
  - 优化 _extract_core_tension: LLM替换硬编码模板
  - 融合 L1-L5 洞察到主体: 用户表达 vs AI理解对比展示
  - 合并需求确认功能: 支持用户直接编辑
v3.0: 两阶段架构重构
  - Phase A: 规则化数据准备（收集整理原始数据）
  - Phase B: 单次LLM综合分析（生成全部输出字段）
  - Fallback: LLM失败时降级为规则提取
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

# 使用LLMFactory创建LLM实例
from ...services.llm_factory import LLMFactory


class RequirementsRestructuringEngine:
    """需求重构引擎 - 将问卷数据转化为结构化需求文档"""

    @staticmethod
    def restructure(
        questionnaire_data: "Dict[str, Any]",
        ai_analysis: "Dict[str, Any]",
        analysis_layers: "Dict[str, Any]",
        user_input: str,
        use_llm: bool = True,
    ) -> "Dict[str, Any]":
        """
        主重构流程 - v3.0 两阶段架构

        Phase A: 规则化数据准备（收集整理原始数据）
        Phase B: 单次LLM综合分析（生成全部输出字段）
        Fallback: LLM失败时降级为规则提取
        """
        logger.info("=" * 80)
        logger.info("🔧 [需求重构引擎 v3.0] 开始两阶段重构")
        logger.info("=" * 80)

        # Phase A: 收集整理原始数据
        context = RequirementsRestructuringEngine._prepare_synthesis_context(
            questionnaire_data, ai_analysis, analysis_layers, user_input
        )
        logger.info(
            f"✅ [Phase A] 数据准备完成: {len(context.get('core_tasks', []))}个任务, "
            f"{len(context.get('gap_filling_raw', {}))}个补充信息, "
            f"{len(context.get('dimensions', []))}个维度"
        )

        # Phase B: 单次LLM综合分析
        if use_llm:
            try:
                result = RequirementsRestructuringEngine._llm_synthesize_insight(context)
                if RequirementsRestructuringEngine._validate_synthesis_result(result):
                    doc = RequirementsRestructuringEngine._format_synthesis_output(result, context)
                    logger.info("✅ [Phase B] LLM综合分析完成")
                    logger.info(f"   - 项目本质: {doc.get('project_essence', '')[:50]}...")
                    logger.info(f"   - 项目目标: {doc.get('project_objectives', {}).get('primary_goal', '')[:50]}...")
                    logger.info(f"   - 设计重点: {len(doc.get('design_priorities', []))} 个维度")
                    logger.info(f"   - 约束条件: {len(doc.get('constraints', {}))} 项")
                    logger.info(f"   - 风险识别: {len(doc.get('identified_risks', []))} 项")
                    return doc
                else:
                    logger.warning("⚠️ [Phase B] LLM输出校验失败，降级为规则提取")
            except Exception as e:
                logger.warning(f"⚠️ [Phase B] LLM综合分析失败: {e}，降级为规则提取")

        # Fallback: 规则降级（复用现有逻辑）
        logger.info("🔄 [Fallback] 使用规则降级方案")
        return RequirementsRestructuringEngine._rule_based_fallback(
            questionnaire_data, ai_analysis, analysis_layers, user_input
        )

    # ==================== v3.0: Phase A - 数据准备 ====================

    @staticmethod
    def _prepare_synthesis_context(
        questionnaire_data: "Dict[str, Any]",
        ai_analysis: "Dict[str, Any]",
        analysis_layers: "Dict[str, Any]",
        user_input: str,
    ) -> "Dict[str, Any]":
        """Phase A: 收集整理原始数据为结构化 context"""

        context: "Dict[str, Any]" = {"user_input": user_input or ""}

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
- design_priorities的维度ID必须从{dim_ids}中选择"""

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
        # 🆕 v14.0: 传入 weight_interpretations 以生成设计驱动信号
        weight_interpretations = context.get("weight_interpretations") if isinstance(context, dict) else None
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
    DIMENSION_TASK_KEYWORDS: "Dict[str, List[str]]" = {
        "functionality": ["功能", "使用", "动线", "收纳", "布局", "分区", "空间"],
        "aesthetics": ["美学", "风格", "视觉", "色彩", "材质", "造型", "氛围"],
        "cost": ["预算", "成本", "造价", "资金", "费用"],
        "cost_control": ["预算", "成本", "造价", "资金", "费用"],
        "timeline": ["工期", "时间", "进度", "交付", "工程"],
        "sustainability": ["可持续", "环保", "节能", "绿色", "低碳"],
        "innovation": ["创新", "智能", "科技", "前沿", "数字"],
        "quality": ["品质", "质量", "精细", "工艺", "细节"],
        "cultural_authenticity": ["文化", "传统", "在地", "历史", "民族"],
        "spatial_atmosphere": ["氛围", "空间感", "光影", "情绪", "体验"],
        "emotional_resonance": ["情感", "共鸣", "归属", "记忆", "温度"],
    }

    @staticmethod
    def _rule_based_task_corrections(
        core_tasks: List[Dict],
        gap_filling: Dict[str, Any],
        dimensions: Dict[str, Any],
        priorities: List[Dict],
        weight_interpretations: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        纯规则的任务校正生成（无 LLM 调用）

        Phase 1: 雷达权重 → 设计驱动信号 → 优先级调整（reprioritize）  🆕 v14.0
        Phase 2: 信息补全 → 描述增强（enhance）
        Phase 3: 信息补全 → 新任务检测（add）
        """
        corrections: List[Dict[str, Any]] = []
        E = RequirementsRestructuringEngine

        # --- 收集维度关键词映射（静态 + 动态维度） ---
        dim_keywords = dict(E.DIMENSION_TASK_KEYWORDS)
        selected_dims = dimensions.get("selected", [])
        for dim in selected_dims:
            if isinstance(dim, dict):
                dim_id = dim.get("id", "")
                if dim_id not in dim_keywords:
                    # 动态维度：从 left_label / right_label / name 提取关键词
                    kws = []
                    for field in ("left_label", "right_label", "name", "description"):
                        val = dim.get(field, "")
                        if val and len(val) >= 2:
                            kws.append(val[:8])
                    if kws:
                        dim_keywords[dim_id] = kws

        weights = dimensions.get("weights", {}) or {}

        # --- Phase 1: 雷达权重 → 设计驱动信号 → 优先级调整 ---
        # 🆕 v14.0: 优先使用 weight_interpretations 的语义翻译结果
        for dim_id, weight_val in weights.items():
            try:
                w = float(weight_val) if not isinstance(weight_val, (int, float)) else weight_val
            except (ValueError, TypeError):
                continue

            kws = dim_keywords.get(dim_id, [])
            if not kws:
                continue

            dim_label = dim_id
            for d in selected_dims:
                if isinstance(d, dict) and d.get("id") == dim_id:
                    dim_label = d.get("name", dim_id)
                    break

            # 🆕 v14.0: 从 weight_interpretations 获取设计驱动信号
            interp = (weight_interpretations or {}).get(dim_id, {}) if weight_interpretations else {}
            tier = interp.get("tier", "")
            tendency = interp.get("tendency_label", "")
            design_intent = interp.get("design_intent", "")

            for task in core_tasks:
                task_text = (task.get("title", "") + " " + task.get("description", "")).lower()
                matched = any(kw in task_text for kw in kws)
                if not matched:
                    continue

                current_pri = task.get("priority", "medium")

                # 🆕 v14.0: 基于设计驱动信号生成更有意义的 reason
                if (tier == "core_driver" or w >= 75) and current_pri != "high":
                    reason = (
                        f"设计驱动力「{dim_label}」→ {tendency}：{design_intent[:60]}"
                        if tendency and design_intent
                        else f"偏好维度「{dim_label}」权重{int(w)}（≥75），提升关联任务优先级"
                    )
                    corrections.append(
                        {
                            "task_id": task.get("id"),
                            "action": "reprioritize",
                            "new_priority": "high",
                            "reason": reason,
                            "source": "radar",
                        }
                    )
                elif (tier == "de_emphasized" or w <= 25) and current_pri == "high":
                    reason = (
                        f"维度「{dim_label}」被弱化 → {tendency}，降低关联任务优先级以释放资源"
                        if tendency
                        else f"偏好维度「{dim_label}」权重{int(w)}（≤25），降低关联任务优先级"
                    )
                    corrections.append(
                        {
                            "task_id": task.get("id"),
                            "action": "reprioritize",
                            "new_priority": "low",
                            "reason": reason,
                            "source": "radar",
                        }
                    )

        # --- Phase 2: 信息补全 → 描述增强 ---
        constraint_keys_map = {
            "budget": ["预算", "造价", "成本", "费用"],
            "budget_details": ["预算", "造价", "成本", "费用"],
            "总预算": ["预算", "造价", "成本"],
            "预算范围": ["预算", "造价", "成本"],
            "timeline": ["工期", "时间", "进度"],
            "expected_duration": ["工期", "时间", "进度"],
            "工期": ["工期", "时间", "进度"],
            "时间要求": ["工期", "时间", "进度"],
            "space_details": ["面积", "空间", "布局"],
            "area": ["面积", "空间", "布局"],
            "面积": ["面积", "空间", "布局"],
        }

        for gf_key, gf_val in gap_filling.items():
            if gf_key.startswith("_") or not gf_val:
                continue
            val_str = str(gf_val)[:200]
            if len(val_str) < 5:
                continue

            match_kws = constraint_keys_map.get(gf_key, [])
            if not match_kws:
                continue

            for task in core_tasks:
                task_text = (task.get("title", "") + " " + task.get("description", "")).lower()
                if any(kw in task_text for kw in match_kws):
                    corrections.append(
                        {
                            "task_id": task.get("id"),
                            "action": "enhance",
                            "enhance_note": f"信息补全明确了{gf_key}: {val_str[:60]}",
                            "reason": f"用户补充了{gf_key}信息（{val_str[:40]}），为关联任务补充执行约束",
                            "source": "gap_filling",
                        }
                    )
                    break  # 每条补全信息只匹配第一个关联任务

        # --- Phase 3: 信息补全 → 新任务检测 ---
        existing_text = " ".join((t.get("title", "") + " " + t.get("description", "")) for t in core_tasks).lower()

        high_value_gap_keywords = [
            "法规",
            "规范",
            "限高",
            "容积率",
            "退界",
            "消防",
            "安全",
            "无障碍",
            "节能",
            "环保",
            "绿建",
            "智能",
            "家居系统",
            "弱电",
        ]
        add_count = 0
        for gf_key, gf_val in gap_filling.items():
            if add_count >= 3:
                break
            val_str = str(gf_val)
            if len(val_str) < 10:
                continue
            for kw in high_value_gap_keywords:
                if kw in val_str and kw not in existing_text:
                    corrections.append(
                        {
                            "task_id": None,
                            "action": "add",
                            "title": f"{kw}相关专项研究",
                            "description": f"用户补充信息提及{kw}，现有任务未覆盖，需专项调研: {val_str[:80]}",
                            "new_priority": "medium",
                            "reason": f"信息补全中发现关键维度「{kw}」（来自{gf_key}），原任务列表未涵盖",
                            "source": "gap_filling",
                        }
                    )
                    add_count += 1
                    break

        # 去重：同一 task_id 的同类 action 只保留第一个
        seen = set()
        deduplicated = []
        for c in corrections:
            key = (c.get("task_id"), c["action"])
            if key not in seen:
                seen.add(key)
                deduplicated.append(c)

        return deduplicated

    @staticmethod
    def _extract_objectives_with_jtbd(
        tasks: List[Dict], jtbd_insight: str, user_input: str, use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        从任务列表中提取项目目标 - 融合JTBD洞察

         v7.151: 增加用户表达 vs AI理解对比
         v7.152: 当JTBD洞察为空时，使用LLM智能改写用户目标
        """

        # 提取用户原始表达（从第一个任务或输入开头）
        user_expression = ""
        if tasks and len(tasks) > 0:
            user_expression = tasks[0].get("title", "")
        if not user_expression and user_input:
            # 提取用户输入的第一句话
            first_sentence = user_input.split("。")[0].split("，")[0][:50]
            user_expression = first_sentence

        # 优先使用JTBD洞察（L4层级，更深刻）
        if jtbd_insight and len(jtbd_insight) > 20:
            primary_goal = jtbd_insight
            source = "L4_JTBD_insight"
            ai_understanding = jtbd_insight
        elif use_llm and user_expression:
            #  v7.152: LLM智能改写用户目标
            try:
                enhanced = RequirementsRestructuringEngine._llm_enhance_goal(user_expression, user_input, tasks)
                if enhanced and len(enhanced) > len(user_expression):
                    primary_goal = enhanced
                    source = "llm_enhanced"
                    ai_understanding = enhanced
                else:
                    primary_goal = user_expression
                    source = "user_confirmed_task"
                    ai_understanding = user_expression
            except Exception as e:
                logger.warning(f"️ [v7.152] LLM目标增强失败: {e}")
                primary_goal = user_expression
                source = "user_confirmed_task"
                ai_understanding = user_expression
        elif tasks and len(tasks) > 0:
            primary_goal = tasks[0].get("title", "待明确")
            source = "user_confirmed_task"
            ai_understanding = primary_goal
        else:
            primary_goal = "待明确核心目标"
            source = "fallback"
            ai_understanding = ""

        # 次要目标（从任务列表2-4）
        secondary_goals = [t.get("title", "") for t in tasks[1:4] if t.get("title")]

        # 成功标准推断
        success_criteria = []
        for task in tasks[:3]:
            desc = task.get("description", "")
            if desc and len(desc) > 10:
                success_criteria.append(f"{task.get('title', '')}达到预期效果")

        if not success_criteria:
            success_criteria = ["满足核心功能需求", "符合预算和时间约束"]

        return {
            "primary_goal": primary_goal,
            "primary_goal_source": source,
            "secondary_goals": secondary_goals,
            "success_criteria": success_criteria,
            #  v7.151: 用户表达 vs AI理解对比
            "understanding_comparison": {
                "user_expression": user_expression,
                "ai_understanding": ai_understanding[:150] if ai_understanding else "",
                "alignment_note": "AI理解基于JTBD框架"
                if source == "L4_JTBD_insight"
                else ("AI智能改写" if source == "llm_enhanced" else "直接采用用户表达"),
            },
        }

    @staticmethod
    def _llm_enhance_goal(user_expression: str, user_input: str, tasks: List[Dict]) -> str:
        """
         v7.152: 使用LLM智能改写用户目标
        将用户的简单表达转化为专业的JTBD格式
        """
        from ...utils.llm_retry import LLMRetryConfig, invoke_llm_with_retry

        llm = LLMFactory.create_llm(temperature=0.6, max_tokens=200)

        # 收集任务上下文
        tasks_context = "\n".join([f"- {t.get('title', '')}" for t in tasks[:5] if t.get("title")]) if tasks else "无"

        prompt = f"""作为室内设计顾问，请将用户的简单需求表达改写为专业的项目目标描述（JTBD格式）。

【用户原始表达】
{user_expression}

【用户完整需求】
{user_input[:300]}

【相关任务】
{tasks_context}

请改写为专业的项目目标（一句话，50-80字）：
- 使用"通过...实现..."或"为...打造..."的句式
- 体现用户的深层诉求，而非表面功能
- 包含具体的价值承诺

改写后的目标："""

        retry_config = LLMRetryConfig(max_attempts=2, min_wait=0.5, max_wait=2.0, multiplier=2.0, timeout=10.0)

        response = invoke_llm_with_retry(llm, prompt, config=retry_config)
        content = response.content.strip() if hasattr(response, "content") else str(response).strip()

        # 清理响应
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]

        logger.info(f" [v7.152] LLM目标增强: {user_expression[:30]}... → {content[:50]}...")
        return content

    @staticmethod
    def _identify_constraints(gap_filling: Dict[str, Any]) -> Dict[str, Any]:
        """识别硬性约束"""

        constraints = {}

        # 预算约束
        budget_keys = ["budget", "budget_details", "总预算", "预算范围"]
        budget_text = ""
        for key in budget_keys:
            if key in gap_filling:
                budget_text = str(gap_filling[key])
                break

        if budget_text:
            constraints["budget"] = {
                "type": "hard_constraint",
                "total": budget_text,
                "breakdown": gap_filling.get("budget_breakdown", {}),
                "flexibility": RequirementsRestructuringEngine._infer_flexibility(budget_text, "budget"),
                "source": "questionnaire_step2",
            }

        # 时间约束
        timeline_keys = ["timeline", "expected_duration", "工期", "时间要求"]
        timeline_text = ""
        for key in timeline_keys:
            if key in gap_filling:
                timeline_text = str(gap_filling[key])
                break

        if timeline_text:
            constraints["timeline"] = {
                "type": "hard_constraint",
                "duration": timeline_text,
                "milestones": gap_filling.get("time_constraints", []),
                "flexibility": RequirementsRestructuringEngine._infer_flexibility(timeline_text, "timeline"),
                "source": "questionnaire_step2",
            }

        # 空间约束
        space_keys = ["space_details", "area", "面积", "空间"]
        space_data = {}
        for key in space_keys:
            if key in gap_filling:
                space_data = gap_filling[key] if isinstance(gap_filling[key], dict) else {"area": gap_filling[key]}
                break

        if space_data or any(k in gap_filling for k in ["area", "layout"]):
            constraints["space"] = {
                "type": "hard_constraint",
                "area": space_data.get("area", gap_filling.get("area", "")),
                "layout": space_data.get("layout", gap_filling.get("layout", "")),
                "flexibility": "none",
                "source": "user_input + questionnaire_step2",
            }

        return constraints

    @staticmethod
    def _build_priorities_with_insights(
        dimensions: Dict[str, Any], user_model: Dict[str, Any], core_tension: str, gap_filling: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """构建设计重点列表 - 融合用户画像和核心张力"""

        selected_dims = dimensions.get("selected", [])
        weights = dimensions.get("weights") or {}  #  v7.150: 防御性处理 None

        #  v7.150: 确保 weights 不为 None（TypedDict 可能返回 None 而非默认值）
        if weights is None:
            logger.warning("️ [v7.150] weights 为 None，使用空字典")
            weights = {}

        if not selected_dims:
            logger.warning("️ 未找到选定的维度，使用默认维度")
            selected_dims = ["functionality", "aesthetics"]

        priorities = []

        dimension_labels = {
            "functionality": "功能性",
            "aesthetics": "美学",
            "sustainability": "可持续性",
            "cost": "成本控制",
            "timeline": "时间管理",
            "quality": "品质感",
            "innovation": "创新性",
        }

        for idx, dim in enumerate(selected_dims):
            #  v7.148: 修复类型不匹配 - 支持 dict 和 str 格式的维度
            if isinstance(dim, dict):
                dim_id = dim.get("id")
                dim_name = dim.get("name", dim_id)
                if not dim_id:
                    logger.warning(f"️ [Dimension {idx}] 维度对象缺少 'id' 字段，跳过: {dim}")
                    continue
            elif isinstance(dim, str):
                dim_id = dim
                dim_name = dimension_labels.get(dim, dim)
            else:
                logger.error(f" [Dimension {idx}] 不支持的维度类型: {type(dim)}，跳过")
                continue

            logger.debug(f" [Dimension {idx}] 处理维度: {dim_id} ({dim_name})")

            # 从gap_filling中提取关键需求（现在传递字符串ID）
            # v8.1: 传递 dim_meta（含left_label/right_label/default_value），支持未知维度兜底
            dim_meta = dim if isinstance(dim, dict) else {}
            key_reqs = RequirementsRestructuringEngine._extract_key_requirements_for_dimension(
                dim_id, gap_filling, dimension_meta=dim_meta
            )

            #  从L2用户画像中增强关键需求
            if dim_id == "aesthetics" and "aesthetic" in user_model:
                aesthetic_profile = user_model.get("aesthetic", "")
                if aesthetic_profile and len(aesthetic_profile) > 10:
                    key_reqs.insert(0, f"美学偏好: {aesthetic_profile[:80]}")

            if dim_id == "functionality" and "psychological" in user_model:
                psych_needs = user_model.get("psychological", "")
                if psych_needs and len(psych_needs) > 10:
                    key_reqs.insert(0, f"心理需求: {psych_needs[:80]}")

            weight = weights.get(dim_id, 1.0 / len(selected_dims) if selected_dims else 0.5)

            priority = {
                "rank": idx + 1,
                "dimension": dim_id,  #  v7.148: 使用提取的维度ID
                "label": dimension_labels.get(dim_id, dim_name),  #  优先使用映射名称，否则使用原始名称
                "weight": weight,
                "key_requirements": key_reqs[:4],  # 限制最多4个
                "derived_from": "questionnaire_step3 + L2_insights",
            }

            #  如果有核心张力且是第一优先级，添加张力说明
            if idx == 0 and core_tension and len(core_tension) > 20:
                priority["_core_tension_note"] = f"核心张力: {core_tension[:100]}"

            priorities.append(priority)

        # 按权重排序
        priorities.sort(key=lambda x: x["weight"], reverse=True)

        # 重新分配rank
        for idx, p in enumerate(priorities):
            p["rank"] = idx + 1

        return priorities

    @staticmethod
    def _extract_key_requirements_for_dimension(
        dimension: str, gap_filling: Dict[str, Any], dimension_meta: Dict = None
    ) -> List[str]:
        """从gap_filling中提取与维度相关的关键需求

        v8.1: 新增 dimension_meta 参数，对未知维度用 left_label/right_label 生成语义化需求，
              彻底消除"待进一步明确"废话
        """

        # 维度关键词映射（7个内置维度）
        dimension_keywords = {
            "functionality": ["功能", "使用", "动线", "收纳", "布局", "实用"],
            "aesthetics": ["美学", "风格", "色彩", "采光", "视觉", "美观"],
            "sustainability": ["环保", "节能", "可持续", "绿色", "生态"],
            "cost": ["预算", "成本", "价格", "经济", "节省"],
            "timeline": ["时间", "工期", "进度", "交付", "周期"],
            "quality": ["品质", "质量", "高级", "精致"],
            "innovation": ["创新", "独特", "个性", "新颖"],
        }

        # 对新维度：从 dimension_meta 中提取关键词扩充匹配范围
        if dimension_meta and dimension not in dimension_keywords:
            left = dimension_meta.get("left_label", "")
            right = dimension_meta.get("right_label", "")
            extra_keywords = [w for w in [left, right] if w and len(w) > 1]
            dimension_keywords[dimension] = extra_keywords

        keywords = dimension_keywords.get(dimension, [])
        requirements = []

        # 从gap_filling各字段中匹配关键词
        for key, value in gap_filling.items():
            if isinstance(value, str) and value:
                for keyword in keywords:
                    if keyword in value:
                        # 提取包含关键词的句子或短语
                        req_text = value[:50] + ("..." if len(value) > 50 else "")
                        requirements.append(req_text)
                        break

        # 去重
        requirements = list(dict.fromkeys(requirements))[:3]

        # 如果没有匹配，使用默认值
        if not requirements:
            default_reqs = {
                "functionality": ["满足基本功能需求"],
                "aesthetics": ["符合审美期望"],
                "sustainability": ["考虑环保因素"],
                "cost": ["控制成本在预算内"],
                "timeline": ["按时完成交付"],
                "quality": ["确保品质标准"],
                "innovation": ["追求设计创新"],
            }
            req = default_reqs.get(dimension)
            if req:
                requirements = req
            elif dimension_meta:
                # v8.1: 对未知维度，用 left_label/right_label/default_value 构造语义化需求
                left = dimension_meta.get("left_label", "")
                right = dimension_meta.get("right_label", "")
                default_val = dimension_meta.get("default_value", 50)
                dim_name = dimension_meta.get("name") or dimension.replace("_", " ")
                if left and right:
                    if default_val >= 65:
                        requirements = [f"{right}导向", f"在{dim_name}上侧重{right}方向的设计决策"]
                    elif default_val <= 35:
                        requirements = [f"{left}导向", f"在{dim_name}上侧重{left}方向的设计决策"]
                    else:
                        requirements = [f"{left}与{right}之间取得平衡", f"需在{left}和{right}间做出明确取舍"]
                elif right or left:
                    requirements = [f"{right or left}导向设计"]
                else:
                    requirements = [f"{dim_name}相关需求待明确"]
            else:
                requirements = ["待进一步明确"]

        return requirements

    @staticmethod
    def _extract_core_tension(tension_text: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        提取核心张力（L3洞察）

         v7.151: 使用LLM生成个性化策略，替换硬编码模板
        """

        if not tension_text or len(tension_text) < 20:
            return {}

        #  v7.151: 尝试使用LLM生成个性化策略
        if use_llm:
            try:
                strategic_options = RequirementsRestructuringEngine._llm_generate_tension_strategies(tension_text)
                if strategic_options:
                    return {
                        "description": tension_text[:200],
                        "strategic_options": strategic_options,
                        "recommended_stance": strategic_options[0].get("stance", "平衡处理")
                        if strategic_options
                        else "待分析",
                        "source": "L3_core_tension_analysis_llm_enhanced",
                    }
            except Exception as e:
                logger.warning(f"️ [v7.151] LLM生成张力策略失败: {e}，使用默认模板")

        # 降级：使用默认模板
        return {
            "description": tension_text[:200],
            "strategic_options": [
                {"stance": "拥抱张力", "approach": "将张力作为设计语言的一部分", "risk": "可能被误解为妥协"},
                {"stance": "化解张力", "approach": "通过设计智慧降低矛盾", "risk": "需要更多时间和专业知识"},
                {"stance": "转化张力", "approach": "分阶段实施，逐步优化", "risk": "初期效果可能不够理想"},
            ],
            "recommended_stance": "化解张力",
            "source": "L3_core_tension_analysis",
        }

    @staticmethod
    def _llm_generate_tension_strategies(tension_text: str) -> List[Dict[str, Any]]:
        """
        v7.151: 使用LLM生成针对具体张力的个性化策略
        """
        import json
        import re

        from ...utils.llm_retry import LLMRetryConfig, invoke_llm_with_retry

        llm = LLMFactory.create_llm(temperature=0.6, max_tokens=600)

        prompt = f"""作为室内设计策略顾问，针对以下项目核心张力，生成3个具体的应对策略。

【核心张力】
{tension_text[:300]}

请针对这个具体的张力，生成3个不同的策略选项。每个策略需要：
1. stance: 策略立场名称（如"预算优先"、"品质妥协"、"分期实现"等，要与具体张力相关）
2. approach: 具体实施方法（50-80字，要可执行）
3. risk: 潜在风险（20-40字）
4. benefit: 预期收益（20-40字）

按推荐程度从高到低排序。输出JSON数组：
```json
[
    {{"stance": "...", "approach": "...", "risk": "...", "benefit": "..."}},
    ...
]
```"""

        retry_config = LLMRetryConfig(max_attempts=2, min_wait=1.0, max_wait=3.0, multiplier=2.0, timeout=15.0)

        response = invoke_llm_with_retry(llm, prompt, config=retry_config)
        content = response.content.strip() if hasattr(response, "content") else str(response).strip()

        # 提取JSON数组
        json_match = re.search(r"\[[\s\S]*\]", content)
        if json_match:
            strategies = json.loads(json_match.group())
            if isinstance(strategies, list) and len(strategies) > 0:
                logger.info(f" [v7.151] LLM生成了{len(strategies)}个张力策略")
                return strategies

        return []

    @staticmethod
    def _extract_special_requirements(user_input: str, questionnaire_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取特殊需求（用户特别强调的点）"""

        special_reqs = []

        # 从用户原始输入中识别强调词
        emphasis_keywords = ["注重", "强调", "重点", "特别", "希望", "必须", "一定要", "关注"]

        sentences = user_input.replace("。", "，").split("，")
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            for keyword in emphasis_keywords:
                if keyword in sent:
                    special_reqs.append(
                        {
                            "requirement": sent,
                            "emphasis_level": "high",
                            "source": "user_input原话",
                            "context": f"用户明确表达了对'{sent[:20]}'的重视",
                        }
                    )
                    break

        # 从问卷任务中识别高优先级项
        tasks = questionnaire_data.get("core_tasks", [])
        for task in tasks:
            if task.get("priority") == "high":
                special_reqs.append(
                    {
                        "requirement": task.get("title", ""),
                        "emphasis_level": "high",
                        "source": "questionnaire_step1",
                        "context": "用户在问卷中标记为高优先级",
                    }
                )

        # 去重（基于requirement文本）
        seen = set()
        unique_reqs = []
        for req in special_reqs:
            req_text = req["requirement"][:30]
            if req_text not in seen:
                seen.add(req_text)
                unique_reqs.append(req)

        return unique_reqs[:5]  # 最多5个

    @staticmethod
    def _identify_risks_with_tension(
        constraints: Dict[str, Any], priorities: List[Dict], objectives: Dict[str, Any], core_tension: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """自动识别潜在风险 - 核心张力即风险点"""

        risks = []

        #  风险1: 核心张力本身就是最大的风险/机遇
        if core_tension and core_tension.get("description"):
            risks.append(
                {
                    "risk_id": "R1",
                    "risk": f"核心张力: {core_tension['description'][:150]}",
                    "severity": "high",
                    "type": "strategic",
                    "source": "L3_core_tension_analysis",
                    "mitigation": "需要在设计中明确选择拥抱、化解或转化这一张力",
                }
            )

        # 风险2: 预算与功能需求的张力
        if "budget" in constraints and len(priorities) >= 2:
            high_priority_count = sum(1 for p in priorities if p["weight"] > 0.25)
            if high_priority_count >= 2:
                risks.append(
                    {
                        "risk_id": "R2",
                        "risk": "多个高优先级需求可能超出预算范围",
                        "severity": "medium",
                        "type": "resource",
                        "source": "constraints_analysis",
                        "mitigation": f"建议按优先级分阶段实施，先满足{priorities[0]['label']}（权重{int(priorities[0]['weight']*100)}%）",
                    }
                )

        # 风险3: 时间约束紧张
        if "timeline" in constraints:
            timeline_text = constraints["timeline"].get("duration", "").lower()
            if any(word in timeline_text for word in ["紧急", "加急", "1个月", "2周", "急"]):
                risks.append(
                    {
                        "risk_id": "R3",
                        "risk": "时间要求较紧，可能影响设计深度",
                        "severity": "high",
                        "type": "execution",
                        "source": "constraints_analysis",
                        "mitigation": "建议简化部分非核心设计环节，专注关键交付物",
                    }
                )

        # 风险4: 目标过多导致资源分散
        if len(objectives.get("secondary_goals", [])) > 3:
            risks.append(
                {
                    "risk_id": "R4",
                    "risk": "次要目标过多，可能导致资源分散",
                    "severity": "low",
                    "type": "strategic",
                    "source": "objectives_analysis",
                    "mitigation": "建议明确优先级，聚焦核心目标",
                }
            )

        return risks

    @staticmethod
    def _extract_insight_summary(analysis_layers: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取L1-L5洞察摘要

         v7.152: 当 analysis_layers 为空时返回更有意义的提示
         v7.153: 改用降级策略而非 pending 状态，确保前端能正常展示
        """

        #  v7.153: 检测空数据 - 改用降级策略
        if not analysis_layers:
            logger.warning("️ [v7.153] analysis_layers 为空，使用规则降级值（非 pending）")
            return {
                "L1_key_facts": ["基于问卷数据分析"],
                "L2_user_profile": {"psychological": "追求品质与舒适", "aesthetic": "注重空间美感", "sociological": "重视家庭互动"},
                "L3_core_tension": "在有限条件下实现最优设计效果",
                "L4_project_task_jtbd": "打造满足核心需求的理想空间",
                "L5_sharpness_score": 60,  #  v7.153: 使用中等分数而非 -1
                "L5_sharpness_note": "基于问卷数据的基础洞察分析",
                "_status": "degraded",  #  v7.153: 标记为降级而非 pending
            }

        l1_facts = analysis_layers.get("L1_facts", [])
        l2_model = analysis_layers.get("L2_user_model", {})
        l3_tension = analysis_layers.get("L3_core_tension", "")
        l4_task = analysis_layers.get("L4_project_task", "")
        l5_sharpness = analysis_layers.get("L5_sharpness", {})

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

    @staticmethod
    def _generate_executive_summary(
        objectives: Dict[str, Any], constraints: Dict[str, Any], priorities: List[Dict], use_llm: bool = True
    ) -> Dict[str, Any]:
        """生成执行摘要（可选LLM）"""

        # 简单拼接版本（不使用LLM）
        primary_goal = objectives.get("primary_goal", "待明确")

        # what
        what = primary_goal[:50] if len(primary_goal) > 50 else primary_goal

        # constraints_summary
        constraint_parts = []
        if "budget" in constraints:
            constraint_parts.append(f"预算{constraints['budget']['total']}")
        if "timeline" in constraints:
            constraint_parts.append(f"时间{constraints['timeline']['duration']}")
        if "space" in constraints:
            constraint_parts.append(f"面积{constraints['space']['area']}")

        constraints_summary = " | ".join(constraint_parts) if constraint_parts else "待明确"

        # how
        if priorities:
            top_priorities = " + ".join([f"{p['label']}({int(p['weight']*100)}%)" for p in priorities[:2]])
            how = f"通过{top_priorities}实现空间价值最大化"
        else:
            how = "通过系统化设计实现目标"

        # one_sentence (如果使用LLM，可以生成更流畅的描述)
        if use_llm:
            try:
                one_sentence = RequirementsRestructuringEngine._llm_generate_one_sentence(
                    primary_goal, constraints_summary, how
                )
            except Exception as e:
                logger.warning(f"️ LLM生成摘要失败: {e}，使用简单版本")
                one_sentence = f"{what}，{how}"
        else:
            one_sentence = f"{what}，{how}"

        return {
            "one_sentence": one_sentence,
            "what": what,
            "why": "满足用户核心需求",
            "how": how,
            "constraints_summary": constraints_summary,
        }

    @staticmethod
    def _llm_generate_one_sentence(goal: str, constraints: str, approach: str) -> str:
        """使用LLM生成流畅的一句话摘要"""

        try:
            #  v7.143: 使用llm_retry模块统一的重试机制，替代手动超时
            from ...utils.llm_retry import LLMRetryConfig, invoke_llm_with_retry

            llm = LLMFactory.create_llm(temperature=0.7, max_tokens=200)

            prompt = f"""基于以下信息，生成一句话项目摘要（30-50字）。

项目目标：{goal}
核心约束：{constraints}
实现方式：{approach}

要求：
1. 一句话概括项目核心价值
2. 语言简洁专业，避免冗余
3. 突出用户获得的价值
4. 30-50字

一句话摘要："""

            #  v7.143: 使用统一的LLM重试机制
            # 配置: 最多3次尝试，每次15秒超时，指数退避
            retry_config = LLMRetryConfig(max_attempts=3, min_wait=1.0, max_wait=5.0, multiplier=2.0, timeout=15.0)

            logger.info(" [LLM摘要] 使用重试机制调用LLM (最多3次尝试, 每次15秒超时)")
            response = invoke_llm_with_retry(llm, prompt, config=retry_config)
            summary = response.content.strip() if hasattr(response, "content") else str(response).strip()

            logger.info(f" [LLM摘要] 生成成功: {summary}")
            return summary

        except Exception as e:
            logger.warning(f"️ [LLM摘要] 所有重试失败: {e}，使用简单版本")
            return f"{goal}，{approach}"

    @staticmethod
    def _infer_flexibility(text: str, constraint_type: str) -> str:
        """推断约束的灵活性"""

        text_lower = text.lower()

        # 检查用户是否使用了灵活性表述
        flexible_keywords = ["左右", "大约", "可以调整", "弹性", "灵活", "上下"]
        strict_keywords = ["必须", "不超过", "固定", "上限", "不能", "严格"]

        if any(kw in text_lower for kw in strict_keywords):
            return "low"
        elif any(kw in text_lower for kw in flexible_keywords):
            return "high"
        else:
            return "medium"

    # ====================  v7.151: LLM深度分析方法 ====================

    @staticmethod
    def _llm_comprehensive_analysis(
        user_input: str,
        questionnaire_data: Dict[str, Any],
        analysis_layers: Dict[str, Any],
        objectives: Dict[str, Any],
        constraints: Dict[str, Any],
        core_tension: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
         v7.151: LLM深度分析 - 生成项目本质、隐性需求、关键冲突
         v7.152: 增强独立性 - 即使 analysis_layers 为空也能生成高质量洞察

        将分散的问卷数据转化为连贯的、有洞察的结构化理解
        """
        try:
            from ...utils.llm_retry import LLMRetryConfig, invoke_llm_with_retry

            llm = LLMFactory.create_llm(temperature=0.5, max_tokens=1200)

            #  v7.152: 增强上下文准备 - 从问卷数据中提取更丰富的信息
            # 核心任务
            tasks = questionnaire_data.get("core_tasks", [])
            tasks_text = (
                "\n".join([f"- {t.get('title', '')}: {t.get('description', '')[:80]}" for t in tasks[:5]])
                if tasks
                else "未提供具体任务"
            )

            # 信息补全答案
            gap_filling = questionnaire_data.get("gap_filling", {})
            gap_items = []
            for k, v in gap_filling.items():
                if v and k not in ["timestamp", "submitted_at", "_meta"]:
                    gap_items.append(f"- {k}: {str(v)[:120]}")
            gap_text = "\n".join(gap_items[:10]) if gap_items else "未提供补充信息"

            # 雷达图维度偏好
            dimensions = questionnaire_data.get("dimensions", {})
            selected_dims = dimensions.get("selected", [])
            weights = dimensions.get("weights", {}) or {}
            dim_items = []
            for dim in selected_dims[:8]:
                if isinstance(dim, dict):
                    dim_id = dim.get("id", "")
                    dim_name = dim.get("name", dim_id)
                else:
                    dim_id = dim
                    dim_name = dim
                weight = weights.get(dim_id, 0.5) if isinstance(weights, dict) else 0.5
                dim_items.append(f"- {dim_name}: {int(weight * 100)}%")
            dimensions_text = "\n".join(dim_items) if dim_items else "未选择设计维度"

            # 已提取的约束条件
            constraint_parts = []
            if "budget" in constraints:
                constraint_parts.append(f"预算: {constraints['budget'].get('total', '未明确')}")
            if "timeline" in constraints:
                constraint_parts.append(f"时间: {constraints['timeline'].get('duration', '未明确')}")
            if "space" in constraints:
                constraint_parts.append(f"空间: {constraints['space'].get('area', '未明确')}")
            constraint_text = " | ".join(constraint_parts) if constraint_parts else "约束条件待明确"

            # 已提取的核心目标
            primary_goal = objectives.get("primary_goal", "")[:150] if objectives else ""

            #  v7.152: AI初步分析作为可选增强（不是必须）
            l3_tension = analysis_layers.get("L3_core_tension", "") if analysis_layers else ""
            l4_jtbd = analysis_layers.get("L4_project_task", "") if analysis_layers else ""

            ai_hints_section = ""
            if l3_tension or l4_jtbd:
                ai_hints_section = f"""
【AI初步分析（参考）】
- 核心张力: {l3_tension[:200] if l3_tension else '无'}
- 项目任务: {l4_jtbd[:200] if l4_jtbd else '无'}
"""
            else:
                ai_hints_section = "\n【注意】AI初步分析数据不可用，请完全基于用户输入进行推断\n"

            prompt = f"""作为资深室内设计顾问，请深度分析以下项目需求，生成专业洞察。

【用户原始需求】
{user_input[:600]}

【用户确认的核心任务】
{tasks_text}

【用户补充的详细信息】
{gap_text}

【用户的设计偏好维度】
{dimensions_text}

【已识别的约束条件】
{constraint_text}

【已提取的核心目标】
{primary_goal if primary_goal else '待从上下文推断'}
{ai_hints_section}

请基于以上信息，输出以下三个维度的深度洞察（JSON格式）：

1. project_essence (项目本质): 用1-2句话揭示这个项目的核心价值主张和情感诉求。
   - 不是功能描述，而是"为什么这个项目对用户重要"
   - 示例："通过现代简约设计语言，为年轻家庭创造既有仪式感又便于日常维护的居住空间"

2. implicit_requirements (隐性需求): 列出3-5个用户没有明确说出但可以合理推断的潜在需求：
   [
     {{"requirement": "需求描述", "evidence": "推断依据（来自用户输入的线索）", "priority": "high/medium/low"}}
   ]

3. key_conflicts (关键冲突): 识别2-3个需要在设计中解决的核心矛盾：
   [
     {{
       "conflict": "冲突描述（如'预算有限 vs 品质追求'）",
       "sides": ["矛盾的一面", "矛盾的另一面"],
       "recommended_approach": "建议的处理策略（50-80字）",
       "trade_off": "可能需要的取舍"
     }}
   ]

请用JSON格式输出：
```json
{{
    "project_essence": "...",
    "implicit_requirements": [...],
    "key_conflicts": [...]
}}
```"""

            retry_config = LLMRetryConfig(
                max_attempts=2, min_wait=1.0, max_wait=3.0, multiplier=2.0, timeout=25.0  # 增加超时时间
            )

            logger.info(" [v7.152] 调用LLM进行独立深度分析...")
            response = invoke_llm_with_retry(llm, prompt, config=retry_config)
            content = response.content.strip() if hasattr(response, "content") else str(response).strip()

            # 解析JSON
            import json
            import re

            # 提取JSON部分
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                result = json.loads(json_match.group())

                # 验证结果质量
                essence = result.get("project_essence", "")
                implicit_reqs = result.get("implicit_requirements", [])
                conflicts = result.get("key_conflicts", [])

                if essence and len(essence) > 20:
                    logger.info(f" [v7.152] LLM深度分析成功")
                    logger.info(f"   - 项目本质: {essence[:60]}...")
                    logger.info(f"   - 隐性需求: {len(implicit_reqs)}项")
                    logger.info(f"   - 关键冲突: {len(conflicts)}项")
                    return {
                        "project_essence": essence,
                        "implicit_requirements": implicit_reqs if isinstance(implicit_reqs, list) else [],
                        "key_conflicts": conflicts if isinstance(conflicts, list) else [],
                    }
                else:
                    logger.warning("️ [v7.152] LLM返回的项目本质过短，使用降级生成")
            else:
                logger.warning("️ [v7.152] LLM响应未包含有效JSON")

            #  v7.152: 降级策略 - 基于规则生成基础洞察
            return RequirementsRestructuringEngine._fallback_deep_insights(
                user_input, questionnaire_data, objectives, constraints
            )

        except Exception as e:
            logger.warning(f"️ [v7.152] LLM深度分析异常: {e}，使用降级生成")
            return RequirementsRestructuringEngine._fallback_deep_insights(
                user_input, questionnaire_data, objectives, constraints
            )

    @staticmethod
    def _fallback_deep_insights(
        user_input: str, questionnaire_data: Dict[str, Any], objectives: Dict[str, Any], constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
         v7.152: 降级策略 - 基于规则生成基础洞察
        当LLM调用失败时，使用规则提取基础信息
        """
        logger.info(" [v7.152] 使用降级策略生成基础洞察")

        # 从用户输入中提取关键词
        primary_goal = objectives.get("primary_goal", "") if objectives else ""

        # 生成基础项目本质
        if primary_goal:
            project_essence = f"实现{primary_goal[:50]}，满足用户的核心需求期望"
        elif user_input:
            first_sentence = user_input.split("。")[0][:80]
            project_essence = f"基于用户表达'{first_sentence}'，打造符合期望的设计方案"
        else:
            project_essence = "待深入分析用户需求，明确项目核心价值"

        # 基础隐性需求（通用）
        implicit_requirements = [
            {"requirement": "空间的舒适度和宜居性", "evidence": "任何室内设计项目的基本诉求", "priority": "high"},
            {"requirement": "设计方案的可落地性", "evidence": "从预算和时间约束推断", "priority": "medium"},
        ]

        # 基础冲突检测
        key_conflicts = []
        if "budget" in constraints and primary_goal and len(primary_goal) > 30:
            key_conflicts.append(
                {
                    "conflict": "预算控制 vs 设计品质",
                    "sides": ["有限的预算约束", "对设计品质的追求"],
                    "recommended_approach": "通过优化材料选择和施工工艺，在预算范围内最大化设计效果",
                    "trade_off": "可能需要在部分非核心区域简化设计",
                }
            )

        if "timeline" in constraints:
            timeline_text = constraints["timeline"].get("duration", "").lower()
            if any(word in timeline_text for word in ["紧急", "加急", "1个月", "2周", "急"]):
                key_conflicts.append(
                    {
                        "conflict": "时间紧迫 vs 设计深度",
                        "sides": ["紧迫的交付时间", "深入思考的设计需求"],
                        "recommended_approach": "聚焦核心功能区域，分阶段实施非紧急设计元素",
                        "trade_off": "初期方案可能需要后续优化迭代",
                    }
                )

        return {
            "project_essence": project_essence,
            "implicit_requirements": implicit_requirements,
            "key_conflicts": key_conflicts,
        }
