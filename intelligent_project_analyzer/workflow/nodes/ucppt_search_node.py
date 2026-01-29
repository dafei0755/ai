"""
ucppt 搜索节点 (v7.180)

将 ucppt 深度迭代搜索集成到 LangGraph 工作流中。

特点：

用法：
    在 main_workflow.py 中添加节点：
    workflow.add_node("ucppt_search", ucppt_search_node)
"""

import asyncio
from typing import Any, Dict, Optional

from loguru import logger

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine, get_ucppt_engine


async def ucppt_search_node(state: ProjectAnalysisState) -> Dict[str, Any]:
    """
    ucppt 深度搜索节点

    执行30轮动态迭代搜索，构建知识框架，
    返回丰富的搜索结果供后续节点使用。

    Args:
        state: 当前工作流状态

    Returns:
        更新后的状态字典
    """
    logger.info("🧠 [Ucppt Node] 开始深度搜索...")

    # 提取搜索查询
    user_input = state.user_input or ""

    # 从问卷数据中提取额外上下文
    context = {}
    if state.questionnaire_data:
        context["questionnaire"] = state.questionnaire_data
    if state.requirements_understanding:
        context["requirements"] = state.requirements_understanding

    # 获取引擎
    engine = get_ucppt_engine()

    # 执行搜索
    all_sources = []
    final_confidence = 0.0
    knowledge_framework = None
    rounds_completed = 0

    try:
        async for event in engine.search_deep(
            query=user_input,
            context=context,
            max_rounds=30,
        ):
            event_type = event.get("type", "")
            data = event.get("data", {})

            if event_type == "framework":
                knowledge_framework = {
                    "core_concepts": data.get("core_concepts", []),
                    "dimensions": data.get("dimensions", []),
                    "initial_gaps": data.get("initial_gaps", []),
                }

            elif event_type == "round_sources":
                sources = data.get("sources", [])
                all_sources.extend(sources)

            elif event_type == "round_complete":
                final_confidence = data.get("confidence", 0)
                rounds_completed = data.get("round", 0)

            elif event_type == "done":
                final_confidence = data.get("final_confidence", 0)
                rounds_completed = data.get("total_rounds", 0)
                break

            elif event_type == "error":
                logger.error(f"❌ [Ucppt Node] 搜索错误: {data.get('message')}")
                break

    except Exception as e:
        logger.error(f"❌ [Ucppt Node] 执行失败: {e}", exc_info=True)

    logger.info(
        f"✅ [Ucppt Node] 搜索完成 | "
        f"rounds={rounds_completed} | sources={len(all_sources)} | confidence={final_confidence:.2f}"
    )

    # 返回更新状态
    return {
        "ucppt_search_results": {
            "sources": all_sources,
            "confidence": final_confidence,
            "rounds_completed": rounds_completed,
            "knowledge_framework": knowledge_framework,
        },
        "search_data": {
            "all_sources": all_sources,
            "ucppt_enabled": True,
        },
    }


def create_ucppt_search_node(
    max_rounds: int = 30,
    confidence_threshold: float = 0.8,
):
    """
    创建配置化的 ucppt 搜索节点

    Args:
        max_rounds: 最大搜索轮数
        confidence_threshold: 信息充分度阈值

    Returns:
        配置好的节点函数
    """

    async def configured_node(state: ProjectAnalysisState) -> Dict[str, Any]:
        logger.info(f"🧠 [Ucppt Node] 配置: max_rounds={max_rounds}, threshold={confidence_threshold}")

        user_input = state.user_input or ""
        engine = UcpptSearchEngine(
            max_rounds=max_rounds,
            confidence_threshold=confidence_threshold,
        )

        all_sources = []
        final_confidence = 0.0
        knowledge_framework = None
        rounds_completed = 0

        try:
            async for event in engine.search_deep(query=user_input):
                event_type = event.get("type", "")
                data = event.get("data", {})

                if event_type == "framework":
                    knowledge_framework = data
                elif event_type == "round_sources":
                    all_sources.extend(data.get("sources", []))
                elif event_type == "done":
                    final_confidence = data.get("final_confidence", 0)
                    rounds_completed = data.get("total_rounds", 0)
                    break
        except Exception as e:
            logger.error(f"❌ [Ucppt Node] 失败: {e}")

        return {
            "ucppt_search_results": {
                "sources": all_sources,
                "confidence": final_confidence,
                "rounds_completed": rounds_completed,
                "knowledge_framework": knowledge_framework,
            },
        }

    return configured_node
