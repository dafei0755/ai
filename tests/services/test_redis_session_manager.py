"""
Services模块测试 - Redis Session Manager

测试Redis会话管理器的核心功能
"""

import pytest
from unittest.mock import Mock, patch
import json
import time


@pytest.fixture
def redis_manager():
    """创建真实的RedisSessionManager实例用于测试"""
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    manager = RedisSessionManager()

    # 使用测试专用DB
    manager.redis_client.select(15)

    yield manager

    # 清理测试数据
    manager.redis_client.flushdb()


def test_save_state_success(redis_manager):
    """测试保存会话状态 - 成功"""
    session_id = "test-save-123"
    state = {
        "requirement": "测试需求",
        "status": "running",
        "progress": 0.5
    }

    result = redis_manager.save_state(session_id, state)

    assert result is True

    # 验证数据已保存
    saved_data = redis_manager.load_state(session_id)
    assert saved_data is not None
    assert saved_data["requirement"] == "测试需求"
    assert saved_data["status"] == "running"


def test_load_state_success(redis_manager):
    """测试加载会话状态 - 成功"""
    session_id = "test-load-123"
    state = {"key": "value", "number": 42}

    # 先保存
    redis_manager.save_state(session_id, state)

    # 再加载
    loaded_state = redis_manager.load_state(session_id)

    assert loaded_state is not None
    assert loaded_state["key"] == "value"
    assert loaded_state["number"] == 42


def test_load_state_not_found(redis_manager):
    """测试加载不存在的会话"""
    loaded_state = redis_manager.load_state("nonexistent-session")

    assert loaded_state is None


def test_delete_state_success(redis_manager):
    """测试删除会话状态 - 成功"""
    session_id = "test-delete-123"
    state = {"data": "to be deleted"}

    # 先保存
    redis_manager.save_state(session_id, state)
    assert redis_manager.load_state(session_id) is not None

    # 再删除
    result = redis_manager.delete_state(session_id)
    assert result is True

    # 验证已删除
    assert redis_manager.load_state(session_id) is None


def test_exists_check(redis_manager):
    """测试会话存在性检查"""
    session_id = "test-exists-123"

    # 初始不存在
    assert redis_manager.exists(session_id) is False

    # 保存后存在
    redis_manager.save_state(session_id, {"data": "test"})
    assert redis_manager.exists(session_id) is True

    # 删除后不存在
    redis_manager.delete_state(session_id)
    assert redis_manager.exists(session_id) is False


def test_list_sessions(redis_manager):
    """测试列出所有会话"""
    # 创建多个会话
    for i in range(5):
        redis_manager.save_state(f"test-list-{i}", {"index": i})

    sessions = redis_manager.list_sessions()

    assert len(sessions) >= 5
    assert any("test-list-" in s for s in sessions)


def test_state_ttl_expiration(redis_manager):
    """测试会话TTL过期"""
    session_id = "test-ttl-123"
    state = {"data": "expires soon"}

    # 保存带TTL的状态（1秒）
    redis_manager.save_state(session_id, state, ttl=1)

    # 立即读取应该存在
    assert redis_manager.load_state(session_id) is not None

    # 等待过期
    time.sleep(2)

    # 应该已过期
    assert redis_manager.load_state(session_id) is None


def test_update_state(redis_manager):
    """测试更新会话状态"""
    session_id = "test-update-123"

    # 初始状态
    initial_state = {"status": "pending", "progress": 0.0}
    redis_manager.save_state(session_id, initial_state)

    # 更新状态
    updated_state = {"status": "running", "progress": 0.5}
    redis_manager.save_state(session_id, updated_state)

    # 验证更新后的状态
    loaded_state = redis_manager.load_state(session_id)
    assert loaded_state["status"] == "running"
    assert loaded_state["progress"] == 0.5


def test_concurrent_access(redis_manager):
    """测试并发访问安全性"""
    import threading

    session_id = "test-concurrent-123"
    counter = {"value": 0}

    def increment_counter():
        for _ in range(10):
            state = redis_manager.load_state(session_id) or {"count": 0}
            state["count"] = state.get("count", 0) + 1
            redis_manager.save_state(session_id, state)

    # 创建多个线程并发访问
    threads = [threading.Thread(target=increment_counter) for _ in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # 验证最终状态（可能有竞态条件，但不应崩溃）
    final_state = redis_manager.load_state(session_id)
    assert final_state is not None
    assert "count" in final_state


def test_large_state_storage(redis_manager):
    """测试大数据状态存储"""
    session_id = "test-large-123"

    # 创建大量数据
    large_state = {
        "agent_results": {f"agent_{i}": f"result_{i}" * 100 for i in range(100)},
        "metadata": {"key": "value"} * 50
    }

    # 保存大数据
    result = redis_manager.save_state(session_id, large_state)
    assert result is True

    # 加载并验证
    loaded_state = redis_manager.load_state(session_id)
    assert loaded_state is not None
    assert len(loaded_state["agent_results"]) == 100


def test_special_characters_in_data(redis_manager):
    """测试特殊字符处理"""
    session_id = "test-special-123"

    state = {
        "chinese": "中文内容测试",
        "emoji": "🎉✨🚀",
        "special": "\"quotes\" and 'apostrophes'",
        "unicode": "\u4e2d\u6587"
    }

    redis_manager.save_state(session_id, state)
    loaded_state = redis_manager.load_state(session_id)

    assert loaded_state["chinese"] == "中文内容测试"
    assert loaded_state["emoji"] == "🎉✨🚀"
    assert loaded_state["special"] == "\"quotes\" and 'apostrophes'"


def test_nested_data_structure(redis_manager):
    """测试嵌套数据结构"""
    session_id = "test-nested-123"

    state = {
        "level1": {
            "level2": {
                "level3": {
                    "data": "deep nested value"
                }
            },
            "array": [1, 2, [3, 4, [5, 6]]]
        }
    }

    redis_manager.save_state(session_id, state)
    loaded_state = redis_manager.load_state(session_id)

    assert loaded_state["level1"]["level2"]["level3"]["data"] == "deep nested value"
    assert loaded_state["level1"]["array"][2][2][1] == 6


@pytest.mark.parametrize("session_id,state", [
    ("test-1", {"status": "pending"}),
    ("test-2", {"status": "running", "progress": 0.5}),
    ("test-3", {"status": "completed", "result": "success"}),
])
def test_multiple_sessions(redis_manager, session_id, state):
    """测试多个会话的独立性"""
    redis_manager.save_state(session_id, state)
    loaded_state = redis_manager.load_state(session_id)

    assert loaded_state == state
