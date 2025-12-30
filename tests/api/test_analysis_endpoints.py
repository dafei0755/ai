"""
API端点测试 - Analysis相关端点

测试覆盖:
- POST /api/analysis/start
- GET /api/analysis/status/{session_id}
- POST /api/analysis/resume
- GET /api/analysis/result/{session_id}
- GET /api/analysis/report/{session_id}

使用pytest + httpx进行异步API测试
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch, AsyncMock
from intelligent_project_analyzer.api.server import app


@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    with patch('intelligent_project_analyzer.services.redis_session_manager.redis') as mock:
        mock_client = Mock()
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.exists.return_value = False
        mock.Redis.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_workflow():
    """Mock LangGraph workflow"""
    with patch('intelligent_project_analyzer.workflow.main_workflow.MainWorkflow') as mock:
        workflow_instance = Mock()
        workflow_instance.run_analysis = AsyncMock(return_value={
            "session_id": "test-session-123",
            "status": "completed",
            "final_result": "测试分析结果"
        })
        mock.return_value = workflow_instance
        yield workflow_instance


@pytest.mark.asyncio
async def test_start_analysis_success(mock_redis, mock_workflow):
    """测试启动分析 - 成功场景"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analysis/start",
            json={
                "requirement": "设计一个咖啡馆",
                "domain": "interior_design",
                "user_id": 1,
                "username": "test_user"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "status" in data
    assert data["status"] in ["pending", "running", "completed"]


@pytest.mark.asyncio
async def test_start_analysis_missing_requirement():
    """测试启动分析 - 缺少必需参数"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analysis/start",
            json={
                "domain": "interior_design"
                # 缺少 requirement
            }
        )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_start_analysis_empty_requirement():
    """测试启动分析 - 空需求"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analysis/start",
            json={
                "requirement": "",
                "domain": "interior_design"
            }
        )

    # 应该被输入守卫拦截或返回验证错误
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_analysis_status_not_found():
    """测试获取分析状态 - 会话不存在"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/analysis/status/nonexistent-session-id")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_analysis_status_success(mock_redis):
    """测试获取分析状态 - 成功"""
    # Mock Redis返回会话数据
    import json
    mock_redis.get.return_value = json.dumps({
        "session_id": "test-session-123",
        "status": "running",
        "progress": 0.5,
        "current_stage": "需求分析"
    }).encode('utf-8')

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/analysis/status/test-session-123")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert "status" in data


@pytest.mark.asyncio
async def test_resume_analysis_success(mock_redis, mock_workflow):
    """测试恢复分析 - 成功"""
    # Mock Redis返回已暂停的会话
    import json
    mock_redis.get.return_value = json.dumps({
        "session_id": "test-session-123",
        "status": "interrupted",
        "user_response": None
    }).encode('utf-8')

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analysis/resume",
            json={
                "session_id": "test-session-123",
                "user_response": {"answer": "确认"}
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


@pytest.mark.asyncio
async def test_get_analysis_result_success(mock_redis):
    """测试获取分析结果 - 成功"""
    import json
    mock_redis.get.return_value = json.dumps({
        "session_id": "test-session-123",
        "status": "completed",
        "final_result": "分析结果内容",
        "agent_results": {"agent1": "result1"}
    }).encode('utf-8')

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/analysis/result/test-session-123")

    assert response.status_code == 200
    data = response.json()
    assert "final_result" in data or "agent_results" in data


@pytest.mark.asyncio
async def test_get_analysis_report_success(mock_redis):
    """测试获取分析报告 - 成功"""
    import json
    mock_redis.get.return_value = json.dumps({
        "session_id": "test-session-123",
        "status": "completed",
        "report_text": "## 项目分析报告\n\n内容...",
        "pdf_path": "/path/to/report.pdf"
    }).encode('utf-8')

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/analysis/report/test-session-123")

    assert response.status_code == 200
    data = response.json()
    assert "report_text" in data or "pdf_path" in data


@pytest.mark.asyncio
async def test_api_health_check():
    """测试健康检查端点"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_root():
    """测试根路径"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data or "version" in data


@pytest.mark.asyncio
async def test_start_analysis_with_files(mock_redis, mock_workflow):
    """测试带文件的分析启动"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 模拟文件上传
        files = {
            "files": ("test.txt", b"Test file content", "text/plain")
        }
        data = {
            "requirement": "分析这个文件",
            "domain": "interior_design"
        }

        response = await client.post(
            "/api/analysis/start-with-files",
            data=data,
            files=files
        )

    # 根据实际实现，可能需要调整断言
    assert response.status_code in [200, 201]


@pytest.mark.asyncio
async def test_concurrent_analysis_requests(mock_redis, mock_workflow):
    """测试并发分析请求"""
    import asyncio

    async def start_analysis(client, index):
        return await client.post(
            "/api/analysis/start",
            json={
                "requirement": f"分析需求 {index}",
                "domain": "interior_design",
                "user_id": index
            }
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 发起10个并发请求
        tasks = [start_analysis(client, i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    # 检查大部分请求成功
    successful = [r for r in responses if not isinstance(r, Exception) and r.status_code == 200]
    assert len(successful) >= 8  # 至少80%成功率
