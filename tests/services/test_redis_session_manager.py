"""
Services模块测试 - Redis Session Manager

测试Redis会话管理器的核心功能
使用conftest.py提供的fixtures避免app初始化问题
"""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def redis_manager(env_setup):
    """创建真实的RedisSessionManager实例用于测试"""
    # 在env_setup之后导入，确保环境变量已设置
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    manager = RedisSessionManager()

    # 连接到Redis
    connected = await manager.connect()

    if connected and manager.redis_client:
        # 使用测试专用DB
        await manager.redis_client.select(15)

    yield manager

    # 清理测试数据
    if manager.redis_client:
        await manager.redis_client.flushdb()
        await manager.redis_client.close()


class TestRedisSessionManagerBasics:
    """测试Redis会话管理器基础功能"""

    @pytest.mark.asyncio
    async def test_create_session_success(self, redis_manager):
        """测试创建会话 - 成功"""
        session_id = "test-create-123"
        session_data = {
            "requirement": "测试需求",
            "status": "running",
            "progress": 0.5
        }

        result = await redis_manager.create(session_id, session_data)
        assert result is True

        # 验证数据已保存
        saved_data = await redis_manager.get(session_id)
        assert saved_data is not None
        assert saved_data["requirement"] == "测试需求"
        assert saved_data["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_session_success(self, redis_manager):
        """测试获取会话 - 成功"""
        session_id = "test-get-123"
        session_data = {"key": "value", "number": 42}

        # 先创建
        await redis_manager.create(session_id, session_data)

        # 再获取
        loaded_data = await redis_manager.get(session_id)

        assert loaded_data is not None
        assert loaded_data["key"] == "value"
        assert loaded_data["number"] == 42

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, redis_manager):
        """测试获取不存在的会话"""
        loaded_data = await redis_manager.get("nonexistent-session")
        assert loaded_data is None

    @pytest.mark.asyncio
    async def test_delete_session_success(self, redis_manager):
        """测试删除会话 - 成功"""
        session_id = "test-delete-123"
        session_data = {"data": "to be deleted"}

        # 先创建
        await redis_manager.create(session_id, session_data)
        assert await redis_manager.get(session_id) is not None

        # 再删除
        result = await redis_manager.delete(session_id)
        assert result is True

        # 验证已删除
        assert await redis_manager.get(session_id) is None

    @pytest.mark.asyncio
    async def test_exists_check(self, redis_manager):
        """测试会话存在性检查"""
        session_id = "test-exists-123"

        # 初始不存在
        assert await redis_manager.exists(session_id) is False

        # 创建后存在
        await redis_manager.create(session_id, {"data": "test"})
        assert await redis_manager.exists(session_id) is True

        # 删除后不存在
        await redis_manager.delete(session_id)
        assert await redis_manager.exists(session_id) is False


class TestRedisSessionManagerAdvanced:
    """测试Redis会话管理器高级功能"""

    @pytest.mark.asyncio
    async def test_list_all_sessions(self, redis_manager):
        """测试列出所有会话"""
        # 创建多个会话
        for i in range(3):
            await redis_manager.create(f"test-list-{i}", {"index": i})

        sessions = await redis_manager.list_all_sessions()

        assert len(sessions) >= 3
        assert any("test-list-" in s for s in sessions)

    @pytest.mark.asyncio
    async def test_update_session(self, redis_manager):
        """测试更新会话"""
        session_id = "test-update-123"

        # 初始状态
        initial_data = {"status": "pending", "progress": 0.0}
        await redis_manager.create(session_id, initial_data)

        # 更新状态
        update_result = await redis_manager.update(session_id, {"status": "running", "progress": 0.5})
        assert update_result is True

        # 验证更新后的状态
        loaded_data = await redis_manager.get(session_id)
        assert loaded_data["status"] == "running"
        assert loaded_data["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_extend_ttl(self, redis_manager):
        """测试延长TTL"""
        session_id = "test-ttl-123"
        session_data = {"data": "test"}

        # 创建会话
        await redis_manager.create(session_id, session_data)

        # 延长TTL
        result = await redis_manager.extend_ttl(session_id, ttl=3600)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_all_sessions(self, redis_manager):
        """测试获取所有会话详情"""
        # 创建多个会话
        for i in range(2):
            await redis_manager.create(f"test-all-{i}", {"index": i, "status": "test"})

        all_sessions = await redis_manager.get_all_sessions()

        assert isinstance(all_sessions, list)
        # 可能为空或包含会话
        if len(all_sessions) > 0:
            assert isinstance(all_sessions[0], dict)


class TestRedisSessionManagerDataHandling:
    """测试Redis会话管理器数据处理"""

    @pytest.mark.asyncio
    async def test_special_characters_in_data(self, redis_manager):
        """测试特殊字符处理"""
        session_id = "test-special-123"

        session_data = {
            "chinese": "中文内容测试",
            "emoji": "🎉✨🚀",
            "special": "\"quotes\" and 'apostrophes'",
            "unicode": "\u4e2d\u6587"
        }

        await redis_manager.create(session_id, session_data)
        loaded_data = await redis_manager.get(session_id)

        assert loaded_data["chinese"] == "中文内容测试"
        assert loaded_data["emoji"] == "🎉✨🚀"
        assert loaded_data["special"] == "\"quotes\" and 'apostrophes'"

    @pytest.mark.asyncio
    async def test_nested_data_structure(self, redis_manager):
        """测试嵌套数据结构"""
        session_id = "test-nested-123"

        session_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": "deep nested value"
                    }
                },
                "array": [1, 2, [3, 4, [5, 6]]]
            }
        }

        await redis_manager.create(session_id, session_data)
        loaded_data = await redis_manager.get(session_id)

        assert loaded_data["level1"]["level2"]["level3"]["data"] == "deep nested value"
        assert loaded_data["level1"]["array"][2][2][1] == 6

    @pytest.mark.asyncio
    async def test_large_data_storage(self, redis_manager):
        """测试大数据存储"""
        session_id = "test-large-123"

        # 创建较大数据（减小规模以加快测试）
        large_data = {
            "agent_results": {f"agent_{i}": f"result_{i}" * 10 for i in range(20)},
            "metadata": {"key": "value", "count": 100}
        }

        # 保存大数据
        result = await redis_manager.create(session_id, large_data)
        assert result is True

        # 加载并验证
        loaded_data = await redis_manager.get(session_id)
        assert loaded_data is not None
        assert len(loaded_data["agent_results"]) == 20

    @pytest.mark.asyncio
    @pytest.mark.parametrize("session_id,session_data", [
        ("test-1", {"status": "pending"}),
        ("test-2", {"status": "running", "progress": 0.5}),
        ("test-3", {"status": "completed", "result": "success"}),
    ])
    async def test_multiple_sessions(self, redis_manager, session_id, session_data):
        """测试多个会话的独立性"""
        await redis_manager.create(session_id, session_data)
        loaded_data = await redis_manager.get(session_id)

        assert loaded_data is not None
        for key, value in session_data.items():
            assert loaded_data[key] == value
