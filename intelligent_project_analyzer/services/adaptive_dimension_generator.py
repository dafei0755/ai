"""
自适应维度生成器 - 混合策略核心模块

基于历史学习数据动态优化维度选择，实现：
- 混合策略: 80% 规则引擎 + 20% 学习优化（动态调整）
- 学习权重: 根据历史数据量自动调整（0-50会话=10%, 50-200=20%, 200-500=40%, 500+=70%）
- 向后兼容: 无数据时回退到传统规则引擎
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from intelligent_project_analyzer.services.dimension_evaluator import DimensionEvaluator
from intelligent_project_analyzer.services.dimension_selector import SCENARIO_DIMENSION_MAPPING, DimensionSelector
from intelligent_project_analyzer.services.dimension_usage_tracker import DimensionUsageTracker

logger = logging.getLogger(__name__)


class AdaptiveDimensionGenerator:
    """
    自适应维度生成器（增强版 DimensionSelector）

    集成学习优化能力，基于历史数据动态调整维度选择策略
    """

    def __init__(self):
        """初始化生成器"""
        self.base_selector = DimensionSelector()
        self.evaluator = DimensionEvaluator()
        self.tracker = DimensionUsageTracker()
        self.logger = logging.getLogger(__name__)

        # 学习开关（环境变量控制）
        self.learning_enabled = os.getenv("ENABLE_DIMENSION_LEARNING", "false").lower() == "true"

        # 学习权重配置
        self.learning_weight_thresholds = {
            "minimal": (0, 50, 0.10),  # 0-50会话: 10%学习权重
            "low": (50, 200, 0.20),  # 50-200会话: 20%学习权重
            "medium": (200, 500, 0.40),  # 200-500会话: 40%学习权重
            "high": (500, float("inf"), 0.70),  # 500+会话: 70%学习权重
        }

    def get_learning_weight(self, historical_count: int) -> Tuple[float, str]:
        """
        根据历史数据量计算学习权重

        Args:
            historical_count: 历史会话数量

        Returns:
            (学习权重, 阶段名称)
        """
        for stage, (min_count, max_count, weight) in self.learning_weight_thresholds.items():
            if min_count <= historical_count < max_count:
                return weight, stage

        return 0.0, "none"

    def select_for_project(
        self,
        project_type: str,
        user_input: str,
        min_dimensions: int = 9,
        max_dimensions: int = 12,
        special_scenes: Optional[List[str]] = None,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        为项目选择维度（混合策略）

        流程:
        1. 基础选择（规则引擎: required + recommended + keyword match）
        2. 场景注入（特殊场景专用维度）
        3. 学习优化（如果启用且有历史数据）
        4. 数量调整（确保在 min-max 范围内）

        Args:
            project_type: 项目类型
            user_input: 用户输入
            min_dimensions: 最小维度数
            max_dimensions: 最大维度数
            special_scenes: 特殊场景标签列表
            historical_data: 历史会话数据（可选，用于学习）

        Returns:
            选中的维度列表
        """
        # Step 1: 基础选择（规则引擎）
        base_dimensions = self.base_selector.select_for_project(
            project_type=project_type,
            user_input=user_input,
            min_dimensions=min_dimensions,
            max_dimensions=max_dimensions,
            special_scenes=special_scenes,
        )

        # 标记来源
        for dim in base_dimensions:
            if "source" not in dim:
                dim["source"] = "rule_engine"

        self.logger.info(f"[AdaptiveDimGen] 基础选择完成 - 项目:{project_type}, " f"维度数:{len(base_dimensions)}")

        # Step 2: 学习优化（如果启用且有数据）
        if self.learning_enabled and historical_data:
            optimized_dimensions = self._apply_learning_optimization(
                base_dimensions=base_dimensions,
                project_type=project_type,
                user_input=user_input,
                historical_data=historical_data,
                max_dimensions=max_dimensions,
            )

            return optimized_dimensions
        else:
            self.logger.info(f"[AdaptiveDimGen] 学习未启用或无历史数据，使用规则引擎结果")
            return base_dimensions

    def _apply_learning_optimization(
        self,
        base_dimensions: List[Dict[str, Any]],
        project_type: str,
        user_input: str,
        historical_data: List[Dict[str, Any]],
        max_dimensions: int,
    ) -> List[Dict[str, Any]]:
        """
        应用学习优化（混合策略核心）

        策略: 根据历史数据质量，动态替换低效维度

        Args:
            base_dimensions: 规则引擎选择的基础维度
            project_type: 项目类型
            user_input: 用户输入
            historical_data: 历史会话数据
            max_dimensions: 最大维度数

        Returns:
            优化后的维度列表
        """
        historical_count = len(historical_data)
        learning_weight, stage = self.get_learning_weight(historical_count)

        self.logger.info(
            f"[AdaptiveDimGen] 学习优化开始 - " f"历史数据:{historical_count}条, 学习权重:{learning_weight:.0%}, 阶段:{stage}"
        )

        # 如果历史数据太少，不进行优化
        if historical_count < 10:
            self.logger.warning(f"[AdaptiveDimGen] 历史数据不足10条({historical_count}), 跳过学习优化")
            return base_dimensions

        # 1. 计算所有维度的得分
        all_dimension_ids = list(self.base_selector.get_all_dimensions().keys())
        dimension_scores = self.evaluator.batch_calculate_scores(
            dimension_ids=all_dimension_ids, historical_data=historical_data
        )

        # 2. 识别当前选择中的低效维度（得分<40）
        low_score_dimensions = []
        for dim in base_dimensions:
            dim_id = dim.get("id")
            score = dimension_scores.get(dim_id, 50.0)
            if score < 40:
                low_score_dimensions.append((dim, score))

        if not low_score_dimensions:
            self.logger.info(f"[AdaptiveDimGen] 当前选择无低效维度，无需优化")
            return base_dimensions

        low_score_dimensions.sort(key=lambda x: x[1])  # 按得分升序

        # 3. 计算应替换的数量（基于学习权重）
        max_replacements = max(1, int(len(low_score_dimensions) * learning_weight))
        replacements_to_make = min(max_replacements, len(low_score_dimensions))

        self.logger.info(f"[AdaptiveDimGen] 发现{len(low_score_dimensions)}个低效维度, " f"计划替换{replacements_to_make}个")

        # 4. 找到高分候选维度（未被选择的高价值维度）
        current_dim_ids = {dim.get("id") for dim in base_dimensions}
        high_value_candidates = [
            (dim_id, score)
            for dim_id, score in dimension_scores.items()
            if dim_id not in current_dim_ids and score >= 60
        ]
        high_value_candidates.sort(key=lambda x: x[1], reverse=True)  # 按得分降序

        if not high_value_candidates:
            self.logger.warning(f"[AdaptiveDimGen] 无可用的高价值候选维度，保持原选择")
            return base_dimensions

        # 5. 执行替换（混合策略）
        optimized_dimensions = base_dimensions.copy()
        replacement_count = 0

        for i in range(replacements_to_make):
            if i >= len(high_value_candidates):
                break

            # 移除低分维度
            low_dim, low_score = low_score_dimensions[i]
            optimized_dimensions.remove(low_dim)

            # 添加高分维度
            candidate_id, candidate_score = high_value_candidates[i]
            candidate_config = self.base_selector.get_dimension_by_id(candidate_id)
            if candidate_config:
                new_dim = self._construct_dimension_config(candidate_id, candidate_config)
                new_dim["source"] = "learning_optimized"
                new_dim["replaced_dimension"] = low_dim.get("id")
                new_dim["score_improvement"] = candidate_score - low_score
                optimized_dimensions.append(new_dim)
                replacement_count += 1

                self.logger.info(
                    f"[AdaptiveDimGen] 替换维度 - "
                    f"移除:{low_dim.get('id')}(得分:{low_score:.1f}) → "
                    f"添加:{candidate_id}(得分:{candidate_score:.1f})"
                )

        # 6. 限制总数
        if len(optimized_dimensions) > max_dimensions:
            optimized_dimensions = optimized_dimensions[:max_dimensions]

        self.logger.info(f"[AdaptiveDimGen] 学习优化完成 - " f"替换数量:{replacement_count}, 最终维度数:{len(optimized_dimensions)}")

        return optimized_dimensions

    def _construct_dimension_config(self, dimension_id: str, dimension_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        构造维度配置对象（与 DimensionSelector 格式一致）

        Args:
            dimension_id: 维度ID
            dimension_config: YAML中的维度配置

        Returns:
            格式化的维度配置字典
        """
        return {
            "id": dimension_id,
            "name": dimension_config.get("name", dimension_id),
            "left_label": dimension_config.get("left_label", ""),
            "right_label": dimension_config.get("right_label", ""),
            "category": dimension_config.get("category", "other"),
            "keywords": dimension_config.get("keywords", []),
            "default_value": dimension_config.get("default_value", 50),
            "description": dimension_config.get("description", ""),
        }

    def get_strategy_summary(self, selected_dimensions: List[Dict[str, Any]], historical_count: int) -> Dict[str, Any]:
        """
        获取选择策略摘要（用于日志/监控）

        Args:
            selected_dimensions: 选中的维度列表
            historical_count: 历史数据量

        Returns:
            策略摘要字典
        """
        learning_weight, stage = self.get_learning_weight(historical_count)

        source_counts = {"rule_engine": 0, "learning_optimized": 0, "scene_injection": 0, "other": 0}

        for dim in selected_dimensions:
            source = dim.get("source", "other")
            if source in source_counts:
                source_counts[source] += 1
            else:
                source_counts["other"] += 1

        return {
            "total_dimensions": len(selected_dimensions),
            "source_breakdown": source_counts,
            "learning_enabled": self.learning_enabled,
            "historical_data_count": historical_count,
            "learning_weight": learning_weight,
            "learning_stage": stage,
            "optimization_applied": source_counts["learning_optimized"] > 0,
        }
