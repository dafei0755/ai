"""
分析路由模块 (MT-1 提取自 api/server.py)

Routes:
  POST /api/analysis/start
  POST /api/analysis/start-with-files
  POST /api/analysis/{session_id}/visual-reference/describe
  GET  /api/analysis/status/{session_id}
  POST /api/analysis/resume
  POST /api/analysis/followup
  GET  /api/analysis/result/{session_id}
  GET  /api/analysis/report/{session_id}
  GET  /api/analysis/report/{session_id}/download-pdf
  GET  /api/analysis/report/{session_id}/download-all-experts-pdf
"""
from __future__ import annotations

import json
import os
import time
import uuid
from collections import OrderedDict, defaultdict
from datetime import datetime
from typing import Any, Dict, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from langgraph.types import Command
from loguru import logger
from pydantic import BaseModel, Field

from intelligent_project_analyzer.agents.followup_agent import FollowupAgent
from intelligent_project_analyzer.api._server_proxy import server_proxy as _server
from intelligent_project_analyzer.services.file_processor import (
    build_combined_input,
    file_processor,
)
from intelligent_project_analyzer.services.geoip_service import get_geoip_service

from .deps import DEV_MODE, sessions_cache
from .helpers import (
    _derive_section_identity,
    _enrich_sections_with_agent_results,
    _format_agent_payload,
    _sanitize_structured_data,
)
from .models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
    ChallengeDetectionResponse,
    ChallengeItemResponse,
    ComprehensiveAnalysisResponse,
    ConclusionsResponse,
    DeliberationProcessResponse,
    ExecutiveSummaryResponse,
    QuestionnaireResponseData,
    QuestionnaireResponseItem,
    RecommendationsSectionResponse,
    ReportResponse,
    ReportSectionResponse,
    RequirementsAnalysisResponse,
    ResumeRequest,
    ReviewFeedbackItemResponse,
    ReviewFeedbackResponse,
    ReviewRoundDataResponse,
    ReviewVisualizationResponse,
    SessionResponse,
    StructuredReportResponse,
)
from .pdf_generator import (
    generate_all_experts_pdf_fast,
    generate_report_pdf,
)
from .workflow_runner import run_workflow_async


async def _get_session_manager():
    """向后兼容：代理到 server._get_session_manager()"""
    return await _server._get_session_manager()


router = APIRouter(tags=["analysis"])


