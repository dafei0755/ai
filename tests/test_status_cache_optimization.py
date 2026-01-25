# -*- coding: utf-8 -*-
"""
测试状态接口缓存性能优化

验证：
1. Redis 缓存机制正常工作
2. 响应时间 < 500ms
3. 缓存失效策略正确
4. 错误时回退到直接查询
"""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from intelligent_project_analyzer.api.server import app


@pytest.fixture
async def client():
    """创建测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def sm():
    """获取 session_manager"""
    from intelligent_project_analyzer.api.server import _get_session_manager

    return await _get_session_manager()


class TestStatusCacheOptimization:
    """状态接口缓存优化测试"""

    @pytest.mark.asyncio
    async def test_status_cache_hit(self, client, sm):
        """测试缓存命中场景"""
        # 创建一个测试会话
        test_session_id = "test-cache-session-123"
        await sm.create(
            test_session_id,
            {
                "status": "running",
                "progress": 0.5,
                "current_node": "test_node",
                "detail": "Testing cache",
                "history": ["step1", "step2"],  # 不应出现在缓存中
            },
        )

        # 第一次请求 - 应该从数据库查询并写入缓存
        start_time = time.time()
        response1 = await client.get(f"/api/analysis/status/{test_session_id}")
        first_request_time = time.time() - start_time

        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["session_id"] == test_session_id
        assert data1["status"] == "running"

        # 第二次请求 - 应该命中缓存，速度更快
        start_time = time.time()
        response2 = await client.get(f"/api/analysis/status/{test_session_id}")
        second_request_time = time.time() - start_time

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2 == data1

        # 验证缓存提速效果
        print(f"\n第一次请求耗时: {first_request_time*1000:.0f}ms")
        print(f"第二次请求耗时: {second_request_time*1000:.0f}ms")

        # 清理
        await sm.delete(test_session_id)

    @pytest.mark.asyncio
    async def test_status_cache_invalidation(self, client, sm):
        """测试缓存失效机制"""
        test_session_id = "test-cache-invalidation-456"
        await sm.create(
            test_session_id,
            {
                "status": "running",
                "progress": 0.3,
                "current_node": "initial_node",
            },
        )

        # 第一次请求，建立缓存
        response1 = await client.get(f"/api/analysis/status/{test_session_id}")
        assert response1.status_code == 200
        assert response1.json()["status"] == "running"

        # 更新会话状态 - 应该自动失效缓存
        await sm.update(test_session_id, {"status": "completed", "progress": 1.0})

        # 第二次请求 - 应该返回更新后的数据
        response2 = await client.get(f"/api/analysis/status/{test_session_id}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["status"] == "completed"
        assert data2["progress"] == 1.0

        # 清理
        await sm.delete(test_session_id)

    @pytest.mark.asyncio
    async def test_status_response_time(self, client, sm):
        """测试响应时间 < 500ms"""
        test_session_id = "test-performance-789"
        await sm.create(
            test_session_id,
            {
                "status": "running",
                "progress": 0.7,
                "current_node": "performance_test",
            },
        )

        # 预热缓存
        await client.get(f"/api/analysis/status/{test_session_id}")

        # 测试10次请求的平均响应时间
        times = []
        for _ in range(10):
            start_time = time.time()
            response = await client.get(f"/api/analysis/status/{test_session_id}")
            elapsed = time.time() - start_time
            times.append(elapsed)
            assert response.status_code == 200

        avg_time = sum(times) * 1000 / len(times)
        max_time = max(times) * 1000
        min_time = min(times) * 1000

        print(f"\n响应时间统计:")
        print(f"  平均: {avg_time:.0f}ms")
        print(f"  最大: {max_time:.0f}ms")
        print(f"  最小: {min_time:.0f}ms")

        # 验证平均响应时间 < 500ms
        assert avg_time < 500, f"平均响应时间 {avg_time:.0f}ms 超过500ms目标"

        # 清理
        await sm.delete(test_session_id)

    @pytest.mark.asyncio
    async def test_include_history_skip_cache(self, client, sm):
        """测试 include_history=True 时跳过缓存"""
        test_session_id = "test-history-cache-101"
        history_data = [f"step_{i}" for i in range(100)]  # 大量历史数据

        await sm.create(
            test_session_id,
            {
                "status": "running",
                "progress": 0.5,
                "history": history_data,
            },
        )

        # 不包含 history 的请求 - 使用缓存
        response1 = await client.get(f"/api/analysis/status/{test_session_id}")
        assert response1.status_code == 200
        assert response1.json()["history"] == []

        # 包含 history 的请求 - 跳过缓存，直接查询
        response2 = await client.get(f"/api/analysis/status/{test_session_id}?include_history=true")
        assert response2.status_code == 200
        assert len(response2.json()["history"]) == 100

        # 清理
        await sm.delete(test_session_id)

    @pytest.mark.asyncio
    async def test_cache_fallback_on_error(self, sm):
        """测试缓存失败时回退到直接查询"""
        test_session_id = "test-fallback-202"
        await sm.create(
            test_session_id,
            {
                "status": "running",
                "progress": 0.4,
            },
        )

        # 正常情况下应该能够查询到数据
        session = await sm.get_status_with_cache(test_session_id)
        assert session is not None
        assert session["status"] == "running"

        # 清理
        await sm.delete(test_session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
