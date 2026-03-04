"""
需求重组 输出/摘要 Mixin
由 scripts/refactor/_split_mt18_restructuring.py 自动生成 (MT-18)
"""
from __future__ import annotations

from typing import Any, Dict, List


class RestructuringOutputMixin:
    """Mixin — 需求重组 输出/摘要 Mixin"""
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
                    logger.info(" [v7.152] LLM深度分析成功")
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

