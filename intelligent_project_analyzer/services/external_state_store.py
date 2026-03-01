"""
外部状态存储服务 (MT-3)

为 LangGraph State 大字段提供外部化存储，减少 checkpoint 序列化大小。

设计原则
--------
- 默认使用线程安全的内存存储（TTL 到期后自动回收）
- 设置 REDIS_URL 环境变量后自动切换为 Redis 后端
- TTL 默认 24 小时（可通过 EXTERNAL_STORE_TTL_SECONDS 调整）
- ref_key 格式：``{session_id}:{field}:{seq}``

使用示例
--------
::

    from intelligent_project_analyzer.services.external_state_store import get_store

    store = get_store()
    ref = store.put("sess-001", "conversation_history", messages)
    data = store.get(ref)   # -> messages
    store.delete(ref)
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any, Dict, Optional

from loguru import logger

# ---------------------------------------------------------------------------
# TTL 配置
# ---------------------------------------------------------------------------
_DEFAULT_TTL = 86400  # 24h


def _get_ttl() -> int:
    try:
        return int(os.getenv("EXTERNAL_STORE_TTL_SECONDS", str(_DEFAULT_TTL)))
    except ValueError:
        return _DEFAULT_TTL


# ---------------------------------------------------------------------------
# 内存后端
# ---------------------------------------------------------------------------


class _MemoryBackend:
    """线程安全的内存存储后端，支持 TTL 自动过期。"""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._lock = threading.Lock()

    # ---- 公开 API ----

    def put(self, key: str, value: Any, ttl: int) -> None:
        expires_at = time.monotonic() + ttl
        with self._lock:
            self._store[key] = (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            with self._lock:
                self._store.pop(key, None)
            return None
        return value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def cleanup_expired(self) -> int:
        now = time.monotonic()
        expired: list[str] = []
        with self._lock:
            for k, (_, exp) in list(self._store.items()):
                if now > exp:
                    expired.append(k)
            for k in expired:
                del self._store[k]
        if expired:
            logger.debug(f"[ExternalStateStore] 清理过期条目: {len(expired)} 条")
        return len(expired)

    def size(self) -> int:
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# Redis 后端（可选）
# ---------------------------------------------------------------------------


class _RedisBackend:
    """Redis 存储后端，使用 redis-py。"""

    def __init__(self, redis_url: str) -> None:
        try:
            import redis  # type: ignore
        except ImportError as exc:
            raise ImportError("Redis 后端需要安装 redis 包：pip install redis") from exc
        self._client = redis.from_url(redis_url)
        logger.info(f"[ExternalStateStore] 使用 Redis 后端: {redis_url}")

    def put(self, key: str, value: Any, ttl: int) -> None:
        import pickle

        self._client.setex(key, ttl, pickle.dumps(value))

    def get(self, key: str) -> Optional[Any]:
        import pickle

        raw = self._client.get(key)
        if raw is None:
            return None
        return pickle.loads(raw)  # noqa: S301

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(key))

    def cleanup_expired(self) -> int:
        # Redis 自动处理 TTL，无需手动清理
        return 0

    def size(self) -> int:
        return self._client.dbsize()


# ---------------------------------------------------------------------------
# 公开 Store 类
# ---------------------------------------------------------------------------


class ExternalStateStore:
    """
    大字段外部化存储服务。

    - ``put(session_id, field, data)`` → ``ref_key``
    - ``get(ref_key)`` → ``data | None``
    - ``delete(ref_key)`` → ``bool``
    - ``cleanup_expired()`` → 清理过期条目数量
    """

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", "")
        if redis_url:
            try:
                self._backend: _MemoryBackend | _RedisBackend = _RedisBackend(redis_url)
                logger.info("[ExternalStateStore] 初始化完成 (Redis)")
            except Exception as exc:
                logger.warning(f"[ExternalStateStore] Redis 初始化失败，回退内存存储: {exc}")
                self._backend = _MemoryBackend()
        else:
            self._backend = _MemoryBackend()
            logger.debug("[ExternalStateStore] 初始化完成 (内存)")

    # ---- 公开 API ----

    def put(self, session_id: str, field: str, data: Any) -> str:
        """
        存储大字段数据，返回 ref_key。

        Parameters
        ----------
        session_id : str
            会话 ID
        field : str
            字段名（如 ``conversation_history``）
        data : Any
            要存储的数据

        Returns
        -------
        str
            ref_key，格式为 ``{session_id}:{field}:{uuid4}``
        """
        ref_key = f"{session_id}:{field}:{uuid.uuid4().hex}"
        ttl = _get_ttl()
        self._backend.put(ref_key, data, ttl)
        logger.debug(f"[ExternalStateStore] PUT {ref_key} (ttl={ttl}s)")
        return ref_key

    def get(self, ref_key: str) -> Optional[Any]:
        """
        通过 ref_key 读取数据。

        Returns ``None`` 若 key 不存在或已过期。
        """
        data = self._backend.get(ref_key)
        if data is None:
            logger.debug(f"[ExternalStateStore] GET {ref_key} -> MISS")
        return data

    def delete(self, ref_key: str) -> bool:
        """删除指定 key，返回是否存在。"""
        ok = self._backend.delete(ref_key)
        logger.debug(f"[ExternalStateStore] DEL {ref_key} -> {'ok' if ok else 'not found'}")
        return ok

    def cleanup_expired(self) -> int:
        """手动触发过期清理（内存后端使用；Redis 后端返回 0）。"""
        return self._backend.cleanup_expired()

    def size(self) -> int:
        """返回当前存储条目数（调试用）。"""
        return self._backend.size()

    @property
    def backend_type(self) -> str:
        """返回后端类型名称。"""
        return type(self._backend).__name__.lstrip("_")


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_store_instance: Optional[ExternalStateStore] = None
_store_lock = threading.Lock()


def get_store() -> ExternalStateStore:
    """
    获取全局 ExternalStateStore 单例。

    线程安全（双检锁）。首次调用时根据环境变量自动选择后端。
    """
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                _store_instance = ExternalStateStore()
    return _store_instance


def reset_store() -> None:
    """重置全局单例（仅用于测试）。"""
    global _store_instance
    with _store_lock:
        _store_instance = None
