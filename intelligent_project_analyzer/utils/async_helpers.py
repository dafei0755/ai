"""
异步辅助工具库 v7.501
智能等待条件满足，替代固定sleep()延迟

创建日期: 2026-02-10
性能目标: 减少6-10秒累积延迟
"""

import asyncio
import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


async def wait_for_condition(
    condition_fn: Callable[[], bool], timeout: float = 5.0, poll_interval: float = 0.05, error_message: str = "等待超时"
) -> bool:
    """
    智能等待条件满足（异步版本）

    替代固定sleep()，提供早期退出机制，显著减少不必要等待。

    Args:
        condition_fn: 条件检查函数，返回True表示条件满足
                     例如: lambda: page.evaluate("document.readyState === 'complete'")
        timeout: 最大等待时间（秒），默认5秒
        poll_interval: 轮询间隔（秒），默认50ms（避免CPU空转）
        error_message: 超时时的错误消息

    Returns:
        True if condition met within timeout

    Raises:
        TimeoutError: 超时未满足条件

    Example:
        # 替代: await asyncio.sleep(1.5)  # 固定等待JS渲染
        # 使用:
        await wait_for_condition(
            lambda: page.evaluate("document.readyState === 'complete'"),
            timeout=3.0,
            poll_interval=0.1,
            error_message="JS渲染超时"
        )
        # 性能提升: 最快0.1s完成（比固定1.5s快15倍）

    Performance:
        - Best case: poll_interval时间
        - Worst case: timeout时间
        - Typical: 0.1-1.0s（比固定sleep快5-15倍）
    """
    start = time.time()
    elapsed = 0.0

    while elapsed < timeout:
        try:
            if condition_fn():
                elapsed = time.time() - start
                logger.debug(f" 条件满足，耗时{elapsed:.3f}s（节省{timeout-elapsed:.3f}s）")
                return True
        except Exception as e:
            logger.warning(f"条件检查异常: {e}，继续轮询...")

        await asyncio.sleep(poll_interval)
        elapsed = time.time() - start

    raise TimeoutError(f"{error_message}（超时{timeout}s）")


def wait_for_condition_sync(
    condition_fn: Callable[[], bool], timeout: float = 5.0, poll_interval: float = 0.05, error_message: str = "等待超时"
) -> bool:
    """
    智能等待条件满足（同步版本）

    用于无法使用async/await的场景（如rate_limiter同步方法）

    Args:
        condition_fn: 条件检查函数
        timeout: 最大等待时间（秒）
        poll_interval: 轮询间隔（秒）
        error_message: 超时错误消息

    Returns:
        True if condition met

    Raises:
        TimeoutError: 超时未满足条件

    Example:
        # 替代: time.sleep(0.1)  # 固定轮询
        # 使用:
        wait_for_condition_sync(
            lambda: self.current_requests < self.rate_limit,
            timeout=10.0,
            poll_interval=0.05,
            error_message="限流等待超时"
        )
    """
    start = time.time()
    elapsed = 0.0

    while elapsed < timeout:
        try:
            if condition_fn():
                elapsed = time.time() - start
                logger.debug(f" 条件满足（同步），耗时{elapsed:.3f}s")
                return True
        except Exception as e:
            logger.warning(f"条件检查异常: {e}，继续轮询...")

        time.sleep(poll_interval)
        elapsed = time.time() - start

    raise TimeoutError(f"{error_message}（超时{timeout}s）")


async def wait_with_progress(
    condition_fn: Callable[[], bool],
    progress_callback: Callable[[float], None] | None = None,
    timeout: float = 5.0,
    poll_interval: float = 0.1,
    error_message: str = "等待超时",
) -> bool:
    """
    带进度回调的智能等待

    用于需要向用户展示等待进度的场景

    Args:
        condition_fn: 条件检查函数
        progress_callback: 进度回调函数，接收0.0-1.0的进度值
        timeout: 最大等待时间
        poll_interval: 轮询间隔
        error_message: 超时错误消息

    Returns:
        True if condition met

    Example:
        await wait_with_progress(
            lambda: analysis_complete(),
            progress_callback=lambda p: print(f"进度: {p:.0%}"),
            timeout=60.0
        )
    """
    start = time.time()
    elapsed = 0.0

    while elapsed < timeout:
        try:
            if condition_fn():
                if progress_callback:
                    progress_callback(1.0)
                return True
        except Exception as e:
            logger.warning(f"条件检查异常: {e}")

        # 更新进度
        if progress_callback:
            progress = min(elapsed / timeout, 0.95)  # 最多95%，最后5%留给完成
            progress_callback(progress)

        await asyncio.sleep(poll_interval)
        elapsed = time.time() - start

    raise TimeoutError(f"{error_message}（超时{timeout}s）")


