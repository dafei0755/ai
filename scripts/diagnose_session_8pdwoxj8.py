#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
会话 8pdwoxj8-20260106154858-dc82c8eb 完整诊断脚本

验证 v7.144 修复是否解决报告空白问题：
1. 检查归档会话数据完整性
2. 分析 project_director 执行情况
3. 验证数据流转链是否完整
4. 生成诊断报告
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class SessionDiagnostic:
    """会话诊断工具"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.workspace_root = Path(__file__).parent.parent
        self.archived_db = self.workspace_root / "data" / "archived_sessions.db"
        self.checkpoint_db = self.workspace_root / "data" / "checkpoints" / "workflow.db"
        self.report = []

    def print_section(self, title: str, symbol: str = "="):
        """打印章节标题"""
        line = symbol * 80
        self.report.append(f"\n{line}")
        self.report.append(f"{title}")
        self.report.append(f"{line}\n")
        print(f"\n{line}")
        print(title)
        print(f"{line}\n")

    def print_info(self, message: str, prefix: str = ""):
        """打印信息"""
        full_msg = f"{prefix}{message}"
        self.report.append(full_msg)
        print(full_msg)

    def analyze_archived_session(self):
        """分析归档会话数据"""
        self.print_section("📂 归档会话数据分析")

        if not self.archived_db.exists():
            self.print_info("❌ 归档数据库不存在", "  ")
            return None

        conn = sqlite3.connect(str(self.archived_db))
        cursor = conn.cursor()

        try:
            # 查询会话基本信息
            cursor.execute(
                """
                SELECT session_id, status, created_at, archived_at,
                       final_report, session_data, progress, current_stage
                FROM archived_sessions
                WHERE session_id = ?
            """,
                (self.session_id,),
            )

            row = cursor.fetchone()
            if not row:
                self.print_info(f"❌ 会话 {self.session_id} 不存在于归档数据库", "  ")
                return None

            session_id, status, created_at, archived_at, final_report, session_data_json, progress, current_stage = row

            self.print_info(f"✅ 找到归档会话: {session_id}", "  ")
            self.print_info(f"   状态: {status}", "  ")
            self.print_info(f"   创建时间: {created_at}", "  ")
            self.print_info(f"   归档时间: {archived_at}", "  ")
            self.print_info(f"   进度: {progress}%", "  ")
            self.print_info(f"   当前阶段: {current_stage}", "  ")
            self.print_info(f"   有最终报告: {bool(final_report)}", "  ")
            if final_report:
                self.print_info(f"   报告长度: {len(final_report)} 字符", "  ")

            # 解析会话数据
            try:
                if session_data_json:
                    session_data = json.loads(session_data_json)
                else:
                    self.print_info("   ⚠️ session_data 字段为空", "  ")
                    session_data = {}
            except Exception as e:
                self.print_info(f"   ⚠️ 会话数据JSON解析失败: {e}", "  ")
                session_data = {}

            return session_data

        finally:
            conn.close()

    def analyze_session_data_structure(self, session_data: dict):
        """分析会话数据结构"""
        self.print_section("🔍 会话数据结构分析")

        # 关键字段检查
        key_fields = [
            "structured_requirements",
            "restructured_requirements",
            "strategic_analysis",
            "execution_batches",
            "total_batches",
            "current_batch",
            "active_agents",
            "agent_results",
            "final_report",
            "pdf_path",
        ]

        for field in key_fields:
            value = session_data.get(field)
            if value is None:
                self.print_info(f"❌ {field}: None (缺失)", "  ")
            elif isinstance(value, (list, dict)) and len(value) == 0:
                self.print_info(f"⚠️ {field}: 空 {type(value).__name__}", "  ")
            elif isinstance(value, str) and len(value) < 10:
                self.print_info(f"⚠️ {field}: '{value}' (过短)", "  ")
            else:
                if isinstance(value, dict):
                    self.print_info(f"✅ {field}: dict ({len(value)} keys)", "  ")
                elif isinstance(value, list):
                    self.print_info(f"✅ {field}: list ({len(value)} items)", "  ")
                elif isinstance(value, str):
                    self.print_info(f"✅ {field}: str ({len(value)} chars)", "  ")
                else:
                    self.print_info(f"✅ {field}: {type(value).__name__} = {value}", "  ")

        return session_data

    def analyze_project_director_execution(self, session_data: dict):
        """分析 project_director 执行情况"""
        self.print_section("🎯 Project Director 执行分析")

        # 检查需求数据来源
        restructured = session_data.get("restructured_requirements")
        structured = session_data.get("structured_requirements")

        self.print_info("需求数据来源:", "  ")
        if restructured:
            self.print_info(f"  ✅ restructured_requirements 存在 ({len(str(restructured))} chars)", "    ")
        else:
            self.print_info("  ❌ restructured_requirements 不存在", "    ")

        if structured:
            self.print_info(f"  ✅ structured_requirements 存在 ({len(str(structured))} chars)", "    ")
        else:
            self.print_info("  ❌ structured_requirements 不存在", "    ")

        # 检查角色选择结果
        strategic_analysis = session_data.get("strategic_analysis")
        self.print_info("\nProject Director 输出:", "  ")

        if not strategic_analysis:
            self.print_info("  ❌ strategic_analysis 为空 - PROJECT DIRECTOR 未成功执行", "    ")
            return False

        if isinstance(strategic_analysis, dict):
            self.print_info(f"  ✅ strategic_analysis 类型: dict", "    ")

            # 检查关键字段
            roles = strategic_analysis.get("roles", [])
            execution_batches = strategic_analysis.get("execution_batches", [])

            self.print_info(f"  选中角色数量: {len(roles)}", "    ")
            self.print_info(f"  执行批次数量: {len(execution_batches)}", "    ")

            if len(execution_batches) == 0:
                self.print_info("  ❌ 执行批次为空 - 任务分配失败", "    ")
                return False
            else:
                self.print_info(f"  ✅ 执行批次已创建", "    ")
                for i, batch in enumerate(execution_batches):
                    batch_roles = batch.get("agents", [])
                    self.print_info(f"    Batch {i+1}: {len(batch_roles)} agents", "      ")
                return True
        else:
            self.print_info(f"  ⚠️ strategic_analysis 类型异常: {type(strategic_analysis)}", "    ")
            return False

    def analyze_workflow_execution(self, session_data: dict):
        """分析工作流执行情况"""
        self.print_section("⚙️ 工作流执行分析")

        total_batches = session_data.get("total_batches", 0)
        current_batch = session_data.get("current_batch", 0)
        agent_results = session_data.get("agent_results", {})

        self.print_info(f"总批次数: {total_batches}", "  ")
        self.print_info(f"当前批次: {current_batch}", "  ")
        self.print_info(f"专家结果数量: {len(agent_results)}", "  ")

        if total_batches == 0:
            self.print_info("  ❌ total_batches = 0 - 工作流异常", "    ")
            return False

        if len(agent_results) == 0:
            self.print_info("  ❌ 无专家执行结果 - 批次执行失败", "    ")
            return False

        self.print_info("  ✅ 专家执行完成:", "    ")
        for role_key, result in agent_results.items():
            if isinstance(result, dict):
                content_len = len(str(result.get("content", "")))
                self.print_info(f"    - {role_key}: {content_len} chars", "      ")
            else:
                self.print_info(f"    - {role_key}: {type(result)}", "      ")

        return True

    def analyze_report_generation(self, session_data: dict):
        """分析报告生成情况"""
        self.print_section("📄 报告生成分析")

        final_report = session_data.get("final_report")
        pdf_path = session_data.get("pdf_path")

        if not final_report:
            self.print_info("❌ final_report 不存在", "  ")
            return False

        if isinstance(final_report, str):
            report_len = len(final_report)
            self.print_info(f"✅ final_report 类型: str ({report_len} chars)", "  ")

            if report_len < 100:
                self.print_info("  ⚠️ 报告内容过短，可能损坏", "    ")
                self.print_info(f"  内容预览: {final_report[:100]}", "    ")
                return False
            else:
                self.print_info("  ✅ 报告内容长度正常", "    ")
        elif isinstance(final_report, dict):
            self.print_info(f"✅ final_report 类型: dict ({len(final_report)} keys)", "  ")

        if pdf_path:
            self.print_info(f"✅ PDF路径: {pdf_path}", "  ")

            # 检查实际文件
            pdf_file = Path(pdf_path)
            if pdf_file.exists():
                self.print_info(f"  ✅ PDF文件存在 ({pdf_file.stat().st_size} bytes)", "    ")
            else:
                self.print_info(f"  ⚠️ PDF文件不存在", "    ")

            # 检查 .md 或 .txt 文件
            md_path = str(pdf_path).replace(".pdf", ".md")
            txt_path = str(pdf_path).replace(".pdf", ".txt")

            if Path(md_path).exists():
                self.print_info(f"  ✅ Markdown文件存在 ({Path(md_path).stat().st_size} bytes)", "    ")
            elif Path(txt_path).exists():
                self.print_info(f"  ✅ 文本文件存在 ({Path(txt_path).stat().st_size} bytes)", "    ")
            else:
                self.print_info(f"  ⚠️ 文本文件不存在 (.md/.txt)", "    ")
        else:
            self.print_info("⚠️ pdf_path 不存在", "  ")

        return True

    def verify_v7_144_fixes(self, session_data: dict):
        """验证 v7.144 修复是否生效"""
        self.print_section("🔧 v7.144 修复验证")

        checks = []

        # 修复1: questionnaire_summary 数据保护
        self.print_info("修复1: questionnaire_summary 数据保护", "  ")
        agent_results = session_data.get("agent_results")
        final_report = session_data.get("final_report")

        if agent_results and final_report:
            self.print_info("  ✅ agent_results 和 final_report 均存在", "    ")
            checks.append(True)
        else:
            self.print_info("  ❌ 关键数据缺失，可能仍存在覆盖问题", "    ")
            checks.append(False)

        # 修复2: project_director 支持 restructured_requirements
        self.print_info("\n修复2: project_director 双路径支持", "  ")
        restructured = session_data.get("restructured_requirements")
        structured = session_data.get("structured_requirements")
        strategic_analysis = session_data.get("strategic_analysis")

        if restructured and strategic_analysis:
            self.print_info("  ✅ restructured_requirements 存在且 strategic_analysis 已生成", "    ")
            checks.append(True)
        elif structured and strategic_analysis:
            self.print_info("  ✅ structured_requirements 存在且 strategic_analysis 已生成", "    ")
            checks.append(True)
        else:
            self.print_info("  ❌ 需求数据或角色选择失败", "    ")
            checks.append(False)

        # 修复3: API 归档查询（需要实际测试）
        self.print_info("\n修复3: API 归档查询支持", "  ")
        self.print_info("  ℹ️ 需要通过 API 调用验证，此处跳过", "    ")

        # 修复4: PDF 文件读取
        self.print_info("\n修复4: PDF 文件读取逻辑", "  ")
        pdf_path = session_data.get("pdf_path")
        if pdf_path:
            md_path = str(pdf_path).replace(".pdf", ".md")
            txt_path = str(pdf_path).replace(".pdf", ".txt")

            if Path(md_path).exists() or Path(txt_path).exists():
                self.print_info("  ✅ 文本文件存在，可正常读取", "    ")
                checks.append(True)
            else:
                self.print_info("  ⚠️ 文本文件不存在", "    ")
                checks.append(False)
        else:
            self.print_info("  ⚠️ pdf_path 不存在", "    ")
            checks.append(False)

        return checks

    def generate_diagnosis_summary(self, checks: list):
        """生成诊断摘要"""
        self.print_section("📊 诊断摘要", "=")

        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c)

        self.print_info(f"总检查项: {total_checks}", "  ")
        self.print_info(f"通过检查: {passed_checks}", "  ")
        self.print_info(f"失败检查: {total_checks - passed_checks}", "  ")

        if passed_checks == total_checks:
            self.print_info("\n✅ v7.144 修复已生效，问题已解决", "  ")
            return True
        elif passed_checks > total_checks / 2:
            self.print_info("\n⚠️ v7.144 修复部分生效，仍有问题需要解决", "  ")
            return False
        else:
            self.print_info("\n❌ v7.144 修复未生效或存在其他问题", "  ")
            return False

    def save_report(self):
        """保存诊断报告"""
        report_path = self.workspace_root / f"SESSION_{self.session_id[:8]}_DIAGNOSIS.txt"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"会话诊断报告\n")
            f.write(f"会话ID: {self.session_id}\n")
            f.write(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n" + "\n".join(self.report))

        print(f"\n📁 诊断报告已保存: {report_path}")

    def run(self):
        """运行完整诊断"""
        print(f"\n🔍 开始诊断会话: {self.session_id}\n")

        # 1. 分析归档会话
        session_data = self.analyze_archived_session()
        if not session_data:
            self.print_info("❌ 无法继续诊断，会话数据缺失")
            self.save_report()
            return False

        # 2. 分析数据结构
        self.analyze_session_data_structure(session_data)

        # 3. 分析 project_director
        director_success = self.analyze_project_director_execution(session_data)

        # 4. 分析工作流执行
        workflow_success = self.analyze_workflow_execution(session_data)

        # 5. 分析报告生成
        report_success = self.analyze_report_generation(session_data)

        # 6. 验证 v7.144 修复
        fix_checks = self.verify_v7_144_fixes(session_data)

        # 7. 生成摘要
        all_checks = [director_success, workflow_success, report_success] + fix_checks
        overall_success = self.generate_diagnosis_summary(all_checks)

        # 8. 保存报告
        self.save_report()

        return overall_success


def main():
    """主函数"""
    session_id = "8pdwoxj8-20260106154858-dc82c8eb"

    diagnostic = SessionDiagnostic(session_id)
    success = diagnostic.run()

    if success:
        print("\n✅ 诊断完成：问题已解决")
        sys.exit(0)
    else:
        print("\n⚠️ 诊断完成：仍存在问题")
        sys.exit(1)


if __name__ == "__main__":
    main()
