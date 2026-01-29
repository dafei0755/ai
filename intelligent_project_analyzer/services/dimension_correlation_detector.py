"""
维度关联检测器 - 检测维度冲突和推荐调整

v7.139 Phase 3: 维度关联建模
自动检测维度配置中的冲突（互斥、正负相关），并提供智能调整建议。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger


class DimensionCorrelationDetector:
    """
    维度关联检测器

    功能：
    1. 检测维度配置中的冲突（互斥、正负相关违规）
    2. 识别特殊约束违规（如适老化→安全性）
    3. 生成智能调整建议
    4. 计算冲突严重程度和置信度
    """

    _instance = None
    _correlation_config: Optional[Dict[str, Any]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if DimensionCorrelationDetector._correlation_config is None:
            self._load_config()

    def _load_config(self) -> None:
        """加载维度关联规则配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "dimension_correlations.yaml"

        if not config_path.exists():
            logger.warning(f"⚠️ 维度关联配置文件不存在: {config_path}，功能降级")
            DimensionCorrelationDetector._correlation_config = {}
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                DimensionCorrelationDetector._correlation_config = yaml.safe_load(f)
            logger.info(f"✅ [v7.139] 维度关联配置加载成功")
        except Exception as e:
            logger.error(f"❌ 维度关联配置加载失败: {e}")
            DimensionCorrelationDetector._correlation_config = {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return DimensionCorrelationDetector._correlation_config or {}

    def is_enabled(self) -> bool:
        """检查关联检测是否启用"""
        detection_config = self.config.get("detection_config", {})
        return detection_config.get("enabled", True)

    def detect_conflicts(self, dimensions: List[Dict[str, Any]], mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检测维度配置中的冲突

        Args:
            dimensions: 维度配置列表，每个维度包含 dimension_id 和 default_value
            mode: 检测模式（strict/balanced/lenient），默认使用配置文件中的模式

        Returns:
            冲突列表，每个冲突包含：
            - conflict_type: 冲突类型（mutual_exclusion/positive_correlation/negative_correlation/special_constraint）
            - severity: 严重程度（critical/warning/info）
            - dimension_a: 维度A的ID
            - dimension_b: 维度B的ID（特殊约束可能没有）
            - current_value_a: 维度A的当前值
            - current_value_b: 维度B的当前值（特殊约束可能没有）
            - reason: 冲突原因
            - suggestion: 调整建议
            - confidence: 置信度（0.0-1.0）
        """
        if not self.is_enabled():
            logger.debug("ℹ️ [v7.139] 维度关联检测已禁用")
            return []

        if not dimensions:
            return []

        # 获取检测模式
        detection_config = self.config.get("detection_config", {})
        mode = mode or detection_config.get("mode", "balanced")
        min_confidence = detection_config.get("min_confidence", 0.7)

        # 构建维度ID → 值的映射
        dimension_values = {dim["dimension_id"]: dim["default_value"] for dim in dimensions}

        conflicts = []

        # 1. 检测互斥关系
        conflicts.extend(self._detect_mutual_exclusion(dimension_values))

        # 2. 检测正相关关系
        conflicts.extend(self._detect_positive_correlation(dimension_values))

        # 3. 检测负相关关系
        conflicts.extend(self._detect_negative_correlation(dimension_values))

        # 4. 检测特殊约束
        conflicts.extend(self._detect_special_constraints(dimension_values))

        # 过滤：根据模式和置信度
        filtered_conflicts = self._filter_conflicts(conflicts, mode, min_confidence)

        # 排序：按严重程度
        priority_order = detection_config.get("priority_order", ["critical", "warning", "info"])
        filtered_conflicts.sort(
            key=lambda x: priority_order.index(x["severity"]) if x["severity"] in priority_order else 99
        )

        if filtered_conflicts:
            logger.info(f"🔍 [v7.139] 检测到 {len(filtered_conflicts)} 个维度冲突")
        else:
            logger.debug("✅ [v7.139] 未检测到维度冲突")

        return filtered_conflicts

    def _detect_mutual_exclusion(self, dimension_values: Dict[str, int]) -> List[Dict[str, Any]]:
        """检测互斥关系冲突"""
        conflicts = []
        mutual_exclusion_rules = self.config.get("mutual_exclusion", [])

        for rule in mutual_exclusion_rules:
            dim_a = rule.get("dimension_a")
            dim_b = rule.get("dimension_b")
            threshold = rule.get("threshold", 140)

            # 检查两个维度是否都存在
            if dim_a not in dimension_values or dim_b not in dimension_values:
                continue

            value_a = dimension_values[dim_a]
            value_b = dimension_values[dim_b]
            sum_value = value_a + value_b

            # 检测冲突
            if sum_value > threshold:
                conflict = {
                    "conflict_type": "mutual_exclusion",
                    "severity": rule.get("severity", "warning"),
                    "dimension_a": dim_a,
                    "dimension_b": dim_b,
                    "current_value_a": value_a,
                    "current_value_b": value_b,
                    "sum_value": sum_value,
                    "threshold": threshold,
                    "reason": rule.get("reason", "互斥维度同时设置高值"),
                    "suggestion": rule.get("suggestion", "建议降低其中一个维度的值"),
                    "confidence": min(1.0, (sum_value - threshold) / 40),  # 超出越多，置信度越高
                }
                conflicts.append(conflict)
                logger.debug(f"   🔍 检测到互斥冲突: {dim_a}({value_a}) + {dim_b}({value_b}) = {sum_value} > {threshold}")

        return conflicts

    def _detect_positive_correlation(self, dimension_values: Dict[str, int]) -> List[Dict[str, Any]]:
        """检测正相关关系冲突"""
        conflicts = []
        positive_correlation_rules = self.config.get("positive_correlation", [])

        for rule in positive_correlation_rules:
            dim_a = rule.get("dimension_a")
            dim_b = rule.get("dimension_b")
            min_diff = rule.get("min_diff", 25)

            # 检查两个维度是否都存在
            if dim_a not in dimension_values or dim_b not in dimension_values:
                continue

            value_a = dimension_values[dim_a]
            value_b = dimension_values[dim_b]
            diff_value = abs(value_a - value_b)

            # 检测冲突（差值过大）
            if diff_value > min_diff:
                conflict = {
                    "conflict_type": "positive_correlation",
                    "severity": rule.get("severity", "info"),
                    "dimension_a": dim_a,
                    "dimension_b": dim_b,
                    "current_value_a": value_a,
                    "current_value_b": value_b,
                    "diff_value": diff_value,
                    "min_diff": min_diff,
                    "reason": rule.get("reason", "正相关维度差值过大"),
                    "suggestion": rule.get("suggestion", "建议调整两个维度保持一致"),
                    "confidence": min(1.0, (diff_value - min_diff) / 30),  # 差值越大，置信度越高
                }
                conflicts.append(conflict)
                logger.debug(f"   🔍 检测到正相关冲突: |{dim_a}({value_a}) - {dim_b}({value_b})| = {diff_value} > {min_diff}")

        return conflicts

    def _detect_negative_correlation(self, dimension_values: Dict[str, int]) -> List[Dict[str, Any]]:
        """检测负相关关系冲突"""
        conflicts = []
        negative_correlation_rules = self.config.get("negative_correlation", [])

        for rule in negative_correlation_rules:
            dim_a = rule.get("dimension_a")
            dim_b = rule.get("dimension_b")
            max_sum = rule.get("max_sum", 140)

            # 检查两个维度是否都存在
            if dim_a not in dimension_values or dim_b not in dimension_values:
                continue

            value_a = dimension_values[dim_a]
            value_b = dimension_values[dim_b]
            sum_value = value_a + value_b

            # 检测冲突（和值过大）
            if sum_value > max_sum:
                conflict = {
                    "conflict_type": "negative_correlation",
                    "severity": rule.get("severity", "warning"),
                    "dimension_a": dim_a,
                    "dimension_b": dim_b,
                    "current_value_a": value_a,
                    "current_value_b": value_b,
                    "sum_value": sum_value,
                    "max_sum": max_sum,
                    "reason": rule.get("reason", "负相关维度同时设置高值"),
                    "suggestion": rule.get("suggestion", "建议降低其中一个维度的值"),
                    "confidence": min(1.0, (sum_value - max_sum) / 40),  # 超出越多，置信度越高
                }
                conflicts.append(conflict)
                logger.debug(f"   🔍 检测到负相关冲突: {dim_a}({value_a}) + {dim_b}({value_b}) = {sum_value} > {max_sum}")

        return conflicts

    def _detect_special_constraints(self, dimension_values: Dict[str, int]) -> List[Dict[str, Any]]:
        """检测特殊约束违规"""
        conflicts = []
        special_constraints = self.config.get("special_constraints", [])

        for constraint in special_constraints:
            constraint_id = constraint.get("constraint_id")
            trigger_condition = constraint.get("trigger_condition", {})
            required_adjustments = constraint.get("required_adjustments", [])

            # 检查触发条件
            trigger_dim = trigger_condition.get("dimension")
            trigger_threshold = trigger_condition.get("threshold", 70)

            if trigger_dim not in dimension_values:
                continue

            trigger_value = dimension_values[trigger_dim]

            # 触发条件满足
            if trigger_value > trigger_threshold:
                # 检查每个必需调整
                for adjustment in required_adjustments:
                    adj_dim = adjustment.get("dimension")
                    min_value = adjustment.get("min_value", 0)

                    if adj_dim not in dimension_values:
                        continue

                    adj_value = dimension_values[adj_dim]

                    # 检测违规
                    if adj_value < min_value:
                        conflict = {
                            "conflict_type": "special_constraint",
                            "severity": constraint.get("severity", "critical"),
                            "constraint_id": constraint_id,
                            "dimension_a": trigger_dim,  # 触发维度
                            "dimension_b": adj_dim,  # 要求调整的维度
                            "current_value_a": trigger_value,
                            "current_value_b": adj_value,
                            "required_min_value": min_value,
                            "reason": adjustment.get("reason", "特殊约束违规"),
                            "suggestion": f"由于{trigger_dim}={trigger_value}，建议将{adj_dim}提升至{min_value}以上",
                            "confidence": 1.0,  # 特殊约束置信度100%
                        }
                        conflicts.append(conflict)
                        logger.debug(f"   🔍 检测到特殊约束违规: {constraint_id} - {adj_dim}({adj_value}) < {min_value}")

        return conflicts

    def _filter_conflicts(
        self, conflicts: List[Dict[str, Any]], mode: str, min_confidence: float
    ) -> List[Dict[str, Any]]:
        """根据模式和置信度过滤冲突"""
        filtered = []

        for conflict in conflicts:
            severity = conflict.get("severity", "info")
            confidence = conflict.get("confidence", 1.0)

            # 置信度过滤
            if confidence < min_confidence:
                continue

            # 模式过滤
            if mode == "strict":
                # 严格模式：所有冲突都保留
                filtered.append(conflict)
            elif mode == "balanced":
                # 平衡模式：仅保留warning和critical
                if severity in ["warning", "critical"]:
                    filtered.append(conflict)
            elif mode == "lenient":
                # 宽松模式：仅保留critical
                if severity == "critical":
                    filtered.append(conflict)

        return filtered

    def suggest_adjustments(
        self, conflicts: List[Dict[str, Any]], current_dimensions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根据冲突生成智能调整建议

        Args:
            conflicts: 冲突列表（detect_conflicts的返回值）
            current_dimensions: 当前维度配置列表

        Returns:
            调整建议列表，每个建议包含：
            - dimension_id: 要调整的维度ID
            - current_value: 当前值
            - suggested_value: 建议值
            - reason: 调整原因
            - priority: 优先级（high/medium/low）
        """
        if not conflicts:
            return []

        detection_config = self.config.get("detection_config", {})
        adjustment_range = detection_config.get("adjustment_range", 10)

        # 构建维度ID → 值的映射
        dimension_values = {dim["dimension_id"]: dim["default_value"] for dim in current_dimensions}

        suggestions = []
        adjusted_dims = set()  # 避免重复调整同一个维度

        for conflict in conflicts:
            conflict_type = conflict["conflict_type"]
            severity = conflict["severity"]

            if conflict_type in ["mutual_exclusion", "negative_correlation"]:
                # 互斥和负相关：建议降低其中一个维度
                dim_a = conflict["dimension_a"]
                dim_b = conflict["dimension_b"]
                value_a = conflict["current_value_a"]
                value_b = conflict["current_value_b"]

                # 优先降低值较高的维度
                if value_a > value_b and dim_a not in adjusted_dims:
                    suggested_value = max(0, value_a - adjustment_range)
                    suggestions.append(
                        {
                            "dimension_id": dim_a,
                            "current_value": value_a,
                            "suggested_value": suggested_value,
                            "reason": conflict["reason"],
                            "priority": "high" if severity == "critical" else "medium",
                        }
                    )
                    adjusted_dims.add(dim_a)
                elif dim_b not in adjusted_dims:
                    suggested_value = max(0, value_b - adjustment_range)
                    suggestions.append(
                        {
                            "dimension_id": dim_b,
                            "current_value": value_b,
                            "suggested_value": suggested_value,
                            "reason": conflict["reason"],
                            "priority": "high" if severity == "critical" else "medium",
                        }
                    )
                    adjusted_dims.add(dim_b)

            elif conflict_type == "positive_correlation":
                # 正相关：建议调整值较低的维度，使两者接近
                dim_a = conflict["dimension_a"]
                dim_b = conflict["dimension_b"]
                value_a = conflict["current_value_a"]
                value_b = conflict["current_value_b"]

                # 调整值较低的维度，向值较高的维度靠拢
                if value_a < value_b and dim_a not in adjusted_dims:
                    suggested_value = min(100, value_a + adjustment_range)
                    suggestions.append(
                        {
                            "dimension_id": dim_a,
                            "current_value": value_a,
                            "suggested_value": suggested_value,
                            "reason": conflict["reason"],
                            "priority": "medium" if severity == "warning" else "low",
                        }
                    )
                    adjusted_dims.add(dim_a)
                elif dim_b not in adjusted_dims:
                    suggested_value = min(100, value_b + adjustment_range)
                    suggestions.append(
                        {
                            "dimension_id": dim_b,
                            "current_value": value_b,
                            "suggested_value": suggested_value,
                            "reason": conflict["reason"],
                            "priority": "medium" if severity == "warning" else "low",
                        }
                    )
                    adjusted_dims.add(dim_b)

            elif conflict_type == "special_constraint":
                # 特殊约束：建议提升要求调整的维度
                dim_b = conflict["dimension_b"]
                required_min_value = conflict["required_min_value"]

                if dim_b not in adjusted_dims:
                    suggestions.append(
                        {
                            "dimension_id": dim_b,
                            "current_value": conflict["current_value_b"],
                            "suggested_value": required_min_value,
                            "reason": conflict["reason"],
                            "priority": "high",  # 特殊约束优先级总是高
                        }
                    )
                    adjusted_dims.add(dim_b)

        # 排序：优先级 high > medium > low
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 99))

        if suggestions:
            logger.info(f"💡 [v7.139] 生成 {len(suggestions)} 条调整建议")

        return suggestions
