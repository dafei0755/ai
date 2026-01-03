"""
维度效果评估器 - 学习模块

基于历史数据评估每个维度的效果，计算综合得分，
识别低效维度和缺失场景。
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DimensionEvaluator:
    """维度效果评估器"""

    def __init__(self):
        """初始化评估器"""
        self.logger = logging.getLogger(__name__)
        self._score_cache: Dict[str, float] = {}  # 维度得分缓存
        self._last_updated: Optional[str] = None

    def calculate_dimension_score(self, dimension_id: str, historical_data: List[Dict[str, Any]]) -> float:
        """
        计算单个维度的综合得分 (0-100)

        算法:
        score = w1 * usage_frequency    # 使用频率（归一化）
              + w2 * avg_user_rating    # 平均用户评分（1-5 → 0-100）
              + w3 * gap_follow_rate    # Gap 后续行动率
              + w4 * report_completion  # 报告完成率

        Args:
            dimension_id: 维度ID
            historical_data: 历史会话数据列表

        Returns:
            综合得分 (0-100)
        """
        if not historical_data:
            return 50.0  # 默认中性得分

        # 权重配置
        w1, w2, w3, w4 = 0.25, 0.35, 0.25, 0.15

        # 指标1: 使用频率（归一化到0-100）
        total_sessions = len(historical_data)
        usage_count = sum(
            1
            for session in historical_data
            if dimension_id in session.get("dimension_usage_metadata", {}).get("selection", {}).get("dimension_ids", [])
        )
        usage_frequency = (usage_count / total_sessions) * 100 if total_sessions > 0 else 0

        # 指标2: 平均用户评分（1-5 → 0-100）
        ratings = []
        for session in historical_data:
            feedback = session.get("dimension_usage_metadata", {}).get("feedback")
            if feedback and dimension_id in feedback.get("dimension_ratings", {}):
                rating = feedback["dimension_ratings"][dimension_id]
                ratings.append((rating - 1) * 25)  # 1→0, 2→25, 3→50, 4→75, 5→100
        avg_rating = sum(ratings) / len(ratings) if ratings else 50.0

        # 指标3: Gap 后续行动率
        gap_sessions = []
        for session in historical_data:
            gap_data = session.get("dimension_usage_metadata", {}).get("gap_analysis")
            if gap_data and dimension_id in gap_data.get("gap_dimension_ids", []):
                gap_sessions.append(gap_data.get("user_provided_followup", False))
        gap_follow_rate = (sum(gap_sessions) / len(gap_sessions)) * 100 if gap_sessions else 50.0

        # 指标4: 报告完成率
        completion_sessions = []
        for session in historical_data:
            if dimension_id in session.get("dimension_usage_metadata", {}).get("selection", {}).get(
                "dimension_ids", []
            ):
                completion_sessions.append(bool(session.get("final_report")))
        completion_rate = (sum(completion_sessions) / len(completion_sessions)) * 100 if completion_sessions else 50.0

        # 综合得分
        score = w1 * usage_frequency + w2 * avg_rating + w3 * gap_follow_rate + w4 * completion_rate

        self.logger.debug(
            f"[DimensionEval] 维度评分 - {dimension_id}: "
            f"总分={score:.1f}, 使用率={usage_frequency:.1f}, "
            f"评分={avg_rating:.1f}, Gap跟进={gap_follow_rate:.1f}, "
            f"完成率={completion_rate:.1f}"
        )

        return score

    def batch_calculate_scores(
        self, dimension_ids: List[str], historical_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        批量计算维度得分

        Args:
            dimension_ids: 维度ID列表
            historical_data: 历史会话数据列表

        Returns:
            维度得分字典 {dimension_id: score}
        """
        scores = {}
        for dim_id in dimension_ids:
            scores[dim_id] = self.calculate_dimension_score(dim_id, historical_data)

        self._score_cache = scores

        self.logger.info(f"[DimensionEval] 批量评分完成 - " f"维度数:{len(scores)}, 平均分:{sum(scores.values())/len(scores):.1f}")

        return scores

    def identify_redundant_dimensions(
        self, dimension_scores: Dict[str, float], threshold: float = 30.0
    ) -> List[Tuple[str, float]]:
        """
        识别冗余维度（低分、低使用）

        Args:
            dimension_scores: 维度得分字典
            threshold: 得分阈值，低于此值视为冗余

        Returns:
            冗余维度列表 [(dimension_id, score), ...]，按得分升序排列
        """
        redundant = [(dim_id, score) for dim_id, score in dimension_scores.items() if score < threshold]
        redundant.sort(key=lambda x: x[1])  # 按得分升序

        self.logger.info(f"[DimensionEval] 识别冗余维度 - " f"阈值:{threshold}, 数量:{len(redundant)}")

        return redundant

    def identify_high_value_dimensions(
        self, dimension_scores: Dict[str, float], threshold: float = 75.0
    ) -> List[Tuple[str, float]]:
        """
        识别高价值维度（高分、高效）

        Args:
            dimension_scores: 维度得分字典
            threshold: 得分阈值，高于此值视为高价值

        Returns:
            高价值维度列表 [(dimension_id, score), ...]，按得分降序排列
        """
        high_value = [(dim_id, score) for dim_id, score in dimension_scores.items() if score >= threshold]
        high_value.sort(key=lambda x: x[1], reverse=True)  # 按得分降序

        self.logger.info(f"[DimensionEval] 识别高价值维度 - " f"阈值:{threshold}, 数量:{len(high_value)}")

        return high_value

    def identify_missing_scenarios(
        self, historical_data: List[Dict[str, Any]], min_frequency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        识别缺失场景（高频但未覆盖的关键词模式）

        简化版：基于特殊场景标签统计
        完整版需要使用 sentence-transformers 聚类

        Args:
            historical_data: 历史会话数据列表
            min_frequency: 最小出现频率

        Returns:
            缺失场景列表 [{"keywords": [...], "frequency": n}, ...]
        """
        # 统计特殊场景标签频率
        scene_counter = defaultdict(int)
        for session in historical_data:
            scenes = session.get("dimension_usage_metadata", {}).get("selection", {}).get("special_scenes", [])
            for scene in scenes:
                scene_counter[scene] += 1

        # 筛选高频场景
        missing_scenarios = [
            {"scene_tag": scene, "frequency": count} for scene, count in scene_counter.items() if count >= min_frequency
        ]
        missing_scenarios.sort(key=lambda x: x["frequency"], reverse=True)

        self.logger.info(f"[DimensionEval] 识别缺失场景 - " f"高频场景数:{len(missing_scenarios)}, 最小频率:{min_frequency}")

        return missing_scenarios

    def get_dimension_statistics(self, dimension_id: str, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取维度的详细统计信息

        Args:
            dimension_id: 维度ID
            historical_data: 历史会话数据列表

        Returns:
            统计信息字典
        """
        stats = {
            "dimension_id": dimension_id,
            "total_usage": 0,
            "avg_rating": 0.0,
            "rating_count": 0,
            "gap_appearance": 0,
            "gap_follow_count": 0,
            "completion_count": 0,
            "useful_count": 0,  # 评分>=4
            "ineffective_count": 0,  # 评分<=2
        }

        for session in historical_data:
            metadata = session.get("dimension_usage_metadata", {})

            # 使用统计
            if dimension_id in metadata.get("selection", {}).get("dimension_ids", []):
                stats["total_usage"] += 1
                if session.get("final_report"):
                    stats["completion_count"] += 1

            # 评分统计
            feedback = metadata.get("feedback")
            if feedback and dimension_id in feedback.get("dimension_ratings", {}):
                rating = feedback["dimension_ratings"][dimension_id]
                stats["rating_count"] += 1
                stats["avg_rating"] += rating
                if rating >= 4:
                    stats["useful_count"] += 1
                elif rating <= 2:
                    stats["ineffective_count"] += 1

            # Gap统计
            gap_data = metadata.get("gap_analysis")
            if gap_data and dimension_id in gap_data.get("gap_dimension_ids", []):
                stats["gap_appearance"] += 1
                if gap_data.get("user_provided_followup"):
                    stats["gap_follow_count"] += 1

        if stats["rating_count"] > 0:
            stats["avg_rating"] /= stats["rating_count"]

        return stats
