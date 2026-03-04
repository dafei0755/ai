"""
工作流引擎模块 (MT-1 提取自 api/server.py)

包含:
  - subscribe_to_redis_pubsub       (Redis Pub/Sub 订阅)
  - _ensure_aiosqlite_is_alive      (aiosqlite 兼容补丁)
  - get_or_create_async_checkpointer (LangGraph 检查点惰性初始化)
  - create_workflow                  (创建 MainWorkflow 实例)
  - broadcast_to_websockets          (多实例 WebSocket 广播)
  - run_workflow_async               (主工作流异步执行函数)
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from types import MethodType
from typing import Any, Dict

from loguru import logger

from intelligent_project_analyzer.settings import settings
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

try:
    from langgraph.checkpoint.base import BaseCheckpointSaver
except ImportError:
    BaseCheckpointSaver = None  # type: ignore[assignment,misc]

# ── 模块级全局变量（从 server.py 移至此处）──────────────────────────────────
workflows: Dict[str, MainWorkflow] = {}
async_checkpointer: Any | None = None  # AsyncSqliteSaver，惰性初始化
async_checkpointer_lock: asyncio.Lock | None = None

from intelligent_project_analyzer.api._server_proxy import server_proxy as _server
from intelligent_project_analyzer.api.deps import (  # noqa: E402
    _serialize_for_json,
    sync_checkpoint_to_redis,
)
from intelligent_project_analyzer.core.state import StateManager  # noqa: E402

# ==================== 辅助函数 ====================


async def subscribe_to_redis_pubsub():
    """
    订阅 Redis Pub/Sub 频道，用于多实例 WebSocket 消息广播
    """
    if not _server.redis_pubsub_client:
        return

    try:
        pubsub = _server.redis_pubsub_client.pubsub()
        await pubsub.subscribe("workflow:broadcast")

        logger.info(" Redis Pub/Sub 订阅已启动")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    import json

                    data = json.loads(message["data"])
                    session_id = data.get("session_id")
                    payload = data.get("payload")

                    # 本地广播到 WebSocket
                    if session_id in _server.websocket_connections:
                        connections = _server.websocket_connections[session_id]
                        disconnected = []

                        for ws in connections:
                            try:
                                #  Fix 1.1: Check WebSocket state before sending (matches local broadcast logic)
                                if ws.client_state.name != "CONNECTED":
                                    logger.debug(f"️ 跳过非连接状态的WebSocket (state={ws.client_state.name})")
                                    disconnected.append(ws)
                                    continue

                                await ws.send_json(payload)
                            except Exception as e:
                                logger.warning(f"️ WebSocket 发送失败: {e}")
                                disconnected.append(ws)

                        # 清理断开的连接
                        for ws in disconnected:
                            connections.remove(ws)

                except Exception as e:
                    logger.error(f" 处理 Pub/Sub 消息失败: {e}")

    except asyncio.CancelledError:
        logger.info(" Redis Pub/Sub 订阅已停止")
        await pubsub.unsubscribe("workflow:broadcast")
        await pubsub.close()
    except Exception as e:
        logger.error(f" Redis Pub/Sub 订阅失败: {e}")


def _ensure_aiosqlite_is_alive(conn: Any) -> Any:
    """为缺少 is_alive() 方法的 aiosqlite 连接打补丁。"""

    if hasattr(conn, "is_alive") and callable(conn.is_alive):
        return conn

    def _is_alive(self: Any) -> bool:  # pragma: no cover - 简单代理
        thread = getattr(self, "_thread", None)
        running = getattr(self, "_running", False)
        return bool(thread and thread.is_alive() and running)

    conn.is_alive = MethodType(_is_alive, conn)  # type: ignore[attr-defined]
    logger.debug("🩹 AsyncSqliteSaver 兼容补丁：已为 aiosqlite.Connection 注入 is_alive()")
    return conn


async def get_or_create_async_checkpointer() -> BaseCheckpointSaver[str] | None:
    """惰性初始化 AsyncSqliteSaver，所有会话复用同一个连接。"""

    global async_checkpointer, async_checkpointer_lock

    if async_checkpointer is not None:
        return async_checkpointer

    if async_checkpointer_lock is None:
        async_checkpointer_lock = asyncio.Lock()

    async with async_checkpointer_lock:
        if async_checkpointer is not None:
            return async_checkpointer

        try:
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        except ImportError as exc:
            logger.warning(f"️ AsyncSqliteSaver 不可用，回退到同步 SqliteSaver: {exc}")
            return None

        db_path = Path("./data/checkpoints/workflow.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = await aiosqlite.connect(str(db_path))
        conn = _ensure_aiosqlite_is_alive(conn)
        async_checkpointer = AsyncSqliteSaver(conn)
        logger.info(f" AsyncSqliteSaver 初始化成功: {db_path}")
        return async_checkpointer


async def create_workflow() -> MainWorkflow | None:
    """
    创建工作流实例 - 使用 LLMFactory（支持自动降级）

     使用 LLMFactory 创建 LLM，支持运行时降级
    """
    try:
        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        logger.info(" 使用 LLMFactory 创建 LLM（支持自动降级）")

        #  使用 LLMFactory 创建 LLM（自动应用 .env 配置和降级链）
        llm = LLMFactory.create_llm()

        # 默认使用 Dynamic Mode
        config = {
            "mode": "dynamic",
            "enable_role_config": True,
            "post_completion_followup_enabled": settings.post_completion_followup_enabled,
        }

        checkpointer = await get_or_create_async_checkpointer()

        workflow = MainWorkflow(llm, config, checkpointer=checkpointer)
        logger.info(" 工作流创建成功（LLM 降级已启用）")
        return workflow

    except Exception as e:
        logger.error(f" 创建工作流失败: {e}")
        import traceback

        traceback.print_exc()
        return None


async def broadcast_to_websockets(session_id: str, message: Dict[str, Any]):
    """
     v7.133: 增强的WebSocket广播 - 添加连接健康检查和自动清理

    向所有连接到指定会话的 WebSocket 客户端广播消息
     使用 Redis Pub/Sub 支持多实例部署

    Args:
        session_id: 会话 ID
        message: 要发送的消息（字典格式，将被转换为 JSON）
    """
    # 🆕 MT-4: 事件持久化 —— 写入 EventStore 供断线重连补偿
    try:
        from intelligent_project_analyzer.services.event_store import get_event_store

        await get_event_store().append(session_id, message)
    except Exception as _evt_exc:
        logger.debug(f"[MT-4] EventStore 写入失败（不影响广播）: {_evt_exc}")
    #  Redis Pub/Sub 模式：发布到 Redis，所有实例监听
    if _server.redis_pubsub_client:
        try:
            import json

            payload = {"session_id": session_id, "payload": message}
            await _server.redis_pubsub_client.publish("workflow:broadcast", json.dumps(payload, ensure_ascii=False))
            logger.debug(f" [v7.133] Redis Pub/Sub 发布成功: {session_id}")
            return
        except Exception as e:
            logger.warning(f"️ [v7.133] Redis Pub/Sub 发布失败，回退到本地广播: {e}")

    #  本地模式：直接广播到本实例的 WebSocket 连接
    if session_id not in _server.websocket_connections:
        logger.debug(f" [v7.133] 未找到会话的WebSocket连接: {session_id}")
        return

    # 获取该会话的所有连接
    connections = _server.websocket_connections[session_id]

    # 存储断开的连接
    disconnected = []
    success_count = 0
    failed_count = 0

    # 广播消息到所有连接
    for ws in connections:
        try:
            from starlette.websockets import WebSocketState

            #  v7.133: 增强连接状态检查
            if ws.client_state != WebSocketState.CONNECTED:
                logger.debug(f"️ [v7.133] WebSocket未连接 (状态: {ws.client_state.name})，标记为断开")
                disconnected.append(ws)
                failed_count += 1
                continue

            #  v7.133: 添加发送超时保护
            import asyncio

            await asyncio.wait_for(ws.send_json(message), timeout=5.0)
            success_count += 1

        except asyncio.TimeoutError:
            logger.warning("️ [v7.133] WebSocket 发送超时(5s)，标记为断开")
            disconnected.append(ws)
            failed_count += 1
        except Exception as e:
            error_str = str(e)
            if "not connected" in error_str.lower() or "closed" in error_str.lower():
                logger.debug(f" [v7.133] WebSocket已断开: {type(e).__name__}")
            else:
                logger.warning(f"️ [v7.133] WebSocket 发送失败: {type(e).__name__}: {e}")
            disconnected.append(ws)
            failed_count += 1

    # 清理断开的连接
    for ws in disconnected:
        if ws in connections:
            connections.remove(ws)

    #  v7.133: 记录广播统计
    if success_count > 0 or failed_count > 0:
        logger.debug(
            f" [v7.133] WebSocket广播完成: {session_id} | "
            f"成功={success_count} 失败={failed_count} 消息类型={message.get('type', 'unknown')}"
        )


async def run_workflow_async(session_id: str, user_input: str):
    """异步执行工作流（仅 Dynamic Mode）"""
    try:
        logger.info(f" [ASYNC] run_workflow_async 开始 | session_id={session_id}")

        #  v7.39: 从 session 获取分析模式
        session_data = await _server.session_manager.get(session_id)
        logger.info(f" [ASYNC] 获取session数据成功 | session_data={session_data is not None}")

        analysis_mode = session_data.get("analysis_mode", "normal") if session_data else "normal"
        user_id = session_data.get("user_id", "api_user") if session_data else "api_user"

        logger.info(f" [ASYNC] 解析模式信息 | analysis_mode={analysis_mode}, user_id={user_id}")

        logger.info(" [ASYNC] 准备打印工作流启动信息...")

        print(f"\n{'='*60}")
        print(" 开始执行工作流")
        print(f"Session ID: {session_id}")
        print(f"用户输入: {user_input[:100]}...")
        print("运行模式: Dynamic Mode")
        print(f"分析模式: {analysis_mode}")  #  v7.39
        print(f"{'='*60}\n")

        logger.info(" [ASYNC] 工作流启动信息已打印")

        #  更新会话状态
        logger.info(" [ASYNC] 准备更新会话状态...")
        await _server.session_manager.update(session_id, {"status": "running", "progress": 0.1})
        logger.info(" [ASYNC] 会话状态已更新")

        #  广播状态到 WebSocket
        await broadcast_to_websockets(
            session_id, {"type": "status_update", "status": "running", "progress": 0.1, "message": "工作流开始执行"}
        )

        # 创建工作流
        print(" 创建工作流 (Dynamic Mode)...")
        workflow = await create_workflow()
        if not workflow:
            print(" 工作流创建失败")
            await _server.session_manager.update(
                session_id, {"status": "failed", "error": "工作流创建失败", "traceback": "工作流创建失败，请检查配置"}
            )
            return

        print(" 工作流创建成功")
        workflows[session_id] = workflow

        logger.info(" [ASYNC] 准备创建初始状态...")

        #  v7.156: 从 session_data 提取多模态视觉参考
        visual_references = session_data.get("visual_references") if session_data else None
        visual_style_anchor = session_data.get("visual_style_anchor") if session_data else None

        if visual_references:
            logger.info(f"️ [v7.156] 检测到 {len(visual_references)} 个视觉参考，将注入工作流初始状态")
        if visual_style_anchor:
            logger.info(f" [v7.156] 检测到全局风格锚点: {visual_style_anchor[:100]}...")

        # 创建初始状态 -  v7.39: 传递 analysis_mode,  v7.156: 传递视觉参考
        initial_state = StateManager.create_initial_state(
            user_input=user_input,
            session_id=session_id,
            user_id=user_id,
            analysis_mode=analysis_mode,  #  v7.39
            uploaded_visual_references=visual_references,  #  v7.156: 多模态视觉参考
            visual_style_anchor=visual_style_anchor,  #  v7.156: 全局风格锚点
        )

        logger.info(f" [ASYNC] 初始状态已创建 | visual_refs={len(visual_references) if visual_references else 0}")

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}  # 增加递归限制，默认是25

        logger.info(" [ASYNC] 准备开始流式执行工作流...")

        # 流式执行工作流
        # 不指定 stream_mode，使用默认模式以正确接收 __interrupt__
        #  添加GraphRecursionError处理
        from langgraph.errors import GraphRecursionError

        events = []
        try:
            logger.info(" [ASYNC] 进入 astream 循环...")
            logger.info(" [ASYNC] 调用 workflow.graph.astream()...")

            stream = workflow.graph.astream(initial_state, config)
            logger.info(f" [ASYNC] astream() 返回了流对象: {type(stream)}")

            async for chunk in stream:
                #  诊断日志：检查每个 chunk 的键
                logger.info(f" [STREAM] chunk keys: {list(chunk.keys())}")

                events.append(_serialize_for_json(chunk))

                #  检查是否有 interrupt - 提前检测（在处理其他节点之前）
                if "__interrupt__" in chunk:
                    logger.info(f" [INTERRUPT] Detected! chunk keys: {list(chunk.keys())}")
                    # 提取 interrupt 数据
                    interrupt_tuple = chunk["__interrupt__"]
                    logger.info(f" [INTERRUPT] tuple type: {type(interrupt_tuple)}, content: {interrupt_tuple}")

                    # interrupt_tuple 是一个元组，第一个元素是 Interrupt 对象
                    if interrupt_tuple:
                        interrupt_obj = interrupt_tuple[0] if isinstance(interrupt_tuple, tuple) else interrupt_tuple
                        logger.info(f" [INTERRUPT] obj type: {type(interrupt_obj)}")

                        # 提取 interrupt 的 value
                        interrupt_value = None
                        if hasattr(interrupt_obj, "value"):
                            interrupt_value = interrupt_obj.value
                            logger.info(" [INTERRUPT] Extracted value from .value attribute")
                        else:
                            interrupt_value = interrupt_obj
                            logger.info(" [INTERRUPT] Using obj directly as value")

                        logger.info(f" [INTERRUPT] value type: {type(interrupt_value)}")

                        #  v7.119: 更新会话状态为等待用户输入，并记录时间戳
                        import time

                        await _server.session_manager.update(
                            session_id,
                            {
                                "status": "waiting_for_input",
                                "interrupt_data": interrupt_value,
                                "current_node": "interrupt",
                                "interrupt_timestamp": time.time(),  # 记录进入waiting_for_input的时间
                            },
                        )
                        logger.info(f" [INTERRUPT] Session {session_id} updated to waiting_for_input")

                        #  广播 interrupt 到 WebSocket
                        await broadcast_to_websockets(
                            session_id,
                            {"type": "interrupt", "status": "waiting_for_input", "interrupt_data": interrupt_value},
                        )
                        logger.info(" [INTERRUPT] Broadcasted to WebSocket")
                        return

                #  更新当前节点和详细信息（用于前端进度展示）
                for node_name, node_output in chunk.items():
                    if node_name != "__interrupt__":
                        # 提取详细信息
                        detail = ""
                        if isinstance(node_output, dict):
                            #  优先使用 detail 字段（节点返回的详细描述）
                            if "detail" in node_output:
                                detail = node_output["detail"]
                            # 回退：使用 current_stage
                            elif "current_stage" in node_output:
                                detail = node_output["current_stage"]
                            # 最后：使用 status
                            elif "status" in node_output:
                                detail = node_output["status"]

                        #  更新当前节点、详情和历史记录
                        # 获取当前会话以追加历史
                        current_session = await _server.session_manager.get(session_id)
                        history = current_session.get("history", []) if current_session else []

                        # 添加新记录
                        history.append(
                            {"node": node_name, "detail": detail, "time": datetime.now().strftime("%H:%M:%S")}
                        )

                        #  v7.120: 提取search_references（如果节点更新了此字段）
                        update_data = {"current_node": node_name, "detail": detail, "history": history}

                        # 检查并提取search_references
                        if isinstance(node_output, dict) and "search_references" in node_output:
                            search_refs = node_output["search_references"]
                            if search_refs:  # 只有非空才更新
                                update_data["search_references"] = search_refs
                                logger.info(f" [v7.120] 节点 {node_name} 更新了 {len(search_refs)} 个搜索引用")

                        #  v7.153: 同步问卷流程相关字段到 Redis，修复进度显示异常
                        questionnaire_fields = [
                            "progressive_questionnaire_step",
                            "progressive_questionnaire_completed",
                            "questionnaire_summary_completed",
                            "confirmed_core_tasks",
                            "gap_filling_answers",
                            "selected_dimensions",
                            "radar_dimension_values",
                            "requirements_confirmed",
                            "restructured_requirements",
                            "requirements_summary_text",
                            "flow_route_name",
                            "flow_route_decision",
                            "flow_route_reason_codes",
                            "routing_scores",
                            "active_steps",
                            "motivation_routing_profile",
                            "task_intent_profile",
                            "output_intent_confirmed",
                        ]
                        if isinstance(node_output, dict):
                            for field in questionnaire_fields:
                                if field in node_output and node_output[field] is not None:
                                    update_data[field] = node_output[field]
                                    logger.debug(f" [v7.153] 同步问卷字段: {field}")

                        await _server.session_manager.update(session_id, update_data)
                        logger.debug(f"[PROGRESS] 节点: {node_name}, 详情: {detail}")

                        #  诊断日志（2025-11-30）：检查detail提取和广播
                        if node_name == "agent_executor":
                            logger.info(f" [DIAGNOSTIC] agent_executor detail: '{detail}'")
                            logger.info(
                                f" [DIAGNOSTIC] node_output keys: {list(node_output.keys()) if isinstance(node_output, dict) else 'not dict'}"
                            )
                            if isinstance(node_output, dict) and "detail" in node_output:
                                logger.info(f" [DIAGNOSTIC] node_output['detail']: '{node_output['detail']}'")

                        #  广播节点更新到 WebSocket
                        await broadcast_to_websockets(
                            session_id,
                            {
                                "type": "node_update",
                                "current_node": node_name,
                                "detail": detail,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                        #  诊断日志：确认广播内容
                        if node_name == "agent_executor":
                            logger.info(f" [DIAGNOSTIC] Broadcasted node_update with detail: '{detail}'")

                #  更新进度（优化：基于节点名称映射）
                #  获取当前会话数据
                current_session = await _server.session_manager.get(session_id)
                if not current_session:
                    continue

                current_node_name = current_session.get("current_node", "")

                #  v7.21: 定义节点到进度的映射（与 main_workflow.py 实际节点名称对齐）
                #  v7.153: 添加问卷流程节点，修复进度显示异常
                node_progress_map = {
                    # 输入验证阶段 (0-15%)
                    "unified_input_validator_initial": 0.05,  # 5% - 初始输入验证
                    "unified_input_validator_secondary": 0.10,  # 10% - 二次验证
                    # 需求分析阶段 (15-25%)
                    "requirements_analyst": 0.15,  # 15% - 需求分析
                    "feasibility_analyst": 0.18,  # 18% - 可行性分析
                    #  v7.153: 问卷流程阶段 (20-35%)
                    "progressive_step1_core_task": 0.20,  # 20% - Step 1: 核心任务
                    "progressive_step2_info_gather": 0.25,  # 25% - Step 2: 信息补充
                    "progressive_step3_radar": 0.30,  # 30% - Step 3: 雷达图
                    "questionnaire_summary": 0.35,  # 35% - Step 4: 需求洞察
                    # 项目规划阶段 (35-55%)
                    "project_director": 0.40,  # 40% - 项目总监
                    "role_task_unified_review": 0.45,  # 45% - 角色审核
                    "quality_preflight": 0.50,  # 50% - 质量预检
                    # 专家执行阶段 (55-80%)
                    "batch_executor": 0.55,  # 55% - 批次调度
                    "agent_executor": 0.70,  # 70% - 专家执行
                    "batch_aggregator": 0.75,  # 75% - 批次聚合
                    "batch_router": 0.76,  # 76% - 批次路由
                    "batch_strategy_review": 0.78,  # 78% - 策略审核
                    # 审核聚合阶段 (80-100%)
                    "detect_challenges": 0.80,  # 80% - 挑战检测
                    "analysis_review": 0.85,  # 85% - 分析审核
                    "result_aggregator": 0.90,  # 90% - 结果聚合
                    "report_guard": 0.95,  # 95% - 报告审核
                    "pdf_generator": 0.98,  # 98% - PDF 生成
                }

                # 使用节点映射或回退到计数
                new_progress = node_progress_map.get(current_node_name, min(0.9, len(events) * 0.1))

                #  防止进度回退：只有新进度 ≥ 旧进度时才更新
                old_progress = current_session.get("progress", 0)
                progress = max(new_progress, old_progress if isinstance(old_progress, (int, float)) else 0)

                if new_progress < old_progress:
                    logger.debug(f"️ 检测到进度回退: {old_progress:.0%} → {new_progress:.0%}，使用旧进度 {progress:.0%}")

                #  单次更新 Redis（避免重复写入和竞态条件）
                await _server.session_manager.update(
                    session_id,
                    {
                        "progress": progress,
                        "events": events,
                        "current_node": current_node_name,
                        "detail": current_session.get("detail"),
                        "status": current_session["status"],
                    },
                )

                #  直接使用计算值广播到 WebSocket（避免 Redis 读取竞态）
                #  v7.120: 包含search_references
                broadcast_data = {
                    "type": "status_update",
                    "status": current_session["status"],
                    "progress": progress,
                    "current_node": current_node_name,
                    "detail": current_session.get("detail"),
                }

                # 添加search_references（如果存在）
                search_refs = current_session.get("search_references")
                if search_refs:
                    broadcast_data["search_references"] = search_refs

                await broadcast_to_websockets(session_id, broadcast_data)

            # 检查是否有节点错误或被拒绝
            has_error = False
            error_message = None
            is_rejected = False
            rejection_message = None

            for event in events:
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        # 检查错误
                        if node_output.get("error") or node_output.get("status") == "error":
                            has_error = True
                            error_message = node_output.get("error", f"节点 {node_name} 执行失败")
                            break
                        #  检查被拒绝
                        if (
                            node_output.get("final_status") == "rejected"
                            or node_output.get("current_stage") == "REJECTED"
                        ):
                            is_rejected = True
                            rejection_message = node_output.get("rejection_message", "输入不符合要求")
                            rejection_reason = node_output.get("rejection_reason", "unknown")  # 获取拒绝原因
                            break
                if has_error or is_rejected:
                    break

            # 根据状态设置会话
            if is_rejected:
                await _server.session_manager.update(
                    session_id,
                    {
                        "status": "rejected",
                        "rejection_message": rejection_message,
                        "rejection_reason": rejection_reason,  # 保存拒绝原因
                        "progress": 1.0,
                    },
                )
                logger.info(f" 输入被拒绝: {rejection_message[:100]}...")

                #  获取最新会话数据用于广播
                updated_session = await _server.session_manager.get(session_id)

                #  广播拒绝状态
                await broadcast_to_websockets(
                    session_id,
                    {
                        "type": "status_update",
                        "status": "rejected",
                        "progress": 1.0,
                        "rejection_message": rejection_message,
                        "rejection_reason": rejection_reason,  # 广播拒绝原因
                        "current_node": updated_session.get("current_node") if updated_session else None,
                        "detail": updated_session.get("detail") if updated_session else None,
                    },
                )
            elif has_error:
                await _server.session_manager.update(session_id, {"status": "failed", "error": error_message})
                logger.error(f"工作流失败: {error_message}")

                #  获取最新会话数据
                updated_session = await _server.session_manager.get(session_id)

                #  广播错误状态
                await broadcast_to_websockets(
                    session_id,
                    {
                        "type": "status_update",
                        "status": "failed",
                        "error": error_message,
                        "current_node": updated_session.get("current_node") if updated_session else None,
                        "detail": updated_session.get("detail") if updated_session else None,
                        "progress": updated_session.get("progress") if updated_session else 0,
                    },
                )
            else:
                #  v7.153: 先同步 checkpoint 数据到 Redis，确保 final_report 结构化数据完整
                try:
                    sync_success = await sync_checkpoint_to_redis(session_id)
                    if sync_success:
                        logger.info(" [v7.153] checkpoint 数据已同步到 Redis（工作流完成）")
                except Exception as sync_error:
                    logger.error(f" [v7.153] checkpoint 同步异常: {sync_error}")

                # 提取最终报告和PDF路径（从 events 中作为备用）
                final_report = None
                pdf_path = None

                for event in events:
                    for node_name, node_output in event.items():
                        if isinstance(node_output, dict):
                            # 提取 final_report
                            if "final_report" in node_output:
                                final_report = node_output["final_report"]
                            # 提取 pdf_path（由 report_generator 节点生成）
                            if "pdf_path" in node_output:
                                pdf_path = node_output["pdf_path"]
                                logger.info(f" 提取到报告路径: {pdf_path}")

                #  更新完成状态（final_report 优先使用 sync 同步的数据）
                update_data = {
                    "status": "completed",
                    "progress": 1.0,
                    "pdf_path": pdf_path,
                }
                # 只有当 sync 没有同步 final_report 时，才使用 events 中的备用值
                if final_report:
                    # 检查 Redis 中是否已有 final_report
                    current_session = await _server.session_manager.get(session_id)
                    if not current_session.get("final_report"):
                        update_data["final_report"] = final_report

                await _server.session_manager.update(session_id, update_data)

                #  获取最新会话数据
                updated_session = await _server.session_manager.get(session_id)

                #  广播完成状态（v7.120: 包含search_references）
                completion_broadcast = {
                    "type": "status_update",
                    "status": "completed",
                    "progress": 1.0,
                    "final_report": final_report or "分析完成",
                    "current_node": updated_session.get("current_node") if updated_session else None,
                    "detail": updated_session.get("detail") if updated_session else None,
                }

                # 添加search_references（如果存在）
                if updated_session and updated_session.get("search_references"):
                    completion_broadcast["search_references"] = updated_session["search_references"]
                    logger.info(f" [v7.120] 完成广播包含 {len(updated_session['search_references'])} 个搜索引用")

                await broadcast_to_websockets(session_id, completion_broadcast)

                #  提取最终状态作为结构化结果（供get_analysis_result使用）
                final_state = None
                challenge_detection = None
                challenge_handling = None

                if events:
                    # 最后一个事件可能包含完整状态
                    last_event = events[-1] if events else {}
                    # 尝试从各个节点提取状态
                    for node_name, node_output in last_event.items():
                        if isinstance(node_output, dict):
                            if "agent_results" in node_output:
                                final_state = node_output
                            #  提取挑战检测数据
                            if "challenge_detection" in node_output:
                                challenge_detection = node_output["challenge_detection"]
                            if "challenge_handling" in node_output:
                                challenge_handling = node_output["challenge_handling"]

                    # 如果最后一个事件没有，遍历所有事件查找
                    if not challenge_detection:
                        for event in events:
                            for node_name, node_output in event.items():
                                if isinstance(node_output, dict):
                                    if "challenge_detection" in node_output and node_output["challenge_detection"]:
                                        challenge_detection = node_output["challenge_detection"]
                                        challenge_handling = node_output.get("challenge_handling")
                                        logger.info(f" 从 {node_name} 提取到挑战检测数据")
                                        break
                            if challenge_detection:
                                break

                #  保存最终状态和事件（包含挑战检测）
                update_data = {"final_state": final_state, "results": events}
                if challenge_detection:
                    update_data["challenge_detection"] = challenge_detection
                    update_data["challenge_handling"] = challenge_handling
                    logger.info(f" 保存挑战检测数据: has_challenges={challenge_detection.get('has_challenges')}")

                await _server.session_manager.update(session_id, update_data)

                #  v3.6新增: 自动归档完成的会话（永久保存）
                if _server.archive_manager:
                    try:
                        #  v7.145: 归档前同步 checkpoint 数据到 Redis
                        sync_success = await sync_checkpoint_to_redis(session_id)
                        if sync_success:
                            logger.info(" [v7.145] checkpoint 数据已同步，准备归档")

                        # 获取完整会话数据
                        final_session = await _server.session_manager.get(session_id)
                        if final_session:
                            await _server.archive_manager.archive_session(
                                session_id=session_id, session_data=final_session, force=False  # 仅归档completed状态的会话
                            )
                            logger.info(f" 会话已自动归档（永久保存）: {session_id}")
                    except Exception as archive_error:
                        # 归档失败不应影响主流程
                        logger.warning(f"️ 自动归档失败（不影响主流程）: {archive_error}")

        #  处理递归限制错误
        except GraphRecursionError as e:
            logger.warning(f"️ 达到递归限制！会话: {session_id}")
            logger.info(" 尝试获取最佳结果...")

            # 获取当前状态
            #  v7.153: 修复 AsyncSqliteSaver 同步调用错误，使用 aget_state 异步方法
            try:
                current_state = await workflow.graph.aget_state(config)
                state_values = current_state.values

                # 尝试获取最佳结果
                best_result = state_values.get("best_result")
                if best_result:
                    logger.info(f" 找到最佳结果（评分{state_values.get('best_score', 0):.1f}）")
                    # 使用最佳结果更新agent_results
                    state_values["agent_results"] = best_result
                    state_values["metadata"]["forced_completion"] = True
                    state_values["metadata"]["completion_reason"] = "达到递归限制，使用最佳历史结果"
                else:
                    logger.warning("️ 未找到最佳结果，使用当前结果")
                    state_values["metadata"]["forced_completion"] = True
                    state_values["metadata"]["completion_reason"] = "达到递归限制"

                #  更新为完成状态
                await _server.session_manager.update(
                    session_id,
                    {
                        "status": "completed",
                        "progress": 1.0,
                        "results": events,
                        "final_report": "分析已完成（达到递归限制）",
                        "metadata": state_values.get("metadata", {}),
                    },
                )

            except Exception as state_error:
                logger.error(f" 获取状态失败: {state_error}")
                import traceback

                await _server.session_manager.update(
                    session_id,
                    {"status": "failed", "error": f"达到递归限制且无法获取状态: {str(e)}", "traceback": traceback.format_exc()},
                )

    except Exception as e:
        import traceback

        error_msg = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f" [ASYNC] run_workflow_async 异常: {error_msg}")
        logger.error(f" [ASYNC] 异常堆栈:\n{error_traceback}")

        await _server.session_manager.update(
            session_id, {"status": "failed", "error": error_msg, "traceback": error_traceback}
        )


# ==================== API 端点 ====================


# ====== 监控/健康/用户路由（MT-1: 已提取至 api/monitoring_routes.py）======
# Routes: /, /health, /readiness, /api/debug/*, /api/user/*, /api/v1/dimensions/validate


# ====== 分析路由（MT-1: 已提取至 api/analysis_routes.py）======
# Routes: /api/analysis/start, /api/analysis/start-with-files, /api/analysis/resume,
#         /api/analysis/followup, /api/analysis/result, /api/analysis/report,
#         /api/analysis/report/download-pdf, /api/analysis/report/download-all-experts-pdf

# ====== 图像路由（MT-1: 已提取至 api/image_routes.py）======
# Routes: /api/analysis/regenerate-image, /api/analysis/add-image,
#         /api/analysis/delete-image, /api/analysis/suggest-prompts,
#         /api/analysis/image-chat-history, /api/analysis/regenerate-image-with-context


# ====== 会话/对话/归档路由（MT-1: 已提取至 api/session_routes.py）======
# Routes: suggest-questions, followup-history, /api/sessions/*, /api/conversation/*, /api/showcase/*
