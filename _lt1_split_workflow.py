#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LT-1 Migration Script: Automatically extract MainWorkflow methods into Mixin files.

Usage:
    python _lt1_split_workflow.py [--dry-run]

This script:
1. Parses main_workflow.py using Python AST to get exact method boundaries
2. Groups methods into 5 categories
3. Generates 5 Mixin files in workflow/nodes/
4. Prints the modified main_workflow.py class definition

Run with --dry-run to preview without writing files.
"""
from __future__ import annotations

import ast
import re
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple

WORKFLOW_PATH = Path("intelligent_project_analyzer/workflow/main_workflow.py")
NODES_DIR = Path("intelligent_project_analyzer/workflow/nodes")

# ─── Method groupings (by method name, without leading underscore is fine) ───
# Key: mixin_file_stem, Value: list of method names that belong there
GROUPS: Dict[str, List[str]] = {
    "security_nodes": [
        "_unified_input_validator_initial_node",
        "_input_rejected_node",
        "_unified_input_validator_secondary_node",
        "_report_guard_node",
    ],
    "requirements_nodes": [
        "_requirements_analyst_node",
        "_output_intent_detection_node",
        "_feasibility_analyst_node",
        "_calibration_questionnaire_node",
        "_progressive_step1_node",
        "_progressive_step2_node",
        "_progressive_step3_node",
        "_questionnaire_summary_node",
    ],
    "planning_nodes": [
        "_find_matching_role",
        "_project_director_node",
        "_deliverable_id_generator_node",
        "_search_query_generator_node",
        "_role_task_unified_review_node",
        "_role_selection_quality_review_node",
        "_quality_preflight_node",
        "_continue_to_first_batch_agents",
        "_continue_to_second_batch_agents",
    ],
    "execution_nodes": [
        "_execute_agent_node",
        "_batch_executor_node",
        "_execute_agent_with_semaphore",
        "_execute_single_agent_with_timing",
        "_create_batch_sends",
    ],
    "aggregation_nodes": [
        "_intermediate_aggregator_node",
        "_intermediate_aggregator_node_legacy",
        "_detect_challenges_node",
        "_route_after_challenge_detection",
        "_batch_router_node",
        "_batch_strategy_review_node",
        "_manual_review_node",
        "_result_aggregator_node",
        "_projection_dispatcher_node",
        "_pdf_generator_node",
        "_user_question_node",
        "_route_from_batch_aggregator",
        "_route_after_pdf_generator",
        "_route_after_analysis_review",
        "_route_after_user_question",
        "run",
        "_filter_tools_for_role",
        "_build_context_for_expert",
    ],
}

# Reverse map: method → group
METHOD_TO_GROUP: Dict[str, str] = {m: g for g, methods in GROUPS.items() for m in methods}

# Friendly class names
MIXIN_CLASS_NAMES = {
    "security_nodes": "SecurityNodesMixin",
    "requirements_nodes": "RequirementsNodesMixin",
    "planning_nodes": "PlanningNodesMixin",
    "execution_nodes": "ExecutionNodesMixin",
    "aggregation_nodes": "AggregationNodesMixin",
}

# Module docstrings for each mixin
MIXIN_DOCS = {
    "security_nodes": "LT-1 安全节点 Mixin — 输入验证、拒绝、报告审核",
    "requirements_nodes": "LT-1 需求节点 Mixin — 需求分析师、可行性、问卷流程",
    "planning_nodes": "LT-1 规划节点 Mixin — 项目总监、角色选择、任务分派、质量预检",
    "execution_nodes": "LT-1 执行节点 Mixin — 动态批次执行、Agent 并发调度",
    "aggregation_nodes": "LT-1 聚合节点 Mixin — 批次路由、挑战检测、结果聚合、输出生成",
}


def get_method_line_ranges(source: str) -> Dict[str, Tuple[int, int]]:
    """
    Parse the MainWorkflow class and return {method_name: (start_line, end_line)} (1-indexed).
    end_line is INCLUSIVE (last line of the method body).
    """
    tree = ast.parse(source)
    source_lines = source.splitlines()
    total_lines = len(source_lines)

    # Find MainWorkflow class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "MainWorkflow":
            class_node = node
            break
    else:
        raise RuntimeError("MainWorkflow class not found")

    # Collect (start_line, name) for all direct methods
    methods: List[Tuple[int, str]] = []
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append((item.lineno, item.name))

    # Also collect decorated methods
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check for decorators - start from first decorator
            dec_start = item.decorator_list[0].lineno if item.decorator_list else item.lineno
            methods_sorted = sorted(methods, key=lambda x: x[0])

    methods_sorted = sorted(methods, key=lambda x: x[0])

    # For each method, end_line = (next method's start_line - 1) or class end
    ranges: Dict[str, Tuple[int, int]] = {}
    for idx, (start, name) in enumerate(methods_sorted):
        if idx + 1 < len(methods_sorted):
            next_start = methods_sorted[idx + 1][0]
            end = next_start - 1
        else:
            end = total_lines
        ranges[name] = (start, end)

    return ranges


def get_method_with_decorators(
    source_lines: List[str], method_name: str, ranges: Dict[str, Tuple[int, int]]
) -> List[str]:
    """
    Return the lines for method `method_name`, including preceding @decorators.
    Also includes any blank lines / comments above the decorator that belong to this method.
    """
    start, end = ranges[method_name]
    # 0-indexed
    start_idx = start - 1
    end_idx = end - 1  # inclusive

    # Walk backwards to pick up decorators (lines starting with @)
    dec_start_idx = start_idx
    while dec_start_idx > 0:
        prev = source_lines[dec_start_idx - 1].strip()
        if prev.startswith("@") or prev.startswith("#"):
            dec_start_idx -= 1
        else:
            break

    return source_lines[dec_start_idx : end_idx + 1]


def build_mixin_file(
    group_name: str,
    method_names: List[str],
    source_lines: List[str],
    ranges: Dict[str, Tuple[int, int]],
    top_imports: str,
) -> str:
    """Build the full mixin file content for a given group."""
    class_name = MIXIN_CLASS_NAMES[group_name]
    doc = MIXIN_DOCS[group_name]

    # Gather method code
    method_blocks: List[str] = []
    for mname in method_names:
        if mname not in ranges:
            print(f"  [WARN] Method {mname!r} not found in MainWorkflow, skipping")
            continue
        lines = get_method_with_decorators(source_lines, mname, ranges)
        method_blocks.append("\n".join(lines))

    methods_joined = "\n\n".join(method_blocks)

    return f'''# -*- coding: utf-8 -*-
"""
{doc}

