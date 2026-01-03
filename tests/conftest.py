"""
Pytest配置和全局fixture定义
用于延迟加载FastAPI app和提供测试依赖
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ============================================================================
# 事件循环配置
# ============================================================================

# 移除event_loop fixture，使用pytest-asyncio的默认配置


# ============================================================================
# FastAPI App Fixtures (延迟加载避免初始化问题)
# ============================================================================


@pytest.fixture(scope="function")
def app():
    """
    延迟加载FastAPI app避免测试收集时初始化
    使用此fixture避免在import阶段触发Redis/DB连接
    """
    # 在fixture内部导入，避免测试收集阶段加载
    from intelligent_project_analyzer.api import server as server_module
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    # 默认：使用内存模式 session_manager，避免测试时尝试真实 Redis 连接
    server_module.session_manager = RedisSessionManager(fallback_to_memory=True)
    server_module.session_manager._memory_mode = True
    server_module.session_manager.is_connected = False

    # Mock archive_manager to avoid None and 404s
    server_module.archive_manager = AsyncMock()
    server_module.archive_manager.count_archived_sessions.return_value = 0
    server_module.archive_manager.update_metadata.return_value = True

    async def _get_archived_session(session_id):
        if session_id == "test-1":
            return {"session_id": "test-1", "user_id": "web_user"}
        return None

    server_module.archive_manager.get_archived_session.side_effect = _get_archived_session

    server_module.archive_manager.delete_archived_session.return_value = True
    server_module.archive_manager.list_archived_sessions.return_value = []

    yield server_module.app
    # 清理逻辑（如果需要）


@pytest_asyncio.fixture(scope="function")
async def client(app):
    """
    提供异步HTTP客户端用于API测试

    使用示例:
        async def test_endpoint(client):
            response = await client.post("/api/analysis/start", json={...})
            assert response.status_code == 200
    """
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """
    Mock Redis连接

    返回一个Mock对象，模拟Redis客户端的所有方法
    """
    # 使用 AsyncMock 来模拟 redis.asyncio 客户端（RedisSessionManager 内部是 await 调用）
    mock_instance = AsyncMock()

    # 轻量内存存储：让 setex 写入的数据可以被后续 get 读到（支持 CRUD flow 测试）
    _kv_store = {}

    # 模拟常用Redis方法（异步）
    mock_instance.get.return_value = None
    mock_instance.setex.return_value = True
    mock_instance.delete.return_value = 0
    mock_instance.exists.return_value = 0
    mock_instance.expire.return_value = True
    mock_instance.ttl.return_value = -1
    mock_instance.keys.return_value = []
    mock_instance.hset.return_value = True
    mock_instance.hget.return_value = None
    mock_instance.hgetall.return_value = {}
    mock_instance.mget.return_value = []
    mock_instance.pipeline.return_value = AsyncMock()

    # redis.asyncio.lock.Lock 依赖 redis_client.register_script() 返回一个“可调用脚本对象”。
    # 如果这里是 AsyncMock，会导致 register_script 返回 coroutine，从而在 Lock 内部触发
    # "'coroutine' object is not callable"。
    def _register_script(_script_text: str):
        async def _script_callable(*args, **kwargs):
            # 这里不需要真实执行 Lua，只要返回一个可 await 的结果即可。
            return 1

        return _script_callable

    mock_instance.register_script = Mock(side_effect=_register_script)

    async def _setex(key, ttl, value):
        # 如果测试显式设置了 setex.return_value，则尊重它，但仍存储值用于后续读取
        _kv_store[key] = value
        return mock_instance.setex.return_value

    async def _get(key):
        # 如果测试显式设置了 get.return_value（非 None），优先返回该值
        if mock_instance.get.return_value is not None:
            return mock_instance.get.return_value
        return _kv_store.get(key)

    async def _delete(*keys):
        # 如果测试显式设置了 delete.return_value（非 0），优先返回该值
        if mock_instance.delete.return_value not in (0, None):
            # 同时尽量从 store 里删除，保证行为一致
            for k in keys:
                _kv_store.pop(k, None)
            return mock_instance.delete.return_value

        deleted = 0
        for k in keys:
            if k in _kv_store:
                deleted += 1
                del _kv_store[k]
        return deleted

    mock_instance.setex.side_effect = _setex
    mock_instance.get.side_effect = _get
    mock_instance.delete.side_effect = _delete

    # scan_iter 需要可 async for 的对象，这里提供一个空的 async generator
    async def _empty_scan_iter(*args, **kwargs):
        if False:
            yield None

    mock_instance.scan_iter = _empty_scan_iter

    # lock() 在 RedisSessionManager.delete 里会被调用；提供一个可 await acquire/release 的锁
    lock_mock = AsyncMock()
    lock_mock.acquire.return_value = True
    lock_mock.release.return_value = True
    # Fix: redis.lock is synchronous, so use Mock, not AsyncMock behavior
    mock_instance.lock = Mock(return_value=lock_mock)

    # 将 server.session_manager 切换到使用该 mock redis_client 的实例
    from intelligent_project_analyzer.api import server as server_module
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    server_module.session_manager = RedisSessionManager(fallback_to_memory=True)
    server_module.session_manager.redis_client = mock_instance
    server_module.session_manager._memory_mode = False
    server_module.session_manager.is_connected = True

    yield mock_instance


@pytest.fixture
def mock_llm():
    """
    Mock LLM (Language Model)

    模拟LLM的响应，避免实际API调用
    """
    with patch("intelligent_project_analyzer.services.llm_factory.LLMFactory") as mock_llm_class:
        mock_instance = AsyncMock()

        # 模拟LLM响应
        mock_instance.ainvoke.return_value = {"content": "这是一个模拟的LLM响应", "role": "assistant"}
        mock_instance.invoke.return_value = "Mock LLM response"

        mock_llm_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_workflow():
    """
    Mock 主工作流

    模拟工作流执行结果
    """
    # The FastAPI endpoints schedule `run_workflow_async(...)` via BackgroundTasks.
    # Patch it to a no-op so tests don't execute the full LangGraph workflow.
    from intelligent_project_analyzer.api import server as server_module

    mock_run = AsyncMock(return_value=None)
    with patch.object(server_module, "run_workflow_async", mock_run):
        yield mock_run


@pytest.fixture
def mock_tavily():
    """
    Mock Tavily搜索工具
    """
    with patch("intelligent_project_analyzer.tools.tavily_search.TavilyClient") as mock_tavily_class:
        mock_instance = Mock()

        # 模拟搜索结果
        mock_instance.search.return_value = {
            "results": [{"title": "搜索结果1", "url": "https://example.com/1", "content": "这是搜索结果内容", "score": 0.95}],
            "query": "测试查询",
        }

        mock_tavily_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_session_manager():
    """
    Mock Redis会话管理器
    """
    with patch("intelligent_project_analyzer.services.redis_session_manager.RedisSessionManager") as mock_class:
        mock_instance = AsyncMock()

        # 模拟会话管理器方法
        mock_instance.create.return_value = "test-session-123"
        mock_instance.get.return_value = {
            "session_id": "test-session-123",
            "user_input": "测试需求",
            "created_at": "2025-12-30T20:00:00",
            "status": "active",
        }
        mock_instance.delete.return_value = True
        mock_instance.update.return_value = True

        mock_class.return_value = mock_instance
        yield mock_instance


# ============================================================================
# 测试数据Fixtures
# ============================================================================


@pytest.fixture
def sample_requirement():
    """提供测试用的需求示例"""
    return {
        "requirement": "设计一个200平米的现代简约风格办公空间，需要包含开放办公区、会议室和休息区",
        "budget": "50-100万",
        "timeline": "3个月",
        "constraints": ["采光要好", "隔音效果好"],
    }


@pytest.fixture
def sample_session_data():
    """提供测试用的会话数据"""
    return {
        "session_id": "test-session-123",
        "device_id": "test-device-456",
        "user_input": "设计智能家居系统",
        "created_at": "2025-12-30T20:00:00",
        "status": "active",
        "agent_results": [],
    }


@pytest.fixture
def sample_analysis_result():
    """提供测试用的分析结果"""
    return {
        "session_id": "test-session-123",
        "analysis_complete": True,
        "agent_results": [
            {
                "agent_name": "requirements_analyst",
                "result": {
                    "requirement_type": "interior_design",
                    "complexity": "medium",
                    "dimensions": ["space_planning", "lighting", "materials"],
                },
                "confidence": 0.92,
                "execution_time": 2.5,
            },
            {
                "agent_name": "feasibility_analyst",
                "result": {
                    "feasibility_score": 0.85,
                    "challenges": ["预算可能偏紧", "时间安排需优化"],
                    "recommendations": ["考虑分期实施", "优化材料选择"],
                },
                "confidence": 0.88,
                "execution_time": 1.8,
            },
        ],
        "final_report": {
            "summary": "项目可行性良好，建议分期实施以控制成本",
            "overall_score": 0.87,
            "next_steps": ["确认预算", "细化设计方案", "选择施工团队"],
        },
    }


# ============================================================================
# 环境配置Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """
    自动设置测试环境变量
    autouse=True 表示自动应用于所有测试
    """
    # 设置测试环境 - 使用'dev'而不是'test'，因为Settings只接受dev/staging/prod
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("REDIS_DB", "15")  # 使用测试专用Redis DB
    monkeypatch.setenv("ENABLE_TENCENT_CONTENT_SAFETY", "false")  # 禁用外部API

    # 设置Mock API密钥（避免加载真实密钥）
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-placeholder")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")

    yield

    # 清理（pytest会自动清理monkeypatch）


@pytest.fixture
def temp_dir(tmp_path):
    """提供临时目录用于文件操作测试"""
    return tmp_path


# ============================================================================
# 标记(Markers)配置
# ============================================================================


def pytest_configure(config):
    """注册自定义pytest标记"""
    config.addinivalue_line("markers", "slow: 标记慢速测试 (运行时间>5秒)")
    config.addinivalue_line("markers", "integration: 标记集成测试 (需要外部依赖)")
    config.addinivalue_line("markers", "unit: 标记单元测试 (不依赖外部服务)")
    config.addinivalue_line("markers", "api: 标记API端点测试")
    config.addinivalue_line("markers", "workflow: 标记工作流测试")


# ============================================================================
# 测试会话钩子
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """
    修改测试收集项
    自动为async测试添加asyncio标记
    """
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
