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
        questionnaire_data: Dict[str, Any],
        ai_analysis: Dict[str, Any],
        analysis_layers: Dict[str, Any],
        user_input: str,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        主重构流程

        Args:
            questionnaire_data: 问卷原始数据 (core_tasks, gap_filling, dimensions)
            ai_analysis: AI初步分析 (requirement_analysis)
            analysis_layers: L1-L5洞察层 (来自需求分析师)
            user_input: 用户原始输入
            use_llm: 是否使用LLM进行内容生成优化

        Returns:
            结构化需求文档
        """
        logger.info("=" * 80)
        logger.info("🔧 [需求重构引擎] 开始重构")
        logger.info("=" * 80)

        # Step 1: 提取核心目标（融合L4 JTBD）- 🔧 v7.152: 传递use_llm参数
        objectives = RequirementsRestructuringEngine._extract_objectives_with_jtbd(
            questionnaire_data.get("core_tasks", []),
            analysis_layers.get("L4_project_task", ""),
            user_input,
            use_llm=use_llm,
        )

        # Step 2: 识别核心约束
        constraints = RequirementsRestructuringEngine._identify_constraints(questionnaire_data.get("gap_filling", {}))

        # Step 3: 构建设计重点（融合L2 + L3 + 雷达维度）
        priorities = RequirementsRestructuringEngine._build_priorities_with_insights(
            questionnaire_data.get("dimensions", {}),
            analysis_layers.get("L2_user_model", {}),
            analysis_layers.get("L3_core_tension", ""),
            questionnaire_data.get("gap_filling", {}),
        )

        # Step 4: 提取核心张力（L3）- 🆕 v7.151: 传递use_llm参数
        core_tension = RequirementsRestructuringEngine._extract_core_tension(
            analysis_layers.get("L3_core_tension", ""), use_llm=use_llm
        )

        # Step 5: 识别特殊需求
        special_reqs = RequirementsRestructuringEngine._extract_special_requirements(user_input, questionnaire_data)

        # Step 6: 风险识别（融合L3张力）
        risks = RequirementsRestructuringEngine._identify_risks_with_tension(
            constraints, priorities, objectives, core_tension
        )

        # Step 7: 提取洞察摘要
        insight_summary = RequirementsRestructuringEngine._extract_insight_summary(analysis_layers)

        # Step 8: 生成执行摘要（可选LLM）
        executive_summary = RequirementsRestructuringEngine._generate_executive_summary(
            objectives, constraints, priorities, use_llm=use_llm
        )

        # 🆕 v7.151: Step 9 - LLM深度分析（项目本质、隐性需求、关键冲突）
        deep_insights = {}
        if use_llm:
            try:
                deep_insights = RequirementsRestructuringEngine._llm_comprehensive_analysis(
                    user_input=user_input,
                    questionnaire_data=questionnaire_data,
                    analysis_layers=analysis_layers,
                    objectives=objectives,
                    constraints=constraints,
                    core_tension=core_tension,
                )
                logger.info(f"✅ [v7.151] LLM深度分析完成")
                logger.info(f"   - 项目本质: {deep_insights.get('project_essence', '')[:50]}...")
                logger.info(f"   - 隐性需求: {len(deep_insights.get('implicit_requirements', []))}项")
                logger.info(f"   - 关键冲突: {len(deep_insights.get('key_conflicts', []))}项")
            except Exception as e:
                logger.warning(f"⚠️ [v7.151] LLM深度分析失败: {e}，使用空值")
                deep_insights = {"project_essence": "", "implicit_requirements": [], "key_conflicts": []}

        logger.info(f"✅ 需求重构完成")
        logger.info(f"   - 项目目标: {objectives.get('primary_goal', '')[:50]}...")
        logger.info(f"   - 设计重点: {len(priorities)} 个维度")
        logger.info(f"   - 约束条件: {len(constraints)} 项")
        logger.info(f"   - 风险识别: {len(risks)} 项")

        return {
            "metadata": {
                "document_version": "2.0",  # 🆕 v7.151: 升级版本号
                "generated_at": datetime.now().isoformat(),
                "generation_method": "questionnaire_based_with_ai_insights",
                "data_sources": ["user_questionnaire", "ai_analysis_L1-L5", "original_input"],
                "llm_enhanced": use_llm,  # 🆕 v7.151: 标记是否使用LLM增强
            },
            "project_objectives": objectives,
            "constraints": constraints,
            "design_priorities": priorities,
            "core_tension": core_tension,
            "special_requirements": special_reqs,
            "identified_risks": risks,
            "insight_summary": insight_summary,
            # 🆕 v7.151: 新增深度洞察字段
            "project_essence": deep_insights.get("project_essence", ""),
            "implicit_requirements": deep_insights.get("implicit_requirements", []),
            "key_conflicts": deep_insights.get("key_conflicts", []),
            "deliverable_expectations": ["设计策略文档", "空间布局建议", "材料选择指导", "预算分配框架"],
            "executive_summary": executive_summary,
        }

    @staticmethod
    def _extract_objectives_with_jtbd(
        tasks: List[Dict], jtbd_insight: str, user_input: str, use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        从任务列表中提取项目目标 - 融合JTBD洞察

        🆕 v7.151: 增加用户表达 vs AI理解对比
        🔧 v7.152: 当JTBD洞察为空时，使用LLM智能改写用户目标
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
            # 🔧 v7.152: LLM智能改写用户目标
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
                logger.warning(f"⚠️ [v7.152] LLM目标增强失败: {e}")
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
            # 🆕 v7.151: 用户表达 vs AI理解对比
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
        🆕 v7.152: 使用LLM智能改写用户目标
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

        logger.info(f"✅ [v7.152] LLM目标增强: {user_expression[:30]}... → {content[:50]}...")
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
        weights = dimensions.get("weights") or {}  # 🔧 v7.150: 防御性处理 None

        # 🔧 v7.150: 确保 weights 不为 None（TypedDict 可能返回 None 而非默认值）
        if weights is None:
            logger.warning("⚠️ [v7.150] weights 为 None，使用空字典")
            weights = {}

        if not selected_dims:
            logger.warning("⚠️ 未找到选定的维度，使用默认维度")
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
            # 🔧 v7.148: 修复类型不匹配 - 支持 dict 和 str 格式的维度
            if isinstance(dim, dict):
                dim_id = dim.get("id")
                dim_name = dim.get("name", dim_id)
                if not dim_id:
                    logger.warning(f"⚠️ [Dimension {idx}] 维度对象缺少 'id' 字段，跳过: {dim}")
                    continue
            elif isinstance(dim, str):
                dim_id = dim
                dim_name = dimension_labels.get(dim, dim)
            else:
                logger.error(f"❌ [Dimension {idx}] 不支持的维度类型: {type(dim)}，跳过")
                continue

            logger.debug(f"🔍 [Dimension {idx}] 处理维度: {dim_id} ({dim_name})")

            # 从gap_filling中提取关键需求（现在传递字符串ID）
            key_reqs = RequirementsRestructuringEngine._extract_key_requirements_for_dimension(
                dim_id, gap_filling  # ✅ 传递维度ID字符串
            )

            # 🔑 从L2用户画像中增强关键需求
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
                "dimension": dim_id,  # ✅ v7.148: 使用提取的维度ID
                "label": dimension_labels.get(dim_id, dim_name),  # ✅ 优先使用映射名称，否则使用原始名称
                "weight": weight,
                "key_requirements": key_reqs[:4],  # 限制最多4个
                "derived_from": "questionnaire_step3 + L2_insights",
            }

            # 🔑 如果有核心张力且是第一优先级，添加张力说明
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
    def _extract_key_requirements_for_dimension(dimension: str, gap_filling: Dict[str, Any]) -> List[str]:
        """从gap_filling中提取与维度相关的关键需求"""

        # 维度关键词映射
        dimension_keywords = {
            "functionality": ["功能", "使用", "动线", "收纳", "布局", "实用"],
            "aesthetics": ["美学", "风格", "色彩", "采光", "视觉", "美观"],
            "sustainability": ["环保", "节能", "可持续", "绿色", "生态"],
            "cost": ["预算", "成本", "价格", "经济", "节省"],
            "timeline": ["时间", "工期", "进度", "交付", "周期"],
            "quality": ["品质", "质量", "高级", "精致"],
            "innovation": ["创新", "独特", "个性", "新颖"],
        }

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
            requirements = default_reqs.get(dimension, ["待进一步明确"])

        return requirements

    @staticmethod
    def _extract_core_tension(tension_text: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        提取核心张力（L3洞察）

        🆕 v7.151: 使用LLM生成个性化策略，替换硬编码模板
        """

        if not tension_text or len(tension_text) < 20:
            return {}

        # 🆕 v7.151: 尝试使用LLM生成个性化策略
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
                logger.warning(f"⚠️ [v7.151] LLM生成张力策略失败: {e}，使用默认模板")

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
        🆕 v7.151: 使用LLM生成针对具体张力的个性化策略
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
                logger.info(f"✅ [v7.151] LLM生成了{len(strategies)}个张力策略")
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

        # 🔑 风险1: 核心张力本身就是最大的风险/机遇
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

        🔧 v7.152: 当 analysis_layers 为空时返回更有意义的提示
        🔧 v7.153: 改用降级策略而非 pending 状态，确保前端能正常展示
        """

        # 🔧 v7.153: 检测空数据 - 改用降级策略
        if not analysis_layers:
            logger.warning("⚠️ [v7.153] analysis_layers 为空，使用规则降级值（非 pending）")
            return {
                "L1_key_facts": ["基于问卷数据分析"],
                "L2_user_profile": {"psychological": "追求品质与舒适", "aesthetic": "注重空间美感", "sociological": "重视家庭互动"},
                "L3_core_tension": "在有限条件下实现最优设计效果",
                "L4_project_task_jtbd": "打造满足核心需求的理想空间",
                "L5_sharpness_score": 60,  # 🔧 v7.153: 使用中等分数而非 -1
                "L5_sharpness_note": "基于问卷数据的基础洞察分析",
                "_status": "degraded",  # 🔧 v7.153: 标记为降级而非 pending
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
                logger.warning(f"⚠️ LLM生成摘要失败: {e}，使用简单版本")
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
            # 🔧 v7.143: 使用llm_retry模块统一的重试机制，替代手动超时
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

            # 🔧 v7.143: 使用统一的LLM重试机制
            # 配置: 最多3次尝试，每次15秒超时，指数退避
            retry_config = LLMRetryConfig(max_attempts=3, min_wait=1.0, max_wait=5.0, multiplier=2.0, timeout=15.0)

            logger.info("🚀 [LLM摘要] 使用重试机制调用LLM (最多3次尝试, 每次15秒超时)")
            response = invoke_llm_with_retry(llm, prompt, config=retry_config)
            summary = response.content.strip() if hasattr(response, "content") else str(response).strip()

            logger.info(f"✅ [LLM摘要] 生成成功: {summary}")
            return summary

        except Exception as e:
            logger.warning(f"⚠️ [LLM摘要] 所有重试失败: {e}，使用简单版本")
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

    # ==================== 🆕 v7.151: LLM深度分析方法 ====================

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
        🆕 v7.151: LLM深度分析 - 生成项目本质、隐性需求、关键冲突
        🔧 v7.152: 增强独立性 - 即使 analysis_layers 为空也能生成高质量洞察

        将分散的问卷数据转化为连贯的、有洞察的结构化理解
        """
        try:
            from ...utils.llm_retry import LLMRetryConfig, invoke_llm_with_retry

            llm = LLMFactory.create_llm(temperature=0.5, max_tokens=1200)

            # 🔧 v7.152: 增强上下文准备 - 从问卷数据中提取更丰富的信息
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

            # 🔧 v7.152: AI初步分析作为可选增强（不是必须）
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

            logger.info("🧠 [v7.152] 调用LLM进行独立深度分析...")
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
                    logger.info(f"✅ [v7.152] LLM深度分析成功")
                    logger.info(f"   - 项目本质: {essence[:60]}...")
                    logger.info(f"   - 隐性需求: {len(implicit_reqs)}项")
                    logger.info(f"   - 关键冲突: {len(conflicts)}项")
                    return {
                        "project_essence": essence,
                        "implicit_requirements": implicit_reqs if isinstance(implicit_reqs, list) else [],
                        "key_conflicts": conflicts if isinstance(conflicts, list) else [],
                    }
                else:
                    logger.warning("⚠️ [v7.152] LLM返回的项目本质过短，使用降级生成")
            else:
                logger.warning("⚠️ [v7.152] LLM响应未包含有效JSON")

            # 🔧 v7.152: 降级策略 - 基于规则生成基础洞察
            return RequirementsRestructuringEngine._fallback_deep_insights(
                user_input, questionnaire_data, objectives, constraints
            )

        except Exception as e:
            logger.warning(f"⚠️ [v7.152] LLM深度分析异常: {e}，使用降级生成")
            return RequirementsRestructuringEngine._fallback_deep_insights(
                user_input, questionnaire_data, objectives, constraints
            )

    @staticmethod
    def _fallback_deep_insights(
        user_input: str, questionnaire_data: Dict[str, Any], objectives: Dict[str, Any], constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🆕 v7.152: 降级策略 - 基于规则生成基础洞察
        当LLM调用失败时，使用规则提取基础信息
        """
        logger.info("🔄 [v7.152] 使用降级策略生成基础洞察")

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
