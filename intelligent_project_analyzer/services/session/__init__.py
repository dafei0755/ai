# -*- coding: utf-8 -*-
"""
services/session — 会话与存储子包

收录 Session 管理、ExternalStateStore、EventStore、Redis 存储、配额管理等组件。

快捷导入示例：
    from intelligent_project_analyzer.services.session import (
        get_event_store, get_store, UserSessionManager
    )
"""

# ── MT-3: 外部状态存储 ────────────────────────────────────────────────────────
from intelligent_project_analyzer.services.external_state_store import (
    ExternalStateStore,
    get_store,
    reset_store,
)

# ── MT-4: WebSocket 事件存储 ─────────────────────────────────────────────────
from intelligent_project_analyzer.services.event_store import (
    EventStore,
    get_event_store,
    reset_event_store,
)

# ── 用户会话 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.user_session_manager import (
        UserProgress,
        UserSessionManager,
    )
except Exception:  # pragma: no cover
    UserSessionManager = None  # type: ignore[assignment,misc]
    UserProgress = None  # type: ignore[assignment,misc]

# ── Redis 会话 & 存储 ─────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.redis_session_manager import (
        RedisSessionManager,
    )
except Exception:  # pragma: no cover
    RedisSessionManager = None  # type: ignore[assignment,misc]

try:
    from intelligent_project_analyzer.services.redis_store import RedisStore
except Exception:  # pragma: no cover
    RedisStore = None  # type: ignore[assignment,misc]

# ── 配额管理 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.quota_manager import QuotaManager
except Exception:  # pragma: no cover
    QuotaManager = None  # type: ignore[assignment,misc]

# ── 会话归档 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.session_archive_manager import (
        SessionArchiveManager,
    )
except Exception:  # pragma: no cover
    SessionArchiveManager = None  # type: ignore[assignment,misc]

# ── 过期清理 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.expiry_cleanup_service import (
        ExpiryCleanupService,
    )
except Exception:  # pragma: no cover
    ExpiryCleanupService = None  # type: ignore[assignment,misc]

# ── 设备会话 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.device_session_manager import (
        DeviceSessionManager,
    )
except Exception:  # pragma: no cover
    DeviceSessionManager = None  # type: ignore[assignment,misc]

__all__ = [
    # 外部状态存储
    "ExternalStateStore",
    "get_store",
    "reset_store",
    # 事件存储
    "EventStore",
    "get_event_store",
    "reset_event_store",
    # 用户会话
    "UserSessionManager",
    "UserProgress",
    # Redis
    "RedisSessionManager",
    "RedisStore",
    # 配额 & 归档
    "QuotaManager",
    "SessionArchiveManager",
    # 清理
    "ExpiryCleanupService",
    # 设备
    "DeviceSessionManager",
]
