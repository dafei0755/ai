"""
人性维度引导系统
提供结构化的引导问题，帮助LLM深度挖掘人性维度

创建日期: 2026-02-11
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class DepthScore:
    """深度评分"""

    level: int  # 1=浅薄, 2=一般, 3=深刻
    score: float  # 0-100
    reasoning: str
    improvements: List[str]


class HumanDimensionGuide:
    """人性维度深度挖掘引导系统"""

    # 引导问题库（基础模板）
    PROBE_QUESTIONS = {
        "emotional_landscape": [
            "描述您在{核心场景}中的情绪起伏：进入前/使用时/离开后的感受",
            "什么情境会让您感到焦虑或不安？什么空间能让您找到平静？",
            "您希望这个空间帮您摆脱什么情绪？获得什么情绪状态？",
            "在最疲惫的时刻，您希望空间如何回应您的情绪？",
            "有哪些空间元素会触发您的负面情绪？（压抑、焦虑、烦躁等）",
        ],
        "spiritual_aspirations": [
            "这个空间需要帮助您成为什么样的人？支持您的什么价值观？",
            "有哪些价值观是您绝对不能妥协的？必须在空间中体现？",
            "5年后回望，您希望这个空间见证了您的什么变化或成长？",
            "您通过这个空间想向自己证明什么？或向他人传达什么？",
            "您的精神追求与社会角色有什么矛盾？空间如何调和？",
        ],
        "psychological_safety_needs": [
            "在什么情况下，您感觉最能做真实的自己？",
            "哪些空间特征会让您紧张或感到被审视？",
            "您需要一个什么样的'避风港'或'安全基地'？",
            "您在对抗什么恐惧？（失控、被评判、隐私暴露、社交压力等）",
            "空间的哪些边界对您来说是至关重要的？（视觉/声音/物理）",
        ],
        "ritual_behaviors": [
            "描述您一天的典型流程，哪些环节对您有特殊意义或仪式感？",
            "有哪些小习惯或仪式感行为是您珍视的？（如晨间咖啡、睡前阅读）",
            "空间需要如何配合或强化这些日常仪式？",
            "哪些行为需要专属的空间容器？（冥想、创作、独处、聚会等）",
            "您有哪些'过渡仪式'？（如下班回家的身份切换）",
        ],
        "memory_anchors": [
            "有哪些物品或元素承载了重要记忆？必须在新空间找到归属？",
            "您想在空间中保留或延续哪些过去的美好体验？",
            "未来您希望在这个空间留下什么样的记忆？",
            "有哪些'情感物品'是您舍不得丢弃的？它们的故事是什么？",
            "您希望孩子/家人在这个空间中记住什么？",
        ],
    }

    # 禁用词汇列表
    FORBIDDEN_PHRASES = [
        "温馨",
        "舒适",
        "有归属感",
        "幸福感",
        "品质生活",
        "家庭氛围",
        "生活品味",
        "优雅",
        "格调",
        "档次",
        "气质",  # 除非有具体描述
        "现代",
        "简约",
        "时尚",  # 除非有具体场景支撑
    ]

    # 深度标准
    DEPTH_CRITERIA = {
        "level_1_shallow": {
            "characteristics": ["使用通用描述", "缺乏具体场景", "依赖抽象词汇", "无法转化为设计决策"],
            "example": "用户希望有温馨舒适的居住氛围，感受到归属感",
        },
        "level_2_moderate": {
            "characteristics": ["有具体场景描述", "但缺乏情感动机推理", "描述表面行为", "设计指导性有限"],
            "example": "用户每天晚上会在客厅看书，需要舒适的阅读角落",
        },
        "level_3_profound": {
            "characteristics": ["场景+动机+转化路径完整", "揭示潜意识需求", "情感逻辑清晰", "可直接转化为设计决策"],
            "example": "晚间阅读不仅是信息获取，更是从'职场高效模式'切换到'自我关怀模式'的仪式。需要：柔和暖光（对抗办公室冷光压力）+ 包裹感座椅（重建心理边界）+ 与家人共享空间可视但不打扰的布局（平衡独处与连结）",
        },
    }

    def generate_contextual_probes(
        self, project_type: str, user_identity: str, core_tension: str, user_input: str
    ) -> Dict[str, List[str]]:
        """
        基于项目上下文生成个性化引导问题

        Args:
            project_type: 项目类型（residential, commercial等）
            user_identity: 用户身份（如"32岁单身职场女性"）
            core_tension: 核心张力（如"展示需求 vs 精神庇护"）
            user_input: 用户原始输入

        Returns:
            个性化引导问题字典
        """
        personalized_questions = {}

        # 从用户输入中提取关键词
        keywords = self._extract_keywords(user_input)

        # 为每个维度生成个性化问题
        for dimension, base_questions in self.PROBE_QUESTIONS.items():
            personalized = []
            for question in base_questions:
                # 动态替换占位符
                personalized_q = question.replace("{核心场景}", self._infer_core_scenario(keywords))
                personalized.append(personalized_q)

            # 根据用户身份和张力添加专属问题
            if dimension == "emotional_landscape" and "职场" in user_identity:
                personalized.append("工作压力如何影响您对空间的情绪需求？下班回家的那一刻您最需要什么情绪转变？")

            if dimension == "spiritual_aspirations" and "转型" in user_input:
                personalized.append(f"作为正在转型的{user_identity}，空间如何支持您的身份重建？")

            personalized_questions[dimension] = personalized

        return personalized_questions

    def evaluate_depth(self, dimension_name: str, dimension_output: str) -> DepthScore:
        """
        评估人性维度分析的深度

        Args:
            dimension_name: 维度名称
            dimension_output: LLM生成的维度分析内容

        Returns:
            深度评分对象
        """
        score = 100.0
        level = 3
        issues = []

        # 检查1: 禁用词汇
        forbidden_found = [
            word
            for word in self.FORBIDDEN_PHRASES
            if word in dimension_output and not self._has_concrete_context(dimension_output, word)
        ]
        if forbidden_found:
            score -= len(forbidden_found) * 15
            level = min(level, 1)
            issues.append(f"使用了空洞词汇: {', '.join(forbidden_found)}")

        # 检查2: 具体性（是否有具体场景/行为/情绪）
        if not self._has_specific_scenario(dimension_output):
            score -= 20
            level = min(level, 2)
            issues.append("缺乏具体场景描述")

        # 检查3: 情感动机推理
        if not self._has_emotional_reasoning(dimension_output):
            score -= 15
            level = min(level, 2)
            issues.append("缺乏情感动机推理")

        # 检查4: 可操作性（是否能转化为设计决策）
        if not self._is_actionable(dimension_output):
            score -= 10
            level = min(level, 2)
            issues.append("设计指导性不足")

        # 检查5: 长度（过短通常深度不足）
        if len(dimension_output) < 50:
            score -= 20
            level = 1
            issues.append("内容过于简短")

        score = max(0, score)

        # 生成改进建议
        improvements = self._generate_improvements(dimension_name, issues)

        return DepthScore(
            level=level, score=score, reasoning="; ".join(issues) if issues else "分析深度充分", improvements=improvements
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        # TODO: 实现更智能的关键词提取
        return text.split()

    def _infer_core_scenario(self, keywords: List[str]) -> str:
        """推断核心场景"""
        # TODO: 基于关键词推断核心场景
        return "日常生活中"

    def _has_concrete_context(self, text: str, word: str) -> bool:
        """检查词汇是否有具体上下文支撑"""
        # 简单启发式：词汇前后有详细描述
        word_index = text.find(word)
        if word_index == -1:
            return False

        # 检查前后50个字符是否有具体描述
        context = text[max(0, word_index - 50) : min(len(text), word_index + len(word) + 50)]
        concrete_markers = ["时", "在", "通过", "需要", "感受", "场景", "行为", "元素"]
        return any(marker in context for marker in concrete_markers)

    def _has_specific_scenario(self, text: str) -> bool:
        """检查是否包含具体场景"""
        scenario_markers = [
            "早晨",
            "晚上",
            "周末",
            "工作日",
            "进门",
            "客厅",
            "卧室",
            "厨房",
            "独处",
            "聚会",
            "工作",
            "休息",
            "阅读",
            "烹饪",
            "冥想",
            "创作",
        ]
        return any(marker in text for marker in scenario_markers)

    def _has_emotional_reasoning(self, text: str) -> bool:
        """检查是否包含情感动机推理"""
        reasoning_markers = ["因为", "所以", "为了", "对抗", "渴望", "恐惧", "焦虑", "平静", "压力", "安全", "自由", "控制"]
        return any(marker in text for marker in reasoning_markers)

    def _is_actionable(self, text: str) -> bool:
        """检查是否可转化为设计决策"""
        actionable_markers = ["需要", "通过", "设计", "空间", "材料", "光线", "色彩", "布局", "分区", "动线", "尺度", "氛围"]
        return any(marker in text for marker in actionable_markers)

    def _generate_improvements(self, dimension_name: str, issues: List[str]) -> List[str]:
        """生成改进建议"""
        improvements = []

        if "空洞词汇" in str(issues):
            improvements.append(f"请用具体场景和行为替代抽象词汇，描述用户在{dimension_name}中的真实体验")

        if "缺乏具体场景" in str(issues):
            improvements.append("请描述至少2-3个具体场景，包含时间、地点、行为、情绪")

        if "缺乏情感动机推理" in str(issues):
            improvements.append("请解释为什么用户有这种需求？背后的情感动机或恐惧是什么？")

        if "设计指导性不足" in str(issues):
            improvements.append("请说明如何将这种洞察转化为具体的空间/材料/光线/色彩/布局决策")

        if "内容过于简短" in str(issues):
            improvements.append("请扩展描述，至少100-200字，包含场景+动机+设计启示")

        return improvements


# 示例用法
if __name__ == "__main__":
    guide = HumanDimensionGuide()

    # 示例1: 生成个性化引导问题
    print("=" * 70)
    print("示例1: 生成个性化引导问题")
    print("=" * 70)

    questions = guide.generate_contextual_probes(
        project_type="personal_residential",
        user_identity="32岁单身职场女性",
        core_tension="展示需求 vs 精神庇护",
        user_input="我想设计一个75平米的住宅，既能作为内容创作基地，又能提供精神庇护",
    )

    for dimension, qs in questions.items():
        print(f"\n【{dimension}】")
        for i, q in enumerate(qs[:3], 1):  # 只显示前3个
            print(f"  {i}. {q}")

    # 示例2: 评估深度
    print("\n" + "=" * 70)
    print("示例2: 评估深度")
    print("=" * 70)

    shallow_output = "用户希望有温馨舒适的居住氛围"
    moderate_output = "用户每天晚上会在客厅阅读，需要一个舒适的阅读角落"
    profound_output = """
