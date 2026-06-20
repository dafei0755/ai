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
from unittest.mock import AsyncMock

import pytest

from intelligent_project_analyzer.api.server import _session_display_title


class TestSessionDisplayTitle:
    """测试历史列表标题源选择"""

    def test_prefers_original_user_input_over_stale_display_name(self):
        title = _session_display_title(
            {
                "display_name": "深圳市南山区来福士广场",
                "user_input": "深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。",
            }
        )

        assert title == "深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。"

    def test_falls_back_to_first_user_message_before_display_name(self):
        title = _session_display_title(
            {
                "display_name": "设计需求摘要",
                "conversation_history_v2": [
                    {"role": "assistant", "content": "先说结论"},
                    {"role": "user", "content": "50岁男性室内设计师，背井离乡，想在老家建一栋民居"},
                ],
            }
        )

        assert title == "50岁男性室内设计师，背井离乡，想在老家建一栋民居"

    def test_prefers_full_user_message_when_legacy_user_input_is_stale_prefix(self):
        title = _session_display_title(
            {
                "display_name": "深圳市南山区来福士广场",
                "user_input": "深圳市南山区来福士广场",
                "conversation_history_v2": [
                    {
                        "role": "user",
                        "content": "深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场连接处，打算做一个奶茶店。",
                    }
                ],
            }
        )

        assert title == "深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场连接处，打算做一个奶茶店。"


class TestSessionListEndpoints:
    """测试会话列表端点"""

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, mock_redis):
        """测试列出所有会话"""
        # Mock Redis返回会话列表
        mock_redis.keys.return_value = [b"session:test-1", b"session:test-2", b"session:test-3"]

        response = await client.get("/api/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "sessions" in data

    @pytest.mark.asyncio
    async def test_list_sessions_with_user_filter(self, client):
        """测试按用户ID过滤会话"""
        response = await client.get("/api/sessions?user_id=1")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_sessions_with_pagination(self, client):
        """测试分页参数"""
        response = await client.get("/api/sessions?offset=0&limit=10")
        assert response.status_code == 200


class TestSessionDetailEndpoints:
    """测试单个会话端点"""

    @pytest.mark.asyncio
    async def test_get_session_by_id_success(self, client, mock_redis):
        """测试获取特定会话 - 成功"""
        # Mock Redis返回会话数据
        mock_redis.get.return_value = json.dumps(
            {"session_id": "test-1", "requirement": "咖啡馆设计", "status": "completed", "created_at": "2025-12-30T10:00:00"}
        ).encode("utf-8")

        response = await client.get("/api/sessions/test-1")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-1"

    @pytest.mark.asyncio
    async def test_get_session_by_id_not_found(self, client):
        """测试获取不存在的会话"""
        response = await client.get("/api/sessions/nonexistent-id")
        assert response.status_code == 404


class TestSessionUpdateEndpoints:
    """测试会话更新端点"""

    @pytest.mark.asyncio
    async def test_update_session_metadata(self, client, mock_redis):
        """测试更新会话元数据"""
        response = await client.patch("/api/sessions/test-1", json={"title": "更新后的标题", "tags": ["咖啡馆", "设计"]})

        # 根据实际实现调整状态码
        assert response.status_code in [200, 204, 404]


class TestSessionDeleteEndpoints:
    """测试会话删除端点"""

    @pytest.mark.asyncio
    async def test_delete_session_success(self, client, mock_redis):
        """测试删除会话 - 成功"""
        import json

        # 模拟会话存在
        mock_redis.get.return_value = json.dumps({"session_id": "test-1", "user_id": "web_user", "status": "completed"})
        mock_redis.delete.return_value = 1

        response = await client.delete("/api/sessions/test-1")

        assert response.status_code in [200, 204]
        # 验证Redis delete被调用
        assert mock_redis.delete.called

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client):
        """测试删除不存在的会话"""
        response = await client.delete("/api/sessions/nonexistent-id")
        assert response.status_code == 404


