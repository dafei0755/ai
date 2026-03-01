"""
MT-4: WebSocket 断线重连事件补偿 E2E 测试

测试内容
--------
1. EventStore 基本 append / get_after / cleanup 功能
2. broadcast_to_websockets 钩子写入 EventStore
3. 事件回放 API 端点（模拟）
4. 重连后遗漏事件补偿
5. seq 单调递增 & 去重校验
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from intelligent_project_analyzer.services.event_store import (
    EventStore,
    _MemoryEventBackend,
    get_event_store,
    reset_event_store,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_store():
    reset_event_store()
    yield
    reset_event_store()


@pytest.fixture(autouse=True)
def force_memory_backend(monkeypatch):
    """强制使用内存后端，避免 Redis 跨测试污染。"""
    monkeypatch.delenv("REDIS_URL", raising=False)


@pytest.fixture()
def store() -> EventStore:
    """内存后端 EventStore 实例（依赖 force_memory_backend autouse fixture）。"""
    return EventStore()


# ===========================================================================
# [1] _MemoryEventBackend 内部操作
# ===========================================================================


class TestMemoryEventBackend:
    @pytest.mark.asyncio
    async def test_append_returns_incrementing_seq(self):
        b = _MemoryEventBackend()
        s1 = await b.append("sess", {"type": "A"})
        s2 = await b.append("sess", {"type": "B"})
        s3 = await b.append("sess", {"type": "C"})
        assert s1 == 1
        assert s2 == 2
        assert s3 == 3

    @pytest.mark.asyncio
    async def test_append_separate_sessions_independent(self):
        b = _MemoryEventBackend()
        s1 = await b.append("s1", {})
        s2 = await b.append("s2", {})
        assert s1 == 1
        assert s2 == 1  # 各 session 独立

    @pytest.mark.asyncio
    async def test_get_after_returns_events_after_seq(self):
        b = _MemoryEventBackend()
        for i in range(5):
            await b.append("sess", {"val": i})
        events = await b.get_after("sess", 2)
        assert len(events) == 3
        assert [e["seq"] for e in events] == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_get_after_0_returns_all(self):
        b = _MemoryEventBackend()
        for i in range(3):
            await b.append("sess", {"val": i})
        events = await b.get_after("sess", 0)
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_get_after_missing_session_returns_empty(self):
        b = _MemoryEventBackend()
        events = await b.get_after("nonexistent", 0)
        assert events == []

    @pytest.mark.asyncio
    async def test_cleanup_session_removes_events(self):
        b = _MemoryEventBackend()
        await b.append("sess", {})
        await b.cleanup_session("sess")
        events = await b.get_after("sess", 0)
        assert events == []
        # seq counter 也应重置
        s = await b.append("sess", {})
        assert s == 1

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        import os

        with patch.dict(os.environ, {"EVENT_STORE_TTL_SECONDS": "0"}):
            b = _MemoryEventBackend()
            await b.append("sess", {"type": "test"})
        await asyncio.sleep(0.02)
        events = await b.get_after("sess", 0)
        assert events == []

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        import os

        with patch.dict(os.environ, {"EVENT_STORE_TTL_SECONDS": "0"}):
            b = _MemoryEventBackend()
            await b.append("sess", {})
        await asyncio.sleep(0.02)
        cleaned = await b.cleanup_expired()
        assert cleaned >= 1


# ===========================================================================
# [2] EventStore 公开 API
# ===========================================================================


class TestEventStore:
    @pytest.mark.asyncio
    async def test_append_and_get_after(self, store):
        await store.append("sess", {"type": "progress", "step": 1})
        await store.append("sess", {"type": "progress", "step": 2})
        events = await store.get_after("sess", 0)
        assert len(events) == 2
        assert events[0]["payload"]["step"] == 1
        assert events[1]["payload"]["step"] == 2

    @pytest.mark.asyncio
    async def test_events_sorted_by_seq(self, store):
        for i in range(5):
            await store.append("sess", {"idx": i})
        events = await store.get_after("sess", 0)
        seqs = [e["seq"] for e in events]
        assert seqs == sorted(seqs)

    @pytest.mark.asyncio
    async def test_event_contains_required_fields(self, store):
        await store.append("sess", {"type": "test"})
        events = await store.get_after("sess", 0)
        e = events[0]
        assert "seq" in e
        assert "session_id" in e
        assert "timestamp" in e
        assert "payload" in e
        assert e["session_id"] == "sess"

    @pytest.mark.asyncio
    async def test_cleanup_session(self, store):
        await store.append("sess", {})
        await store.cleanup_session("sess")
        assert await store.get_after("sess", 0) == []


# ===========================================================================
# [3] broadcast_to_websockets 钩子
# ===========================================================================


class TestBroadcastHook:
    @pytest.mark.asyncio
    async def test_broadcast_writes_to_event_store(self):
        """broadcast_to_websockets 调用时，消息应自动写入 EventStore。"""
        from intelligent_project_analyzer.api import workflow_runner as wr

        # Mock _server 使其无连接（只触发 event_store 写入逻辑）
        mock_server = MagicMock()
        mock_server.redis_pubsub_client = None
        mock_server.websocket_connections = {}
        with patch.object(wr, "_server", mock_server):
            test_msg = {"type": "analysis_update", "data": "hello"}
            await wr.broadcast_to_websockets("sess-broadcast-test", test_msg)

        events = await get_event_store().get_after("sess-broadcast-test", 0)
        assert len(events) == 1
        assert events[0]["payload"]["type"] == "analysis_update"

    @pytest.mark.asyncio
    async def test_multiple_broadcasts_increment_seq(self):
        from intelligent_project_analyzer.api import workflow_runner as wr

        mock_server = MagicMock()
        mock_server.redis_pubsub_client = None
        mock_server.websocket_connections = {}
        with patch.object(wr, "_server", mock_server):
            for i in range(3):
                await wr.broadcast_to_websockets("sess-seq", {"step": i})

        events = await get_event_store().get_after("sess-seq", 0)
        assert len(events) == 3
        assert [e["seq"] for e in events] == [1, 2, 3]


# ===========================================================================
# [4] 事件回放场景：断线重连
# ===========================================================================


class TestReconnectScenario:
    @pytest.mark.asyncio
    async def test_missed_events_recoverable(self, store):
        """模拟断线场景：客户端在 seq=2 时断线，重连后补回 seq=3,4,5。"""
        sid = "reconnect-test-1"
        for i in range(5):
            await store.append(sid, {"idx": i})

        # 客户端断线前收到 seq 1,2
        last_received_seq = 2
        missed = await store.get_after(sid, last_received_seq)
        assert len(missed) == 3
        assert [e["seq"] for e in missed] == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_no_duplicate_events_on_reconnect(self, store):
        """重连补偿不应返回已收到的事件。"""
        sid = "reconnect-test-2"
        for i in range(10):
            await store.append(sid, {"idx": i})

        # 客户端已收到前 7 个
        missed = await store.get_after(sid, 7)
        assert len(missed) == 3
        assert missed[0]["seq"] == 8

    @pytest.mark.asyncio
    async def test_fresh_connect_seq_0_gets_all(self, store):
        """全新连接（seq=0）应获取全部历史事件。"""
        sid = "reconnect-test-3"
        for i in range(4):
            await store.append(sid, {})
        all_events = await store.get_after(sid, 0)
        assert len(all_events) == 4


# ===========================================================================
# [5] 全局单例
# ===========================================================================


def test_singleton():
    s1 = get_event_store()
    s2 = get_event_store()
    assert s1 is s2


def test_reset():
    s1 = get_event_store()
    reset_event_store()
    s2 = get_event_store()
    assert s1 is not s2