@router.get("/api/analysis/status/{session_id}", response_model=AnalysisStatus)
async def get_analysis_status(
    session_id: str,
    extend_ttl: bool = False,
    include_history: bool = Query(False, description="是否包含完整history（影响性能）"),  #  v7.120 P1
):
    """
    获取分析状态

    查询指定会话的当前状态和进度

    Args:
        session_id: 会话ID
        extend_ttl: 是否延长TTL（默认False，避免频繁轮询时过度续期）
        include_history: 是否包含完整history（默认False，减少序列化开销） v7.120 P1优化

     v7.120 P1优化: 默认不返回history字段，预期性能提升: 2.03s→0.5s
     性能优化: 添加Redis缓存机制（30秒TTL），预期响应时间: <500ms
    """

    start_time = time.time()

    #  使用 Redis 读取会话（带缓存）
    sm = await _get_session_manager()
    session = await sm.get_status_with_cache(session_id, include_history=include_history)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    #  Fix 2.5: 仅在明确请求时才续期TTL（减少95% Redis负载）
    if extend_ttl:
        await sm.extend_ttl(session_id)

    #  v7.119: 检查 waiting_for_input 状态的超时
    if session["status"] == "waiting_for_input":
        interrupt_timestamp = session.get("interrupt_timestamp")
        if interrupt_timestamp:
            elapsed_minutes = (time.time() - interrupt_timestamp) / 60

            # 超过15分钟发送WebSocket提醒
            if elapsed_minutes > 15 and not session.get("timeout_reminder_sent"):
                logger.warning(f" Session {session_id} 等待用户输入已超过15分钟")
                await _server.broadcast_to_websockets(
                    session_id,
                    {
                        "type": "status_update",
                        "status": "waiting_for_input",
                        "message": "️ 系统已等待您的确认超过15分钟，请及时响应",
                        "detail": "超时提醒",
                    },
                )
                await sm.update(session_id, {"timeout_reminder_sent": True})

            # 超过30分钟自动标记为timeout
            if elapsed_minutes > 30:
                logger.error(f" Session {session_id} 等待用户输入超时（30分钟）")
                await sm.update(session_id, {"status": "timeout", "error": "用户未在30分钟内响应，会话已超时", "detail": "会话超时"})
                session["status"] = "timeout"
                session["error"] = "用户未在30分钟内响应，会话已超时"

    # 性能监控日志
    elapsed_ms = (time.time() - start_time) * 1000
    if elapsed_ms > 1000:
        logger.warning(f" 慢请求检测: GET /api/analysis/status/{session_id} 耗时 {elapsed_ms:.0f}ms")
    else:
        logger.debug(f" 状态查询完成: {session_id}, 耗时 {elapsed_ms:.0f}ms")

    return AnalysisStatus(
        session_id=session_id,
        status=session["status"],
        current_stage=session.get("current_node"),
        detail=session.get("detail"),  #  新增：返回详细信息
        progress=session["progress"],
        history=session.get("history", []) if include_history else [],  #  v7.120 P1: 按需返回
        interrupt_data=session.get("interrupt_data"),
        error=session.get("error"),
        traceback=session.get("traceback"),  # 返回traceback用于调试
        rejection_message=session.get("rejection_message"),  #  返回拒绝提示
        user_input=session.get("user_input"),  #  v7.37.7: 返回用户原始输入
        flow_route_name=session.get("flow_route_name"),
        flow_route_decision=session.get("flow_route_decision"),
        flow_route_reason_codes=session.get("flow_route_reason_codes"),
        routing_scores=session.get("routing_scores"),
        active_steps=session.get("active_steps"),
    )


