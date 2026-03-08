"""
任务完整性分析器

v7.80.6: Step 3 核心服务，分析核心任务的信息完整性
检查 6大维度：基本信息、核心目标、预算约束、时间节点、交付要求、特殊需求
"""

import re
from typing import Any, Dict, List

from loguru import logger

#  v7.150: 导出特殊场景检测器常量，供其他模块（如 dimension_selector）使用
SPECIAL_SCENARIO_DETECTORS = {
    "poetic_philosophical": {"keywords": ["月亮", "湖面", "诗意", "哲学", "灵魂", "禅", "意境"], "trigger_message": "检测到诗意/哲学表达"},
    "extreme_environment": {"keywords": ["高海拔", "严寒", "酷暑", "极端", "沙漠", "高原"], "trigger_message": "检测到极端环境场景"},
    "medical_special_needs": {"keywords": ["无障碍", "适老", "轮椅", "医疗", "康复", "辅助"], "trigger_message": "检测到医疗/无障碍需求"},
    "cultural_depth": {"keywords": ["传统文化", "非遗", "文化传承", "authentic", "在地文化"], "trigger_message": "检测到文化深度需求"},
    "tech_geek": {"keywords": ["声学", "录音", "音乐室", "专业级", "发烧友"], "trigger_message": "检测到科技极客场景"},
    "complex_relationships": {"keywords": ["多代同堂", "冲突", "隐私", "边界", "独立空间"], "trigger_message": "检测到复杂关系场景"},
}


