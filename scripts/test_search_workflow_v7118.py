"""
v7.118 搜索工具全流程测试
测试场景：北京四合院改造为纽约Loft风格

目标：
1. 验证SearchStrategyGenerator生成查询正常
2. 验证搜索工具调用（Tavily, Arxiv, RAGFlow）
3. 验证搜索结果处理和集成
4. 发现搜索流程中的bug
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
An American who grew up in Beijing bought a small courtyard house (Siheyuan).
He wants to preserve the traditional architectural 'Qi', but achieve New York Loft's openness, minimalism and party functions inside.
"""


class SearchWorkflowTester:
    """搜索工作流测试器"""

    def __init__(self):
        self.session_id = None
        self.errors = []
        self.warnings = []
        self.search_events = []
        self.deliverables_tested = set()

    async def run_full_test(self):
        """运行完整搜索工作流测试"""
        logger.info("=" * 80)
        logger.info("🔍 开始 v7.118 搜索工具全流程测试")
        logger.info("=" * 80)

        try:
            # 步骤1: 检查服务器状态
            if not await self.check_server():
                logger.error("❌ 服务器未运行，测试终止")
                return

            # 步骤2: 启动分析
            if not await self.start_analysis():
                logger.error("❌ 启动分析失败，测试终止")
                return

            # 步骤3: 监听WebSocket获取实时进度
            await self.monitor_workflow_with_websocket()

            # 步骤4: 生成报告
            self.generate_report()

        except Exception as e:
            logger.error(f"❌ 测试失败: {e}")
            self.errors.append(f"测试异常: {e}")
            import traceback

            traceback.print_exc()

    async def check_server(self):
        """检查服务器是否运行"""
        logger.info("\n" + "=" * 60)
        logger.info("🏥 步骤1: 检查服务器状态")
        logger.info("=" * 60)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        logger.success("✅ 服务器运行正常")
                        return True
                    else:
                        logger.error(f"❌ 服务器响应异常: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ 无法连接服务器: {e}")
            logger.info("💡 请先启动服务器: python -m intelligent_project_analyzer.api.server")
            return False

    async def start_analysis(self):
        """启动分析"""
        logger.info("\n" + "=" * 60)
        logger.info("🚀 步骤2: 启动分析会话")
        logger.info("=" * 60)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{BASE_URL}/api/analysis/start",
                    json={"user_input": TEST_USER_INPUT, "user_id": "test_search_v7118"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.session_id = data.get("session_id")
                        logger.success(f"✅ 分析启动成功")
                        logger.info(f"   Session ID: {self.session_id}")
                        return True
                    else:
                        error = f"启动失败: HTTP {response.status}"
                        logger.error(f"❌ {error}")
                        self.errors.append(error)
                        return False

            except Exception as e:
                error = f"启动异常: {e}"
                logger.error(f"❌ {error}")
                self.errors.append(error)
                return False

    async def monitor_workflow_with_websocket(self):
        """通过WebSocket监听工作流并捕获搜索事件"""
        logger.info("\n" + "=" * 60)
        logger.info("📡 步骤3: 监听工作流进度（关注搜索事件）")
        logger.info("=" * 60)

        if not self.session_id:
            logger.warning("⚠️ 无session_id，跳过监听")
            return

        ws_url = f"ws://localhost:8000/ws/{self.session_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url, timeout=300) as ws:
                    logger.success("✅ WebSocket连接建立")
                    logger.info("   等待工作流事件...")

                    message_count = 0
                    start_time = time.time()
                    timeout_seconds = 180  # 3分钟超时

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            message_count += 1
                            data = json.loads(msg.data)

                            # 处理消息
                            self.process_workflow_message(data, message_count)

                            # 检查是否完成
                            if data.get("type") == "complete":
                                logger.success(f"✅ 工作流完成（共收到{message_count}条消息）")
                                break

                            # 检查错误
                            if data.get("type") == "error":
                                error = f"工作流错误: {data.get('detail')}"
                                logger.error(f"❌ {error}")
                                self.errors.append(error)
                                break

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"❌ WebSocket错误: {ws.exception()}")
                            break

                        # 超时检查
                        if time.time() - start_time > timeout_seconds:
                            warning = f"监听超时({timeout_seconds}秒)，共收到{message_count}条消息"
                            logger.warning(f"⚠️ {warning}")
                            self.warnings.append(warning)
                            break

        except Exception as e:
            error = f"WebSocket监听失败: {e}"
            logger.error(f"❌ {error}")
            self.errors.append(error)

    def process_workflow_message(self, data: dict, msg_num: int):
        """处理工作流消息，重点关注搜索相关事件"""
        msg_type = data.get("type", "unknown")

        # 节点进度消息
        if msg_type == "node_progress":
            node = data.get("node", "")
            progress = data.get("progress", {})

            logger.debug(f"[消息{msg_num}] 节点: {node}")

            # 🔍 重点关注：搜索查询生成节点
            if "search_query_generator" in node.lower():
                logger.info(f"🔍 [搜索事件] 搜索查询生成节点")
                self.search_events.append({"type": "query_generation", "node": node, "data": progress})

            # 🔍 重点关注：专家搜索节点
            if "expert" in node.lower() and "search" in node.lower():
                logger.info(f"🔍 [搜索事件] 专家搜索执行")
                self.search_events.append({"type": "expert_search", "node": node, "data": progress})

            # 🔍 提取交付物信息
            if progress.get("deliverable_name"):
                deliv_name = progress["deliverable_name"]
                self.deliverables_tested.add(deliv_name)
                logger.info(f"   交付物: {deliv_name}")

        # 工具调用消息
        elif msg_type == "tool_call":
            tool_name = data.get("tool_name", "")
            logger.info(f"🔧 [工具调用] {tool_name}")

            # 🔍 重点关注：搜索工具
            if any(keyword in tool_name.lower() for keyword in ["tavily", "arxiv", "ragflow", "search"]):
                logger.success(f"✅ [搜索工具调用] {tool_name}")
                self.search_events.append({"type": "tool_call", "tool": tool_name, "data": data})

        # 状态更新消息
        elif msg_type == "status_update":
            status = data.get("status", "")
            current_node = data.get("current_node", "")

            if status == "waiting_for_input":
                logger.info(f"⏸️  等待用户输入 - 节点: {current_node}")
            elif status == "running":
                logger.debug(f"▶️  运行中 - 节点: {current_node}")

        # 错误消息
        elif msg_type == "error":
            error = data.get("detail", "未知错误")
            logger.error(f"❌ [工作流错误] {error}")
            self.errors.append(error)

    def generate_report(self):
        """生成测试报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 搜索工作流测试报告")
        logger.info("=" * 80)

        # 搜索事件统计
        logger.info(f"\n🔍 搜索事件统计: {len(self.search_events)}个")

        query_gen_count = sum(1 for e in self.search_events if e["type"] == "query_generation")
        search_exec_count = sum(1 for e in self.search_events if e["type"] == "expert_search")
        tool_call_count = sum(1 for e in self.search_events if e["type"] == "tool_call")

        logger.info(f"  - 查询生成事件: {query_gen_count}")
        logger.info(f"  - 搜索执行事件: {search_exec_count}")
        logger.info(f"  - 工具调用事件: {tool_call_count}")

        # 交付物统计
        logger.info(f"\n📦 测试的交付物数量: {len(self.deliverables_tested)}")
        for deliv in sorted(self.deliverables_tested):
            logger.info(f"  - {deliv}")

        # 工具调用详情
        logger.info(f"\n🔧 搜索工具调用详情:")
        tool_calls = [e for e in self.search_events if e["type"] == "tool_call"]
        if tool_calls:
            for i, event in enumerate(tool_calls, 1):
                logger.info(f"  {i}. {event['tool']}")
        else:
            logger.warning("  ⚠️ 未检测到任何搜索工具调用")
            self.warnings.append("未检测到搜索工具调用")

        # 错误统计
        logger.info(f"\n❌ 错误数量: {len(self.errors)}")
        if self.errors:
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")
        else:
            logger.success("  ✅ 无错误")

        # 警告统计
        logger.info(f"\n⚠️  警告数量: {len(self.warnings)}")
        if self.warnings:
            for i, warning in enumerate(self.warnings, 1):
                logger.warning(f"  {i}. {warning}")
        else:
            logger.success("  ✅ 无警告")

        # 总体评估
        logger.info("\n" + "=" * 80)
        if not self.errors and len(self.search_events) > 0:
            logger.success("✅ 搜索工作流测试通过")
            logger.success(f"   检测到{len(self.search_events)}个搜索相关事件")
        elif not self.errors:
            logger.warning("⚠️ 测试完成但未检测到搜索事件")
        else:
            logger.error("❌ 测试失败 - 发现错误需要修复")
        logger.info("=" * 80)


async def main():
    """主函数"""
    tester = SearchWorkflowTester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