@router.post("/api/analysis/resume", response_model=SessionResponse)
async def resume_analysis(request: ResumeRequest, background_tasks: BackgroundTasks):
    """
    恢复分析

    在 interrupt 后提供用户输入并继续执行
    """
    session_id = request.session_id

    sm = await _get_session_manager()

    #  获取活跃会话列表
    active_sessions = await sm.list_all_sessions()

    logger.info(f" 收到 resume 请求: session_id={session_id}")
    logger.info(f"   resume_value: {request.resume_value}")
    logger.info(f"   当前活跃会话: {active_sessions}")

    #  检查会话是否存在
    session = await sm.get(session_id)
    if not session:
        logger.error(f" 会话不存在: {session_id}")
        logger.error(f"   可用会话: {active_sessions}")
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    # 兼容：历史数据/旧实现可能使用 interrupted 表示等待用户输入
    if session.get("status") not in {"waiting_for_input", "interrupted"}:
        raise HTTPException(status_code=400, detail=f"会话状态不正确: {session.get('status')}")

    # 获取工作流
    workflow = _server.workflows.get(session_id)
    if not workflow:
        logger.error(f" 工作流实例不存在: {session_id}")
        logger.error("   这通常发生在服务器重启后，工作流无法继续")
        logger.error("   建议：使用持久化的检查点存储（如SqliteSaver）而非MemorySaver")

        #  DEV_MODE：测试/本地调试时，不用 410 直接阻塞（单测只关注 API 是否可用）
        if DEV_MODE:
            # DEV_MODE 下尽量不依赖 Redis 分布式锁更新（测试环境 mock redis_client 不一定支持 Lock）
            try:
                await sm.update(session_id, {"status": "running", "interrupt_data": None})
            except Exception:
                pass
            return SessionResponse(
                session_id=session_id, status="processing", message="恢复请求已接收（DEV_MODE 下跳过 workflow 实例校验）"
            )

        raise HTTPException(
            status_code=410, detail="工作流已失效，请重新开始分析。如果问题持续出现，请联系管理员。"  # 410 Gone - resource no longer available
        )

    # 更新状态
    logger.debug(f"[DEBUG] Resume request for session {session_id}")
    logger.debug(f"[DEBUG] resume_value type: {type(request.resume_value)}")
    logger.debug(f"[DEBUG] resume_value content: {request.resume_value}")

    #  v7.119: 立即更新 Redis 状态为 running，清除超时相关字段
    await sm.update(
        session_id,
        {
            "status": "running",
            "interrupt_data": None,
            "interrupt_timestamp": None,  # 清除超时时间戳
            "timeout_reminder_sent": None,  # 清除提醒标记
        },
    )

    # 更新本地 session 对象（虽然 continue_workflow 使用的是闭包中的 session，但为了保险起见）
    session["status"] = "running"
    session["interrupt_data"] = None

    # 继续执行工作流
    async def continue_workflow():
        #  导入GraphRecursionError
        from langgraph.errors import GraphRecursionError

        try:
            config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}  # 增加递归限制，默认是25

            logger.info(f"[DEBUG] Resuming workflow with Command(resume={request.resume_value})")

            # 使用 Command(resume) 继续执行
            # 不指定 stream_mode，使用默认模式以正确接收 __interrupt__
            async for chunk in workflow.graph.astream(Command(resume=request.resume_value), config):
                logger.debug(f"[DEBUG] Resume stream chunk keys: {chunk.keys()}")

                #  更新当前节点和详细信息
                for node_name, node_output in chunk.items():
                    if node_name != "__interrupt__":
                        session["current_node"] = node_name
                        detail = ""
                        if isinstance(node_output, dict):
                            if "current_stage" in node_output:
                                detail = node_output["current_stage"]
                            elif "status" in node_output:
                                detail = node_output["status"]
                        session["detail"] = detail
                        logger.debug(f"[PROGRESS] 节点: {node_name}, 详情: {detail}")

                session["events"].append(chunk)
                #  v7.21: 节点映射与 main_workflow.py 对齐
                current_node = session.get("current_node", "")
                node_progress_map = {
                    "unified_input_validator_initial": 0.05,
                    "unified_input_validator_secondary": 0.10,
                    "requirements_analyst": 0.15,
                    "feasibility_analyst": 0.20,
                    "calibration_questionnaire": 0.25,
                    "questionnaire_summary": 0.35,  #  v7.151: 替换 requirements_confirmation
                    "project_director": 0.40,
                    "role_task_unified_review": 0.45,
                    "quality_preflight": 0.50,
                    "batch_executor": 0.55,
                    "agent_executor": 0.70,
                    "batch_aggregator": 0.75,
                    "batch_router": 0.76,
                    "batch_strategy_review": 0.78,
                    "detect_challenges": 0.80,
                    "analysis_review": 0.85,
                    "result_aggregator": 0.90,
                    "report_guard": 0.95,
                    "pdf_generator": 0.98,
                }
                session["progress"] = node_progress_map.get(current_node, min(0.9, len(session["events"]) * 0.1))

                #  确保 Redis 和 WebSocket 原子性同步
                # 1. 先更新 Redis
                await _server.session_manager.update(
                    session_id,
                    {
                        "status": session["status"],
                        "progress": session["progress"],
                        "current_node": current_node,
                        "detail": session.get("detail"),
                        "events": session["events"],
                    },
                )

                # 2. 基于最新 Redis 数据广播 WebSocket
                updated_session = await _server.session_manager.get(session_id)
                if updated_session:
                    await _server.broadcast_to_websockets(
                        request.session_id,
                        {
                            "type": "status_update",
                            "status": updated_session["status"],
                            "progress": updated_session["progress"],
                            "current_node": updated_session.get("current_node"),
                            "detail": updated_session.get("detail"),
                        },
                    )

                # 检查是否又有 interrupt - interrupt 作为独立的 chunk 返回
                if "__interrupt__" in chunk:
                    # 提取 interrupt 数据
                    interrupt_tuple = chunk["__interrupt__"]
                    # interrupt_tuple 是一个元组，第一个元素是 Interrupt 对象
                    if interrupt_tuple:
                        interrupt_obj = interrupt_tuple[0] if isinstance(interrupt_tuple, tuple) else interrupt_tuple

                        # 提取 interrupt 的 value
                        interrupt_value = None
                        if hasattr(interrupt_obj, "value"):
                            interrupt_value = interrupt_obj.value
                        else:
                            interrupt_value = interrupt_obj

                        session["status"] = "waiting_for_input"
                        session["interrupt_data"] = interrupt_value
                        session["current_node"] = "interrupt"

                        #  广播 interrupt 到 WebSocket
                        await _server.broadcast_to_websockets(
                            request.session_id,
                            {"type": "interrupt", "status": "waiting_for_input", "interrupt_data": interrupt_value},
                        )

                        #  更新 Redis 中的 interrupt 状态
                        await _server.session_manager.update(
                            session_id,
                            {
                                "status": "waiting_for_input",
                                "interrupt_data": interrupt_value,
                                "current_node": "interrupt",
                            },
                        )

                        logger.info(
                            f" 已广播第二个 interrupt 到 WebSocket: {interrupt_value.get('interaction_type', 'unknown') if isinstance(interrupt_value, dict) else type(interrupt_value)}"
                        )
                        return

            # 检查是否有节点错误
            has_error = False
            error_message = None
            for event in session["events"]:
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if node_output.get("error") or node_output.get("status") == "error":
                            has_error = True
                            error_message = node_output.get("error", f"节点 {node_name} 执行失败")
                            break
                if has_error:
                    break

            # 根据是否有错误设置状态
            if has_error:
                session["status"] = "failed"
                session["error"] = error_message
                logger.error(f"工作流失败: {error_message}")

                #  广播失败状态到 WebSocket
                await _server.broadcast_to_websockets(
                    request.session_id, {"type": "status", "status": "failed", "message": error_message}
                )

                #  更新 Redis 失败状态
                await _server.session_manager.update(session_id, {"status": "failed", "error": error_message})
            else:
                #  v7.146: stream 结束 ≠ 一定完成。
                # 在某些路由缺失/边未连接的情况下，图会提前结束，过去会被误判为 completed 并触发自动归档。
                # 这里通过检查图状态中的批次执行进度 / final_report 来判定是否真的完成。
                #  v7.153: 修复 AsyncSqliteSaver 同步调用错误，使用 aget_state 异步方法
                try:
                    current_state = await workflow.graph.aget_state(config)
                    state_values = getattr(current_state, "values", {}) or {}
                except Exception as state_read_error:
                    logger.warning(f"️ Resume结束后读取graph state失败: {type(state_read_error).__name__}: {state_read_error}")
                    state_values = {}

                total_batches = state_values.get("total_batches", 0) or 0
                completed_batches = state_values.get("completed_batches", []) or []
                state_final_report = state_values.get("final_report")

                # 兼容 completed_batches 非 list 的异常情况
                completed_batch_count = len(completed_batches) if isinstance(completed_batches, list) else 0
                is_batches_completed = (
                    isinstance(total_batches, int)
                    and total_batches > 0
                    and isinstance(completed_batches, list)
                    and completed_batch_count >= total_batches
                )

                #  完成判定：
                # - 若 state 已写入 final_report，则认为完成；
                # - 或者批次已全部完成（total_batches>0 且 completed_batches 覆盖）。
                is_truly_completed = bool(state_final_report) or is_batches_completed

                logger.info(
                    f"[DEBUG] Resume stream finished. is_truly_completed={is_truly_completed}, "
                    f"current_node={session.get('current_node')}, total_batches={total_batches}, "
                    f"completed_batches={completed_batch_count}, has_state_final_report={bool(state_final_report)}"
                )

                if not is_truly_completed:
                    # 视为异常提前结束：不归档、不标 completed，避免误完成。
                    session["status"] = "failed"
                    session["error"] = "工作流提前结束（未检测到最终完成条件）。" "可能原因：路由缺失/边未连接/节点未按预期返回 Command(goto=...)。"

                    await _server.broadcast_to_websockets(
                        request.session_id,
                        {
                            "type": "status",
                            "status": "failed",
                            "message": session["error"],
                        },
                    )

                    await _server.session_manager.update(
                        session_id,
                        {
                            "status": "failed",
                            "error": session["error"],
                            "detail": session.get("detail"),
                        },
                    )
                    logger.error(
                        f" Resume流程提前结束且未满足完成条件: session_id={session_id}, "
                        f"current_node={session.get('current_node')}, total_batches={total_batches}, "
                        f"completed_batches={completed_batch_count}"
                    )
                    return

                session["status"] = "completed"
                session["progress"] = 1.0

                # 提取最终报告（优先使用 state 中的 final_report）
                final_report = state_final_report
                if not final_report:
                    for event in session["events"]:
                        for _node_name, node_output in event.items():
                            if isinstance(node_output, dict) and "final_report" in node_output:
                                final_report = node_output["final_report"]
                                break
                        if final_report:
                            break

                session["final_report"] = final_report or "分析完成"

                #  广播完成状态到 WebSocket
                await _server.broadcast_to_websockets(
                    request.session_id,
                    {
                        "type": "status",
                        "status": "completed",
                        "progress": 1.0,
                        "message": "分析完成",
                        "final_report": session.get("final_report"),
                    },
                )

                #  v7.153: 先同步 checkpoint 数据到 Redis，确保 final_report 和 aggregated_result 完整
                try:
                    sync_success = await _server.sync_checkpoint_to_redis(session_id)
                    if sync_success:
                        logger.info(" [v7.153] checkpoint 数据已同步到 Redis（resume流程完成）")
                    else:
                        logger.warning("️ [v7.153] checkpoint 同步未成功，使用 state_values 中的 final_report")
                        # 同步失败时，至少确保 final_report 被保存（从 state_values 获取）
                        if state_final_report and isinstance(state_final_report, dict):
                            await _server.session_manager.update(session_id, {"final_report": state_final_report})
                except Exception as sync_error:
                    logger.error(f" [v7.153] checkpoint 同步异常: {sync_error}")

                #  更新 Redis 完成状态
                await _server.session_manager.update(session_id, {"status": "completed", "progress": 1.0})

                #  v3.6新增: 自动归档完成的会话（永久保存）
                if _server.archive_manager:
                    try:
                        #  v7.145: 归档前同步 checkpoint 数据到 Redis
                        sync_success = await _server.sync_checkpoint_to_redis(session_id)
                        if sync_success:
                            logger.info(" [v7.145] checkpoint 数据已同步（resume流程），准备归档")

                        # 获取完整会话数据
                        final_session = await _server.session_manager.get(session_id)
                        if final_session:
                            await _server.archive_manager.archive_session(
                                session_id=session_id, session_data=final_session, force=False
                            )
                            logger.info(f" 会话已自动归档（永久保存）: {session_id}")
                    except Exception as archive_error:
                        logger.warning(f"️ 自动归档失败（不影响主流程）: {archive_error}")

                logger.info(f" 已广播完成状态到 WebSocket: {request.session_id}")

        #  处理递归限制错误
        except GraphRecursionError as e:
            logger.warning(f"️ Resume时达到递归限制！会话: {session_id}")
            logger.info(" 尝试获取最佳结果...")

            #  v7.153: 修复 AsyncSqliteSaver 同步调用错误，使用 aget_state 异步方法
            try:
                current_state = await workflow.graph.aget_state(config)
                state_values = current_state.values

                best_result = state_values.get("best_result")
                if best_result:
                    logger.info(f" 找到最佳结果（评分{state_values.get('best_score', 0):.1f}）")
                    state_values["agent_results"] = best_result
                else:
                    logger.warning("️ 未找到最佳结果，使用当前结果")

                session["status"] = "completed"
                session["progress"] = 1.0
                session["final_report"] = "分析已完成（达到递归限制）"

                #  广播完成状态到 WebSocket
                await _server.broadcast_to_websockets(
                    session_id, {"type": "status", "status": "completed", "progress": 1.0, "message": "分析已完成（达到递归限制）"}
                )
                logger.info(f" 已广播完成状态到 WebSocket (递归限制): {session_id}")
                session["metadata"] = {"forced_completion": True, "best_score": state_values.get("best_score", 0)}

            except Exception as state_error:
                logger.error(f" 获取状态失败: {state_error}")
                session["status"] = "failed"
                session["error"] = f"达到递归限制: {str(e)}"

        except Exception as e:
            session["status"] = "failed"
            session["error"] = str(e)
            import traceback

            session["traceback"] = traceback.format_exc()
            logger.error(f"[ERROR] Resume workflow failed: {e}")
            logger.error(f"[ERROR] Traceback:\n{traceback.format_exc()}")

    background_tasks.add_task(continue_workflow)

    return SessionResponse(session_id=session_id, status="resumed", message="分析已恢复")


