"""
维度使用追踪器 - 数据收集模块

用于记录维度选择、用户反馈、Gap分析效果等数据，
为后续的学习优化提供数据基础。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DimensionUsageTracker:
    """维度使用数据追踪器"""

    def __init__(self):
        """初始化追踪器"""
        self.logger = logging.getLogger(__name__)

    def track_selection(
        self,
        session_id: str,
        dimensions: List[Dict[str, Any]],
        selection_strategy: Dict[str, int],
        user_input: str,
        project_type: str,
        special_scenes: List[str] = None,
    ) -> Dict[str, Any]:
        """
        记录维度选择过程

        Args:
            session_id: 会话ID
            dimensions: 选中的维度列表
            selection_strategy: 选择策略统计 {"required": 3, "recommended": 5, "keyword": 2, "scene": 1}
            user_input: 用户输入
            project_type: 项目类型
            special_scenes: 特殊场景标签列表

        Returns:
            追踪元数据字典
        """
        metadata = {
            "tracked_at": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "dimension_ids": [d.get("id") for d in dimensions],
            "dimension_count": len(dimensions),
            "selection_strategy": selection_strategy,
            "project_type": project_type,
            "special_scenes": special_scenes or [],
            "user_input_length": len(user_input),
            "dimension_sources": {},
        }

        # 记录每个维度的来源
        for dim in dimensions:
            dim_id = dim.get("id")
            source = dim.get("source", "unknown")
            metadata["dimension_sources"][dim_id] = source

        self.logger.info(
            f"[DimensionTracker] 记录维度选择 - 会话:{session_id}, " f"维度数:{len(dimensions)}, 策略:{selection_strategy}"
        )

        return metadata

    def track_user_feedback(
        self,
        session_id: str,
        dimension_ratings: Dict[str, int],
        feedback_text: Optional[str] = None,
        completion_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        记录用户反馈

        Args:
            session_id: 会话ID
            dimension_ratings: 维度评分字典 {dimension_id: rating (1-5)}
            feedback_text: 可选的文本反馈
            completion_time: 填写耗时（秒）

        Returns:
            反馈元数据字典
        """
        feedback_metadata = {
            "tracked_at": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "dimension_ratings": dimension_ratings,
            "avg_rating": sum(dimension_ratings.values()) / len(dimension_ratings) if dimension_ratings else 0,
            "rating_count": len(dimension_ratings),
            "feedback_text": feedback_text,
            "completion_time_seconds": completion_time,
            "useful_dimensions": [dim_id for dim_id, rating in dimension_ratings.items() if rating >= 4],
            "ineffective_dimensions": [dim_id for dim_id, rating in dimension_ratings.items() if rating <= 2],
        }

        self.logger.info(
            f"[DimensionTracker] 记录用户反馈 - 会话:{session_id}, "
            f"平均评分:{feedback_metadata['avg_rating']:.2f}, "
            f"有用维度:{len(feedback_metadata['useful_dimensions'])}, "
            f"低效维度:{len(feedback_metadata['ineffective_dimensions'])}"
        )

        return feedback_metadata

    def track_gap_analysis(
        self,
        session_id: str,
        gap_dimensions: List[str],
        extreme_dimensions: List[str],
        user_provided_followup: bool,
        followup_quality_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        记录Gap分析效果

        Args:
            session_id: 会话ID
            gap_dimensions: 识别出的短板维度ID列表
            extreme_dimensions: 极端值维度ID列表
            user_provided_followup: 用户是否提供了后续信息
            followup_quality_score: 后续信息质量评分 (0-1)

        Returns:
            Gap分析元数据字典
        """
        gap_metadata = {
            "tracked_at": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "gap_dimension_ids": gap_dimensions,
            "extreme_dimension_ids": extreme_dimensions,
            "gap_count": len(gap_dimensions),
            "extreme_count": len(extreme_dimensions),
            "user_provided_followup": user_provided_followup,
            "followup_quality_score": followup_quality_score,
            "gap_effective": user_provided_followup and (followup_quality_score or 0) > 0.5,
        }

        self.logger.info(
            f"[DimensionTracker] 记录Gap分析 - 会话:{session_id}, "
            f"短板维度:{len(gap_dimensions)}, 极端维度:{len(extreme_dimensions)}, "
            f"用户跟进:{user_provided_followup}, 有效:{gap_metadata['gap_effective']}"
        )

        return gap_metadata

    def build_session_metadata(
        self,
        selection_metadata: Dict[str, Any],
        feedback_metadata: Optional[Dict[str, Any]] = None,
        gap_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        构建完整的会话维度元数据

        Args:
            selection_metadata: 维度选择元数据
            feedback_metadata: 用户反馈元数据（可选）
            gap_metadata: Gap分析元数据（可选）

        Returns:
            完整的元数据字典，用于保存到 session_data
        """
        complete_metadata = {
            "dimension_usage_metadata": {
                "selection": selection_metadata,
                "feedback": feedback_metadata,
                "gap_analysis": gap_metadata,
                "has_feedback": feedback_metadata is not None,
                "has_gap_analysis": gap_metadata is not None,
                "metadata_version": "1.0.0",
            }
        }

        self.logger.debug(
            f"[DimensionTracker] 构建完整元数据 - "
            f"会话:{selection_metadata.get('session_id')}, "
            f"包含反馈:{feedback_metadata is not None}, "
            f"包含Gap:{gap_metadata is not None}"
        )

        return complete_metadata

    def calculate_completion_score(self, session_data: Dict[str, Any]) -> float:
        """
        计算会话完成质量得分 (0-1)

        用于评估用户是否完整完成了整个流程

        Args:
            session_data: 完整的会话数据

        Returns:
            完成质量得分
        """
        score = 0.0

        # 基础分 (0.3): 完成了维度选择
        if "selected_radar_dimensions" in session_data:
            score += 0.3

        # 反馈分 (0.3): 提供了用户评分
        metadata = session_data.get("dimension_usage_metadata", {})
        if metadata.get("feedback"):
            feedback = metadata["feedback"]
            if feedback.get("rating_count", 0) > 0:
                score += 0.3

        # 完成分 (0.4): 生成了最终报告
        if session_data.get("final_report"):
            score += 0.4

        return min(score, 1.0)
