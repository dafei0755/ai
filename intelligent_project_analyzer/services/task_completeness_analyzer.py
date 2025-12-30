"""
任务完整性分析器

v7.80.6: Step 3 核心服务，分析核心任务的信息完整性
检查 6大维度：基本信息、核心目标、预算约束、时间节点、交付要求、特殊需求
"""

import re
from typing import Dict, Any, List, Optional, Set
from loguru import logger


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
        "特殊需求": ["特殊场景", "约束条件", "特殊要求"]
    }

    def __init__(self):
        pass

    def analyze(
        self,
        confirmed_tasks: List[Dict[str, Any]],
        user_input: str,
        structured_data: Dict[str, Any]
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
        completeness_score = (
            (len(covered_dimensions) / len(self.DIMENSIONS)) * 0.6 +
            task_density_score * 0.4
        )

        return {
            "completeness_score": completeness_score,
            "covered_dimensions": covered_dimensions,
            "missing_dimensions": missing_dimensions,
            "critical_gaps": critical_gaps,
            "dimension_scores": dimension_scores
        }

    def _merge_text(
        self,
        confirmed_tasks: List[Dict[str, Any]],
        user_input: str,
        structured_data: Dict[str, Any]
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
                if isinstance(value, (list, tuple)):
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
            # 预算模式
            if any(kw in keywords for kw in ["预算", "成本"]):
                if re.search(r'\d+万|\d+元|预算|成本|费用', text):
                    matched += 1

            # 时间模式
            if any(kw in keywords for kw in ["时间", "工期"]):
                if re.search(r'\d+月|\d+天|时间|工期|周期', text):
                    matched += 1

            # 面积模式
            if any(kw in keywords for kw in ["规模", "面积"]):
                if re.search(r'\d+平|平米|m2|㎡', text):
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
            total_keywords += len(re.split(r'[，、；,;]', desc))

        # 归一化：平均每个任务 30-50 字为标准密度
        avg_chars = total_chars / len(confirmed_tasks) if confirmed_tasks else 0
        density = min(avg_chars / 40, 1.0)

        return density

    def _identify_critical_gaps(
        self,
        missing_dimensions: List[str],
        all_text: str
    ) -> List[Dict[str, str]]:
        """识别关键缺失点"""
        critical_gaps = []

        for dim in missing_dimensions:
            reason = self._generate_gap_reason(dim, all_text)
            if reason:  # 只添加关键性缺失
                critical_gaps.append({
                    "dimension": dim,
                    "reason": reason
                })

        return critical_gaps

    def _generate_gap_reason(self, dimension: str, all_text: str) -> Optional[str]:
        """生成缺失原因说明"""
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
        target_count: int = 10
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
            questions.extend(generic_questions[:target_count - len(questions)])

        # 4. 限制最多 target_count 个问题
        return questions[:target_count]

    def _generate_question_for_dimension(
        self,
        dimension: str,
        is_required: bool
    ) -> Optional[Dict[str, Any]]:
        """为特定维度生成问题"""

        question_templates = {
            "预算约束": {
                "id": "budget_range",
                "question": "请问您的预算范围大致是？",
                "type": "single_choice",
                "options": ["10万以下", "10-30万", "30-50万", "50-100万", "100万以上"],
                "priority": 1,
                "weight": 10
            },
            "时间节点": {
                "id": "timeline",
                "question": "请问期望的交付时间是？",
                "type": "single_choice",
                "options": ["1个月内", "1-3个月", "3-6个月", "6个月以上", "暂无明确要求"],
                "priority": 2,
                "weight": 9
            },
            "交付要求": {
                "id": "deliverables",
                "question": "您期望的交付物包括哪些？（可多选）",
                "type": "multiple_choice",
                "options": ["设计方案", "效果图", "施工图", "软装清单", "预算清单", "其他"],
                "priority": 3,
                "weight": 8
            },
            "特殊需求": {
                "id": "special_requirements",
                "question": "是否有其他特殊需求或约束条件？",
                "type": "open_ended",
                "priority": 4,
                "weight": 7
            }
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
                "weight": 6
            },
            {
                "id": "color_preference",
                "question": "对色彩搭配有什么倾向？（可多选）",
                "type": "multiple_choice",
                "options": ["明亮清新", "温暖舒适", "沉稳大气", "冷峻现代", "多彩活力", "无特别要求"],
                "is_required": False,
                "priority": 6,
                "weight": 5
            },
            {
                "id": "material_preference",
                "question": "对材质有什么偏好？（可多选）",
                "type": "multiple_choice",
                "options": ["天然木材", "石材大理石", "金属质感", "玻璃通透", "织物软装", "无特别要求"],
                "is_required": False,
                "priority": 7,
                "weight": 4
            },
            {
                "id": "lighting_preference",
                "question": "对光线氛围有什么期望？",
                "type": "single_choice",
                "options": ["明亮充足", "柔和温馨", "层次丰富", "可调节变化", "无特别要求"],
                "is_required": False,
                "priority": 8,
                "weight": 3
            },
            {
                "id": "sustainability_concern",
                "question": "是否关注环保和可持续性？",
                "type": "single_choice",
                "options": ["非常重视", "适度考虑", "不是优先考虑", "无特别要求"],
                "is_required": False,
                "priority": 9,
                "weight": 2
            },
            {
                "id": "future_flexibility",
                "question": "是否需要考虑未来调整的灵活性？",
                "type": "single_choice",
                "options": ["需要高度灵活", "适度灵活", "固定使用", "无特别要求"],
                "is_required": False,
                "priority": 10,
                "weight": 1
            }
        ]

    def detect_special_scenarios(
        self,
        user_input: str,
        task_summary: str
    ) -> Dict[str, Dict[str, Any]]:
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

        # 场景检测规则
        scenario_rules = {
            "poetic_philosophical": {
                "keywords": ["月亮", "湖面", "诗意", "哲学", "灵魂", "禅", "意境"],
                "message": "检测到诗意/哲学表达"
            },
            "extreme_environment": {
                "keywords": ["高海拔", "严寒", "酷暑", "极端", "沙漠", "高原"],
                "message": "检测到极端环境场景"
            },
            "medical_special_needs": {
                "keywords": ["无障碍", "适老", "轮椅", "医疗", "康复", "辅助"],
                "message": "检测到医疗/无障碍需求"
            },
            "cultural_depth": {
                "keywords": ["传统文化", "非遗", "文化传承", "authentic", "在地文化"],
                "message": "检测到文化深度需求"
            },
            "tech_geek": {
                "keywords": ["声学", "录音", "音乐室", "专业级", "发烧友"],
                "message": "检测到科技极客场景"
            },
            "complex_relationships": {
                "keywords": ["多代同堂", "冲突", "隐私", "边界", "独立空间"],
                "message": "检测到复杂关系场景"
            }
        }

        combined_text = f"{user_input} {task_summary}"

        for scenario_id, rule in scenario_rules.items():
            matched = [kw for kw in rule["keywords"] if kw in combined_text]
            if len(matched) >= 2:  # 至少匹配2个关键词
                special_scenarios[scenario_id] = {
                    "matched_keywords": matched,
                    "trigger_message": rule["message"]
                }
                logger.info(f"🎯 [特殊场景检测] {scenario_id}: {matched}")

        return special_scenarios
