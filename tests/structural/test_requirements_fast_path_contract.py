"""
ST: Requirements Fast Path 合同测试

目标：
1) 锁定默认主链静态边不变（secondary -> step3）
2) 锁定无 direct static edge: secondary -> project_director
3) 锁定 fast-path 开关定义与默认值
4) 锁定 security 节点内存在动态短路与可观测标记

说明：
- 本文件为结构化/契约测试，主要做静态源码断言。
- 动态行为（Command 跳转、guard 分支）由 unit 测试
  tests/unit/test_requirements_fast_path_guard.py 覆盖。
"""

from __future__ import annotations

import pathlib
import re

import pytest


REPO_ROOT = pathlib.Path(__file__).parents[2]
MAIN_WORKFLOW_FILE = REPO_ROOT / "intelligent_project_analyzer" / "workflow" / "main_workflow.py"
FEATURE_FLAGS_FILE = REPO_ROOT / "intelligent_project_analyzer" / "config" / "feature_flags.py"
SECURITY_NODES_FILE = REPO_ROOT / "intelligent_project_analyzer" / "workflow" / "nodes" / "security_nodes.py"


def _read(path: pathlib.Path) -> str:
    assert path.exists(), f"文件不存在: {path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.unit
class TestRequirementsFastPathContract:
    def test_secondary_static_edge_keeps_default_path_to_step3(self):
        src = _read(MAIN_WORKFLOW_FILE)
        assert 'workflow.add_edge("unified_input_validator_secondary", "progressive_step3_gap_filling")' in src, (
            "冻结约束被破坏：secondary 默认静态边必须仍指向 progressive_step3_gap_filling"
        )

    def test_secondary_has_no_direct_static_edge_to_project_director(self):
        src = _read(MAIN_WORKFLOW_FILE)
        assert 'workflow.add_edge("unified_input_validator_secondary", "project_director")' not in src, (
            "检测到 secondary 直接静态边到 project_director，违反冻结约束"
        )

    def test_feature_flag_declared_with_default_false(self):
        src = _read(FEATURE_FLAGS_FILE)
        pattern = re.compile(
            r"ENABLE_REQUIREMENTS_FAST_PATH\s*:\s*bool\s*=\s*os\.getenv\(\s*\"ENABLE_REQUIREMENTS_FAST_PATH\"\s*,\s*\"false\"\s*\)",
            re.DOTALL,
        )
        assert pattern.search(src), "ENABLE_REQUIREMENTS_FAST_PATH 未定义或默认值不是 false"

    def test_secondary_node_contains_dynamic_short_circuit_command(self):
        src = _read(SECURITY_NODES_FILE)
        assert "ENABLE_REQUIREMENTS_FAST_PATH" in src
        assert "_can_apply_requirements_fast_path" in src
        assert 'return Command(update=result, goto="project_director")' in src, (
            "security 节点缺少 fast-path 动态短路 Command 到 project_director"
        )

    def test_secondary_node_contains_fast_path_observability_markers(self):
        src = _read(SECURITY_NODES_FILE)
        required_markers = [
            '"requirements_fast_path"',
            '"questionnaire_summary_skipped"',
            '"progressive_step3_skipped"',
            '"progressive_step2_skipped"',
            '"requirements_fast_path_guard"',
        ]
        missing = [m for m in required_markers if m not in src]
        assert not missing, f"security 节点缺少 fast-path 可观测标记: {missing}"
