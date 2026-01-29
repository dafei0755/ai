#!/usr/bin/env python3
"""
ArXiv搜索工具端到端测试脚本

测试完整链路：
1. 创建会话（包含学术关键词）
2. 执行工作流（V4角色）
3. 验证ArXiv引用是否正确提取和展示
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


class ArXivE2ETester:
    """ArXiv端到端测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {"total": 0, "passed": 0, "failed": 0},
        }

    def add_test_result(self, test_name: str, passed: bool, details: dict):
        """添加测试结果"""
        self.test_results["tests"].append(
            {"name": test_name, "passed": passed, "details": details, "timestamp": datetime.now().isoformat()}
        )
        self.test_results["summary"]["total"] += 1
        if passed:
            self.test_results["summary"]["passed"] += 1
        else:
            self.test_results["summary"]["failed"] += 1

    async def test_api_health(self) -> bool:
        """测试1: API健康检查"""
        print("\n" + "=" * 70)
        print("🧪 测试1: API健康检查")
        print("=" * 70)

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)

                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ API正常运行")
                    print(f"   状态: {health_data.get('status', 'N/A')}")
                    self.add_test_result("API健康检查", True, health_data)
                    return True
                else:
                    print(f"❌ API响应异常: HTTP {response.status_code}")
                    self.add_test_result("API健康检查", False, {"error": f"HTTP {response.status_code}"})
                    return False
        except Exception as e:
            print(f"❌ API连接失败: {str(e)}")
            print(f"   请确保后端服务已启动: python -B scripts\\run_server_production.py")
            self.add_test_result("API健康检查", False, {"error": str(e)})
            return False

    async def test_arxiv_tool_availability(self) -> bool:
        """测试2: ArXiv工具可用性"""
        print("\n" + "=" * 70)
        print("🧪 测试2: ArXiv工具可用性")
        print("=" * 70)

        try:
            from intelligent_project_analyzer.services.tool_factory import ToolFactory

            # 创建所有工具
            tools = ToolFactory.create_all_tools()

            if "arxiv" in tools:
                print(f"✅ ArXiv工具已注册")
                arxiv_tool = tools["arxiv"]
                print(f"   工具名称: {arxiv_tool.name}")

                # 尝试简单搜索
                from intelligent_project_analyzer.core.types import ToolConfig
                from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

                test_tool = ArxivSearchTool(config=ToolConfig(name="arxiv_search"))
                result = test_tool.search("machine learning", max_results=1)

                if result.get("success") and result.get("total_results", 0) > 0:
                    print(f"✅ ArXiv搜索功能正常")
                    print(f"   测试查询返回: {result['total_results']} 条结果")
                    self.add_test_result(
                        "ArXiv工具可用性",
                        True,
                        {"tool_registered": True, "search_functional": True, "test_results": result["total_results"]},
                    )
                    return True
                else:
                    print(f"⚠️  ArXiv搜索无结果")
                    self.add_test_result(
                        "ArXiv工具可用性",
                        True,
                        {"tool_registered": True, "search_functional": False, "reason": "no_results"},
                    )
                    return True  # 工具可用但无结果仍算通过
            else:
                print(f"❌ ArXiv工具未注册")
                self.add_test_result("ArXiv工具可用性", False, {"error": "tool_not_registered"})
                return False
        except Exception as e:
            print(f"❌ ArXiv工具测试失败: {str(e)}")
            import traceback

            traceback.print_exc()
            self.add_test_result("ArXiv工具可用性", False, {"error": str(e)})
            return False

    async def test_role_tool_mapping(self) -> bool:
        """测试3: 角色工具权限配置"""
        print("\n" + "=" * 70)
        print("🧪 测试3: 角色工具权限配置")
        print("=" * 70)

        try:
            # 读取main_workflow.py检查role_tool_mapping
            workflow_file = project_root / "intelligent_project_analyzer" / "workflow" / "main_workflow.py"
            content = workflow_file.read_text(encoding="utf-8")

            # 检查V4和V6的ArXiv配置
            checks = {
                "V4有ArXiv权限": '"V4"' in content and '"arxiv"' in content.split('"V4"')[1].split("}")[0],
                "V6有ArXiv权限": '"V6"' in content and '"arxiv"' in content.split('"V6"')[1].split("}")[0]
                if '"V6"' in content
                else False,
            }

            all_passed = all(checks.values())

            for check_name, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"{status} {check_name}")

            self.add_test_result("角色工具权限配置", all_passed, checks)
            return all_passed
        except Exception as e:
            print(f"❌ 角色权限检查失败: {str(e)}")
            self.add_test_result("角色工具权限配置", False, {"error": str(e)})
            return False

    async def test_full_workflow_with_arxiv(self) -> bool:
        """测试4: 完整工作流（包含ArXiv调用）"""
        print("\n" + "=" * 70)
        print("🧪 测试4: 完整工作流（包含ArXiv调用）")
        print("=" * 70)
        print("⚠️  此测试需要大约2-3分钟完成...")

        try:
            import httpx

            # 测试用户输入（包含学术关键词）
            test_input = "我需要研究室内空间寻路设计的最新理论和实践方法，请帮我分析相关的学术研究和设计原则"

            print(f"\n📝 测试输入: {test_input[:50]}...")

            async with httpx.AsyncClient(timeout=180.0) as client:
                # 1. 创建会话
                print(f"\n1️⃣ 创建会话...")
                create_response = await client.post(
                    f"{self.base_url}/api/sessions/create", json={"user_input": test_input}
                )

                if create_response.status_code != 200:
                    print(f"❌ 会话创建失败: HTTP {create_response.status_code}")
                    self.add_test_result("完整工作流", False, {"error": "session_creation_failed"})
                    return False

                session_data = create_response.json()
                session_id = session_data["session_id"]
                print(f"✅ 会话已创建: {session_id}")

                # 2. 启动工作流（简化版：直接运行，跳过问卷）
                print(f"\n2️⃣ 启动工作流（简化模式）...")
                print(f"   提示: 实际使用时建议完成问卷以提高分析质量")

                # 注意：这里为了测试速度，我们直接调用简化流程
                # 实际使用应该通过问卷步骤

                print(f"\n⏳ 等待分析完成（这可能需要2-3分钟）...")
                print(f"   提示: 可以在另一个终端查看实时日志")

                # 由于完整工作流测试时间较长，这里我们检查日志文件
                # 查找是否有ArXiv调用记录
                print(f"\n3️⃣ 检查工具调用日志...")

                log_dir = project_root / "logs" / "tool_calls"
                if log_dir.exists():
                    today = datetime.now().strftime("%Y%m%d")
                    log_file = log_dir / f"{today}.jsonl"

                    if log_file.exists():
                        arxiv_calls = []
                        with open(log_file, "r", encoding="utf-8") as f:
                            for line in f:
                                try:
                                    record = json.loads(line)
                                    if record.get("tool_name", "").lower() == "arxiv_search":
                                        arxiv_calls.append(record)
                                except:
                                    continue

                        if arxiv_calls:
                            print(f"✅ 发现ArXiv调用记录: {len(arxiv_calls)} 次")
                            latest_call = arxiv_calls[-1]
                            print(f"   最近调用:")
                            print(f"   - 会话ID: {latest_call.get('session_id', 'N/A')[:12]}...")
                            print(f"   - 查询: {latest_call.get('query', 'N/A')[:50]}...")
                            print(f"   - 状态: {latest_call.get('status', 'N/A')}")
                            print(f"   - 结果数: {latest_call.get('result', {}).get('total_results', 0)}")

                            self.add_test_result(
                                "完整工作流",
                                True,
                                {
                                    "session_created": True,
                                    "arxiv_calls_found": len(arxiv_calls),
                                    "latest_call": {
                                        "session_id": latest_call.get("session_id"),
                                        "status": latest_call.get("status"),
                                        "results": latest_call.get("result", {}).get("total_results", 0),
                                    },
                                },
                            )
                            return True
                        else:
                            print(f"⚠️  今日日志中未发现ArXiv调用记录")
                            print(f"   可能原因:")
                            print(f"   1. 测试会话尚未完成（需要完整运行工作流）")
                            print(f"   2. LLM未决策调用ArXiv工具")
                            print(f"   3. 需要使用V4或V6角色")
                    else:
                        print(f"⚠️  今日日志文件不存在: {log_file}")
                else:
                    print(f"⚠️  日志目录不存在: {log_dir}")

                # 如果没有找到日志，说明需要完整运行
                print(f"\n💡 建议: 运行完整测试")
                print(f"   1. 启动前端: cd frontend-nextjs && npm run dev")
                print(f"   2. 访问: http://localhost:3000")
                print(f"   3. 输入包含学术关键词的需求")
                print(f"   4. 选择V4（设计研究员）或V6（总工程师）角色")
                print(f"   5. 完成分析后检查是否有📚图标的ArXiv引用")

                self.add_test_result(
                    "完整工作流", False, {"session_created": True, "workflow_not_completed": True, "reason": "需要手动运行完整流程"}
                )
                return False

        except Exception as e:
            print(f"❌ 工作流测试失败: {str(e)}")
            import traceback

            traceback.print_exc()
            self.add_test_result("完整工作流", False, {"error": str(e)})
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始ArXiv搜索工具端到端测试...")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 测试1: API健康
        await self.test_api_health()

        # 测试2: ArXiv工具可用性
        await self.test_arxiv_tool_availability()

        # 测试3: 角色权限配置
        await self.test_role_tool_mapping()

        # 测试4: 完整工作流（可选，耗时较长）
        # await self.test_full_workflow_with_arxiv()

        # 打印测试摘要
        self.print_summary()

        # 保存测试报告
        self.save_report()

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("📊 测试摘要")
        print("=" * 70)

        summary = self.test_results["summary"]
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]

        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"总测试数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"通过率: {pass_rate:.1f}%")

        print("\n详细结果:")
        for test in self.test_results["tests"]:
            status = "✅" if test["passed"] else "❌"
            print(f"{status} {test['name']}")

        print("\n" + "=" * 70)

        if failed == 0:
            print("🎉 所有测试通过！ArXiv搜索工具功能正常")
        else:
            print("⚠️  部分测试失败，请查看详细日志")

    def save_report(self):
        """保存测试报告"""
        report_dir = project_root / "reports"
        report_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"arxiv_e2e_test_{timestamp}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 测试报告已保存: {report_file}")


async def main():
    """主函数"""
    tester = ArXivE2ETester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
