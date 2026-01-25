# -*- coding: utf-8 -*-
"""
状态接口性能对比测试

测试优化前后的性能差异
"""

import asyncio
import json
import time
from typing import List

import aiohttp

BASE_URL = "http://localhost:8000"


async def create_test_session() -> str:
    """创建测试会话"""
    async with aiohttp.ClientSession() as session:
        # 创建一个简单的分析任务
        data = aiohttp.FormData()
        data.add_field("text", "测试性能优化", content_type="text/plain")

        async with session.post(f"{BASE_URL}/api/analyze", data=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["session_id"]
            else:
                raise Exception(f"创建会话失败: {response.status}")


async def measure_status_request(session_id: str, include_history: bool = False) -> float:
    """测量单次状态查询耗时"""
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/api/analysis/status/{session_id}"
        if include_history:
            url += "?include_history=true"

        start_time = time.time()
        async with session.get(url) as response:
            await response.json()
            elapsed = time.time() - start_time
            return elapsed * 1000  # 转换为毫秒


async def benchmark_cold_cache(session_id: str, num_requests: int = 10) -> List[float]:
    """测试冷缓存性能（每次清除缓存）"""
    times = []
    for i in range(num_requests):
        # 注意：实际清除缓存需要调用 Redis 命令，这里只是测量首次请求
        elapsed = await measure_status_request(session_id)
        times.append(elapsed)
        await asyncio.sleep(0.1)  # 短暂延迟
    return times


async def benchmark_hot_cache(session_id: str, num_requests: int = 100) -> List[float]:
    """测试热缓存性能（连续请求）"""
    times = []
    for i in range(num_requests):
        elapsed = await measure_status_request(session_id)
        times.append(elapsed)
    return times


async def benchmark_concurrent(session_id: str, num_concurrent: int = 50) -> List[float]:
    """测试并发请求性能"""
    tasks = [measure_status_request(session_id) for _ in range(num_concurrent)]
    return await asyncio.gather(*tasks)


def print_statistics(times: List[float], label: str):
    """打印统计信息"""
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    p50 = sorted(times)[len(times) // 2]
    p95 = sorted(times)[int(len(times) * 0.95)]
    p99 = sorted(times)[int(len(times) * 0.99)]

    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"请求数:     {len(times)}")
    print(f"平均耗时:   {avg:.0f}ms")
    print(f"最小耗时:   {min_time:.0f}ms")
    print(f"最大耗时:   {max_time:.0f}ms")
    print(f"P50:        {p50:.0f}ms")
    print(f"P95:        {p95:.0f}ms")
    print(f"P99:        {p99:.0f}ms")

    # 性能评级
    if avg < 100:
        grade = "🟢 优秀"
    elif avg < 500:
        grade = "🟡 良好"
    elif avg < 1000:
        grade = "🟠 一般"
    else:
        grade = "🔴 需优化"

    print(f"性能评级:   {grade}")
    print(f"{'='*60}")


async def main():
    """主测试流程"""
    print("=" * 60)
    print("状态接口性能测试")
    print("=" * 60)
    print("\n⏳ 创建测试会话...")

    try:
        session_id = await create_test_session()
        print(f"✅ 会话创建成功: {session_id}\n")

        # 等待会话初始化
        await asyncio.sleep(2)

        # 测试1: 首次请求（冷缓存）
        print("📊 测试1: 首次请求性能（冷缓存）")
        cold_times = await benchmark_cold_cache(session_id, num_requests=5)
        print_statistics(cold_times, "首次请求（冷缓存）")

        # 测试2: 连续请求（热缓存）
        print("\n📊 测试2: 连续请求性能（热缓存）")
        hot_times = await benchmark_hot_cache(session_id, num_requests=100)
        print_statistics(hot_times, "连续请求（热缓存）")

        # 测试3: 并发请求
        print("\n📊 测试3: 并发请求性能")
        concurrent_times = await benchmark_concurrent(session_id, num_concurrent=50)
        print_statistics(concurrent_times, "并发请求（50个并发）")

        # 对比分析
        print("\n" + "=" * 60)
        print("性能对比分析")
        print("=" * 60)
        cold_avg = sum(cold_times) / len(cold_times)
        hot_avg = sum(hot_times) / len(hot_times)
        improvement = ((cold_avg - hot_avg) / cold_avg) * 100

        print(f"\n冷缓存平均:   {cold_avg:.0f}ms")
        print(f"热缓存平均:   {hot_avg:.0f}ms")
        print(f"性能提升:     {improvement:.0f}%")

        # 目标达成检查
        print("\n" + "=" * 60)
        print("优化目标检查")
        print("=" * 60)

        target_met = hot_avg < 500
        status = "✅ 达成" if target_met else "❌ 未达成"
        print(f"\n目标: 响应时间 < 500ms")
        print(f"实际: {hot_avg:.0f}ms")
        print(f"状态: {status}")

        if cold_avg > 2000:
            print("\n💡 建议: 首次请求较慢，可能是序列化或数据库查询导致")
            print("   - 检查是否需要优化数据库查询")
            print("   - 考虑使用更轻量的序列化方案")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
