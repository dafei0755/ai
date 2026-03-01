# -*- coding: utf-8 -*-
"""
MT-1 (2026-03-01): 共享服务器状态模块

从 api/server.py 提取的模块级可变状态。
外部模块（路由模块）通过如下方式访问实时值：

    import intelligent_project_analyzer.api.state as _state
    sm = _state.session_manager          # 始终获取当前值（非 None 时已初始化完毕）

⚠ 警告：切勿 `from .state import session_manager`，这只会捕获模块加载时的
         初始 None 值，无法感知 lifespan() 的赋值更新。
         请使用模块属性访问：`_state.session_manager` 或调用 `_get_session_manager()`。
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from cachetools import TTLCache

if TYPE_CHECKING:
    import redis.asyncio as aioredis
    from fastapi import WebSocket
    from langgraph.checkpoint.base import BaseCheckpointSaver

    from intelligent_project_analyzer.services.followup_history_manager import (
        FollowupHistoryManager,
    )
    from intelligent_project_analyzer.services.redis_session_manager import (
        RedisSessionManager,
    )
    from intelligent_project_analyzer.services.session_archive_manager import (
        SessionArchiveManager,
    )
    from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

# ---------------------------------------------------------------------------
# 工作流实例池
# ---------------------------------------------------------------------------
workflows: Dict[str, Any] = {}

# LangGraph 检查点存储（异步版，全局复用）
async_checkpointer: Optional[Any] = None
async_checkpointer_lock: Optional[asyncio.Lock] = None

# ---------------------------------------------------------------------------
# Redis 会话管理器（替代内存字典）
# ---------------------------------------------------------------------------
session_manager: Optional[Any] = None


async def _get_session_manager() -> Any:
    """获取会话管理器（支持在未触发生命周期事件时惰性初始化）。

    说明：在使用 ASGITransport/某些测试客户端时，FastAPI lifespan 可能不会自动触发，
    导致全局 session_manager 仍为 None。这里提供一个安全兜底。
    """
    global session_manager
    if session_manager is None:
        from intelligent_project_analyzer.services.redis_session_manager import (
            RedisSessionManager,
        )

        session_manager = RedisSessionManager()
        try:
            await session_manager.connect()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("session_manager 惰性初始化失败: %s", exc)
    return session_manager


# ---------------------------------------------------------------------------
# 会话归档管理器
# ---------------------------------------------------------------------------
archive_manager: Optional[Any] = None

# ---------------------------------------------------------------------------
# 追问历史管理器
# ---------------------------------------------------------------------------
followup_history_manager: Optional[Any] = None

# ---------------------------------------------------------------------------
# WebSocket 连接管理
# ---------------------------------------------------------------------------
websocket_connections: Dict[str, List[Any]] = {}  # session_id -> [ws, ...]

# ---------------------------------------------------------------------------
# Redis Pub/Sub
# ---------------------------------------------------------------------------
redis_pubsub_client: Optional[Any] = None
redis_pubsub_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

# ---------------------------------------------------------------------------
# PDF 缓存（TTL=1h, maxsize=100）
# ---------------------------------------------------------------------------
pdf_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)  # type: ignore[type-arg]