class SmartPoller:
    """
    智能轮询器（可复用）

    适合需要多次执行相同轮询模式的场景

    Example:
        poller = SmartPoller(
            condition_check=lambda: redis.ping(),
            timeout=5.0,
            name="Redis连接检查"
        )

        # 第一次检查
        await poller.wait()

        # 稍后再次检查
        await poller.wait()
    """

    def __init__(
        self, condition_check: Callable[[], bool], timeout: float = 5.0, poll_interval: float = 0.05, name: str = "条件检查"
    ):
        self.condition_check = condition_check
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.name = name

        # 统计信息
        self.total_waits = 0
        self.total_time = 0.0
        self.failures = 0

    async def wait(self) -> bool:
        """执行等待"""
        self.total_waits += 1
        start = time.time()

        try:
            await wait_for_condition(
                self.condition_check,
                timeout=self.timeout,
                poll_interval=self.poll_interval,
                error_message=f"{self.name}超时",
            )
            elapsed = time.time() - start
            self.total_time += elapsed
            logger.info(f" {self.name}成功，耗时{elapsed:.3f}s")
            return True

        except TimeoutError:
            self.failures += 1
            raise

    def get_stats(self) -> dict:
        """获取统计信息"""
        avg_time = self.total_time / self.total_waits if self.total_waits > 0 else 0
        success_rate = (self.total_waits - self.failures) / self.total_waits if self.total_waits > 0 else 0

        return {
            "name": self.name,
            "total_waits": self.total_waits,
            "avg_time": avg_time,
            "success_rate": success_rate,
            "failures": self.failures,
        }


# 预定义常用条件
def is_page_loaded(page) -> bool:
    """检查页面是否加载完成（Playwright）"""
    try:
        return page.evaluate("document.readyState === 'complete'")
    except Exception:
        return False


def is_redis_ready(redis_client) -> bool:
    """检查Redis是否就绪"""
    try:
        return redis_client.ping()
    except Exception:
        return False


def is_file_exists(filepath: str) -> bool:
    """检查文件是否存在"""
    import os

    return os.path.exists(filepath)


# 使用示例（文档用）
if __name__ == "__main__":

    async def demo():
        """演示用法"""

        # 示例1: 基础用法
        print("示例1: 智能等待模拟条件")
        import random

        counter = {"value": 0}

        def mock_condition():
            counter["value"] += 1
            # 模拟30%概率满足条件
            return random.random() < 0.3

        try:
            await wait_for_condition(mock_condition, timeout=2.0, poll_interval=0.1, error_message="模拟条件超时")
            print(f" 条件满足！检查次数: {counter['value']}")
        except TimeoutError as e:
            print(f" {e}，检查次数: {counter['value']}")

        # 示例2: 带进度回调
        print("\n示例2: 带进度回调")

        def progress_handler(progress: float):
            bar = "█" * int(progress * 20)
            print(f"\r进度: [{bar:<20}] {progress:.0%}", end="")

        counter["value"] = 0
        try:
            await wait_with_progress(mock_condition, progress_callback=progress_handler, timeout=3.0, poll_interval=0.1)
            print("\n 完成！")
        except TimeoutError:
            print("\n 超时")

        # 示例3: 智能轮询器
        print("\n示例3: 可复用轮询器")
        poller = SmartPoller(condition_check=lambda: random.random() < 0.5, timeout=1.0, name="随机检查")

        for i in range(3):
            try:
                await poller.wait()
            except TimeoutError:
                pass

        print(f"统计信息: {poller.get_stats()}")

    # 运行演示
    asyncio.run(demo())
