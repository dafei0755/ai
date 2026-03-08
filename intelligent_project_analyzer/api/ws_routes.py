"""
WebSocket 路由模块 (MT-1 提取自 api/server.py)

Routes:
  WS  /ws/{session_id}  — 实时推送工作流状态更新
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from intelligent_project_analyzer.api._server_proxy import server_proxy as _server

router = APIRouter(tags=["websocket"])


async def _wait_for_connected(websocket: WebSocket, timeout: float = 2.0) -> bool:
    """
     Fix 1.1 + v7.118: Wait for WebSocket to reach CONNECTED state

    增强版本：添加更详细的状态检查和日志

    Args:
        websocket: WebSocket connection
        timeout: Maximum wait time in seconds

    Returns:
        True if connected, False if timeout
    """
    import asyncio

    from starlette.websockets import WebSocketState

    start = asyncio.get_event_loop().time()
    while websocket.client_state != WebSocketState.CONNECTED:
        elapsed = asyncio.get_event_loop().time() - start
        if elapsed > timeout:
            logger.error(f" WebSocket 连接超时 (state: {websocket.client_state.name}, elapsed: {elapsed:.2f}s)")
            return False
        await asyncio.sleep(0.05)

    logger.debug(f" WebSocket已连接 (耗时: {(asyncio.get_event_loop().time() - start):.2f}s)")
    return True


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket 端点 - 实时推送工作流状态更新

    客户端连接后，会实时接收：
    - 节点更新 (node_update)
    - 状态更新 (status_update)
    - 中断通知 (interrupt)
    """
    # 接受连接
    await websocket.accept()
    logger.info(f" WebSocket 握手完成: {session_id}")

    try:
        #  P0修复: 先等待达到CONNECTED状态，再加入连接池
        is_connected = await _wait_for_connected(websocket, timeout=3.0)
        if not is_connected:
            logger.error(f" WebSocket 连接超时，关闭连接: {session_id}")
            await websocket.close(code=1008, reason="Connection timeout")
            return  # 不加入连接池，直接返回

        #  P0修复: 仅在确认连接后才加入连接池
        if session_id not in _server.websocket_connections:
            _server.websocket_connections[session_id] = []
        _server.websocket_connections[session_id].append(websocket)
        logger.info(f" WebSocket 已加入连接池: {session_id}")

        # 发送初始状态（简化重试逻辑）
        if _server.session_manager:
            session = await _server.session_manager.get(session_id)
            if session:
                #  P0修复: 连接已确认，直接发送初始状态（无需重试）
                await websocket.send_json(
                    {
                        "type": "initial_status",
                        "status": session.get("status", "pending"),
                        "progress": session.get("progress", 0),
                        "current_node": session.get("current_node"),
                        "detail": session.get("detail"),
                    }
                )
                logger.debug(f" WebSocket 初始状态已发送: {session_id}")

        # 保持连接并接收客户端心跳
        while True:
            try:
                # 接收客户端消息（主要用于心跳检测）
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # 可选：处理客户端发送的消息
                if data == "ping":
                    #  P0修复: 发送pong前检查连接状态
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # 60秒无心跳，发送 ping 检查连接
                #  P0修复: 发送ping前检查连接状态
                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        logger.info(f" WebSocket 断开: {session_id}")
    except Exception as e:
        #  v7.118: 改进错误处理，忽略常见的连接关闭错误
        error_str = str(e)
        if any(keyword in error_str for keyword in ["Cannot call", "send", "close message", "not connected"]):
            logger.debug(f" WebSocket 连接已关闭: {session_id} ({type(e).__name__})")
        else:
            logger.error(f" WebSocket 错误: {session_id}, {type(e).__name__}: {e}", exc_info=True)
    finally:
        # 从连接池移除
        if session_id in _server.websocket_connections:
            if websocket in _server.websocket_connections[session_id]:
                _server.websocket_connections[session_id].remove(websocket)
            # 如果没有连接了，清理字典
            if not _server.websocket_connections[session_id]:
                del _server.websocket_connections[session_id]
                # v7.131 BUG FIX: 不在此处清理 Playwright 浏览器池
                # 原逻辑在 WebSocket 断开时检查 total_active==0 就调用 cleanup()，
                # 但存在竞态条件：旧连接断开与新连接注册之间有 ~10ms 窗隙，
                # 导致后台工作流仍在执行时浏览器池被错误销毁，PDF 生成必定失败。
                # Playwright 浏览器池的正确清理时机是服务器关闭（lifespan handler），
                # 而非 WebSocket 断开。
