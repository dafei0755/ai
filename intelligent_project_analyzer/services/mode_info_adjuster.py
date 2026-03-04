"""
模式感知信息质量调整器（Mode-Aware Info Quality Adjuster）
v7.750 P1-Task1

目的：
根据检测到的设计模式，动态调整info_status的判断标准，
让phase1_node()的信息充分性判断能够感知不同模式的特殊需求。

核心逻辑：
- M1 概念驱动：需要精神主轴信息
- M2 功能效率：需要动线和效率相关信息
- M3 情绪体验：需要体验目标信息
- M4 资产资本：需要成本预算和ROI信息
- M5 乡建在地：需要地域和文化信息
- M6 城市更新：需要片区和改造范围信息
- M7 技术整合：需要技术系统和智能需求
- M8 极端环境：需要环境条件和气候数据
- M9 社会结构：需要家庭/组织结构信息
- M10 未来推演：需要趋势和长期规划信息
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ModeInfoRequirement:
    """模式特定的信息需求"""

    mode_id: str
    mode_name: str
    required_keywords: List[str]  # 必须包含的关键词
    quality_weight: float  # 质量权重（0.5-1.5）
    missing_penalty: float  # 缺失惩罚（降低info_status的程度）


# 10种模式的信息需求定义
MODE_INFO_REQUIREMENTS = {
    "M1_concept_driven": ModeInfoRequirement(
        mode_id="M1_concept_driven",
        mode_name="概念驱动型",
        required_keywords=["概念", "精神", "文化", "主题", "叙事", "理念", "意义", "表达"],
        quality_weight=1.2,
        missing_penalty=0.15,
    ),
    "M2_function_efficiency": ModeInfoRequirement(
        mode_id="M2_function_efficiency",
        mode_name="功能效率型",
        required_keywords=["动线", "效率", "流线", "功能", "使用", "操作", "流程", "优化"],
        quality_weight=1.0,
        missing_penalty=0.10,
    ),
    "M3_emotional_experience": ModeInfoRequirement(
        mode_id="M3_emotional_experience",
        mode_name="情绪体验型",
        required_keywords=["体验", "氛围", "感受", "情绪", "沉浸", "记忆", "感官", "触动"],
        quality_weight=1.1,
        missing_penalty=0.12,
    ),
    "M4_capital_asset": ModeInfoRequirement(
        mode_id="M4_capital_asset",
        mode_name="资产资本型",
        required_keywords=["预算", "成本", "投资", "回报", "盈利", "价格", "费用", "资金", "造价", "万元"],
        quality_weight=1.3,
        missing_penalty=0.20,
    ),
    "M5_rural_context": ModeInfoRequirement(
        mode_id="M5_rural_context",
        mode_name="乡建在地型",
        required_keywords=["乡村", "村落", "本地", "地域", "民俗", "传统", "农村", "在地"],
        quality_weight=1.1,
        missing_penalty=0.12,
    ),
    "M6_urban_regeneration": ModeInfoRequirement(
        mode_id="M6_urban_regeneration",
        mode_name="城市更新型",
        required_keywords=["改造", "更新", "旧", "老", "片区", "街区", "城市", "现状"],
        quality_weight=1.2,
        missing_penalty=0.15,
    ),
    "M7_tech_integration": ModeInfoRequirement(
        mode_id="M7_tech_integration",
        mode_name="技术整合型",
        required_keywords=["智能", "技术", "系统", "自动", "数据", "传感", "AI", "科技", "控制"],
        quality_weight=1.1,
        missing_penalty=0.12,
    ),
    "M8_extreme_condition": ModeInfoRequirement(
        mode_id="M8_extreme_condition",
        mode_name="极端环境型",
        required_keywords=["高原", "海拔", "极寒", "极热", "沙漠", "海岛", "气候", "环境", "温度", "盐雾"],
        quality_weight=1.5,  # 极端环境需要最详细的信息
        missing_penalty=0.25,
    ),
    "M9_social_structure": ModeInfoRequirement(
        mode_id="M9_social_structure",
        mode_name="社会结构型",
        required_keywords=["家庭", "成员", "人口", "代际", "关系", "隐私", "社交", "结构"],
        quality_weight=1.2,
        missing_penalty=0.15,
    ),
    "M10_future_projection": ModeInfoRequirement(
        mode_id="M10_future_projection",
        mode_name="未来推演型",
        required_keywords=["未来", "趋势", "长期", "演化", "变化", "发展", "升级", "迭代"],
        quality_weight=1.1,
        missing_penalty=0.12,
    ),
    "M11_healthcare_healing": ModeInfoRequirement(
        mode_id="M11_healthcare_healing",
        mode_name="健康疗愈型",
        required_keywords=["疗愈", "康复", "安全感", "无障碍", "医疗", "护理", "心理", "焦虑", "尊严", "节律"],
        quality_weight=1.4,
        missing_penalty=0.20,
    ),
}


class ModeAwareInfoQualityAdjuster:
    """模式感知信息质量调整器"""

    @staticmethod
    def adjust_info_status(
        original_status: str,
        user_input: str,
        detected_modes: List[Dict[str, Any]],
        phase1_result: Dict[str, Any],
        confidence_threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """
        根据检测到的设计模式调整info_status

        Args:
            original_status: Phase1 LLM输出的原始info_status
            user_input: 用户原始输入
            detected_modes: 检测到的模式列表 [{"mode": "M1_concept_driven", "confidence": 0.85}, ...]
            phase1_result: Phase1完整结果（包含project_type等）
            confidence_threshold: 模式置信度阈值（默认0.3）

        Returns:
            {
                "adjusted_status": "sufficient/partial/insufficient",
                "original_status": "...",
                "mode_adjustments": [...],  # 各模式的调整详情
                "final_confidence": 0.75,  # 调整后的信息充分度
                "adjustment_summary": "..."  # 调整说明
            }
        """

        # 过滤低置信度模式
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) >= confidence_threshold]

        if not valid_modes:
            return {
                "adjusted_status": original_status,
                "original_status": original_status,
                "mode_adjustments": [],
                "final_confidence": ModeAwareInfoQualityAdjuster._status_to_score(original_status),
                "adjustment_summary": "无高置信度模式，保持原状态",
            }

        # 计算基础分数（从原始status转换）
        base_score = ModeAwareInfoQualityAdjuster._status_to_score(original_status)

        # 逐个模式检查信息完整性
        mode_adjustments = []
        total_penalty = 0.0
        total_weight = 0.0

        for mode_info in valid_modes:
            mode_id = mode_info.get("mode", "")
            confidence = mode_info.get("confidence", 0)

            if mode_id not in MODE_INFO_REQUIREMENTS:
                continue

            requirement = MODE_INFO_REQUIREMENTS[mode_id]

            # 检查关键词覆盖率
            keyword_coverage = ModeAwareInfoQualityAdjuster._check_keyword_coverage(
                user_input, requirement.required_keywords
            )

            # 计算该模式的信息充分度

            # 如果关键词覆盖率低，应用惩罚
            if keyword_coverage < 0.3:  # 覆盖率低于30%
                penalty = requirement.missing_penalty * confidence  # 惩罚与置信度成正比
                total_penalty += penalty

            total_weight += requirement.quality_weight * confidence

            mode_adjustments.append(
                {
                    "mode_id": mode_id,
                    "mode_name": requirement.mode_name,
                    "confidence": round(confidence, 2),
                    "keyword_coverage": round(keyword_coverage, 2),
                    "quality_weight": requirement.quality_weight,
                    "penalty_applied": round(requirement.missing_penalty * confidence, 2)
                    if keyword_coverage < 0.3
                    else 0,
                }
            )

        # 计算最终分数
        # 公式：base_score - total_penalty
        final_score = max(0.0, min(1.0, base_score - total_penalty))

        # 转换回status
        adjusted_status = ModeAwareInfoQualityAdjuster._score_to_status(final_score)

        # 生成调整说明
        adjustment_summary = ModeAwareInfoQualityAdjuster._generate_adjustment_summary(
            original_status, adjusted_status, mode_adjustments
        )

        return {
            "adjusted_status": adjusted_status,
            "original_status": original_status,
            "mode_adjustments": mode_adjustments,
            "final_confidence": round(final_score, 2),
            "adjustment_summary": adjustment_summary,
        }

    @staticmethod
    def _status_to_score(status: str) -> float:
        """info_status -> 数值分数"""
        mapping = {"sufficient": 0.85, "partial": 0.55, "insufficient": 0.25}
        return mapping.get(status, 0.55)

    @staticmethod
    def _score_to_status(score: float) -> str:
        """数值分数 -> info_status"""
        if score >= 0.75:
            return "sufficient"
        elif score >= 0.45:
            return "partial"
        else:
            return "insufficient"

    @staticmethod
    def _check_keyword_coverage(text: str, keywords: List[str]) -> float:
        """
        检查文本中关键词的覆盖率

        Returns:
            覆盖率 (0.0 - 1.0)
        """
        if not keywords:
            return 1.0

        text_lower = text.lower()
        matched_count = 0

        for keyword in keywords:
            # 中文关键词直接使用in检查，英文使用正则
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                matched_count += 1

        return matched_count / len(keywords)

    @staticmethod
    def _generate_adjustment_summary(
        original_status: str, adjusted_status: str, mode_adjustments: List[Dict[str, Any]]
    ) -> str:
        """生成调整说明"""
        if original_status == adjusted_status:
            return f"保持原状态 '{original_status}' (根据{len(mode_adjustments)}个模式验证)"

        # 找出惩罚最大的模式
        max_penalty_mode = None
        max_penalty = 0
        for adj in mode_adjustments:
            if adj["penalty_applied"] > max_penalty:
                max_penalty = adj["penalty_applied"]
                max_penalty_mode = adj

        if max_penalty_mode:
            return (
                f"从 '{original_status}' 调整为 '{adjusted_status}' - "
                f"{max_penalty_mode['mode_name']}(置信度{max_penalty_mode['confidence']}) "
                f"关键信息覆盖率仅{max_penalty_mode['keyword_coverage']*100:.0f}%"
            )

        return f"从 '{original_status}' 调整为 '{adjusted_status}'"

    @staticmethod
    def get_missing_info_hints(
        detected_modes: List[Dict[str, Any]], user_input: str, confidence_threshold: float = 0.3
    ) -> List[str]:
        """
        获取缺失信息的提示

        Returns:
            提示列表，例如：["建议补充概念主题信息", "需要明确成本预算"]
        """
        hints = []
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) >= confidence_threshold]

        for mode_info in valid_modes:
            mode_id = mode_info.get("mode", "")
            mode_info.get("confidence", 0)

            if mode_id not in MODE_INFO_REQUIREMENTS:
                continue

            requirement = MODE_INFO_REQUIREMENTS[mode_id]

            # 检查关键词覆盖率
            keyword_coverage = ModeAwareInfoQualityAdjuster._check_keyword_coverage(
                user_input, requirement.required_keywords
            )

            # 如果覆盖率低，生成提示
            if keyword_coverage < 0.3:
                # 找出缺失的关键词类别
                missing_keywords = []
                text_lower = user_input.lower()
                for keyword in requirement.required_keywords[:3]:  # 只取前3个关键词
                    keyword_lower = keyword.lower()
                    if keyword_lower not in text_lower:
                        missing_keywords.append(keyword)

                if missing_keywords:
                    hint = f"[{requirement.mode_name}] 建议补充: {'/'.join(missing_keywords)}相关信息"
                    hints.append(hint)

        return hints


# 便捷函数：用于requirements_analyst_agent.py中调用
def adjust_info_status_by_mode(
    original_status: str, user_input: str, detected_modes: List[Dict[str, Any]], phase1_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    便捷调用函数

    使用方式（在phase1_node中）:

    ```python
    from ..services.mode_info_adjuster import adjust_info_status_by_mode

    # 原始LLM输出
    info_status = phase1_result.get("info_status", "insufficient")

    # 模式感知调整
    if detected_modes:
        adjustment_result = adjust_info_status_by_mode(
            original_status=info_status,
            user_input=user_input,
            detected_modes=detected_modes,
            phase1_result=phase1_result
        )

        info_status = adjustment_result["adjusted_status"]
        logger.info(f"[ModeAdjustment] {adjustment_result['adjustment_summary']}")
    ```
    """
    return ModeAwareInfoQualityAdjuster.adjust_info_status(
        original_status=original_status,
        user_input=user_input,
        detected_modes=detected_modes,
        phase1_result=phase1_result,
    )
