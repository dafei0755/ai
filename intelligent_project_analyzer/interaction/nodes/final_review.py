"""最终审核节点"""

from typing import Dict, Any, Literal, Optional
from loguru import logger
from langgraph.types import interrupt, Command
from langgraph.store.base import BaseStore

from ...core.state import ProjectAnalysisState, AnalysisStage
from ...core.types import InteractionType


class FinalReviewNode:
    """最终审核节点"""

    @staticmethod
    def execute(
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None
    ) -> Command[Literal["pdf_generator", "result_aggregator"]]:
        """
        执行最终报告审核交互

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("Starting final review interaction")

        # 准备最终审核信息
        final_report = state.get("final_report", {})
        review_data = {
            "interaction_type": "final_review",
            "message": "请审核最终分析报告：",
            "report_summary": {
                "sections_completed": len(final_report.get("sections", {})),
                "total_pages": final_report.get("metadata", {}).get("estimated_pages", 0),
                "analysis_quality": final_report.get("metadata", {}).get("overall_confidence", 0),
                "key_recommendations": final_report.get("executive_summary", {}).get("key_recommendations", [])[:3]
            },
            "options": {
                "approve": "报告满意，生成PDF文档",
                "revise": "报告需要修改，重新生成",
                "preview": "先预览报告内容"
            }
        }

        # 使用interrupt暂停执行，等待用户审核
        user_response = interrupt(review_data)
        logger.info(f"Received user response for final review: {user_response}")

        # 更新状态
        updated_state = {
            "current_stage": AnalysisStage.FINAL_REVIEW.value,
            "interaction_history": state.get("interaction_history", []) + [{
                "type": InteractionType.FINAL_REVIEW.value,
                "data": review_data,
                "response": user_response,
                "timestamp": "2024-01-01T00:00:00Z"
            }]
        }

        # 根据用户响应决定下一步
        if isinstance(user_response, str):
            action = user_response
        elif isinstance(user_response, dict):
            action = user_response.get("action", "approve")
        else:
            action = "approve"

        if action == "approve":
            logger.info("Final report approved, generating PDF")
            updated_state["final_approved"] = True
            return Command(update=updated_state, goto="pdf_generator")
        else:
            logger.info("Final report needs revision")
            updated_state["final_approved"] = False
            if isinstance(user_response, dict) and user_response.get("feedback"):
                updated_state["user_feedback"] = user_response["feedback"]
            return Command(update=updated_state, goto="result_aggregator")
