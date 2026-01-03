"""
维度反馈路由 - 收集用户对维度有用性的评分

提供API端点接收前端的维度评分数据，
用于学习系统的效果评估。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from intelligent_project_analyzer.services.dimension_usage_tracker import DimensionUsageTracker
from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dimensions", tags=["维度反馈"])


class DimensionFeedbackRequest(BaseModel):
    """维度反馈请求模型"""

    session_id: str = Field(..., description="会话ID")
    dimension_ratings: Dict[str, int] = Field(..., description="维度评分字典 {dimension_id: rating}")
    feedback_text: Optional[str] = Field(None, description="可选的文本反馈")
    completion_time: Optional[float] = Field(None, description="填写耗时（秒）")

    @validator("dimension_ratings")
    def validate_ratings(cls, v):
        """验证评分范围"""
        for dim_id, rating in v.items():
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                raise ValueError(f"维度 {dim_id} 的评分必须是 1-5 之间的整数")
        return v


class DimensionFeedbackResponse(BaseModel):
    """维度反馈响应模型"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    feedback_id: Optional[str] = Field(None, description="反馈记录ID")
    avg_rating: Optional[float] = Field(None, description="平均评分")


@router.post("/feedback", response_model=DimensionFeedbackResponse)
async def submit_dimension_feedback(request: DimensionFeedbackRequest) -> DimensionFeedbackResponse:
    """
    提交维度反馈

    接收用户对维度有用性的评分，保存到会话数据中。

    **评分标准**:
    - 5星: 非常有用，帮助我明确了关键需求
    - 4星: 有用，提供了有价值的思考角度
    - 3星: 一般，有一定参考价值
    - 2星: 用处不大，与我的需求关联不强
    - 1星: 无用，完全不相关

    **示例请求**:
    ```json
    {
        "session_id": "abc-123",
        "dimension_ratings": {
            "cultural_axis": 5,
            "tech_visibility": 4,
            "privacy_level": 2
        },
        "feedback_text": "文化维度很有用，但隐私维度对我的项目不太适用",
        "completion_time": 45.3
    }
    ```
    """
    try:
        # 验证会话是否存在
        redis_manager = RedisSessionManager()
        session = await redis_manager.get_session(request.session_id)

        if not session:
            # 尝试从归档中获取
            archive_manager = SessionArchiveManager()
            archived = await archive_manager.get_archived_session(request.session_id)
            if not archived:
                raise HTTPException(status_code=404, detail=f"会话 {request.session_id} 不存在")
            session = archived

        # 记录反馈
        tracker = DimensionUsageTracker()
        feedback_metadata = tracker.track_user_feedback(
            session_id=request.session_id,
            dimension_ratings=request.dimension_ratings,
            feedback_text=request.feedback_text,
            completion_time=request.completion_time,
        )

        # 更新会话数据
        session_data = session.get("session_data", {})
        if "dimension_usage_metadata" not in session_data:
            session_data["dimension_usage_metadata"] = {}

        session_data["dimension_usage_metadata"]["feedback"] = feedback_metadata

        # 保存到Redis（如果是活跃会话）
        try:
            await redis_manager.update_session(session_id=request.session_id, session_data=session_data)
        except Exception:
            # 如果Redis更新失败，可能是归档会话，更新归档记录
            await archive_manager.update_archived_session_data(session_id=request.session_id, session_data=session_data)

        logger.info(
            f"[DimensionFeedback] 反馈已保存 - 会话:{request.session_id}, " f"平均评分:{feedback_metadata['avg_rating']:.2f}"
        )

        return DimensionFeedbackResponse(
            success=True,
            message="反馈提交成功，感谢您的宝贵意见！",
            feedback_id=f"{request.session_id}_feedback",
            avg_rating=feedback_metadata["avg_rating"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DimensionFeedback] 提交失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")


@router.get("/feedback/{session_id}", response_model=Dict[str, Any])
async def get_dimension_feedback(session_id: str) -> Dict[str, Any]:
    """
    获取会话的维度反馈数据

    Args:
        session_id: 会话ID

    Returns:
        反馈数据字典
    """
    try:
        redis_manager = RedisSessionManager()
        session = await redis_manager.get_session(session_id)

        if not session:
            # 尝试从归档中获取
            archive_manager = SessionArchiveManager()
            archived = await archive_manager.get_archived_session(session_id)
            if not archived:
                raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
            session = archived

        session_data = session.get("session_data", {})
        feedback = session_data.get("dimension_usage_metadata", {}).get("feedback")

        if not feedback:
            return {"has_feedback": False, "message": "该会话暂无反馈数据"}

        return {"has_feedback": True, "feedback": feedback}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DimensionFeedback] 获取反馈失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取反馈失败: {str(e)}")
