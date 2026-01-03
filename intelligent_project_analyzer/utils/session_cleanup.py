"""
🆕 P2优化: 会话清理定时任务

自动清理过期会话，避免Redis内存溢出
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger


class SessionCleanupTask:
    """会话清理定时任务"""

    def __init__(self, session_manager, cleanup_interval_hours: int = 24, session_ttl_days: int = 7):
        """
        初始化清理任务

        Args:
            session_manager: Redis会话管理器实例
            cleanup_interval_hours: 清理间隔（小时）
            session_ttl_days: 会话过期天数
        """
        self.session_manager = session_manager
        self.cleanup_interval_hours = cleanup_interval_hours
        self.session_ttl_days = session_ttl_days
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动定时清理任务"""
        if self._running:
            logger.warning("⚠️ 会话清理任务已在运行")
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"✅ 会话清理任务已启动 " f"(间隔: {self.cleanup_interval_hours}h, TTL: {self.session_ttl_days}天)")

    async def stop(self):
        """停止定时清理任务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("✅ 会话清理任务已停止")

    async def _cleanup_loop(self):
        """清理循环"""
        while self._running:
            try:
                # 等待下一次清理
                await asyncio.sleep(self.cleanup_interval_hours * 3600)

                # 执行清理
                await self.cleanup_expired_sessions()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 会话清理任务异常: {e}")
                # 发生错误后等待1小时再重试
                await asyncio.sleep(3600)

    async def cleanup_expired_sessions(self) -> int:
        """
        🆕 P2优化: 清理过期会话

        Returns:
            清理的会话数量
        """
        try:
            logger.info("🧹 开始清理过期会话...")

            # 获取所有会话
            all_sessions = await self.session_manager.list_all_sessions()

            if not all_sessions:
                logger.info("✅ 无会话需要清理")
                return 0

            # 计算过期时间
            cutoff_time = datetime.now() - timedelta(days=self.session_ttl_days)

            deleted_count = 0
            errors = []

            for session_id in all_sessions:
                try:
                    # 获取会话数据
                    session_data = await self.session_manager.get(session_id)

                    if not session_data:
                        continue

                    # 检查更新时间
                    updated_at_str = session_data.get("updated_at")
                    if not updated_at_str:
                        # 无更新时间，保留会话
                        continue

                    # 解析时间
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str)
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️ 会话 {session_id} 时间格式错误: {updated_at_str}")
                        continue

                    # 判断是否过期
                    if updated_at < cutoff_time:
                        logger.info(f"🗑️ 删除过期会话: {session_id} " f"(最后更新: {updated_at.strftime('%Y-%m-%d %H:%M:%S')})")
                        await self.session_manager.delete(session_id)
                        deleted_count += 1

                except Exception as session_error:
                    error_msg = f"清理会话 {session_id} 失败: {session_error}"
                    errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")

            # 清理总结
            logger.success(f"✅ 会话清理完成: 删除 {deleted_count}/{len(all_sessions)} 个过期会话")

            if errors:
                logger.warning(f"⚠️ {len(errors)} 个会话清理失败")

            return deleted_count

        except Exception as e:
            logger.error(f"❌ 清理过期会话失败: {e}")
            return 0

    async def cleanup_by_pattern(self, pattern: str) -> int:
        """
        按模式清理会话（高级功能）

        Args:
            pattern: 会话ID匹配模式（如"test-*"）

        Returns:
            清理的会话数量
        """
        try:
            logger.info(f"🧹 按模式清理会话: {pattern}")

            all_sessions = await self.session_manager.list_all_sessions()

            import fnmatch

            deleted_count = 0

            for session_id in all_sessions:
                if fnmatch.fnmatch(session_id, pattern):
                    try:
                        await self.session_manager.delete(session_id)
                        deleted_count += 1
                        logger.debug(f"🗑️ 删除匹配会话: {session_id}")
                    except Exception as e:
                        logger.error(f"❌ 删除会话 {session_id} 失败: {e}")

            logger.success(f"✅ 按模式清理完成: 删除 {deleted_count} 个会话")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ 按模式清理失败: {e}")
            return 0


# 使用示例:
# from intelligent_project_analyzer.api.server import session_manager
# cleanup_task = SessionCleanupTask(
#     session_manager=session_manager,
#     cleanup_interval_hours=24,
#     session_ttl_days=7
# )


def create_cleanup_task(session_manager, **kwargs):
    """
    创建清理任务实例

    Args:
        session_manager: Redis会话管理器
        **kwargs: 其他参数

    Returns:
        SessionCleanupTask实例
    """
    return SessionCleanupTask(session_manager, **kwargs)
