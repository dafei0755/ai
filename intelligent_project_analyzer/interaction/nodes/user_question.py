"""用户追问节点"""

import json
from typing import Dict, Any, Literal, Optional
from loguru import logger
from langgraph.types import interrupt, Command
from langgraph.store.base import BaseStore

from ...core.state import ProjectAnalysisState
from ...core.types import InteractionType


class UserQuestionNode:
    """用户追问节点"""

    @staticmethod
    def execute(
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None
    ) -> Command[Literal["project_director", "result_aggregator"]]:
        """
        处理用户追问交互

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("Starting user question interaction")

        # 准备追问信息
        question_data = {
            "interaction_type": "user_question",
            "message": "您有什么问题需要进一步分析？",
            "current_analysis": {
                "completed_sections": list(state.get("agent_results", {}).keys()),
                "available_topics": [
                    "设计研究", "技术架构", "用户体验",
                    "商业模式", "实施规划", "其他"
                ]
            },
            "input_type": "text",
            "placeholder": "请输入您的问题或需要深入分析的方面..."
        }

        # 使用interrupt暂停执行，等待用户输入
        user_question = interrupt(question_data)
        logger.info(f"Received user question: {user_question}")

        # 更新状态
        updated_state = {
            "interaction_history": state.get("interaction_history", []) + [{
                "type": InteractionType.QUESTION.value,
                "data": question_data,
                "response": user_question,
                "timestamp": "2024-01-01T00:00:00Z"
            }],
            "post_completion_followup_completed": state.get("post_completion_followup_completed", False)
        }

        # 处理用户问题
        if user_question:
            # 兼容前端传入的 JSON 字符串
            if isinstance(user_question, str):
                stripped = user_question.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        parsed = json.loads(stripped)
                        if isinstance(parsed, dict):
                            user_question = parsed
                        else:
                            user_question = stripped
                    except json.JSONDecodeError:
                        user_question = stripped
                else:
                    user_question = stripped

            question_text = None
            requires_analysis = True

            if isinstance(user_question, str):
                if user_question.lower() == "skip":
                    question_text = None
                    requires_analysis = False
                else:
                    question_text = user_question
            elif isinstance(user_question, dict):
                if user_question.get("skip"):
                    question_text = None
                    requires_analysis = False
                else:
                    raw_question = user_question.get("question") or ""
                    question_text = raw_question.strip()
                    requires_analysis = user_question.get("requires_analysis", True)

            if question_text:
                logger.info(f"User asked: {question_text}")
                updated_state["additional_questions"] = state.get("additional_questions", []) + [question_text]

                if requires_analysis:
                    updated_state["post_completion_followup_completed"] = False
                    return Command(update=updated_state, goto="project_director")
                else:
                    updated_state["post_completion_followup_completed"] = True
                    return Command(update=updated_state, goto="result_aggregator")

        # 没有问题，继续流程
        logger.info("No additional questions, proceeding")
        updated_state["post_completion_followup_completed"] = True
        return Command(update=updated_state, goto="result_aggregator")
