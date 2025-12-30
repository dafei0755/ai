"""
Pytest配置和全局fixture定义
用于延迟加载FastAPI app和提供测试依赖
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import AsyncGenerator, Generator
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


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
    from intelligent_project_analyzer.api.server import app as _app
    yield _app
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
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
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
    with patch('redis.Redis') as mock_redis_class:
        mock_instance = Mock()

        # 模拟常用Redis方法
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = True
        mock_instance.exists.return_value = False
        mock_instance.expire.return_value = True
        mock_instance.ttl.return_value = -1
        mock_instance.keys.return_value = []
        mock_instance.hset.return_value = True
        mock_instance.hget.return_value = None
        mock_instance.hgetall.return_value = {}

        mock_redis_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_llm():
    """
    Mock LLM (Language Model)

    模拟LLM的响应，避免实际API调用
    """
    with patch('intelligent_project_analyzer.services.llm_factory.LLMFactory') as mock_llm_class:
        mock_instance = AsyncMock()

        # 模拟LLM响应
        mock_instance.ainvoke.return_value = {
            "content": "这是一个模拟的LLM响应",
            "role": "assistant"
        }
        mock_instance.invoke.return_value = "Mock LLM response"

        mock_llm_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_workflow():
    """
    Mock 主工作流

    模拟工作流执行结果
    """
    with patch('intelligent_project_analyzer.workflow.main_workflow.create_workflow_graph') as mock_workflow_func:
        mock_graph = AsyncMock()

        # 模拟工作流执行结果
        mock_graph.ainvoke.return_value = {
            "session_id": "test-session-123",
            "user_input": "测试需求",
            "analysis_complete": True,
            "agent_results": [
                {
                    "agent_name": "requirements_analyst",
                    "result": "需求分析完成",
                    "confidence": 0.95
                }
            ],
            "final_report": {
                "summary": "分析报告摘要",
                "recommendations": ["建议1", "建议2"]
            }
        }

        mock_workflow_func.return_value = mock_graph
        yield mock_graph


@pytest.fixture
def mock_tavily():
    """
    Mock Tavily搜索工具
    """
    with patch('intelligent_project_analyzer.tools.tavily_search.TavilyClient') as mock_tavily_class:
        mock_instance = Mock()

        # 模拟搜索结果
        mock_instance.search.return_value = {
            "results": [
                {
                    "title": "搜索结果1",
                    "url": "https://example.com/1",
                    "content": "这是搜索结果内容",
                    "score": 0.95
                }
            ],
            "query": "测试查询"
        }

        mock_tavily_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_session_manager():
    """
    Mock Redis会话管理器
    """
    with patch('intelligent_project_analyzer.services.redis_session_manager.RedisSessionManager') as mock_class:
        mock_instance = AsyncMock()

        # 模拟会话管理器方法
        mock_instance.create.return_value = "test-session-123"
        mock_instance.get.return_value = {
            "session_id": "test-session-123",
            "user_input": "测试需求",
            "created_at": "2025-12-30T20:00:00",
            "status": "active"
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
        "constraints": ["采光要好", "隔音效果好"]
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
        "agent_results": []
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
                    "dimensions": ["space_planning", "lighting", "materials"]
                },
                "confidence": 0.92,
                "execution_time": 2.5
            },
            {
                "agent_name": "feasibility_analyst",
                "result": {
                    "feasibility_score": 0.85,
                    "challenges": ["预算可能偏紧", "时间安排需优化"],
                    "recommendations": ["考虑分期实施", "优化材料选择"]
                },
                "confidence": 0.88,
                "execution_time": 1.8
            }
        ],
        "final_report": {
            "summary": "项目可行性良好，建议分期实施以控制成本",
            "overall_score": 0.87,
            "next_steps": ["确认预算", "细化设计方案", "选择施工团队"]
        }
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
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试 (运行时间>5秒)"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试 (需要外部依赖)"
    )
    config.addinivalue_line(
        "markers", "unit: 标记单元测试 (不依赖外部服务)"
    )
    config.addinivalue_line(
        "markers", "api: 标记API端点测试"
    )
    config.addinivalue_line(
        "markers", "workflow: 标记工作流测试"
    )


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
