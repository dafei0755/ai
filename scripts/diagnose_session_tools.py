#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
会话工具使用情况全链路诊断 (v7.129)

用法:
    python scripts/diagnose_session_tools.py <session_id>

示例:
    python scripts/diagnose_session_tools.py 8pdwoxj8-20260104090435-9feb4b48

作者: Claude Code
创建: 2026-01-04
"""

import io
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 🔧 修复Windows GBK编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SessionToolsDiagnostic:
    """会话工具使用诊断器"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.issues = []
        self.warnings = []

    def run(self):
        """运行完整诊断"""
        print(f"\n{'=' * 70}")
        print(f"🔍 会话工具使用诊断: {self.session_id}")
        print(f"{'=' * 70}\n")

        # 检查1: 会话基本信息
        session_data = self.check_session_exists()
        if not session_data:
            return

        # 检查2: 角色信息
        self.check_role_info(session_data)

        # 检查3: 工具绑定日志
        self.check_tool_binding()

        # 检查4: 工具调用记录
        self.check_tool_calls()

        # 检查5: 搜索引用
        self.check_search_references(session_data)

        # 检查6: 综合报告
        self.generate_report()

    def check_session_exists(self) -> Optional[Dict]:
        """检查会话是否存在"""
        print("📋 [1/6] 检查会话基本信息...")

        db_path = project_root / "data" / "archived_sessions.db"
        if not db_path.exists():
            print(f"  ❌ 数据库不存在: {db_path}")
            self.issues.append("数据库文件不存在")
            return None

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM archived_sessions WHERE session_id = ?", (self.session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            print(f"  ❌ 会话不存在于数据库")
            self.issues.append("会话不存在")
            return None

        data = dict(row)
        print(f"  ✅ 会话状态: {data['status']}")
        print(f"  ✅ 创建时间: {data['created_at']}")
        print(f"  ✅ 模式: {data.get('mode', 'unknown')}")

        return data

    def check_role_info(self, session_data: Dict):
        """检查角色信息"""
        print("\n🎭 [2/6] 检查角色信息...")

        try:
            session_json = json.loads(session_data["session_data"])
            agent_results = session_json.get("agent_results", {})

            if not agent_results or agent_results == {}:
                print("  ⚠️  无agent_results - 专家结果未保存")
                self.warnings.append("专家结果为空")
            else:
                print(f"  ✅ 检测到 {len(agent_results)} 个专家")
                for role_id, result in list(agent_results.items())[:5]:
                    expert_name = result.get("expert_name", "Unknown")
                    print(f"     - {role_id}: {expert_name}")
        except Exception as e:
            print(f"  ❌ 解析session_data失败: {e}")
            self.issues.append("session_data解析失败")

    def check_tool_binding(self):
        """检查工具绑定日志"""
        print("\n🔧 [3/6] 检查工具绑定日志...")

        log_path = project_root / "logs" / "server.log"
        if not log_path.exists():
            print(f"  ⚠️  日志文件不存在: {log_path}")
            self.warnings.append("server.log不存在")
            return

        bind_logs = self._search_logs(pattern=r"绑定.*个工具|bind.*tools")

        if not bind_logs:
            print("  ❌ 未找到工具绑定日志")
            self.issues.append("🔴 工具未绑定到LLM")
        else:
            print(f"  ✅ 找到 {len(bind_logs)} 条工具绑定日志:")
            for log in bind_logs[:3]:
                print(f"     {log[:100]}...")

    def check_tool_calls(self):
        """检查工具调用记录"""
        print("\n📞 [4/6] 检查工具调用记录...")

        jsonl_path = project_root / "logs" / "tool_calls.jsonl"
        if not jsonl_path.exists():
            print(f"  ❌ tool_calls.jsonl 不存在")
            self.issues.append("🔴 工具调用日志文件缺失")
            return

        tool_calls = self._get_tool_calls_from_jsonl()

        if not tool_calls:
            print("  ❌ 无工具调用记录")
            self.issues.append("🔴 工具未被调用")
        else:
            print(f"  ✅ 找到 {len(tool_calls)} 条工具调用")
            tool_counts = {}
            for call in tool_calls:
                tool = call.get("tool_name", "unknown")
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

            for tool, count in tool_counts.items():
                print(f"     - {tool}: {count}次")

    def check_search_references(self, session_data: Dict):
        """检查搜索引用"""
        print("\n🔗 [5/6] 检查搜索引用...")

        try:
            session_json = json.loads(session_data["session_data"])
            search_refs = session_json.get("search_references", [])

            if not search_refs:
                print("  ❌ search_references为空")
                self.warnings.append("🟡 无搜索引用（可能是V2角色或工具未调用）")
            else:
                print(f"  ✅ 找到 {len(search_refs)} 条搜索引用")
                by_tool = {}
                for ref in search_refs:
                    tool = ref.get("source_tool", "unknown")
                    by_tool[tool] = by_tool.get(tool, 0) + 1

                for tool, count in sorted(by_tool.items()):
                    print(f"     - {tool}: {count}条")
        except Exception as e:
            print(f"  ❌ 解析search_references失败: {e}")

    def generate_report(self):
        """生成综合诊断报告"""
        print("\n📊 [6/6] 综合诊断报告...")

        if not self.issues and not self.warnings:
            print("  ✅ 所有检查通过，工具系统正常运行")
            return

        if self.issues:
            print("\n  ⚠️  发现以下问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"     {i}. {issue}")

        if self.warnings:
            print("\n  ℹ️  警告信息:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"     {i}. {warning}")

        # 提供修复建议
        print("\n💡 修复建议:")
        if any("工具未绑定" in issue for issue in self.issues):
            print("  1. 检查 main_workflow.py 是否传递 tools 参数")
            print("  2. 检查 ToolFactory 是否正常初始化")

        if any("工具未被调用" in issue for issue in self.issues):
            print("  1. 检查角色 prompt 是否包含工具调用指令")
            print("  2. 检查是否为 V2 角色（V2 仅用内部知识库）")
            print("  3. 运行: python scripts/test_tool_binding.py")

        if any("搜索引用" in warning for warning in self.warnings):
            print("  1. 确认角色类型（V2 默认无外部搜索）")
            print("  2. 检查 LLM 是否决策不调用工具")

    def _search_logs(self, pattern: str) -> List[str]:
        """搜索日志文件"""
        log_path = project_root / "logs" / "server.log"
        results = []

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if self.session_id in line and re.search(pattern, line, re.IGNORECASE):
                        results.append(line.strip())
        except Exception:
            pass

        return results

    def _get_tool_calls_from_jsonl(self) -> List[Dict]:
        """从JSONL获取工具调用"""
        jsonl_path = project_root / "logs" / "tool_calls.jsonl"
        calls = []

        try:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if self.session_id[:8] in data.get("deliverable_id", ""):
                            calls.append(data)
                    except:
                        pass
        except Exception:
            pass

        return calls


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("❌ 用法: python diagnose_session_tools.py <session_id>")
        print("\n示例:")
        print("  python scripts/diagnose_session_tools.py 8pdwoxj8-20260104090435-9feb4b48")
        sys.exit(1)

    session_id = sys.argv[1]
    diagnostic = SessionToolsDiagnostic(session_id)
    diagnostic.run()


if __name__ == "__main__":
    main()
