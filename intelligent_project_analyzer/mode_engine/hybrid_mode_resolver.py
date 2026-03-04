"""
混合模式冲突解决服务模块

功能：
1. 检测混合模式（多个高置信度模式共存）
2. 加载冲突解决策略配置
3. 应用维度优先级规则
4. 生成设计指导和约束条件

版本: v7.800
创建日期: 2026-02-13
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass
class HybridModeDetectionResult:
    """混合模式检测结果"""

    is_hybrid: bool
    detected_modes: List[str]  # 例如: ["M1", "M4"]
    confidence_scores: Dict[str, float]  # 例如: {"M1": 0.78, "M4": 0.65}
    confidence_gap: float  # 最高与次高置信度的差值
    pattern_key: str | None  # 例如: "M1_M4"

    def __str__(self):
        if not self.is_hybrid:
            return f"单模式: {self.detected_modes[0]} (置信度: {self.confidence_scores[self.detected_modes[0]]:.2f})"
        return f"混合模式: {'+'.join(self.detected_modes)} (模式键: {self.pattern_key})"


@dataclass
class ConflictDimension:
    """冲突维度"""

    dimension: str
    mode_positions: Dict[str, str]  # 各模式在该维度的立场
    severity: str  # low/medium/high
    priority_mode: str  # 优先模式或策略
    rule: str  # 解决规则
    constraint: str | None  # 约束条件


@dataclass
class ResolutionResult:
    """冲突解决结果"""

    pattern_key: str
    pattern_name: str
    resolution_strategy: str
    conflict_dimensions: List[ConflictDimension]
    dimension_priorities: Dict[str, Dict]
    risks: List[str]
    typical_scenarios: List[str]
    recommendations: List[str]  # 生成的设计建议

    def get_priority_summary(self) -> Dict[str, str]:
        """获取维度优先级摘要"""
        summary = {}
        for dim_name, dim_data in self.dimension_priorities.items():
            priority_mode = dim_data.get("priority_mode", "unknown")
            rule = dim_data.get("rule", "")
            summary[dim_name] = f"[{priority_mode}] {rule}"
        return summary


class HybridModeResolver:
    """
    混合模式冲突解决器

    职责：
    1. 检测混合模式
    2. 查找冲突解决策略
    3. 应用维度优先级规则
    4. 生成设计指导
    """

    def __init__(self, config_path: str | None = None):
        """
        初始化混合模式解决器

        Args:
            config_path: MODE_HYBRID_PATTERNS.yaml配置文件路径
        """
        if config_path is None:
            # 默认配置路径
            config_path = Path(__file__).parent.parent.parent / "config" / "MODE_HYBRID_PATTERNS.yaml"

        self.config_path = Path(config_path)
        self._config_cache = None
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                self._config_cache = yaml.safe_load(f)

            logger.info(f"混合模式配置加载成功: {self.config_path}")

            # 验证配置结构
            required_keys = ["global_config", "hybrid_patterns", "resolution_workflow", "general_principles"]
            for key in required_keys:
                if key not in self._config_cache:
                    logger.warning(f"配置缺少必要键: {key}")

        except Exception as e:
            logger.error(f"加载混合模式配置失败: {e}")
            self._config_cache = None

    def detect_hybrid_mode(
        self,
        mode_confidences: Dict[str, float],
        min_confidence: float | None = None,
        max_confidence_gap: float | None = None,
    ) -> HybridModeDetectionResult:
        """
        检测是否为混合模式

        Args:
            mode_confidences: 模式置信度字典，例如 {"M1": 0.78, "M4": 0.65, "M3": 0.32}
            min_confidence: 最小置信度阈值（低于此值不参与混合判断）
            max_confidence_gap: 最大置信度差（差值小于此值视为混合模式）

        Returns:
            HybridModeDetectionResult
        """
        if not self._config_cache:
            logger.error("配置未加载，无法检测混合模式")
            return self._create_error_result(mode_confidences)

        # 获取阈值配置
        global_config = self._config_cache.get("global_config", {})
        thresholds = global_config.get("detection_thresholds", {})

        if min_confidence is None:
            min_confidence = thresholds.get("min_confidence", 0.45)
        if max_confidence_gap is None:
            max_confidence_gap = thresholds.get("max_confidence_gap", 0.25)

        # 过滤低置信度模式
        valid_modes = {mode: conf for mode, conf in mode_confidences.items() if conf >= min_confidence}

        if not valid_modes:
            logger.warning("无有效模式（所有置信度低于阈值）")
            return self._create_error_result(mode_confidences)

        # 按置信度降序排序
        sorted_modes = sorted(valid_modes.items(), key=lambda x: x[1], reverse=True)

        # 判断是否为混合模式
        if len(sorted_modes) == 1:
            # 单模式
            mode, conf = sorted_modes[0]
            return HybridModeDetectionResult(
                is_hybrid=False,
                detected_modes=[mode],
                confidence_scores={mode: conf},
                confidence_gap=0.0,
                pattern_key=None,
            )

        # 计算置信度差
        top_mode, top_conf = sorted_modes[0]
        second_mode, second_conf = sorted_modes[1]
        confidence_gap = top_conf - second_conf

        # 判断是否为混合模式
        is_hybrid = confidence_gap <= max_confidence_gap

        if is_hybrid:
            # 混合模式：取前两个高置信度模式
            detected_modes = [top_mode, second_mode]
            pattern_key = self._generate_pattern_key(detected_modes)

            logger.info(
                f"检测到混合模式: {'+'.join(detected_modes)} "
                f"(置信度: {top_conf:.2f} vs {second_conf:.2f}, 差值: {confidence_gap:.2f})"
            )

            return HybridModeDetectionResult(
                is_hybrid=True,
                detected_modes=detected_modes,
                confidence_scores={top_mode: top_conf, second_mode: second_conf},
                confidence_gap=confidence_gap,
                pattern_key=pattern_key,
            )
        else:
            # 单模式主导（差距明显）
            logger.info(
                f"单模式主导: {top_mode} (置信度: {top_conf:.2f}, " f"与次高差距: {confidence_gap:.2f} > {max_confidence_gap})"
            )

            return HybridModeDetectionResult(
                is_hybrid=False,
                detected_modes=[top_mode],
                confidence_scores={top_mode: top_conf},
                confidence_gap=confidence_gap,
                pattern_key=None,
            )

    def _generate_pattern_key(self, modes: List[str]) -> str:
        """
        生成模式键

        规则：按字母序排列（M1_M4, M2_M8等）

        Args:
            modes: 模式列表，例如 ["M4", "M1"]

        Returns:
            模式键，例如 "M1_M4"
        """
        # 提取数字并排序
        mode_numbers = sorted([int(m.replace("M", "")) for m in modes])
        return "_".join([f"M{n}" for n in mode_numbers])

    def resolve_conflict(self, detection_result: HybridModeDetectionResult) -> ResolutionResult | None:
        """
        解决混合模式冲突

        Args:
            detection_result: 混合模式检测结果

        Returns:
            ResolutionResult 或 None（如果非混合模式或无对应策略）
        """
        if not detection_result.is_hybrid:
            logger.info("非混合模式，无需冲突解决")
            return None

        if not self._config_cache:
            logger.error("配置未加载，无法解决冲突")
            return None

        pattern_key = detection_result.pattern_key
        hybrid_patterns = self._config_cache.get("hybrid_patterns", {})

        # 查找对应的混合模式配置
        if pattern_key not in hybrid_patterns:
            logger.warning(f"未找到混合模式配置: {pattern_key}，使用通用平衡策略")
            return self._apply_generic_balance_strategy(detection_result)

        pattern_config = hybrid_patterns[pattern_key]

        # 提取冲突维度
        conflict_dimensions = self._parse_conflict_dimensions(
            pattern_config.get("conflict_dimensions", []), detection_result.detected_modes
        )

        # 提取维度优先级
        dimension_priorities = pattern_config.get("dimension_priorities", {})

        # 生成设计建议
        recommendations = self._generate_recommendations(pattern_config, detection_result)

        result = ResolutionResult(
            pattern_key=pattern_key,
            pattern_name=pattern_config.get("name", pattern_key),
            resolution_strategy=pattern_config.get("resolution_strategy", "balanced"),
            conflict_dimensions=conflict_dimensions,
            dimension_priorities=dimension_priorities,
            risks=pattern_config.get("risks", []),
            typical_scenarios=pattern_config.get("typical_scenarios", []),
            recommendations=recommendations,
        )

        logger.info(f"冲突解决完成: {pattern_key}, 策略: {result.resolution_strategy}")

        return result

    def _parse_conflict_dimensions(
        self, conflict_dims_config: List[Dict], detected_modes: List[str]
    ) -> List[ConflictDimension]:
        """解析冲突维度配置"""
        conflict_dimensions = []

        for dim_config in conflict_dims_config:
            dimension_name = dim_config.get("dimension", "unknown")

            # 提取各模式的立场
            mode_positions = {}
            for mode in detected_modes:
                position_key = f"{mode.lower()}_position"
                if position_key in dim_config:
                    mode_positions[mode] = dim_config[position_key]

            conflict_dimensions.append(
                ConflictDimension(
                    dimension=dimension_name,
                    mode_positions=mode_positions,
                    severity=dim_config.get("severity", "medium"),
                    priority_mode="",  # 将在dimension_priorities中指定
                    rule="",
                    constraint=None,
                )
            )

        return conflict_dimensions

    def _generate_recommendations(self, pattern_config: Dict, detection_result: HybridModeDetectionResult) -> List[str]:
        """生成设计建议"""
        recommendations = []

        pattern_name = pattern_config.get("name", detection_result.pattern_key)
        resolution_strategy = pattern_config.get("resolution_strategy", "balanced")
        dimension_priorities = pattern_config.get("dimension_priorities", {})

        # 建议1: 模式识别
        modes_str = "+".join(detection_result.detected_modes)
        recommendations.append(f"✓ 识别为【{pattern_name}】混合模式 ({modes_str})")

        # 建议2: 策略说明
        strategy_desc = self._get_strategy_description(resolution_strategy)
        recommendations.append(f"✓ 采用【{strategy_desc}】解决策略")

        # 建议3: 维度优先级
        for dim_name, dim_data in dimension_priorities.items():
            priority_mode = dim_data.get("priority_mode", "unknown")
            rule = dim_data.get("rule", "")
            constraint = dim_data.get("constraint", "")

            rec = f"✓ {dim_name}: [{priority_mode}优先] {rule}"
            if constraint:
                rec += f" (约束: {constraint})"
            recommendations.append(rec)

        # 建议4: 风险提示
        risks = pattern_config.get("risks", [])
        if risks:
            recommendations.append(f"⚠ 风险提示: {'; '.join(risks[:2])}")

        return recommendations

    def _get_strategy_description(self, strategy: str) -> str:
        """获取策略描述"""
        strategy_map = {
            "priority_based": "优先级策略",
            "balanced": "平衡策略",
            "zoned": "分区策略",
            "phased": "分阶段策略",
            "synergy": "协同策略",
        }
        return strategy_map.get(strategy, strategy)

    def _apply_generic_balance_strategy(self, detection_result: HybridModeDetectionResult) -> ResolutionResult:
        """应用通用平衡策略（当无预定义配置时）"""
        logger.info("应用通用平衡策略")

        recommendations = [
            f"✓ 识别为混合模式: {'+'.join(detection_result.detected_modes)}",
            "✓ 采用【通用平衡策略】",
            "✓ 建议: 在冲突维度上寻找中间路线",
            "✓ 建议: 核心区域优先高置信度模式",
            "✓ 建议: 非核心区域考虑平衡或分区",
            "⚠ 风险: 缺少预定义策略，需人工判断",
        ]

        return ResolutionResult(
            pattern_key=detection_result.pattern_key,
            pattern_name=f"通用混合模式 ({'+'.join(detection_result.detected_modes)})",
            resolution_strategy="balanced",
            conflict_dimensions=[],
            dimension_priorities={},
            risks=["缺少预定义策略，需人工判断"],
            typical_scenarios=[],
            recommendations=recommendations,
        )

    def _create_error_result(self, mode_confidences: Dict[str, float]) -> HybridModeDetectionResult:
        """创建错误结果"""
        # 选择置信度最高的模式作为默认
        if mode_confidences:
            top_mode = max(mode_confidences, key=mode_confidences.get)
            return HybridModeDetectionResult(
                is_hybrid=False,
                detected_modes=[top_mode],
                confidence_scores={top_mode: mode_confidences[top_mode]},
                confidence_gap=0.0,
                pattern_key=None,
            )
        else:
            return HybridModeDetectionResult(
                is_hybrid=False, detected_modes=[], confidence_scores={}, confidence_gap=0.0, pattern_key=None
            )

    def get_dimension_priority(self, resolution_result: ResolutionResult, dimension_name: str) -> Dict | None:
        """
        获取特定维度的优先级规则

        Args:
            resolution_result: 冲突解决结果
            dimension_name: 维度名称

        Returns:
            维度优先级配置字典，包含 priority_mode, rule, constraint
        """
        return resolution_result.dimension_priorities.get(dimension_name)

    def validate_constraints(
        self, resolution_result: ResolutionResult, design_params: Dict[str, any]
    ) -> Tuple[bool, List[str]]:
        """
        验证设计参数是否满足约束条件

        Args:
            resolution_result: 冲突解决结果
            design_params: 设计参数字典

        Returns:
            (是否通过, 违规信息列表)
        """
        violations = []

        for dim_name, dim_data in resolution_result.dimension_priorities.items():
            constraint = dim_data.get("constraint")
            if not constraint:
                continue

            # 这里可以实现约束验证逻辑
            # 例如：解析 "总成本不得超过资产模型预算15%"
            # 暂时只记录约束，实际验证需要根据具体项目定制

            logger.debug(f"维度 {dim_name} 约束: {constraint}")

        is_valid = len(violations) == 0
        return is_valid, violations


# ==================================================================================
# 便捷函数
# ==================================================================================


def detect_and_resolve_hybrid_mode(
    mode_confidences: Dict[str, float], config_path: str | None = None
) -> Tuple[HybridModeDetectionResult, ResolutionResult | None]:
    """
    一站式检测和解决混合模式冲突

    Args:
        mode_confidences: 模式置信度字典
        config_path: 配置文件路径（可选）

    Returns:
        (检测结果, 解决结果)
    """
    resolver = HybridModeResolver(config_path)

    # 检测混合模式
    detection_result = resolver.detect_hybrid_mode(mode_confidences)

    # 解决冲突（如果是混合模式）
    resolution_result = None
    if detection_result.is_hybrid:
        resolution_result = resolver.resolve_conflict(detection_result)

    return detection_result, resolution_result


# ==================================================================================
# 测试代码
# ==================================================================================

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=" * 80)
    print("混合模式冲突解决器测试")
    print("=" * 80)

    # 测试场景1: M1×M4 混合模式（概念驱动+资本导向）
    print("\n测试场景1: M1×M4 混合模式")
    print("-" * 80)

    mode_confidences_1 = {"M1": 0.78, "M4": 0.65, "M3": 0.32, "M2": 0.28}

    detection_result_1, resolution_result_1 = detect_and_resolve_hybrid_mode(mode_confidences_1)

    print(f"\n检测结果: {detection_result_1}")
    if resolution_result_1:
        print(f"解决策略: {resolution_result_1.resolution_strategy}")
        print(f"模式名称: {resolution_result_1.pattern_name}")
        print("\n设计建议:")
        for rec in resolution_result_1.recommendations:
            print(f"  {rec}")

    # 测试场景2: M2×M8 混合模式（功能效率+极端环境）
    print("\n\n测试场景2: M2×M8 混合模式")
    print("-" * 80)

    mode_confidences_2 = {"M2": 0.72, "M8": 0.68, "M7": 0.35}

    detection_result_2, resolution_result_2 = detect_and_resolve_hybrid_mode(mode_confidences_2)

    print(f"\n检测结果: {detection_result_2}")
    if resolution_result_2:
        print(f"解决策略: {resolution_result_2.resolution_strategy}")
        print(f"模式名称: {resolution_result_2.pattern_name}")
        print("\n设计建议:")
        for rec in resolution_result_2.recommendations:
            print(f"  {rec}")

    # 测试场景3: 单模式主导（M1置信度远高于其他）
    print("\n\n测试场景3: 单模式主导")
    print("-" * 80)

    mode_confidences_3 = {"M1": 0.85, "M3": 0.45, "M4": 0.28}

    detection_result_3, resolution_result_3 = detect_and_resolve_hybrid_mode(mode_confidences_3)

    print(f"\n检测结果: {detection_result_3}")
    if resolution_result_3:
        print("需要冲突解决")
    else:
        print("无需冲突解决（单模式主导）")

    # 测试场景4: 未预定义的混合模式（M3×M7）
    print("\n\n测试场景4: 未预定义混合模式 (M3×M7)")
    print("-" * 80)

    mode_confidences_4 = {"M3": 0.70, "M7": 0.62, "M1": 0.38}

    detection_result_4, resolution_result_4 = detect_and_resolve_hybrid_mode(mode_confidences_4)

    print(f"\n检测结果: {detection_result_4}")
    if resolution_result_4:
        print(f"解决策略: {resolution_result_4.resolution_strategy}")
        print("\n设计建议:")
        for rec in resolution_result_4.recommendations:
            print(f"  {rec}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