class TaskCompletenessAnalyzer:
    """
    任务完整性分析器

    分析核心任务列表是否包含足够的执行信息，识别缺失维度并生成补充问题
    """

    # 6大信息完整性维度
    DIMENSIONS = {
        "基本信息": ["项目类型", "地点", "规模", "面积"],
        "核心目标": ["核心任务", "期望愿景", "目标定位"],
        "预算约束": ["预算范围", "资源限制", "成本"],
        "时间节点": ["交付时间", "里程碑", "工期"],
        "交付要求": ["交付物类型", "质量标准", "成果形式"],
        "特殊需求": ["特殊场景", "约束条件", "特殊要求"],
    }

    def __init__(self):
        pass

    def analyze(
        self, confirmed_tasks: List[Dict[str, Any]], user_input: str, structured_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析任务信息完整性

        Args:
            confirmed_tasks: Step 1 确认的任务列表
            user_input: 用户原始输入
            structured_data: requirements_analyst 的结构化数据

        Returns:
            {
                "completeness_score": 0.65,  # 完整度评分 (0-1)
                "covered_dimensions": ["基本信息", "核心目标"],
                "missing_dimensions": ["预算约束", "时间节点", "交付要求"],
                "critical_gaps": [
                    {"dimension": "预算约束", "reason": "未明确预算范围"},
                    {"dimension": "时间节点", "reason": "未说明交付时间"}
                ],
                "dimension_scores": {"基本信息": 0.8, ...}
            }
        """
        # 1. 合并所有文本信息
        all_text = self._merge_text(confirmed_tasks, user_input, structured_data)

        # 2. 评估每个维度的覆盖度
        dimension_scores = {}
        for dim, keywords in self.DIMENSIONS.items():
            score = self._calculate_dimension_score(all_text, keywords)
            dimension_scores[dim] = score

        # 3. 识别已覆盖和缺失维度
        covered_dimensions = [dim for dim, score in dimension_scores.items() if score > 0.3]
        missing_dimensions = [dim for dim, score in dimension_scores.items() if score <= 0.3]

        # 4. 识别关键缺失点
        critical_gaps = self._identify_critical_gaps(missing_dimensions, all_text)

        # 5. 计算整体完整性评分
        task_density_score = self._calculate_task_density(confirmed_tasks)
        completeness_score = (len(covered_dimensions) / len(self.DIMENSIONS)) * 0.6 + task_density_score * 0.4

        return {
            "completeness_score": completeness_score,
            "covered_dimensions": covered_dimensions,
            "missing_dimensions": missing_dimensions,
            "critical_gaps": critical_gaps,
            "dimension_scores": dimension_scores,
        }

    def analyze_with_expert_foresight(
        self,
        confirmed_tasks: List[Dict[str, Any]],
        user_input: str,
        structured_data: Dict[str, Any],
        predicted_roles: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        增强版完整性分析 + 专家视角风险预判

        v7.136: 融合质量预检机制到问卷阶段

        在基础完整性分析的基础上，预判各专家执行时会遇到的信息缺口，
        提前生成针对性补充问题，避免后续质量预检环节的重复警告。

        Args:
            confirmed_tasks: Step 1 确认的任务列表
            user_input: 用户原始输入
            structured_data: requirements_analyst 的结构化数据
            predicted_roles: 预测的专家角色列表（可选）

        Returns:
            基础分析结果 + 专家视角分析:
            {
                ...基础分析字段...,
                "expert_perspective_gaps": {
                    "V3_叙事专家": {
                        "risk_score": 65,
                        "missing_info": ["用户画像数据", "场景细节"],
                        "suggested_questions": [...],
                        "reason": "为什么这些信息很关键"
                    },
                    ...
                },
                "high_risk_roles": ["V3_叙事专家"]  # risk_score > 70
            }
        """
        # 1. 执行基础完整性分析
        base_analysis = self.analyze(confirmed_tasks, user_input, structured_data)

        # 2. 如果提供了预测角色，执行专家视角分析
        if predicted_roles:
            logger.info(f" [v7.136] 开始专家视角风险预判，角色数: {len(predicted_roles)}")

            expert_gaps = self._analyze_expert_perspective_gaps(
                confirmed_tasks=confirmed_tasks,
                user_input=user_input,
                structured_data=structured_data,
                predicted_roles=predicted_roles,
            )

            # 识别高风险角色
            high_risk_roles = [role for role, gaps in expert_gaps.items() if gaps.get("risk_score", 0) > 70]

            # 融合到基础分析结果
            base_analysis["expert_perspective_gaps"] = expert_gaps
            base_analysis["high_risk_roles"] = high_risk_roles

            logger.info(f" [v7.136] 专家视角分析完成，高风险角色: {len(high_risk_roles)}个")

        return base_analysis

    def _analyze_expert_perspective_gaps(
        self,
        confirmed_tasks: List[Dict[str, Any]],
        user_input: str,
        structured_data: Dict[str, Any],
        predicted_roles: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        从专家视角分析信息缺口

        模拟质量预检的逻辑，但在任务分配前执行

        Args:
            confirmed_tasks: 确认的任务列表
            user_input: 用户原始输入
            structured_data: 结构化数据
            predicted_roles: 预测的专家角色列表

        Returns:
            专家视角的信息缺口分析
        """
        import json
        import re

        from ..services.llm_factory import LLMFactory

        results = {}

        # 只分析前3个关键角色，避免过慢
        roles_to_analyze = predicted_roles[:3]

        logger.info(f" [v7.136] 并行分析 {len(roles_to_analyze)} 个角色的信息需求")

        try:
            llm = LLMFactory.create_llm(temperature=0.3, max_tokens=800)

            for role_id in roles_to_analyze:
                # 提取角色名称
                role_name = role_id.split("_")[1] if "_" in role_id else role_id

                # 构建简化的已有信息摘要
                info_summary = self._summarize_structured_data(structured_data)

                prompt = f"""你是一个{role_name}，即将执行以下项目任务。

**用户需求**: {user_input[:300]}

**核心任务**:
{chr(10).join(f"{i+1}. {t.get('title', '')}" for i, t in enumerate(confirmed_tasks[:5]))}

**已有信息**: {info_summary}

请从你的专业视角，快速判断：
1. 哪些信息不足会导致你无法高质量完成任务？
2. 你需要补充询问用户哪1-2个最关键的问题？

输出JSON格式（不要有注释）：
{{
    "risk_score": 65,
    "missing_info": ["缺失的关键信息1", "缺失的关键信息2"],
    "suggested_questions": ["具体的补充问题1？", "具体的补充问题2？"],
    "reason": "简要说明为什么这些信息很关键"
}}"""

                try:
                    response = llm.invoke(prompt)
                    content = response.content if hasattr(response, "content") else str(response)

                    # 提取JSON
                    json_match = re.search(r"\{[\s\S]*\}", content)
                    if json_match:
                        json_str = json_match.group()
                        # 清理注释
                        json_str = re.sub(r"//.*?(?=\n|$)", "", json_str)
                        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

                        result = json.loads(json_str)
                        results[role_id] = result

                        risk_score = result.get("risk_score", 0)
                        logger.info(f"   {role_name}: 风险={risk_score}, 缺口={len(result.get('missing_info', []))}")
                    else:
                        logger.warning(f"  ️ {role_name}: JSON解析失败")
                        results[role_id] = self._get_default_expert_gap()

                except Exception as e:
                    logger.warning(f"  ️ {role_name}: 分析失败 - {e}")
                    results[role_id] = self._get_default_expert_gap()

        except Exception as e:
            logger.error(f" [v7.136] 专家视角分析失败: {e}")
            import traceback

            logger.debug(traceback.format_exc())

        return results

    def _summarize_structured_data(self, structured_data: Dict[str, Any]) -> str:
        """快速摘要结构化数据"""
        parts = []

        if structured_data.get("project_type"):
            parts.append(f"类型:{structured_data['project_type']}")
        if structured_data.get("budget"):
            parts.append(f"预算:{structured_data['budget']}")
        if structured_data.get("timeline"):
            parts.append(f"时间:{structured_data['timeline']}")
        if structured_data.get("scale") or structured_data.get("area"):
            parts.append(f"规模:{structured_data.get('scale') or structured_data.get('area')}")

        return " | ".join(parts) if parts else "信息不足"

    def _get_default_expert_gap(self) -> Dict[str, Any]:
        """获取默认的专家缺口分析"""
        return {
            "risk_score": 50,
            "missing_info": ["需要更多信息"],
            "suggested_questions": ["请补充更多项目细节"],
            "reason": "信息不足，建议补充",
        }

    def _merge_text(
        self, confirmed_tasks: List[Dict[str, Any]], user_input: str, structured_data: Dict[str, Any]
    ) -> str:
        """合并所有文本信息"""
        texts = [user_input]

        # 添加任务标题和描述
        for task in confirmed_tasks:
            texts.append(task.get("title", ""))
            texts.append(task.get("description", ""))

        # 添加结构化数据中的关键字段
        for key in ["project_type", "physical_context", "resource_constraints", "core_objectives"]:
            value = structured_data.get(key, "")
            if value:
                if isinstance(value, list | tuple):
                    texts.extend(str(v) for v in value)
                else:
                    texts.append(str(value))

        return " ".join(texts)

    def _calculate_dimension_score(self, text: str, keywords: List[str]) -> float:
        """计算单个维度的覆盖评分"""
        matched = 0
        for keyword in keywords:
            if keyword in text:
                matched += 1

        # 如果没有关键词匹配，检查相关模式
        if matched == 0:
            # 预算相关（v7.107.1：增强单价识别）
            if any(kw in keywords for kw in ["预算", "成本"]):
                # 支持多种预算表达形式：
                # - 总价：50万、100万元
                # - 单价：3000元/平米、5K/㎡、8000每平米
                if re.search(r"\d+万|\d+元|\d+元[/每]平米?|\d+[kK]/[㎡m²平米]|预算|成本|费用", text):
                    matched += 1

            # 时间模式
            if any(kw in keywords for kw in ["时间", "工期"]):
                if re.search(r"\d+月|\d+天|时间|工期|周期", text):
                    matched += 1

            # 面积模式
            if any(kw in keywords for kw in ["规模", "面积"]):
                if re.search(r"\d+平|平米|m2|㎡", text):
                    matched += 1

        return min(matched / max(len(keywords), 1), 1.0)

    def _calculate_task_density(self, confirmed_tasks: List[Dict[str, Any]]) -> float:
        """计算任务描述的信息密度"""
        if not confirmed_tasks:
            return 0.0

        total_chars = 0
        total_keywords = 0

        for task in confirmed_tasks:
            desc = task.get("description", "")
            total_chars += len(desc)
            # 简单统计关键词（逗号、顿号分隔的片段数）
            total_keywords += len(re.split(r"[，、；,;]", desc))

        # 归一化：平均每个任务 30-50 字为标准密度
        avg_chars = total_chars / len(confirmed_tasks) if confirmed_tasks else 0
        density = min(avg_chars / 40, 1.0)

        return density

    def _identify_critical_gaps(self, missing_dimensions: List[str], all_text: str) -> List[Dict[str, str]]:
        """识别关键缺失点"""
        critical_gaps = []

        for dim in missing_dimensions:
            reason = self._generate_gap_reason(dim, all_text)
            if reason:  # 只添加关键性缺失
                critical_gaps.append({"dimension": dim, "reason": reason})

        return critical_gaps

    def _generate_gap_reason(self, dimension: str, all_text: str) -> str | None:
        """生成缺失原因说明（v7.107.1：动态优先级判断）"""

        # v7.107.1：智能判断时间节点优先级
        #  v7.129: 提高触发阈值，避免过度跳过
        # 如果用户输入聚焦于设计挑战/方案探讨，时间节点非关键
        if dimension == "时间节点":
            design_focus_keywords = [
                #  v7.129: 移除常见词，只保留明确的设计方法论词汇
                # 移除: "如何", "怎样", "怎么", "方案", "策略", "体面感", "价值感", "氛围", "调性", "格调", "空间"
                "设计手法",
                "设计方向",
            ]
            #  v7.129: 提高阈值 - 至少匹配2个关键词才降级（原来是1个）
            matched_count = sum(1 for kw in design_focus_keywords if kw in all_text)
            if matched_count >= 2:
                logger.info(f" [Step 3过滤] 时间节点维度降级：匹配{matched_count}个设计方法论关键词")
                return None  # 降级为非关键缺失

        reasons = {
            "预算约束": "未明确预算范围，影响设计方向和材料选择",
            "时间节点": "未说明交付时间，无法规划工作流程和里程碑",
            "交付要求": "未明确交付物类型，可能影响成果预期",
            "特殊需求": "可能存在未表达的特殊约束条件",
        }

        # 基本信息和核心目标通常不是关键缺失（已在 Step 1 确认）
        if dimension in ["基本信息", "核心目标"]:
            return None

        return reasons.get(dimension)

    def generate_gap_questions(
        self,
        missing_dimensions: List[str],
        critical_gaps: List[Dict[str, str]],
        confirmed_tasks: List[Dict[str, Any]],
        existing_info_summary: str = "",
        target_count: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        生成针对性补充问题

        Args:
            missing_dimensions: 缺失维度列表
            critical_gaps: 关键缺失点
            confirmed_tasks: 确认的任务列表
            existing_info_summary: 已有信息摘要
            target_count: 目标问题数量（默认10个）

        Returns:
            问题列表，每个问题包含:
            {
                "id": "budget_range",
                "question": "请问您的预算范围大致是？",
                "type": "single_choice",
                "options": ["10万以下", "10-30万", ...],
                "is_required": True,
                "priority": 1,
                "weight": 10
            }
        """
        questions = []

        # 1. 为每个关键缺失点生成必答问题
        for gap in critical_gaps:
            dim = gap["dimension"]
            question = self._generate_question_for_dimension(dim, is_required=True)
            if question:
                questions.append(question)

        # 2. 为其他缺失维度生成选答问题
        for dim in missing_dimensions:
            if dim not in [g["dimension"] for g in critical_gaps]:
                question = self._generate_question_for_dimension(dim, is_required=False)
                if question:
                    questions.append(question)

        # 3. 如果问题不足 target_count，添加通用补充问题
        if len(questions) < target_count:
            generic_questions = self._generate_generic_questions()
            questions.extend(generic_questions[: target_count - len(questions)])

        # 4. 限制最多 target_count 个问题
        return questions[:target_count]

    def _generate_question_for_dimension(self, dimension: str, is_required: bool) -> Dict[str, Any] | None:
        """为特定维度生成问题"""

        question_templates = {
            "预算约束": {
                "id": "budget_range",
                "question": "请问您的预算范围大致是？",
                "type": "single_choice",
                "options": ["10万以下", "10-30万", "30-50万", "50-100万", "100万以上"],
                "priority": 1,
                "weight": 10,
            },
            "时间节点": {
                "id": "timeline",
                "question": "请问期望的交付时间是？",
                "type": "single_choice",
                "options": ["1个月内", "1-3个月", "3-6个月", "6个月以上", "暂无明确要求"],
                "priority": 2,
                "weight": 9,
            },
            "交付要求": {
                "id": "deliverables",
                "question": "您期望的交付物包括哪些？（可多选）",
                "type": "multiple_choice",
                "options": ["设计策略文档", "空间概念描述", "材料选择指导", "预算框架", "分析报告", "其他"],
                "priority": 3,
                "weight": 8,
                "context": "系统提供策略性指导，不提供需要专业工具的CAD图纸、3D效果图或精确清单",
            },
            "特殊需求": {
                "id": "special_requirements",
                "question": "是否有其他特殊需求或约束条件？",
                "type": "open_ended",
                "priority": 4,
                "weight": 7,
            },
        }

        template = question_templates.get(dimension)
        if template:
            template["is_required"] = is_required
            return template

        return None

    def _generate_generic_questions(self) -> List[Dict[str, Any]]:
        """生成通用补充问题"""
        return [
            {
                "id": "design_style_preference",
                "question": "对设计风格有没有特别偏好或禁忌？",
                "type": "open_ended",
                "is_required": False,
                "priority": 5,
                "weight": 6,
            },
            {
                "id": "color_preference",
                "question": "对色彩搭配有什么倾向？（可多选）",
                "type": "multiple_choice",
                "options": ["明亮清新", "温暖舒适", "沉稳大气", "冷峻现代", "多彩活力", "无特别要求"],
                "is_required": False,
                "priority": 6,
                "weight": 5,
            },
            {
                "id": "material_preference",
                "question": "对材质有什么偏好？（可多选）",
                "type": "multiple_choice",
                "options": ["天然木材", "石材大理石", "金属质感", "玻璃通透", "织物软装", "无特别要求"],
                "is_required": False,
                "priority": 7,
                "weight": 4,
            },
            {
                "id": "lighting_preference",
                "question": "对光线氛围有什么期望？",
                "type": "single_choice",
                "options": ["明亮充足", "柔和温馨", "层次丰富", "可调节变化", "无特别要求"],
                "is_required": False,
                "priority": 8,
                "weight": 3,
            },
            {
                "id": "sustainability_concern",
                "question": "是否关注环保和可持续性？",
                "type": "single_choice",
                "options": ["非常重视", "适度考虑", "不是优先考虑", "无特别要求"],
                "is_required": False,
                "priority": 9,
                "weight": 2,
            },
            {
                "id": "future_flexibility",
                "question": "是否需要考虑未来调整的灵活性？",
                "type": "single_choice",
                "options": ["需要高度灵活", "适度灵活", "固定使用", "无特别要求"],
                "is_required": False,
                "priority": 10,
                "weight": 1,
            },
        ]

    def detect_special_scenarios(self, user_input: str, task_summary: str) -> Dict[str, Dict[str, Any]]:
        """
        检测特殊场景（v7.80.15 P1.2）

        用于 Step 1 诗意解读和特殊场景注入

        Args:
            user_input: 用户原始输入
            task_summary: 任务摘要

        Returns:
            {
                "poetic_philosophical": {
                    "matched_keywords": ["月亮", "湖面", "诗意"],
                    "trigger_message": "检测到诗意表达"
                },
                ...
            }
        """
        special_scenarios = {}

        #  v7.150: 复用模块级常量 SPECIAL_SCENARIO_DETECTORS
        combined_text = f"{user_input} {task_summary}"

        for scenario_id, rule in SPECIAL_SCENARIO_DETECTORS.items():
            matched = [kw for kw in rule["keywords"] if kw in combined_text]
            if len(matched) >= 2:  # 至少匹配2个关键词
                special_scenarios[scenario_id] = {
                    "matched_keywords": matched,
                    "trigger_message": rule["trigger_message"],
                }
                logger.info(f" [特殊场景检测] {scenario_id}: {matched}")

        return special_scenarios
