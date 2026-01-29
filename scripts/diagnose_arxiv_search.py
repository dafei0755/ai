#!/usr/bin/env python3
"""
ArXiv搜索工具全链路诊断脚本
检查：任务生成 → 工具执行 → 引用提取 → 数据传输
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ArXivDiagnosticReport:
    """诊断报告生成器"""

    def __init__(self):
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "phases": {},
            "issues": [],
            "recommendations": [],
        }

    def add_phase_result(self, phase: str, status: str, details: Dict[str, Any]):
        """添加阶段检查结果"""
        self.results["phases"][phase] = {
            "status": status,  # "pass", "warning", "fail"
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }

    def add_issue(self, severity: str, phase: str, message: str, details: Dict[str, Any] = None):
        """添加问题记录"""
        self.results["issues"].append(
            {
                "severity": severity,  # "critical", "warning", "info"
                "phase": phase,
                "message": message,
                "details": details or {},
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_recommendation(self, message: str, action: str):
        """添加修复建议"""
        self.results["recommendations"].append({"message": message, "action": action})

    def generate_report(self) -> str:
        """生成可读报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("🔍 ArXiv搜索工具全链路诊断报告")
        lines.append("=" * 80)
        lines.append(f"生成时间: {self.results['timestamp']}")
        lines.append("")

        # 阶段总览
        lines.append("📊 检查阶段总览")
        lines.append("-" * 80)
        for phase_name, phase_data in self.results["phases"].items():
            status_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(phase_data["status"], "❓")
            lines.append(f"{status_icon} {phase_name}: {phase_data['status'].upper()}")
        lines.append("")

        # 详细结果
        lines.append("📋 详细检查结果")
        lines.append("-" * 80)
        for phase_name, phase_data in self.results["phases"].items():
            lines.append(f"\n▶ {phase_name}")
            for key, value in phase_data["details"].items():
                if isinstance(value, (list, dict)):
                    lines.append(f"  • {key}:")
                    lines.append(f"    {json.dumps(value, indent=4, ensure_ascii=False)}")
                else:
                    lines.append(f"  • {key}: {value}")

        # 问题汇总
        if self.results["issues"]:
            lines.append("\n⚠️ 发现的问题")
            lines.append("-" * 80)
            for issue in self.results["issues"]:
                severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(issue["severity"], "⚪")
                lines.append(f"{severity_icon} [{issue['phase']}] {issue['message']}")
                if issue["details"]:
                    lines.append(f"   详情: {json.dumps(issue['details'], ensure_ascii=False)}")

        # 修复建议
        if self.results["recommendations"]:
            lines.append("\n💡 修复建议")
            lines.append("-" * 80)
            for i, rec in enumerate(self.results["recommendations"], 1):
                lines.append(f"{i}. {rec['message']}")
                lines.append(f"   操作: {rec['action']}")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)

    def save_json_report(self, filepath: Path):
        """保存JSON格式报告"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)


class ArXivDiagnostics:
    """ArXiv诊断主类"""

    def __init__(self):
        self.report = ArXivDiagnosticReport()
        self.project_root = project_root

    async def run_all_checks(self):
        """运行所有诊断检查"""
        print("🚀 开始ArXiv搜索工具全链路诊断...\n")

        await self.check_phase1_task_generation()
        await self.check_phase2_tool_execution()
        await self.check_phase3_reference_extraction()
        await self.check_phase4_data_transmission()
        await self.check_phase5_log_traceability()

        # 生成报告
        print("\n" + self.report.generate_report())

        # 保存JSON报告
        report_path = self.project_root / "reports" / f"arxiv_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report.save_json_report(report_path)
        print(f"\n📄 详细报告已保存: {report_path}")

    async def check_phase1_task_generation(self):
        """阶段1: 检查任务生成逻辑"""
        print("🔍 阶段1: 检查任务生成逻辑...")
        phase_details = {}

        try:
            # 1. 检查search_query_generator文件 (实际路径修正)
            generator_file = (
                self.project_root
                / "intelligent_project_analyzer"
                / "workflow"
                / "nodes"
                / "search_query_generator_node.py"
            )
            if not generator_file.exists():
                self.report.add_issue("critical", "Phase1", f"关键文件不存在: {generator_file}")
                phase_details["search_query_generator"] = "文件不存在"
            else:
                phase_details["search_query_generator"] = "文件存在"
                # 检查是否包含ArXiv相关逻辑
                content = generator_file.read_text(encoding="utf-8")
                if "arxiv" in content.lower():
                    phase_details["arxiv_references"] = "发现arxiv引用"
                else:
                    self.report.add_issue("warning", "Phase1", "search_query_generator_node.py未发现arxiv相关代码")

            # 2. 检查角色工具映射配置 (实际在main_workflow.py中)
            role_mapping_file = self.project_root / "intelligent_project_analyzer" / "workflow" / "main_workflow.py"
            if role_mapping_file.exists():
                content = role_mapping_file.read_text(encoding="utf-8")
                # 提取V4和V6的工具配置
                if '"V4"' in content and "arxiv" in content:
                    phase_details["V4_arxiv_permission"] = "已配置"
                else:
                    self.report.add_issue("critical", "Phase1", "V4角色未配置ArXiv工具权限")
                    phase_details["V4_arxiv_permission"] = "未配置"

                if '"V6"' in content and "arxiv" in content:
                    phase_details["V6_arxiv_permission"] = "已配置"
                else:
                    self.report.add_issue("warning", "Phase1", "V6角色未配置ArXiv工具权限")
                    phase_details["V6_arxiv_permission"] = "未配置"
            else:
                self.report.add_issue("critical", "Phase1", "main_workflow.py文件不存在")

            # 3. 检查ToolFactory创建ArXiv工具
            tool_factory_file = self.project_root / "intelligent_project_analyzer" / "services" / "tool_factory.py"
            if tool_factory_file.exists():
                phase_details["tool_factory"] = "文件存在"
                content = tool_factory_file.read_text(encoding="utf-8")
                if "create_arxiv_tool" in content:
                    phase_details["create_arxiv_tool_method"] = "存在"
                if 'tools["arxiv"]' in content:
                    phase_details["arxiv_registration"] = "已注册到create_all_tools"
            else:
                self.report.add_issue("warning", "Phase1", "tool_factory.py未找到")

            status = (
                "pass"
                if not any(
                    i["severity"] == "critical" and i["phase"] == "Phase1" for i in self.report.results["issues"]
                )
                else "fail"
            )
            self.report.add_phase_result("Phase1_TaskGeneration", status, phase_details)

        except Exception as e:
            self.report.add_issue("critical", "Phase1", f"检查异常: {str(e)}")
            self.report.add_phase_result("Phase1_TaskGeneration", "fail", {"error": str(e)})

    async def check_phase2_tool_execution(self):
        """阶段2: 检查工具执行流程"""
        print("🔍 阶段2: 检查工具执行流程...")
        phase_details = {}

        try:
            # 1. 检查ArXiv工具实现
            arxiv_tool_file = self.project_root / "intelligent_project_analyzer" / "tools" / "arxiv_search.py"
            if not arxiv_tool_file.exists():
                self.report.add_issue("critical", "Phase2", f"ArXiv工具文件不存在: {arxiv_tool_file}")
                phase_details["arxiv_tool_implementation"] = "文件不存在"
            else:
                phase_details["arxiv_tool_implementation"] = "文件存在"
                content = arxiv_tool_file.read_text(encoding="utf-8")

                # 检查关键方法
                key_methods = ["search_for_deliverable", "search_for_agent", "_standardize_result"]
                for method in key_methods:
                    if f"def {method}" in content:
                        phase_details[f"method_{method}"] = "存在"
                    else:
                        self.report.add_issue("warning", "Phase2", f"关键方法缺失: {method}")
                        phase_details[f"method_{method}"] = "缺失"

            # 2. 检查工具调用记录器
            recorder_file = self.project_root / "intelligent_project_analyzer" / "agents" / "tool_callback.py"
            if recorder_file.exists():
                phase_details["tool_call_recorder"] = "文件存在"
                content = recorder_file.read_text(encoding="utf-8")
                if "on_tool_start" in content and "on_tool_end" in content:
                    phase_details["callback_methods"] = "完整"
                else:
                    self.report.add_issue("warning", "Phase2", "回调方法不完整")
            else:
                self.report.add_issue("critical", "Phase2", "tool_call_recorder.py不存在")

            # 3. 检查tool_creator逻辑 (实际可能在ToolFactory中)
            phase_details["tool_creator"] = "通过ToolFactory统一管理"

            # 4. 尝试导入ArXiv工具（测试可用性）
            try:
                from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

                tool = ArxivSearchTool()
                phase_details["arxiv_tool_instantiation"] = "成功"

                # 检查arxiv库是否可用
                import arxiv

                phase_details["arxiv_library"] = f"已安装 (version: {getattr(arxiv, '__version__', 'unknown')})"
            except ImportError as e:
                self.report.add_issue("critical", "Phase2", f"ArXiv工具导入失败: {str(e)}")
                phase_details["arxiv_tool_instantiation"] = f"失败: {str(e)}"
            except Exception as e:
                self.report.add_issue("warning", "Phase2", f"ArXiv工具实例化异常: {str(e)}")
                phase_details["arxiv_tool_instantiation"] = f"异常: {str(e)}"

            status = (
                "pass"
                if not any(
                    i["severity"] == "critical" and i["phase"] == "Phase2" for i in self.report.results["issues"]
                )
                else "fail"
            )
            self.report.add_phase_result("Phase2_ToolExecution", status, phase_details)

        except Exception as e:
            self.report.add_issue("critical", "Phase2", f"检查异常: {str(e)}")
            self.report.add_phase_result("Phase2_ToolExecution", "fail", {"error": str(e)})

    async def check_phase3_reference_extraction(self):
        """阶段3: 检查引用提取与状态合并"""
        print("🔍 阶段3: 检查引用提取与状态合并...")
        phase_details = {}

        try:
            # 1. 检查add_references_to_state节点（可能在workflow/nodes/或直接在workflow中）
            ref_state_files = [
                self.project_root
                / "intelligent_project_analyzer"
                / "workflow"
                / "nodes"
                / "add_references_to_state.py",
                self.project_root / "intelligent_project_analyzer" / "workflow" / "main_workflow.py",
            ]
            ref_state_file = next((f for f in ref_state_files if f.exists()), None)
            if ref_state_file is None:
                self.report.add_issue("critical", "Phase3", "引用状态合并逻辑未找到")
                phase_details["add_references_to_state"] = "文件不存在"
            else:
                phase_details["add_references_to_state"] = "文件存在"
                content = ref_state_file.read_text(encoding="utf-8")
                if "get_search_references" in content:
                    phase_details["get_search_references_call"] = "存在"
                else:
                    self.report.add_issue("warning", "Phase3", "未发现get_search_references调用")

            # 2. 检查SearchReference数据模型
            schema_files = [
                self.project_root / "intelligent_project_analyzer" / "workflow" / "state.py",
                self.project_root / "intelligent_project_analyzer" / "api" / "schemas.py",
            ]
            for schema_file in schema_files:
                if schema_file.exists():
                    content = schema_file.read_text(encoding="utf-8")
                    if "SearchReference" in content or "search_reference" in content:
                        phase_details[f"SearchReference_model_{schema_file.name}"] = "定义存在"
                        # 检查字段
                        if "source_tool" in content and "title" in content:
                            phase_details[f"SearchReference_fields_{schema_file.name}"] = "完整"
                        break

            # 3. 检查ToolCallRecorder的get_search_references方法
            recorder_file = self.project_root / "intelligent_project_analyzer" / "agents" / "tool_callback.py"
            if recorder_file.exists():
                content = recorder_file.read_text(encoding="utf-8")
                if "def get_search_references" in content:
                    phase_details["get_search_references_method"] = "存在"
                    # 检查是否处理ArXiv
                    if "arxiv" in content.lower():
                        phase_details["arxiv_reference_handling"] = "存在处理逻辑"
                    else:
                        self.report.add_issue("warning", "Phase3", "get_search_references未明确处理ArXiv")
                else:
                    self.report.add_issue("critical", "Phase3", "get_search_references方法缺失")

            status = (
                "pass"
                if not any(
                    i["severity"] == "critical" and i["phase"] == "Phase3" for i in self.report.results["issues"]
                )
                else "fail"
            )
            self.report.add_phase_result("Phase3_ReferenceExtraction", status, phase_details)

        except Exception as e:
            self.report.add_issue("critical", "Phase3", f"检查异常: {str(e)}")
            self.report.add_phase_result("Phase3_ReferenceExtraction", "fail", {"error": str(e)})

    async def check_phase4_data_transmission(self):
        """阶段4: 检查数据传输链路"""
        print("🔍 阶段4: 检查数据传输链路...")
        phase_details = {}

        try:
            # 1. 检查WebSocket推送节点（可能在workflow中）
            ws_pusher_file = self.project_root / "intelligent_project_analyzer" / "workflow" / "main_workflow.py"
            if ws_pusher_file.exists():
                phase_details["websocket_pusher"] = "文件存在"
                content = ws_pusher_file.read_text(encoding="utf-8")
                if "search_references" in content:
                    phase_details["search_references_broadcast"] = "存在推送逻辑"
                else:
                    self.report.add_issue("warning", "Phase4", "WebSocket推送未明确包含search_references")
            else:
                self.report.add_issue("critical", "Phase4", "websocket_pusher.py不存在")

            # 2. 检查前端ReportDetailClient
            frontend_client = (
                self.project_root
                / "frontend-nextjs"
                / "src"
                / "app"
                / "report"
                / "[sessionId]"
                / "ReportDetailClient.tsx"
            )
            if frontend_client.exists():
                phase_details["ReportDetailClient"] = "文件存在"
                content = frontend_client.read_text(encoding="utf-8")
                if "search_references" in content or "searchReferences" in content:
                    phase_details["frontend_search_references_handling"] = "存在处理逻辑"
                else:
                    self.report.add_issue("warning", "Phase4", "前端未发现search_references处理")
            else:
                self.report.add_issue("warning", "Phase4", "ReportDetailClient.tsx未找到")

            # 3. 检查SearchReferences组件
            search_ref_component = (
                self.project_root / "frontend-nextjs" / "src" / "components" / "report" / "SearchReferences.tsx"
            )
            if search_ref_component.exists():
                phase_details["SearchReferences_component"] = "文件存在"
                content = search_ref_component.read_text(encoding="utf-8")
                if "arxiv" in content.lower():
                    phase_details["arxiv_ui_support"] = "UI支持ArXiv"
                else:
                    self.report.add_issue("warning", "Phase4", "SearchReferences组件未明确支持ArXiv展示")
            else:
                self.report.add_issue("warning", "Phase4", "SearchReferences.tsx未找到")

            # 4. 检查API端点
            api_server_file = self.project_root / "intelligent_project_analyzer" / "api" / "server.py"
            if api_server_file.exists():
                phase_details["api_server"] = "文件存在"
            else:
                self.report.add_issue("warning", "Phase4", "API server.py未找到")

            status = (
                "pass"
                if not any(
                    i["severity"] == "critical" and i["phase"] == "Phase4" for i in self.report.results["issues"]
                )
                else "fail"
            )
            self.report.add_phase_result("Phase4_DataTransmission", status, phase_details)

        except Exception as e:
            self.report.add_issue("critical", "Phase4", f"检查异常: {str(e)}")
            self.report.add_phase_result("Phase4_DataTransmission", "fail", {"error": str(e)})

    async def check_phase5_log_traceability(self):
        """阶段5: 检查日志追踪能力"""
        print("🔍 阶段5: 检查日志追踪能力...")
        phase_details = {}

        try:
            # 1. 检查logs/tool_calls目录
            tool_calls_dir = self.project_root / "logs" / "tool_calls"
            if tool_calls_dir.exists():
                phase_details["tool_calls_log_dir"] = "目录存在"
                # 统计JSONL文件
                jsonl_files = list(tool_calls_dir.glob("*.jsonl"))
                phase_details["jsonl_log_files_count"] = len(jsonl_files)

                if jsonl_files:
                    # 读取最新日志文件
                    latest_log = max(jsonl_files, key=lambda f: f.stat().st_mtime)
                    phase_details["latest_log_file"] = latest_log.name

                    # 检查是否有ArXiv调用记录
                    arxiv_calls = []
                    try:
                        with open(latest_log, "r", encoding="utf-8") as f:
                            for line in f:
                                try:
                                    record = json.loads(line)
                                    if record.get("tool_name", "").lower() == "arxiv_search":
                                        arxiv_calls.append(record)
                                except json.JSONDecodeError:
                                    continue

                        phase_details["arxiv_calls_in_latest_log"] = len(arxiv_calls)
                        if arxiv_calls:
                            phase_details["sample_arxiv_call"] = {
                                "session_id": arxiv_calls[0].get("session_id"),
                                "status": arxiv_calls[0].get("status"),
                                "timestamp": arxiv_calls[0].get("start_time"),
                            }
                        else:
                            self.report.add_issue("info", "Phase5", "最近日志中未发现ArXiv调用记录")
                    except Exception as e:
                        self.report.add_issue("warning", "Phase5", f"读取日志文件失败: {str(e)}")
                else:
                    self.report.add_issue("warning", "Phase5", "tool_calls目录为空，无历史日志")
            else:
                self.report.add_issue("warning", "Phase5", "logs/tool_calls目录不存在")
                phase_details["tool_calls_log_dir"] = "目录不存在"

            # 2. 检查会话数据目录
            data_dir = self.project_root / "data"
            if data_dir.exists():
                phase_details["data_dir"] = "目录存在"
                session_files = list(data_dir.glob("session_*.json"))
                phase_details["session_files_count"] = len(session_files)
            else:
                self.report.add_issue("warning", "Phase5", "data目录不存在")

            status = "pass"  # 日志问题不影响整体功能
            self.report.add_phase_result("Phase5_LogTraceability", status, phase_details)

        except Exception as e:
            self.report.add_issue("warning", "Phase5", f"检查异常: {str(e)}")
            self.report.add_phase_result("Phase5_LogTraceability", "warning", {"error": str(e)})

        # 生成修复建议
        self._generate_recommendations()

    def _generate_recommendations(self):
        """根据诊断结果生成修复建议"""
        issues = self.report.results["issues"]

        # 按严重程度分类
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        warning_issues = [i for i in issues if i["severity"] == "warning"]

        if critical_issues:
            self.report.add_recommendation("发现严重问题，ArXiv工具可能完全无法工作", "优先修复所有critical级别问题")

        # 针对性建议
        for issue in critical_issues:
            if "文件不存在" in issue["message"]:
                self.report.add_recommendation(f"缺失关键文件: {issue['message']}", "检查代码仓库完整性，可能需要重新克隆或恢复文件")
            elif "导入失败" in issue["message"]:
                self.report.add_recommendation("ArXiv工具导入失败", "执行: pip install arxiv -U")
            elif "V4角色未配置" in issue["message"]:
                self.report.add_recommendation("V4角色缺少ArXiv权限配置", "在expert_factory.py的role_tool_mapping中为V4添加'arxiv'")

        for issue in warning_issues:
            if "未明确处理ArXiv" in issue["message"]:
                self.report.add_recommendation(
                    "引用提取逻辑可能遗漏ArXiv", "检查tool_call_recorder.py的get_search_references方法，确保正确映射arxiv_search工具"
                )
            elif "UI支持" in issue["message"]:
                self.report.add_recommendation("前端可能未正确展示ArXiv结果", "检查SearchReferences.tsx是否正确处理source_tool='arxiv'")

        if not critical_issues and not warning_issues:
            self.report.add_recommendation("代码结构检查通过", "建议执行端到端测试验证实际功能")


async def main():
    """主函数"""
    diagnostics = ArXivDiagnostics()
    await diagnostics.run_all_checks()


if __name__ == "__main__":
    asyncio.run(main())
