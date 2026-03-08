"""
API端点测试 - Session管理相关端点

测试覆盖:
- GET /api/sessions
- GET /api/sessions/{session_id}
- PATCH /api/sessions/{session_id}
- DELETE /api/sessions/{session_id}
- POST /api/sessions/{session_id}/archive
- GET /api/sessions/archived

使用conftest.py提供的fixtures避免app初始化问题
"""

import json

import pytest


class TestSessionListEndpoints:
    """测试会话列表端点"""

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, mock_redis):
        """测试列出所有会话 - 返回分页结构"""
        response = await client.get("/api/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total"] == 0
        assert data["sessions"] == []

    @pytest.mark.asyncio
    async def test_list_sessions_with_user_filter(self, client):
        """测试按用户ID过滤会话（user_id 参数被忽略，仍返回分页结构）"""
        response = await client.get("/api/sessions?user_id=1")

        assert response.status_code == 200
        assert "sessions" in response.json()

    @pytest.mark.asyncio
    async def test_list_sessions_with_pagination(self, client):
        """测试分页参数（page / page_size）"""
        response = await client.get("/api/sessions?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["page"] == 1
        assert data["page_size"] == 10


class TestSessionDetailEndpoints:
    """测试单个会话端点"""

    @pytest.mark.asyncio
    async def test_get_session_by_id_success(self, client, mock_redis):
        """测试获取特定会话 - 成功"""
        mock_redis.get.return_value = json.dumps(
            {"session_id": "test-1", "requirement": "咖啡馆设计", "status": "completed", "created_at": "2025-12-30T10:00:00"}
        ).encode("utf-8")

        response = await client.get("/api/sessions/test-1")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-1"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_session_by_id_not_found(self, client):
        """测试获取不存在的会话 - 返回 404"""
        response = await client.get("/api/sessions/nonexistent-id")

        assert response.status_code == 404


class TestSessionUpdateEndpoints:
    """测试会话更新端点"""

    @pytest.mark.asyncio
    async def test_update_session_metadata(self, client, mock_redis):
        """测试更新会话元数据 - 成功"""
        mock_redis.get.return_value = json.dumps(
            {"session_id": "test-1", "user_id": "web_user", "status": "completed"}
        ).encode("utf-8")

        response = await client.patch("/api/sessions/test-1", json={"title": "更新后的标题", "tags": ["咖啡馆", "设计"]})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "会话更新成功"

    @pytest.mark.asyncio
    async def test_update_session_metadata_not_found(self, client):
        """测试更新不存在的会话 - 返回 404"""
        response = await client.patch("/api/sessions/nonexistent-id", json={"title": "标题"})

        assert response.status_code == 404


class TestSessionDeleteEndpoints:
    """测试会话删除端点"""

    @pytest.mark.asyncio
    async def test_delete_session_success(self, client, mock_redis):
        """测试删除会话 - 成功"""
        mock_redis.get.return_value = json.dumps(
            {"session_id": "test-1", "user_id": "web_user", "status": "completed"}
        ).encode("utf-8")
        mock_redis.delete.return_value = 1

        response = await client.delete("/api/sessions/test-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert mock_redis.delete.called

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client):
        """测试删除不存在的会话 - 返回 404"""
        response = await client.delete("/api/sessions/nonexistent-id")

        assert response.status_code == 404


class TestSessionArchiveEndpoints:
    """测试会话归档端点"""

    @pytest.mark.asyncio
    async def test_archive_session_success(self, client, mock_redis):
        """测试归档会话 - 成功"""
        mock_redis.get.return_value = json.dumps(
            {"session_id": "test-1", "user_id": "web_user", "status": "completed"}
        ).encode("utf-8")

        response = await client.post("/api/sessions/test-1/archive")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == "test-1"

    @pytest.mark.asyncio
    async def test_list_archived_sessions(self, client):
        """测试列出归档会话 - 返回分页结构"""
        response = await client.get("/api/sessions/archived")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total"] == 0
        assert data["sessions"] == []

    @pytest.mark.asyncio
    async def test_get_archived_session(self, client):
        """测试获取特定归档会话 - 成功（conftest 中 test-1 有数据）"""
        response = await client.get("/api/sessions/archived/test-1")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-1"

    @pytest.mark.asyncio
    async def test_update_archived_session(self, client):
        """测试更新归档会话元数据 - 成功"""
        response = await client.patch("/api/sessions/archived/test-1", json={"title": "归档标题"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_archived_session(self, client):
        """测试删除归档会话 - 成功"""
        response = await client.delete("/api/sessions/archived/test-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_archived_stats(self, client):
        """测试获取归档统计信息 - 字段验证"""
        response = await client.get("/api/sessions/archived/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data
        assert "pinned" in data


class TestSessionCRUDFlow:
    """测试完整的会话CRUD流程（不依赖 start analysis，直接构造会话数据）"""

    @pytest.mark.asyncio
    async def test_session_crud_flow(self, client, mock_redis):
        """测试 GET → PATCH → archive 完整链路"""
        session_id = "crud-test-session"
        session_data = {
            "session_id": session_id,
            "user_id": "web_user",
            "user_input": "测试需求",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00",
        }
        mock_redis.get.return_value = json.dumps(session_data).encode("utf-8")

        # 1. 获取会话
        get_response = await client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == 200
        assert get_response.json()["session_id"] == session_id

        # 2. 更新会话
        update_response = await client.patch(f"/api/sessions/{session_id}", json={"title": "CRUD测试标题"})
        assert update_response.status_code == 200
        assert update_response.json()["success"] is True

        # 3. 归档会话
        archive_response = await client.post(f"/api/sessions/{session_id}/archive")
        assert archive_response.status_code == 200
        assert archive_response.json()["success"] is True
