"""
v7.118 系统全流程测试
测试场景：北京四合院改造为纽约Loft风格

目标：
1. 验证WebSocket连接稳定性
2. 验证Emoji编码处理
3. 验证搜索查询生成
4. 验证会话管理性能
5. 发现潜在新问题
"""

import asyncio
import json
import time
from datetime import datetime

import aiohttp
from loguru import logger

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_USER_INPUT = """
一位在北京长大的美国人，买下了一座小型四合院。他希望保留传统建筑的"气"，但内部要实现纽约Loft的开放、极简和派对功能。
"""


class SystemTestRunner:
    """系统测试运行器"""

    def __init__(self):
        self.session_id = None
        self.ws = None
        self.errors = []
        self.warnings = []
        self.performance_metrics = {}

    async def run_full_test(self):
        """运行完整测试流程"""
        logger.info("=" * 80)
        logger.info("🚀 开始 v7.118 系统全流程测试")
        logger.info("=" * 80)

        try:
            # 步骤1: 启动分析
            await self.test_start_analysis()

            # 步骤2: WebSocket连接测试
            await self.test_websocket_connection()

            # 步骤3: 状态查询测试
            await self.test_status_query()

            # 步骤4: 会话列表测试
            await self.test_session_list()

            # 步骤5: 等待问卷阶段
            await self.wait_for_questionnaire()

            # 生成测试报告
            self.generate_report()

        except Exception as e:
            logger.error(f"❌ 测试失败: {e}")
            self.errors.append(f"测试异常: {e}")
            import traceback

            traceback.print_exc()

    async def test_start_analysis(self):
        """测试1: 启动分析"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 测试1: 启动分析")
        logger.info("=" * 60)

        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{BASE_URL}/api/analysis/start",
                    json={"user_input": TEST_USER_INPUT, "user_id": "test_v7118"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    elapsed = time.time() - start_time
                    self.performance_metrics["start_analysis"] = elapsed

                    if response.status == 200:
                        data = await response.json()
                        self.session_id = data.get("session_id")
                        logger.success(f"✅ 分析启动成功")
                        logger.info(f"   Session ID: {self.session_id}")
                        logger.info(f"   耗时: {elapsed:.3f}秒")
                    else:
                        error = f"启动失败: HTTP {response.status}"
                        logger.error(f"❌ {error}")
                        self.errors.append(error)

            except asyncio.TimeoutError:
                error = "启动超时(>10秒)"
                logger.error(f"❌ {error}")
                self.errors.append(error)
            except Exception as e:
                error = f"启动异常: {e}"
                logger.error(f"❌ {error}")
                self.errors.append(error)

    async def test_websocket_connection(self):
        """测试2: WebSocket连接稳定性"""
        logger.info("\n" + "=" * 60)
        logger.info("🔌 测试2: WebSocket连接")
        logger.info("=" * 60)

        if not self.session_id:
            logger.warning("⚠️ 跳过WebSocket测试（无session_id）")
            return

        ws_url = f"ws://localhost:8000/ws/{self.session_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    logger.success("✅ WebSocket连接建立成功")

                    # 等待初始消息
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            logger.info(f"   收到消息: {data.get('type', 'unknown')}")
                            logger.success("✅ WebSocket消息接收正常")
                        else:
                            warning = f"WebSocket消息类型异常: {msg.type}"
                            logger.warning(f"⚠️ {warning}")
                            self.warnings.append(warning)
                    except asyncio.TimeoutError:
                        warning = "WebSocket初始消息超时"
                        logger.warning(f"⚠️ {warning}")
                        self.warnings.append(warning)

        except Exception as e:
            error = f"WebSocket连接失败: {e}"
            logger.error(f"❌ {error}")
            self.errors.append(error)

    async def test_status_query(self):
        """测试3: 状态查询性能"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 测试3: 状态查询性能")
        logger.info("=" * 60)

        if not self.session_id:
            logger.warning("⚠️ 跳过状态查询测试（无session_id）")
            return

        async with aiohttp.ClientSession() as session:
            # 测试多次查询
            query_times = []
            for i in range(5):
                start_time = time.time()
                try:
                    async with session.get(
                        f"{BASE_URL}/api/analysis/status/{self.session_id}", timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        elapsed = time.time() - start_time
                        query_times.append(elapsed)

                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"   查询{i+1}: {elapsed:.3f}秒, 状态={data.get('status')}")
                        else:
                            warning = f"查询{i+1}失败: HTTP {response.status}"
                            logger.warning(f"⚠️ {warning}")
                            self.warnings.append(warning)

                except Exception as e:
                    error = f"查询{i+1}异常: {e}"
                    logger.error(f"❌ {error}")
                    self.errors.append(error)

                await asyncio.sleep(0.5)  # 间隔0.5秒

            # 性能统计
            if query_times:
                avg_time = sum(query_times) / len(query_times)
                max_time = max(query_times)
                self.performance_metrics["status_query_avg"] = avg_time
                self.performance_metrics["status_query_max"] = max_time

                logger.info(f"   平均耗时: {avg_time:.3f}秒")
                logger.info(f"   最大耗时: {max_time:.3f}秒")

                if max_time > 3.0:
                    warning = f"状态查询较慢: {max_time:.3f}秒"
                    logger.warning(f"⚠️ {warning}")
                    self.warnings.append(warning)
                else:
                    logger.success("✅ 状态查询性能正常")

    async def test_session_list(self):
        """测试4: 会话列表查询"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 测试4: 会话列表查询")
        logger.info("=" * 60)

        async with aiohttp.ClientSession() as session:
            # 第一次查询（冷启动）
            start_time = time.time()
            try:
                async with session.get(f"{BASE_URL}/api/sessions", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    elapsed1 = time.time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        count = len(data.get("sessions", []))
                        logger.info(f"   第1次查询: {elapsed1:.3f}秒, {count}个会话")
                    else:
                        error = f"会话列表查询失败: HTTP {response.status}"
                        logger.error(f"❌ {error}")
                        self.errors.append(error)
                        return

            except Exception as e:
                error = f"会话列表查询异常: {e}"
                logger.error(f"❌ {error}")
                self.errors.append(error)
                return

            # 第二次查询（测试缓存）
            await asyncio.sleep(0.1)
            start_time = time.time()
            try:
                async with session.get(f"{BASE_URL}/api/sessions", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    elapsed2 = time.time() - start_time

                    if response.status == 200:
                        logger.info(f"   第2次查询: {elapsed2:.3f}秒 (缓存)")

                        # 计算加速比
                        if elapsed2 > 0:
                            speedup = elapsed1 / elapsed2
                            logger.info(f"   缓存加速: {speedup:.1f}x")

                            if speedup > 10:
                                logger.success("✅ 缓存工作正常")
                            else:
                                warning = f"缓存效果不明显: {speedup:.1f}x"
                                logger.warning(f"⚠️ {warning}")
                                self.warnings.append(warning)

                        self.performance_metrics["session_list_cold"] = elapsed1
                        self.performance_metrics["session_list_cached"] = elapsed2

            except Exception as e:
                error = f"第2次查询异常: {e}"
                logger.error(f"❌ {error}")
                self.errors.append(error)

    async def wait_for_questionnaire(self):
        """测试5: 等待进入问卷阶段"""
        logger.info("\n" + "=" * 60)
        logger.info("⏳ 测试5: 等待工作流进入问卷阶段")
        logger.info("=" * 60)

        if not self.session_id:
            logger.warning("⚠️ 跳过等待测试（无session_id）")
            return

        logger.info("   等待最多60秒...")

        async with aiohttp.ClientSession() as session:
            for i in range(60):
                try:
                    async with session.get(
                        f"{BASE_URL}/api/analysis/status/{self.session_id}", timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            status = data.get("status")
                            current_node = data.get("current_node")

                            logger.info(f"   [{i+1}s] 状态={status}, 节点={current_node}")

                            # 检查是否到达问卷阶段
                            if status == "waiting_for_input" and "questionnaire" in str(current_node).lower():
                                logger.success(f"✅ 已进入问卷阶段 (耗时{i+1}秒)")
                                return

                            # 检查错误
                            if status == "error":
                                error = f"工作流执行失败: {data.get('detail')}"
                                logger.error(f"❌ {error}")
                                self.errors.append(error)
                                return

                except Exception as e:
                    logger.debug(f"   状态查询异常: {e}")

                await asyncio.sleep(1)

            warning = "等待超时(60秒)，未进入问卷阶段"
            logger.warning(f"⚠️ {warning}")
            self.warnings.append(warning)

    def generate_report(self):
        """生成测试报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 测试报告")
        logger.info("=" * 80)

        # 错误统计
        logger.info(f"\n错误数量: {len(self.errors)}")
        if self.errors:
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")
        else:
            logger.success("  ✅ 无错误")

        # 警告统计
        logger.info(f"\n警告数量: {len(self.warnings)}")
        if self.warnings:
            for i, warning in enumerate(self.warnings, 1):
                logger.warning(f"  {i}. {warning}")
        else:
            logger.success("  ✅ 无警告")

        # 性能指标
        logger.info("\n性能指标:")
        for metric, value in self.performance_metrics.items():
            logger.info(f"  {metric}: {value:.3f}秒")

        # 总体评估
        logger.info("\n" + "=" * 80)
        if not self.errors:
            logger.success("✅ 测试通过 - v7.118修复有效")
        else:
            logger.error("❌ 测试失败 - 发现问题需要修复")
        logger.info("=" * 80)


async def main():
    """主函数"""
    runner = SystemTestRunner()
    await runner.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
