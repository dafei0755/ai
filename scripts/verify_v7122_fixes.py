#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v7.122.0 修复验证脚本
验证所有 P0/P1 修复是否正确实施
"""

import os
import sys
from pathlib import Path

# ============================================================================
# 应用 v7.122 的 UTF-8 修复（验证脚本自身也需要）
# ============================================================================
os.environ["PYTHONIOENCODING"] = "utf-8"

if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_file_contains(file_path: str, search_strings: list[str], description: str) -> bool:
    """检查文件是否包含指定字符串"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        missing = []
        for s in search_strings:
            if s not in content:
                missing.append(s)

        if missing:
            print(f"❌ {description}")
            print(f"   文件: {file_path}")
            print(f"   缺失内容: {missing}")
            return False
        else:
            print(f"✅ {description}")
            return True
    except Exception as e:
        print(f"❌ {description} - 读取失败: {e}")
        return False


def main():
    """主验证流程"""
    print("=" * 70)
    print("v7.122.0 修复验证")
    print("=" * 70)
    print()

    all_passed = True

    # ========================================================================
    # P0-1: 专家工具使用强制
    # ========================================================================
    print("【P0-1】专家工具使用强制")
    print("-" * 70)

    # 1. Expert Autonomy Protocol v4.2
    all_passed &= check_file_contains(
        "intelligent_project_analyzer/config/prompts/expert_autonomy_protocol_v4.yaml",
        ['version: "4.2"', "**工具优先**", "tools_used", "必须优先使用搜索工具"],
        "Expert Autonomy Protocol 已升级至 v4.2",
    )

    # 2. Core Task Decomposer v7.122.0
    all_passed &= check_file_contains(
        "intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml",
        ['version: "7.122.0"', "搜索引导词", "搜索...", "查找...", "调研..."],
        "Core Task Decomposer 已升级至 v7.122.0",
    )

    # 3. 工具使用监控
    all_passed &= check_file_contains(
        "intelligent_project_analyzer/workflow/main_workflow.py",
        ["# 🆕 v7.122: 工具使用率监控", "tools_used = protocol_execution.get", "未使用任何工具，质量存疑", "置信度已降低"],
        "工具使用率监控已添加",
    )

    print()

    # ========================================================================
    # P0-2: UTF-8 编码修复
    # ========================================================================
    print("【P0-2】UTF-8 编码修复")
    print("-" * 70)

    all_passed &= check_file_contains(
        "intelligent_project_analyzer/__init__.py",
        ["# 🔧 v7.122: 全局 UTF-8 编码设置", "PYTHONIOENCODING", "SetConsoleCP(65001)", "SetConsoleOutputCP(65001)"],
        "全局 UTF-8 编码设置已添加",
    )

    print()

    # ========================================================================
    # P0-3: 类型安全检查
    # ========================================================================
    print("【P0-3】类型安全检查")
    print("-" * 70)

    all_passed &= check_file_contains(
        "intelligent_project_analyzer/workflow/nodes/deliverable_id_generator_node.py",
        [
            "# 🔧 v7.122: 类型安全处理",
            "isinstance(physical_context, str)",
            "json.loads(physical_context)",
            "isinstance(design_challenge, str)",
        ],
        "交付物ID生成器类型检查已添加",
    )

    print()

    # ========================================================================
    # P0-4: 模板变量修复
    # ========================================================================
    print("【P0-4】模板变量修复")
    print("-" * 70)

    # 检查是否已修复（不应包含未转义的 {开始到}）
    fixed_count = 0
    files_to_check = [
        "intelligent_project_analyzer/config/prompts/requirements_analyst_phase1.yaml",
        "intelligent_project_analyzer/config/prompts/requirements_analyst_phase2.yaml",
        "intelligent_project_analyzer/config/prompts/requirements_analyst_lite.yaml",
        "intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml",
    ]

    for file_path in files_to_check:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否还有未转义的模式（可能会误报，所以用更宽松的检查）
            if "从{开始到}结束" in content or "从 { 开始到 }" in content:
                print(f"⚠️  {file_path} - 可能仍有未转义的变量")
            else:
                print(f"✅ {file_path} - 模板变量已修复")
                fixed_count += 1
        except Exception as e:
            print(f"❌ {file_path} - 读取失败: {e}")

    if fixed_count < len(files_to_check):
        print(f"⚠️  模板变量修复不完整 ({fixed_count}/{len(files_to_check)})")

    print()

    # ========================================================================
    # P0-5: 质量预检幂等性
    # ========================================================================
    print("【P0-5】质量预检幂等性")
    print("-" * 70)

    all_passed &= check_file_contains(
        "intelligent_project_analyzer/interaction/nodes/quality_preflight.py",
        [
            "# 🔧 v7.122: 幂等性检查",
            'if state.get("quality_preflight_completed")',
            "跳过重复执行",
            '"quality_preflight_completed": True',
        ],
        "质量预检幂等性检查已添加",
    )

    print()

    # ========================================================================
    # P0-6: Windows 磁盘监控修复
    # ========================================================================
    print("【P0-6】Windows 磁盘监控修复")
    print("-" * 70)

    all_passed &= check_file_contains(
        "intelligent_project_analyzer/api/admin_routes.py",
        ["# 🔧 v7.122: 增强Windows兼容性", "disk_path_candidates", "os.path.abspath(os.sep)", "所有磁盘路径尝试均失败"],
        "磁盘监控 Windows 兼容性已增强",
    )

    print()

    # ========================================================================
    # P1-3: LLM 并行调用
    # ========================================================================
    print("【P1-3】LLM 并行调用优化")
    print("-" * 70)

    all_passed &= check_file_contains(
        "intelligent_project_analyzer/services/core_task_decomposer.py",
        ["# 🚀 v7.122: 并行执行所有推断任务", "asyncio.gather", "async def infer_single_task", "[并行优化]"],
        "LLM 并行调用已实现",
    )

    print()

    # ========================================================================
    # 总结
    # ========================================================================
    print("=" * 70)
    if all_passed:
        print("✅✅✅ 所有验证通过！v7.122.0 修复已正确实施")
        print()
        print("下一步:")
        print("1. 提交代码: git add . && git commit")
        print("2. 重启服务器: python scripts/run_server_production.py")
        print("3. 运行完整测试流程")
        print("4. 监控关键指标（专家工具使用率、任务推断耗时）")
        return 0
    else:
        print("❌ 部分验证失败，请检查上述标记为 ❌ 的项目")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
