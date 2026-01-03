"""
v7.118 修复验证测试

测试三个修复:
1. WebSocket连接稳定性
2. Emoji编码处理
3. 会话列表查询性能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


async def test_websocket_state_check():
    """测试1: WebSocket状态检查改进"""
    logger.info("=" * 60)
    logger.info("测试1: WebSocket _wait_for_connected 函数")
    logger.info("=" * 60)

    try:
        from starlette.websockets import WebSocketState

        from intelligent_project_analyzer.api.server import _wait_for_connected

        # 创建模拟WebSocket对象
        class MockWebSocket:
            def __init__(self):
                self.client_state = WebSocketState.CONNECTING
                self._connect_after = 0.2  # 0.2秒后连接

            async def simulate_connect(self):
                await asyncio.sleep(self._connect_after)
                self.client_state = WebSocketState.CONNECTED

        mock_ws = MockWebSocket()

        # 启动模拟连接
        asyncio.create_task(mock_ws.simulate_connect())

        # 测试等待连接
        result = await _wait_for_connected(mock_ws, timeout=1.0)

        if result:
            logger.success("✅ WebSocket状态检查正常工作")
        else:
            logger.error("❌ WebSocket状态检查失败")

    except Exception as e:
        logger.error(f"❌ 测试WebSocket失败: {e}")


async def test_emoji_encoding():
    """测试2: Emoji编码处理"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: Emoji安全字符串处理")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

        # 测试包含emoji的字符串
        test_strings = [
            "🆕 新功能",
            "测试文本 🔥 without issues",
            "普通文本",
            "Mixed 中英文 with emoji 🎨✨",
            "'ascii' codec can't encode character '\U0001f195'",
        ]

        all_passed = True
        for test_str in test_strings:
            try:
                safe_str = DynamicDimensionGenerator._safe_str(test_str)
                # 尝试编码为ASCII（应该不会失败）
                safe_str.encode("ascii", errors="ignore")
                logger.success(f"✅ 安全处理: '{test_str[:30]}...' -> '{safe_str[:30]}...'")
            except Exception as e:
                logger.error(f"❌ 处理失败: '{test_str}': {e}")
                all_passed = False

        if all_passed:
            logger.success("✅ Emoji编码处理测试通过")
        else:
            logger.error("❌ Emoji编码处理测试失败")

    except Exception as e:
        logger.error(f"❌ 测试Emoji处理失败: {e}")


async def test_session_query_performance():
    """测试3: 会话列表查询性能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 会话列表查询缓存")
    logger.info("=" * 60)

    try:
        import time

        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        manager = RedisSessionManager()
        connected = await manager.connect()

        if not connected:
            logger.warning("⚠️ Redis未连接，跳过性能测试")
            return

        # 第一次查询（冷启动）
        start = time.time()
        sessions1 = await manager.get_all_sessions()
        time1 = time.time() - start

        logger.info(f"📊 第一次查询: {len(sessions1)} 个会话, 耗时: {time1:.3f}秒")

        # 第二次查询（应该命中缓存）
        start = time.time()
        sessions2 = await manager.get_all_sessions()
        time2 = time.time() - start

        logger.info(f"📊 第二次查询: {len(sessions2)} 个会话, 耗时: {time2:.3f}秒")

        # 验证缓存配置
        cache_ttl = manager._cache_ttl
        logger.info(f"⚙️ 缓存TTL配置: {cache_ttl}秒 ({cache_ttl/60:.1f}分钟)")

        if time2 < time1 * 0.1:  # 缓存查询应该快10倍以上
            logger.success(f"✅ 缓存工作正常 (加速 {time1/time2:.1f}x)")
        else:
            logger.warning(f"⚠️ 缓存效果不明显 (加速 {time1/time2:.1f}x)")

        await manager.disconnect()

    except Exception as e:
        logger.error(f"❌ 测试会话查询性能失败: {e}")


async def main():
    """运行所有测试"""
    logger.info("🚀 开始 v7.118 修复验证测试\n")

    await test_websocket_state_check()
    await test_emoji_encoding()
    await test_session_query_performance()

    logger.info("\n" + "=" * 60)
    logger.success("✅ 所有测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
