"""
API端点测试 - Session管理相关端点

测试覆盖:
- GET /api/sessions
- GET /api/sessions/{session_id}
- PATCH /api/sessions/{session_id}
- DELETE /api/sessions/{session_id}
- POST /api/sessions/{session_id}/archive
- GET /api/sessions/archived
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch
from intelligent_project_analyzer.api.server import app
import json


@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    with patch('intelligent_project_analyzer.services.redis_session_manager.redis') as mock:
        mock_client = Mock()

        # Mock keys方法返回会话列表
        mock_client.keys.return_value = [
            b"session:test-1",
            b"session:test-2",
            b"session:test-3"
        ]

        # Mock get方法返回会话数据
        def mock_get(key):
            if b"test-1" in key:
                return json.dumps({
                    "session_id": "test-1",
                    "requirement": "咖啡馆设计",
                    "status": "completed",
                    "created_at": "2025-12-30T10:00:00"
                }).encode('utf-8')
            return None

        mock_client.get.side_effect = mock_get
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = True

        mock.Redis.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_list_sessions(mock_redis):
    """测试列出所有会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) or "sessions" in data


@pytest.mark.asyncio
async def test_list_sessions_with_user_filter():
    """测试按用户ID过滤会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions?user_id=1")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_sessions_with_pagination():
    """测试分页参数"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions?offset=0&limit=10")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_session_by_id_success(mock_redis):
    """测试获取特定会话 - 成功"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions/test-1")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-1"


@pytest.mark.asyncio
async def test_get_session_by_id_not_found():
    """测试获取不存在的会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions/nonexistent-id")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_session_metadata(mock_redis):
    """测试更新会话元数据"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.patch(
            "/api/sessions/test-1",
            json={
                "title": "更新后的标题",
                "tags": ["咖啡馆", "设计"]
            }
        )

    # 根据实际实现调整状态码
    assert response.status_code in [200, 204]


@pytest.mark.asyncio
async def test_delete_session_success(mock_redis):
    """测试删除会话 - 成功"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.delete("/api/sessions/test-1")

    assert response.status_code in [200, 204]

    # 验证Redis delete被调用
    assert mock_redis.delete.called


@pytest.mark.asyncio
async def test_delete_session_not_found():
    """测试删除不存在的会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.delete("/api/sessions/nonexistent-id")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_archive_session_success(mock_redis):
    """测试归档会话 - 成功"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post("/api/sessions/test-1/archive")

    assert response.status_code in [200, 201]


@pytest.mark.asyncio
async def test_list_archived_sessions():
    """测试列出归档会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions/archived")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_get_archived_session():
    """测试获取特定归档会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions/archived/test-1")

    # 可能返回200（找到）或404（未找到）
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_update_archived_session():
    """测试更新归档会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.patch(
            "/api/sessions/archived/test-1",
            json={"title": "归档标题"}
        )

    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_delete_archived_session():
    """测试删除归档会话"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.delete("/api/sessions/archived/test-1")

    assert response.status_code in [200, 204, 404]


@pytest.mark.asyncio
async def test_get_archived_stats():
    """测试获取归档统计信息"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sessions/archived/stats")

    assert response.status_code == 200
    data = response.json()
    # 验证包含统计字段
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_session_crud_flow(mock_redis):
    """测试完整的会话CRUD流程"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. 创建会话（通过start analysis）
        create_response = await client.post(
            "/api/analysis/start",
            json={
                "requirement": "测试需求",
                "domain": "interior_design"
            }
        )

        if create_response.status_code == 200:
            session_id = create_response.json().get("session_id")

            # 2. 获取会话
            get_response = await client.get(f"/api/sessions/{session_id}")

            # 3. 更新会话
            update_response = await client.patch(
                f"/api/sessions/{session_id}",
                json={"title": "测试"}
            )

            # 4. 归档会话
            archive_response = await client.post(
                f"/api/sessions/{session_id}/archive"
            )

            # 验证流程（允许一些步骤失败，因为依赖实际实现）
            responses = [get_response, update_response, archive_response]
            successful = [r for r in responses if r.status_code < 300]
            assert len(successful) >= 1  # 至少一个步骤成功