自动由 _lt1_split_workflow.py 生成 — 勿手动修改。
通过 Mixin 继承为 MainWorkflow 提供节点方法；完整 `self` 上下文由 MainWorkflow.__init__ 保证。
"""
# ruff: noqa (generated file)
# type: ignore
{top_imports}


class {class_name}:
    """
    {doc}

    Mixin for MainWorkflow. All methods receive full `self` access because
    MainWorkflow inherits from this class along with other Mixin classes.
    Do NOT instantiate this class directly.
    """

{methods_joined}
'''


def extract_top_imports(source: str, fix_relative_levels: bool = False) -> str:
    """
    Extract all import lines (and __future__) before the first class definition.
    If fix_relative_levels=True, adjusts relative import levels by +1
    (for code moved from workflow/ → workflow/nodes/).
    """
    lines = []
    for line in source.splitlines():
        if line.startswith("class "):
            break
        lines.append(line)
    # Keep import lines (including multi-line import continuation and TYPE_CHECKING blocks)
    # using paren depth tracking and block indentation tracking
    import_lines: list[str] = []
    paren_depth = 0
    in_type_checking = False

    for line in lines:
        stripped = line.strip()
        leading = len(line) - len(line.lstrip())

        if paren_depth > 0:
            # Inside a multi-line import — always keep continuation lines
            import_lines.append(line)
            paren_depth += line.count("(") - line.count(")")
        elif in_type_checking:
            if leading == 0 and stripped:
                # Back at col 0 — left the TYPE_CHECKING block
                in_type_checking = False
                # Process this line normally
                if line.startswith("if TYPE_CHECKING"):
                    import_lines.append(line)
                    in_type_checking = True
                elif line.startswith(("import ", "from ", "#")):
                    import_lines.append(line)
                    paren_depth += line.count("(") - line.count(")")
            else:
                # Still inside TYPE_CHECKING block — keep all indented lines
                import_lines.append(line)
                paren_depth += line.count("(") - line.count(")")
        else:
            if line.startswith("if TYPE_CHECKING"):
                import_lines.append(line)
                in_type_checking = True
            elif line.startswith(("import ", "from ", "#")):
                import_lines.append(line)
                paren_depth += line.count("(") - line.count(")")
            # else: skip blank lines, module docstrings, assignments

    if fix_relative_levels:
        # Adjust relative imports: "from ..X" → "from ...X", "from .X" → "from ..X"
        # Handles both top-level and indented (inside TYPE_CHECKING) imports
        adjusted = []
        for line in import_lines:
            stripped_line = line.lstrip()
            indent = line[: len(line) - len(stripped_line)]
            if stripped_line.startswith("from ."):
                rest = stripped_line[5:]  # e.g., "..agents.xxx import YYY"
                dot_count = 0
                for ch in rest:
                    if ch == ".":
                        dot_count += 1
                    else:
                        break
                new_line = indent + "from " + "." * (dot_count + 1) + rest[dot_count:]
                adjusted.append(new_line)
            else:
                adjusted.append(line)
        return "\n".join(adjusted)

    return "\n".join(import_lines)


def main(dry_run: bool = False) -> None:
    source = WORKFLOW_PATH.read_text(encoding="utf-8")
    source_lines = source.splitlines()

    print(f"Parsing {WORKFLOW_PATH} ({len(source_lines)} lines)...")
    ranges = get_method_line_ranges(source)
    print(f"Found {len(ranges)} methods in MainWorkflow:")
    for name, (s, e) in sorted(ranges.items(), key=lambda x: x[1][0]):
        group = METHOD_TO_GROUP.get(name, "<UNASSIGNED>")
        print(f"  L{s:4d}-{e:4d}  {name}  [{group}]")

    top_imports = extract_top_imports(source, fix_relative_levels=True)

    # Report unassigned methods
    all_grouped = set(m for grp in GROUPS.values() for m in grp)
    unassigned = [n for n in ranges if n not in all_grouped and n not in ("__init__", "_build_workflow_graph")]
    if unassigned:
        print(f"\n[WARN] {len(unassigned)} unassigned methods (will stay in main_workflow.py):")
        for u in unassigned:
            print(f"  {u}")

    # Build each mixin file
    results: Dict[str, str] = {}
    for group_name, method_names in GROUPS.items():
        content = build_mixin_file(group_name, method_names, source_lines, ranges, top_imports)
        results[group_name] = content

    if dry_run:
        for group_name, content in results.items():
            print(f"\n{'='*60}")
            print(f"  DRY-RUN: {NODES_DIR}/{group_name}.py ({len(content.splitlines())} lines)")
            print(f"{'='*60}")
            print(content[:500], "...\n[truncated]")
        print("\n[DRY-RUN] No files written.")
        return

    NODES_DIR.mkdir(parents=True, exist_ok=True)
    for group_name, content in results.items():
        out_path = NODES_DIR / f"{group_name}.py"
        out_path.write_text(content, encoding="utf-8")
        print(f"  Written: {out_path} ({len(content.splitlines())} lines)")

    print("\n✅ Mixin files generated.")
    print("\nNext step: Update main_workflow.py to inherit from all Mixin classes.")
    print("  See the generated file headers for import statements.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
