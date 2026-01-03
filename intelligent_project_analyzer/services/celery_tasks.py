# -*- coding: utf-8 -*-
"""
Celery 异步任务定义

支持多用户并发分析的任务队列
"""

import asyncio
import io
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from celery import current_task, shared_task
from celery.exceptions import SoftTimeLimitExceeded
from loguru import logger

# 设置编码
if sys.platform == "win32":
    # Avoid swapping stdio streams at import time; it can break pytest/logging.
    for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# 导入 Celery 应用
from intelligent_project_analyzer.services.celery_app import celery_app


def run_async(coro):
    """在同步环境中运行异步代码"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已有事件循环运行，创建新的
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # 没有事件循环，创建新的
        return asyncio.run(coro)


@celery_app.task(bind=True, name="analyze_project")
def analyze_project(self, session_id: str, user_input: str, user_id: str = "celery_user") -> Dict[str, Any]:
    """
    异步分析项目任务

    Args:
        session_id: 会话ID
        user_input: 用户输入
        user_id: 用户ID

    Returns:
        分析结果
    """
    logger.info(f"🚀 [Celery] 开始分析任务: {session_id}")

    try:
        # 更新任务状态
        self.update_state(
            state="PROGRESS",
            meta={"session_id": session_id, "progress": 0.05, "current_stage": "初始化", "message": "正在启动分析流程..."},
        )

        # 执行异步分析
        result = run_async(_run_workflow(self, session_id, user_input, user_id))

        logger.info(f"✅ [Celery] 分析任务完成: {session_id}")
        return result

    except SoftTimeLimitExceeded:
        logger.warning(f"⏰ [Celery] 任务超时: {session_id}")
        return {"session_id": session_id, "status": "timeout", "error": "分析任务超时，请尝试简化输入"}
    except Exception as e:
        logger.error(f"❌ [Celery] 任务失败: {session_id}, 错误: {str(e)}")
        import traceback

        return {"session_id": session_id, "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


async def _run_workflow(task, session_id: str, user_input: str, user_id: str) -> Dict[str, Any]:
    """
    执行工作流的异步内部函数
    """
    from intelligent_project_analyzer.core.state import StateManager
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager
    from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

    # 初始化 Redis 会话管理器
    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        # 更新会话状态
        await session_manager.update(
            session_id, {"status": "running", "progress": 0.1, "task_id": task.request.id}  # 保存 Celery 任务ID
        )

        # 创建工作流
        workflow = MainWorkflow()
        workflow.build()

        task.update_state(
            state="PROGRESS",
            meta={"session_id": session_id, "progress": 0.15, "current_stage": "工作流初始化", "message": "正在创建分析工作流..."},
        )

        # 创建初始状态
        initial_state = StateManager.create_initial_state(user_input=user_input, session_id=session_id, user_id=user_id)

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}

        # 🎯 v7.21: 节点进度映射（与 main_workflow.py 实际节点名称对齐）
        node_progress_map = {
            # 输入验证阶段 (0-15%)
            "unified_input_validator_initial": 0.05,
            "unified_input_validator_secondary": 0.10,
            # 需求分析阶段 (15-35%)
            "requirements_analyst": 0.15,
            "feasibility_analyst": 0.20,
            "calibration_questionnaire": 0.25,
            "requirements_confirmation": 0.35,
            # 项目规划阶段 (35-55%)
            "project_director": 0.40,
            "role_task_unified_review": 0.45,
            "quality_preflight": 0.50,
            # 专家执行阶段 (55-80%)
            "batch_executor": 0.55,
            "agent_executor": 0.70,
            "batch_aggregator": 0.75,
            "batch_router": 0.76,
            "batch_strategy_review": 0.78,
            # 审核聚合阶段 (80-100%)
            "detect_challenges": 0.80,
            "analysis_review": 0.85,
            "result_aggregator": 0.90,
            "report_guard": 0.95,
            "pdf_generator": 0.98,
        }

        # 流式执行工作流
        events = []
        final_state = None

        async for chunk in workflow.graph.astream(initial_state, config):
            events.append(chunk)

            # 更新进度
            for node_name, node_output in chunk.items():
                if node_name == "__interrupt__":
                    # 处理中断（需要用户输入）
                    interrupt_data = chunk["__interrupt__"]
                    await session_manager.update(
                        session_id,
                        {
                            "status": "waiting_for_input",
                            "interrupt_data": _serialize_interrupt(interrupt_data),
                            "current_node": "interrupt",
                        },
                    )

                    task.update_state(
                        state="WAITING",
                        meta={
                            "session_id": session_id,
                            "progress": node_progress_map.get(node_name, 0.5),
                            "current_stage": "等待用户输入",
                            "message": "需要您的确认才能继续",
                            "interrupt_data": _serialize_interrupt(interrupt_data),
                        },
                    )

                    # 返回等待状态，让 API 处理恢复逻辑
                    return {
                        "session_id": session_id,
                        "status": "waiting_for_input",
                        "interrupt_data": _serialize_interrupt(interrupt_data),
                    }

                # 更新进度
                new_progress = node_progress_map.get(node_name, 0.5)
                detail = ""
                if isinstance(node_output, dict):
                    detail = node_output.get("detail", node_output.get("current_stage", ""))

                # 🔥 防止进度回退：获取当前进度并取最大值
                current_data = await session_manager.get(session_id)
                old_progress = current_data.get("progress", 0) if current_data else 0
                progress = max(new_progress, old_progress if isinstance(old_progress, (int, float)) else 0)

                await session_manager.update(
                    session_id, {"progress": progress, "current_node": node_name, "detail": detail}
                )

                task.update_state(
                    state="PROGRESS",
                    meta={
                        "session_id": session_id,
                        "progress": progress,
                        "current_stage": node_name,
                        "detail": detail,
                        "message": f"正在执行: {node_name}",
                    },
                )

                final_state = node_output

        # 提取最终报告
        final_report = None
        if final_state and isinstance(final_state, dict):
            final_report = final_state.get("final_report") or final_state.get("report_text")

        # 更新完成状态
        await session_manager.update(
            session_id,
            {
                "status": "completed",
                "progress": 1.0,
                "events": events,
                "final_report": final_report,
                "completed_at": datetime.now().isoformat(),
            },
        )

        return {"session_id": session_id, "status": "completed", "progress": 1.0, "final_report": final_report}

    finally:
        await session_manager.disconnect()


def _serialize_interrupt(interrupt_data) -> Dict[str, Any]:
    """序列化中断数据"""
    if interrupt_data is None:
        return {}

    if isinstance(interrupt_data, tuple) and len(interrupt_data) > 0:
        interrupt_obj = interrupt_data[0]
        if hasattr(interrupt_obj, "value"):
            return {"value": interrupt_obj.value}

    return {"raw": str(interrupt_data)}


@celery_app.task(bind=True, name="resume_analysis")
def resume_analysis(self, session_id: str, resume_value: Any) -> Dict[str, Any]:
    """
    恢复分析任务（处理用户输入后继续）

    Args:
        session_id: 会话ID
        resume_value: 用户提交的值

    Returns:
        分析结果
    """
    logger.info(f"🔄 [Celery] 恢复分析任务: {session_id}")

    try:
        result = run_async(_resume_workflow(self, session_id, resume_value))
        return result
    except Exception as e:
        logger.error(f"❌ [Celery] 恢复任务失败: {session_id}, 错误: {str(e)}")
        import traceback

        return {"session_id": session_id, "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


async def _resume_workflow(task, session_id: str, resume_value: Any) -> Dict[str, Any]:
    """
    恢复工作流的异步内部函数
    """
    from langgraph.types import Command

    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        # 获取会话数据
        session = await session_manager.get(session_id)
        if not session:
            return {"session_id": session_id, "status": "failed", "error": "会话不存在"}

        # 获取工作流实例（需要从全局或重建）
        # 这里简化处理，实际可能需要更复杂的状态恢复
        from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

        workflow = MainWorkflow()
        workflow.build()

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}

        # 使用 Command 恢复执行
        resume_command = Command(resume=resume_value)

        # 继续执行
        # 注意：实际实现可能需要检查点机制来完整恢复状态
        # 这里是简化版本

        await session_manager.update(session_id, {"status": "running", "interrupt_data": None})

        task.update_state(
            state="PROGRESS",
            meta={"session_id": session_id, "progress": 0.5, "current_stage": "恢复执行", "message": "正在恢复分析流程..."},
        )

        # TODO: 实现完整的检查点恢复逻辑
        # 这需要 LangGraph 的持久化功能支持

        return {"session_id": session_id, "status": "resumed", "message": "任务已恢复"}

    finally:
        await session_manager.disconnect()


@celery_app.task(name="cleanup_expired_sessions")
def cleanup_expired_sessions() -> Dict[str, Any]:
    """
    清理过期会话（定期任务）
    """
    logger.info("🧹 [Celery] 开始清理过期会话")

    try:
        result = run_async(_cleanup_sessions())
        logger.info(f"✅ [Celery] 清理完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ [Celery] 清理失败: {str(e)}")
        return {"status": "failed", "error": str(e)}


async def _cleanup_sessions() -> Dict[str, Any]:
    """清理过期会话的异步实现"""
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        # Redis TTL 会自动清理，这里可以做额外清理逻辑
        # 比如清理孤立的工作流实例等
        return {"status": "success", "message": "Redis TTL 自动管理会话过期"}
    finally:
        await session_manager.disconnect()


# ==================== 任务状态查询工具函数 ====================


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取 Celery 任务状态

    Args:
        task_id: Celery 任务ID

    Returns:
        任务状态信息
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
    }

    # 添加进度信息
    if result.status == "PROGRESS" or result.status == "WAITING":
        response["meta"] = result.info
    elif result.ready():
        response["result"] = result.result

    return response


def get_queue_length(queue_name: str = "analysis") -> int:
    """
    获取队列中等待的任务数量

    Args:
        queue_name: 队列名称

    Returns:
        队列长度
    """
    from intelligent_project_analyzer.services.celery_app import celery_app

    with celery_app.pool.acquire(block=True) as conn:
        return conn.default_channel.client.llen(queue_name)