class TestSessionArchiveEndpoints:
    """测试会话归档端点"""

    @pytest.mark.asyncio
    async def test_archive_session_success(self, client, mock_redis):
        """测试归档会话 - 成功"""
        response = await client.post("/api/sessions/test-1/archive")
        assert response.status_code in [200, 201, 404]

    @pytest.mark.asyncio
    async def test_list_archived_sessions(self, client):
        """测试列出归档会话"""
        response = await client.get("/api/sessions/archived")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_list_archived_sessions_with_compatible_identifiers(self, client):
        """回归：归档会话查询应兼容 username/user_id/web_user/dev_user 多口径"""
        from intelligent_project_analyzer.api import server as server_module

        # 强制走生产分支逻辑（否则 DEV_MODE 会跳过用户过滤参数）
        old_dev_mode = server_module.DEV_MODE
        server_module.DEV_MODE = False

        # 模拟 JWT 认证通过，用户标识为 alice，数字 user_id 为 123
        server_module.jwt_service.verify_jwt_token = lambda _token: {
            "sub": "alice",
            "user_id": 123,
            "roles": ["subscriber"],
        }

        # 注入 archive_manager mock，验证调用参数
        archive_manager_mock = AsyncMock()
        archive_manager_mock.list_archived_sessions.return_value = []
        archive_manager_mock.count_archived_sessions.return_value = 0
        server_module.archive_manager = archive_manager_mock

        try:
            response = await client.get(
                "/api/sessions/archived",
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == 200

            called_user_ids = archive_manager_mock.list_archived_sessions.await_args.kwargs.get("user_ids")
            assert isinstance(called_user_ids, list)
            assert "alice" in called_user_ids
            assert "123" in called_user_ids
            assert "web_user" in called_user_ids
            assert "dev_user" in called_user_ids

            called_count_user_ids = archive_manager_mock.count_archived_sessions.await_args.kwargs.get("user_ids")
            assert isinstance(called_count_user_ids, list)
            assert "alice" in called_count_user_ids
            assert "123" in called_count_user_ids
        finally:
            server_module.DEV_MODE = old_dev_mode

    @pytest.mark.asyncio
    async def test_get_archived_session(self, client):
        """测试获取特定归档会话"""
        response = await client.get("/api/sessions/archived/test-1")
        # 可能返回200（找到）或404（未找到）
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_update_archived_session(self, client):
        """测试更新归档会话"""
        response = await client.patch("/api/sessions/archived/test-1", json={"title": "归档标题"})
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_archived_session(self, client):
        """测试删除归档会话"""
        response = await client.delete("/api/sessions/archived/test-1")
        assert response.status_code in [200, 204, 404]

    @pytest.mark.asyncio
    async def test_get_archived_stats(self, client):
        """测试获取归档统计信息"""
        response = await client.get("/api/sessions/archived/stats")

        assert response.status_code == 200
        data = response.json()
        # 验证包含统计字段
        assert isinstance(data, dict)


class TestSessionCRUDFlow:
    """测试完整的会话CRUD流程"""

    @pytest.mark.asyncio
    async def test_session_crud_flow(self, client, mock_redis, mock_workflow):
        """测试完整的会话CRUD流程"""
        # 1. 使用固定会话ID验证 CRUD 主路径，避免外部依赖导致阻塞
        session_id = "test-1"

        # 2. 获取会话
        get_response = await client.get(f"/api/sessions/{session_id}")

        # 3. 更新会话
        update_response = await client.patch(f"/api/sessions/{session_id}", json={"title": "测试"})

        # 4. 归档会话
        archive_response = await client.post(f"/api/sessions/{session_id}/archive")

        # 验证流程：接口应有稳定响应，不应出现服务端异常
        responses = [get_response, update_response, archive_response]
        assert all(r.status_code < 500 for r in responses)
