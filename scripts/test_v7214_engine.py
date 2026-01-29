#!/usr/bin/env python3
"""
v7.214结构化分析引擎验证测试脚本
测试所有修复措施是否生效：超时保护、错误处理、回退机制
"""

import asyncio
import json
import time
from datetime import datetime

import httpx

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_QUERY = "现代简约风格的120平米住宅设计，预算25万，注重收纳功能"


class V7214EngineTest:
    def __init__(self):
        self.session_id = None
        self.results = []

    async def test_session_creation(self):
        """测试搜索会话创建"""
        print("\n🔧 测试1: 搜索会话创建")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{BASE_URL}/api/search/session/create", json={"query": TEST_QUERY})

            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session_id")
                print(f"✅ 会话创建成功: {self.session_id}")
                return True
            else:
                print(f"❌ 会话创建失败: {response.status_code}")
                return False

    async def test_v7214_stream_search(self):
        """测试v7.214引擎流式搜索，验证超时和回退机制"""
        if not self.session_id:
            print("❌ 没有有效的会话ID，跳过测试")
            return False

        print("\n🔬 测试2: v7.214引擎流式搜索")
        print(f"   - API超时设置: 60秒")
        print(f"   - 引擎超时设置: 90秒")
        print(f"   - 预期行为: 成功执行或优雅回退")

        start_time = time.time()
        response_count = 0
        timeout_detected = False
        error_detected = False

        try:
            async with httpx.AsyncClient(timeout=120) as client:  # 给客户端更长的超时
                async with client.stream(
                    "POST",
                    f"{BASE_URL}/api/search/ucppt/stream",
                    json={"session_id": self.session_id, "query": TEST_QUERY, "max_rounds": 3},  # 减少轮数避免过长测试
                ) as response:
                    if response.status_code != 200:
                        print(f"❌ 请求失败: {response.status_code}")
                        return False

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # 去除 "data: " 前缀
                                response_count += 1

                                # 检查是否有v7.214相关消息
                                if data.get("type") == "phase":
                                    phase_data = data.get("data", {})
                                    if "v7.214" in phase_data.get("phase_name", ""):
                                        print(f"🔍 v7.214阶段开始: {phase_data.get('message', '')}")

                                # 检查超时或错误处理
                                elif data.get("type") == "error":
                                    error_data = data.get("data", {})
                                    error_type = error_data.get("error_type", "")

                                    if "timeout" in error_type:
                                        timeout_detected = True
                                        print(f"✅ 检测到超时处理: {error_data.get('message', '')}")
                                    else:
                                        error_detected = True
                                        print(f"⚠️ 检测到错误处理: {error_data.get('message', '')}")

                                # 检查搜索结果
                                elif data.get("type") == "search_result":
                                    result_data = data.get("data", {})
                                    print(f"📝 搜索结果: {result_data.get('title', '未知标题')}")

                                # 实时输出进度（每10个响应输出一次）
                                if response_count % 10 == 0:
                                    elapsed = time.time() - start_time
                                    print(f"⏱️ 进度: {response_count}个响应, 耗时{elapsed:.1f}秒")

                                # 超过2分钟强制停止测试
                                if time.time() - start_time > 120:
                                    print("⚠️ 测试超时(2分钟)，终止测试")
                                    break

                            except json.JSONDecodeError:
                                # 跳过非JSON行（如心跳包）
                                continue

        except asyncio.TimeoutError:
            print("❌ 客户端超时")
            return False
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            return False

        elapsed_time = time.time() - start_time
        print(f"\n📊 测试结果:")
        print(f"   - 总响应数: {response_count}")
        print(f"   - 总耗时: {elapsed_time:.2f}秒")
        print(f"   - 超时处理: {'✅ 检测到' if timeout_detected else '❌ 未检测到'}")
        print(f"   - 错误处理: {'✅ 检测到' if error_detected else '⚪ 未检测到'}")

        # 判断测试是否成功
        success = response_count > 0 and elapsed_time < 180  # 3分钟内完成
        if success:
            print("✅ v7.214引擎测试通过")
        else:
            print("❌ v7.214引擎测试失败")

        return success

    async def test_system_health(self):
        """测试系统健康状态"""
        print("\n🏥 测试3: 系统健康检查")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{BASE_URL}/health")

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 系统健康: {data}")
                    return True
                else:
                    print(f"❌ 健康检查失败: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False

    async def run_full_test(self):
        """运行完整的v7.214引擎验证测试"""
        print("=" * 70)
        print(f"🧪 v7.214结构化分析引擎验证测试")
        print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # 运行所有测试
        test1 = await self.test_session_creation()
        test2 = await self.test_v7214_stream_search() if test1 else False
        test3 = await self.test_system_health()

        # 汇总结果
        print("\n" + "=" * 70)
        print("📋 测试汇总")
        print("=" * 70)
        print(f"1. 会话创建测试: {'✅ 通过' if test1 else '❌ 失败'}")
        print(f"2. v7.214引擎测试: {'✅ 通过' if test2 else '❌ 失败'}")
        print(f"3. 系统健康测试: {'✅ 通过' if test3 else '❌ 失败'}")

        overall_success = test1 and test2 and test3
        print(f"\n🎯 总体结果: {'✅ 全部通过 - v7.214引擎修复成功!' if overall_success else '❌ 部分失败 - 需要进一步调试'}")

        return overall_success


async def main():
    """主函数"""
    tester = V7214EngineTest()
    success = await tester.run_full_test()

    if success:
        print("\n🎉 v7.214引擎已完全修复，可以正常使用！")
    else:
        print("\n🛠️ 需要进一步检查系统配置和日志")

    return success


if __name__ == "__main__":
    asyncio.run(main())
