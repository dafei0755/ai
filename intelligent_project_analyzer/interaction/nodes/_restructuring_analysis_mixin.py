"""
需求重组 分析/提取 Mixin
由 scripts/refactor/_split_mt18_restructuring.py 自动生成 (MT-18)
"""
from __future__ import annotations

from typing import Any, Dict, List


class RestructuringAnalysisMixin:
    """Mixin — 需求重组 分析/提取 Mixin"""
    @staticmethod
    def _rule_based_task_corrections(
        core_tasks: List[Dict],
        gap_filling: Dict[str, Any],
        dimensions: Dict[str, Any],
        priorities: List[Dict],
        weight_interpretations: Dict[str, Any] | None = None,
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
                w = float(weight_val) if not isinstance(weight_val, int | float) else weight_val
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
        for _key, value in gap_filling.items():
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