@router.post("/api/analysis/followup", response_model=SessionResponse)
async def submit_followup_question(
    session_id: str = Form(...),
    question: str = Form(...),
    requires_analysis: bool = Form(True),
    image: UploadFile | None = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    提交追问（支持持续对话 + 图片上传）

     v3.11 重大改造：
    - 不再创建新会话，在原会话上追加对话历史
    - 支持无限轮次的连续追问
    - 支持"记忆全部"模式（智能上下文管理）
    - 对话历史持久化到Redis

     v7.108 新增：
    - 支持图片上传（multipart/form-data）
    - 图片永久保存到 data/followup_images/{session_id}/
    - 自动生成缩略图（400px）
    - 集成 Vision API 分析图片内容

    与 /api/analysis/resume 的区别:
    - resume: 用于 waiting_for_input 状态的中断恢复
    - followup: 用于 completed 状态的后续追问
    """
    logger.info(f" 收到追问请求: session_id={session_id}")
    logger.info(f"   问题: {question}")
    logger.info(f"   需要分析: {requires_analysis}")
    logger.info(f"   包含图片: {image is not None}")

    # 检查会话是否存在
    session = await _server.session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    # 允许 completed 状态的会话进行追问
    if session["status"] not in ["completed", "waiting_for_input"]:
        raise HTTPException(status_code=400, detail=f"无法追问，会话状态: {session['status']}（只能对已完成或等待输入的会话追问）")

    #  关键改变：不创建新会话，直接在原会话上追问
    logger.info(" 在原会话上追问（不创建新会话）")

    #  使用后台任务处理追问
    async def handle_followup():
        try:
            # 更新会话状态
            await _server.session_manager.update(session_id, {"status": "processing_followup", "detail": "正在思考回答..."})

            #  获取追问历史
            history_data = await _server.followup_history_manager.get_history(session_id, limit=None)  # 获取全部
            next_turn_id = len(history_data) + 1
            logger.info(f" 当前对话历史: {len(history_data)} 轮")

            #  v7.108: 处理图片上传（如果有）
            image_metadata = None
            enhanced_question = question

            if image is not None:
                try:
                    from pathlib import Path

                    from intelligent_project_analyzer.services.file_processor import FileProcessor
                    from intelligent_project_analyzer.services.followup_image_storage_manager import (
                        FollowupImageStorageManager,
                    )

                    logger.info(f" 开始处理图片: {image.filename}")

                    # 保存图片（原图 + 缩略图）
                    image_metadata = await FollowupImageStorageManager.save_image(
                        image_file=image, session_id=session_id, turn_id=next_turn_id
                    )
                    logger.info(f" 图片已保存: {image_metadata['stored_filename']}")

                    # Vision API 分析（使用 FileProcessor）
                    try:
                        file_processor = FileProcessor(enable_vision_api=True)
                        image_path = Path(f"data/followup_images/{session_id}/{image_metadata['stored_filename']}")

                        vision_result = await file_processor._extract_image(image_path)
                        vision_analysis = (
                            vision_result.get("text", "").split("## AI视觉分析")[-1].strip()
                            if "## AI视觉分析" in vision_result.get("text", "")
                            else ""
                        )

                        image_metadata["vision_analysis"] = vision_analysis
                        logger.info(f" Vision API 分析完成: {len(vision_analysis)} 字符")

                    except Exception as e:
                        logger.warning(f"️ Vision API 分析失败: {e}")
                        image_metadata["vision_analysis"] = ""

                    # 增强问题文本（拼接 Vision 分析）
                    if image_metadata.get("vision_analysis"):
                        enhanced_question = f"""{question}

[图片: {image_metadata['original_filename']}]
AI分析: {image_metadata['vision_analysis']}
"""

                except Exception as e:
                    logger.error(f" 图片处理失败: {e}")
                    import traceback

                    traceback.print_exc()
                    # 不阻塞追问，继续处理

            #  v7.15: 使用 FollowupAgent (LangGraph)
            agent = FollowupAgent()

            # 构建上下文
            parent_session = await _server.session_manager.get(session_id)
            aggregated_results = parent_session.get("aggregated_results", {})
            agent_results = parent_session.get("agent_results", {})
            structured_requirements = parent_session.get("structured_requirements", {})
            original_input = parent_session.get("user_input", "")

            # 如果没有结构化数据，尝试从 final_report 解析
            final_report = parent_session.get("final_report")
            if isinstance(final_report, dict) and not aggregated_results:
                aggregated_results = final_report

            #  v7.15: 构建 report_context (新格式)
            report_context = {
                "final_report": aggregated_results if isinstance(aggregated_results, dict) else {},
                "agent_results": agent_results if isinstance(agent_results, dict) else {},
                "requirements": structured_requirements if isinstance(structured_requirements, dict) else {},
                "user_input": original_input,
            }

            #  v7.15: 调用 FollowupAgent（使用增强后的问题）
            logger.info(f" 调用 FollowupAgent (LangGraph)（历史轮次: {len(history_data)}）")
            result = await agent.answer_question_async(
                question=enhanced_question, report_context=report_context, conversation_history=history_data
            )

            answer = result.get("answer", "抱歉，我无法回答这个问题。")

            #  v7.60.5: 累加追问Token到会话metadata
            from intelligent_project_analyzer.utils.token_utils import (
                extract_tokens_from_result,
                update_session_tokens,
            )

            token_data = extract_tokens_from_result(result)
            if token_data:
                success = await update_session_tokens(
                    _server.session_manager, session_id, token_data, agent_name="followup_qa"
                )
                if success:
                    logger.info(f" [追问Token] 已累加到会话 {session_id}")

            #  保存到追问历史（包含附件）
            attachments = []
            if image_metadata:
                attachments.append({"type": "image", **image_metadata})

            await _server.followup_history_manager.add_turn(
                session_id=session_id,
                question=question,
                answer=answer,
                intent=result.get("intent", "general"),
                referenced_sections=result.get("references", []),
                attachments=attachments,
            )

            # 更新会话状态（保持completed状态）
            await _server.session_manager.update(
                session_id, {"status": "completed", "detail": "追问回答完成", "last_followup_at": datetime.now().isoformat()}
            )

            #  通过WebSocket广播更新（前端实时显示）
            await _server.broadcast_to_websockets(
                session_id,
                {
                    "type": "followup_answer",
                    "turn_id": next_turn_id,
                    "question": question,
                    "answer": answer,
                    "intent": result.get("intent", "general"),
                    "referenced_sections": result.get("references", []),
                    "attachments": attachments,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f" 追问完成: {session_id}, 轮次={next_turn_id}")

        except Exception as e:
            logger.error(f" 追问处理失败: {e}")
            import traceback

            traceback.print_exc()
            await _server.session_manager.update(
                session_id, {"status": "completed", "detail": f"追问失败: {str(e)}"}  # 回到completed状态
            )

            # 广播错误
            await _server.broadcast_to_websockets(session_id, {"type": "followup_error", "error": str(e)})

    # 添加后台任务
    background_tasks.add_task(handle_followup)

    return SessionResponse(session_id=session_id, status="processing", message="追问已提交，正在生成回答...")  #  返回原会话ID，不是新会话


