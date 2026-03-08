"""
Unit tests for ExternalStateStore (MT-3)

Coverage
--------
- put / get / delete 基本功能
- TTL 过期回收
- 内存后端并发安全（粗测）
- Redis 后端降级（无 REDIS_URL 时使用内存）
- 全局单例线程安全
- 有界 reducer _bounded_add_messages / _bounded_merge_lists
- State 初始化含 ref 字段
"""
from __future__ import annotations

import os
import time
import threading
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from intelligent_project_analyzer.services.external_state_store import (
    ExternalStateStore,
    _MemoryBackend,
    get_store,
    reset_store,
)
from intelligent_project_analyzer.core.state import (
    _bounded_add_messages,
    _bounded_merge_lists,
    StateManager,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """每个测试前后重置全局单例，避免交叉污染。"""
    reset_store()
    yield
    reset_store()


@pytest.fixture()
def mem_store() -> ExternalStateStore:
    """无 REDIS_URL 的内存后端存储实例。"""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("REDIS_URL", None)
        yield ExternalStateStore()


# ===========================================================================
# [1] 内存后端基本功能
# ===========================================================================


class TestMemoryBackend:
    def test_put_and_get(self):
        b = _MemoryBackend()
        b.put("k1", [1, 2, 3], ttl=60)
        assert b.get("k1") == [1, 2, 3]

    def test_get_miss_returns_none(self):
        b = _MemoryBackend()
        assert b.get("nonexistent") is None

    def test_delete_existing(self):
        b = _MemoryBackend()
        b.put("k2", "hello", ttl=60)
        assert b.delete("k2") is True
        assert b.get("k2") is None

    def test_delete_nonexistent_returns_false(self):
        b = _MemoryBackend()
        assert b.delete("ghost") is False

    def test_ttl_expiry(self):
        b = _MemoryBackend()
        b.put("k3", "bye", ttl=0)  # 立即过期
        time.sleep(0.01)
        assert b.get("k3") is None

    def test_cleanup_expired(self):
        b = _MemoryBackend()
        b.put("k4", "x", ttl=0)
        b.put("k5", "y", ttl=3600)
        time.sleep(0.01)
        cleaned = b.cleanup_expired()
        assert cleaned == 1
        assert b.size() == 1

    def test_size(self):
        b = _MemoryBackend()
        assert b.size() == 0
        b.put("a", 1, ttl=60)
        b.put("b", 2, ttl=60)
        assert b.size() == 2


# ===========================================================================
# [2] ExternalStateStore 公开 API
# ===========================================================================


class TestExternalStateStore:
    def test_put_returns_ref_key(self, mem_store):
        ref = mem_store.put("sess-001", "conversation_history", ["msg1"])
        assert "sess-001" in ref
        assert "conversation_history" in ref

    def test_get_after_put(self, mem_store):
        data = {"key": "value", "nested": [1, 2, 3]}
        ref = mem_store.put("sess-002", "agent_results", data)
        retrieved = mem_store.get(ref)
        assert retrieved == data

    def test_get_missing_key(self, mem_store):
        assert mem_store.get("sess-xyz:field:nonexistent") is None

    def test_delete(self, mem_store):
        ref = mem_store.put("sess-003", "interaction_history", [1])
        assert mem_store.delete(ref) is True
        assert mem_store.get(ref) is None

    def test_ref_keys_are_unique(self, mem_store):
        r1 = mem_store.put("s", "f", [])
        r2 = mem_store.put("s", "f", [])
        assert r1 != r2

    def test_backend_type_memory(self, mem_store):
        assert mem_store.backend_type == "MemoryBackend"

    def test_cleanup_expired(self, mem_store):
        with patch.dict(os.environ, {"EXTERNAL_STORE_TTL_SECONDS": "0"}):
            ref = mem_store.put("sess", "f", "data")
        time.sleep(0.01)
        cleaned = mem_store.cleanup_expired()
        assert cleaned >= 1
        assert mem_store.get(ref) is None


# ===========================================================================
# [3] 全局单例
# ===========================================================================


class TestSingleton:
    def test_get_store_returns_same_instance(self):
        s1 = get_store()
        s2 = get_store()
        assert s1 is s2

    def test_reset_allows_new_instance(self):
        s1 = get_store()
        reset_store()
        s2 = get_store()
        assert s1 is not s2

    def test_thread_safety(self):
        """多线程同时调用 get_store() 应返回同一实例。"""
        instances: list = []
        lock = threading.Lock()

        def _worker():
            inst = get_store()
            with lock:
                instances.append(inst)

        threads = [threading.Thread(target=_worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert all(x is instances[0] for x in instances)


# ===========================================================================
# [4] 有界 reducer
# ===========================================================================


class TestBoundedAddMessages:
    def _msgs(self, n: int):
        result = []
        for i in range(n):
            result += [HumanMessage(content=f"q{i}"), AIMessage(content=f"a{i}")]
        return result

    def test_below_max_no_truncation(self):
        msgs = self._msgs(10)  # 20 条
        result = _bounded_add_messages([], msgs)
        assert len(result) == 20

    def test_at_max_no_truncation(self):
        with patch.dict(os.environ, {"CONVERSATION_HISTORY_MAX": "20"}):
            msgs = self._msgs(10)  # 20 条
            result = _bounded_add_messages([], msgs)
            assert len(result) == 20

    def test_above_max_truncates(self):
        with patch.dict(os.environ, {"CONVERSATION_HISTORY_MAX": "10"}):
            # 先放 5 轮（10 条），再追加 3 轮（6 条），共 16 → 截至 10
            history = []
            for i in range(8):  # 逐轮追加，确保 add_messages 不去重
                history = _bounded_add_messages(
                    history,
                    [HumanMessage(content=f"q{i}"), AIMessage(content=f"a{i}")],
                )
            assert len(history) == 10
            # 最新消息应为第 7 轮 (i=7)
            assert history[-1].content == "a7"

    def test_incremental_growth_bounded(self):
        with patch.dict(os.environ, {"CONVERSATION_HISTORY_MAX": "6"}):
            history = []
            for i in range(10):
                history = _bounded_add_messages(history, [HumanMessage(content=f"q{i}")])
            assert len(history) <= 6


class TestBoundedMergeLists:
    def test_below_max_no_truncation(self):
        with patch.dict(os.environ, {"INTERACTION_HISTORY_MAX": "10"}):
            result = _bounded_merge_lists(list(range(5)), list(range(5, 8)))
            assert len(result) == 8

    def test_above_max_truncates(self):
        with patch.dict(os.environ, {"INTERACTION_HISTORY_MAX": "5"}):
            existing = list(range(4))
            new_items = list(range(10, 14))
            result = _bounded_merge_lists(existing, new_items)
            assert len(result) == 5

    def test_deduplication_still_works(self):
        with patch.dict(os.environ, {"INTERACTION_HISTORY_MAX": "100"}):
            result = _bounded_merge_lists([1, 2, 3], [2, 3, 4])
            assert result == [1, 2, 3, 4]


# ===========================================================================
# [5] State 初始化含 ref 字段
# ===========================================================================


class TestStateRefFields:
    def test_initial_state_has_ref_fields(self):
        state = StateManager.create_initial_state("测试输入", "sess-test")
        assert "conversation_history_ref" in state
        assert state["conversation_history_ref"] is None
        assert "interaction_history_ref" in state
        assert state["interaction_history_ref"] is None

    def test_initial_conversation_history_empty(self):
        state = StateManager.create_initial_state("测试输入", "sess-test")
        assert state["conversation_history"] == []
        assert state["interaction_history"] == []
