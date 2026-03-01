"""
WebSocket 事件存储服务 (MT-4)

为断线重连提供事件补偿支持。每次 WebSocket 广播消息时，
同步写入本服务；客户端重连后可通过 ``after_seq`` 获取断线期间的遗漏事件。

设计
----
- 内存存储（进程内，单实例场景）
- Redis 后端（设置 REDIS_URL 时，支持多实例部署）
- 事件自动过期（EVENT_STORE_TTL_SECONDS，默认 3600s = 1h）
- 每个 session 独立的自增 seq（从 1 开始）
- 线程 / 协程安全（asyncio.Lock）

事件结构
--------
::

    {
        "seq": 1,
        "session_id": "xxx",
        "timestamp": 1700000000.0,
        "payload": {...}  # 原始 WS message dict
    }
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


def _get_ttl() -> float:
    try:
        return float(os.getenv("EVENT_STORE_TTL_SECONDS", "3600"))
    except ValueError:
        return 3600.0


# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------

WSEvent = Dict[str, Any]  # keys: seq, session_id, timestamp, payload


# ---------------------------------------------------------------------------
# 内存后端
# ---------------------------------------------------------------------------


class _MemoryEventBackend:
    """内存事件后端（单实例）。"""

    def __init__(self) -> None:
        # session_id -> List[(expires_at, WSEvent)]
        self._events: Dict[str, List[tuple[float, WSEvent]]] = {}
        self._seq_counter: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def append(self, session_id: str, payload: Dict[str, Any]) -> int:
        async with self._lock:
            self._seq_counter.setdefault(session_id, 0)
            self._seq_counter[session_id] += 1
            seq = self._seq_counter[session_id]
            event: WSEvent = {
                "seq": seq,
                "session_id": session_id,
                "timestamp": time.time(),
                "payload": payload,
            }
            expires_at = time.time() + _get_ttl()
            self._events.setdefault(session_id, []).append((expires_at, event))
            return seq

    async def get_after(self, session_id: str, after_seq: int) -> List[WSEvent]:
        now = time.time()
        async with self._lock:
            raw = self._events.get(session_id, [])
            # 过滤过期 + seq > after_seq
            return [e for exp, e in raw if now <= exp and e["seq"] > after_seq]

    async def cleanup_session(self, session_id: str) -> None:
        async with self._lock:
            self._events.pop(session_id, None)
            self._seq_counter.pop(session_id, None)

    async def cleanup_expired(self) -> int:
        now = time.time()
        total = 0
        async with self._lock:
            for sid in list(self._events.keys()):
                before = len(self._events[sid])
                self._events[sid] = [(exp, e) for exp, e in self._events[sid] if now <= exp]
                total += before - len(self._events[sid])
                if not self._events[sid]:
                    del self._events[sid]
        return total

    def size(self) -> int:
        return sum(len(v) for v in self._events.values())


# ---------------------------------------------------------------------------
# Redis 后端（可选）
# ---------------------------------------------------------------------------


class _RedisEventBackend:
    """Redis 事件后端（多实例部署）。"""

    def __init__(self, redis_url: str) -> None:
        try:
            import redis.asyncio as aioredis  # type: ignore
        except ImportError as exc:
            raise ImportError("Redis 后端需要 redis[asyncio] 包") from exc
        self._client = aioredis.from_url(redis_url)

    def _key(self, session_id: str) -> str:
        return f"ws_events:{session_id}"

    def _seq_key(self, session_id: str) -> str:
        return f"ws_events_seq:{session_id}"

    async def append(self, session_id: str, payload: Dict[str, Any]) -> int:
        import json

        ttl = int(_get_ttl())
        seq: int = await self._client.incr(self._seq_key(session_id))
        await self._client.expire(self._seq_key(session_id), ttl)
        event: WSEvent = {
            "seq": seq,
            "session_id": session_id,
            "timestamp": time.time(),
            "payload": payload,
        }
        pipe = self._client.pipeline()
        pipe.rpush(self._key(session_id), json.dumps(event, ensure_ascii=False))
        pipe.expire(self._key(session_id), ttl)
        await pipe.execute()
        return seq

    async def get_after(self, session_id: str, after_seq: int) -> List[WSEvent]:
        import json

        raw = await self._client.lrange(self._key(session_id), 0, -1)
        result: List[WSEvent] = []
        for item in raw:
            e: WSEvent = json.loads(item)
            if e["seq"] > after_seq:
                result.append(e)
        return result

    async def cleanup_session(self, session_id: str) -> None:
        await self._client.delete(self._key(session_id), self._seq_key(session_id))

    async def cleanup_expired(self) -> int:
        # Redis 自动 TTL
        return 0

    def size(self) -> int:
        return 0  # 不实现（无需 benchmark）


# ---------------------------------------------------------------------------
# 公开服务类
# ---------------------------------------------------------------------------


class EventStore:
    """
    WebSocket 事件序列存储。

    - ``append(session_id, payload)`` → ``seq``  （异步）
    - ``get_after(session_id, after_seq)`` → ``List[WSEvent]``  （异步）
    - ``cleanup_session(session_id)``  （异步）
    """

    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", "")
        if redis_url:
            try:
                self._backend: _MemoryEventBackend | _RedisEventBackend = _RedisEventBackend(redis_url)
            except Exception:
                self._backend = _MemoryEventBackend()
        else:
            self._backend = _MemoryEventBackend()

    async def append(self, session_id: str, payload: Dict[str, Any]) -> int:
        """写入事件，返回 seq。"""
        return await self._backend.append(session_id, payload)

    async def get_after(self, session_id: str, after_seq: int) -> List[WSEvent]:
        """返回 seq > after_seq 的全部事件（按 seq 升序）。"""
        events = await self._backend.get_after(session_id, after_seq)
        return sorted(events, key=lambda e: e["seq"])

    async def cleanup_session(self, session_id: str) -> None:
        """清除会话的全部事件（会话结束时调用）。"""
        await self._backend.cleanup_session(session_id)

    async def cleanup_expired(self) -> int:
        """清除过期事件（内存后端定期调用）。"""
        return await self._backend.cleanup_expired()

    def size(self) -> int:
        return self._backend.size()

    @property
    def backend_type(self) -> str:
        return type(self._backend).__name__.lstrip("_")


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_store_instance: Optional[EventStore] = None


def get_event_store() -> EventStore:
    """获取全局 EventStore 单例（懒初始化）。"""
    global _store_instance
    if _store_instance is None:
        _store_instance = EventStore()
    return _store_instance


def reset_event_store() -> None:
    """重置单例（仅供测试）。"""
    global _store_instance
    _store_instance = None