早晨：厨房阳光洒入时的平静感，为高压工作提供情绪缓冲（对抗职场紧张）
晚间：客厅柔和灯光营造的'下班仪式感'，标志工作/生活切换（重建心理边界）
深夜：卧室绝对安静的避风港，承载焦虑释放与自我修复（满足心理安全需求）
核心转化路径：从'高度紧张'→'逐步松弛'→'深度安全'
    """.strip()

    print("\n 浅薄示例:")
    print(f"   内容: {shallow_output}")
    score1 = guide.evaluate_depth("emotional_landscape", shallow_output)
    print(f"   评分: Level {score1.level}, Score {score1.score:.1f}")
    print(f"   问题: {score1.reasoning}")

    print("\n️ 一般示例:")
    print(f"   内容: {moderate_output}")
    score2 = guide.evaluate_depth("emotional_landscape", moderate_output)
    print(f"   评分: Level {score2.level}, Score {score2.score:.1f}")
    print(f"   问题: {score2.reasoning}")

    print("\n 深刻示例:")
    print(f"   内容: {profound_output[:100]}...")
    score3 = guide.evaluate_depth("emotional_landscape", profound_output)
    print(f"   评分: Level {score3.level}, Score {score3.score:.1f}")
    print(f"   评价: {score3.reasoning}")
