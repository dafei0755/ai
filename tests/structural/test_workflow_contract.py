"""
ST-4: workflow_contract.py 契约一致性验证测试 (F-02, F-06)

目标：
  确保 workflow_contract.py 中的节点名集合与 main_workflow.py
  实际注册的节点一致，且不包含已废弃节点。

  同时确保 workflow_runner.py 从契约源导入进度映射，
  不再手写副本。

方法：
  静态解析 main_workflow.py 收集注册节点，与契约对比。
  无需启动任何服务或 LLM 连接。

对应架构治理：
  F-02 — 进度映射与真实节点名不一致
  F-06 — 废弃节点 analysis_review 残留在进度映射

维护说明：
  新增节点时：
    1. 在 main_workflow.py 中 workflow.add_node(...)
    2. 同步更新 workflow/workflow_contract.py 的三个映射表
    3. 本测试会自动捕捉遗漏
"""
from __future__ import annotations

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).parents[2]
WORKFLOW_FILE = REPO_ROOT / "intelligent_project_analyzer" / "workflow" / "main_workflow.py"
WORKFLOW_RUNNER_FILE = REPO_ROOT / "intelligent_project_analyzer" / "api" / "workflow_runner.py"
CONTRACT_FILE = REPO_ROOT / "intelligent_project_analyzer" / "workflow" / "workflow_contract.py"


def _extract_registered_nodes(src: str) -> set[str]:
    """从 main_workflow.py 源码中提取 workflow.add_node(name, ...) 的节点名"""
    pattern = r'workflow\.add_node\(\s*["\']([a-z_][a-z_0-9]*)["\']'
    return set(re.findall(pattern, src))


@pytest.mark.unit
class TestWorkflowContractConsistency:
    """workflow_contract.py 与真实工作流图的一致性验证"""

    @pytest.fixture(scope="class")
    def workflow_src(self) -> str:
        assert WORKFLOW_FILE.exists(), f"main_workflow.py 不存在: {WORKFLOW_FILE}"
        return WORKFLOW_FILE.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def registered_nodes(self, workflow_src: str) -> set[str]:
        return _extract_registered_nodes(workflow_src)

    @pytest.fixture(scope="class")
    def contract_src(self) -> str:
        assert CONTRACT_FILE.exists(), f"workflow_contract.py 不存在: {CONTRACT_FILE}"
        return CONTRACT_FILE.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def contract_progress_nodes(self, contract_src: str) -> set[str]:
        """静态解析 NODE_PROGRESS 的键名（不 import，避免触发宿主包导入链）"""
        m = re.search(r'NODE_PROGRESS[^=]*=\s*\{(.*?)\n\}', contract_src, re.DOTALL)
        assert m, "无法在 workflow_contract.py 中找到 NODE_PROGRESS 定义"
        return set(re.findall(r'"([a-z_][a-z_0-9]*)"', m.group(1)))

    @pytest.fixture(scope="class")
    def contract_nodes(self, contract_src: str) -> set[str]:
        """静态解析 ACTIVE_NODE_NAMES 列表中的额外节点 + NODE_PROGRESS 键名"""
        m = re.search(r'ACTIVE_NODE_NAMES[^=]*=.*?\+\s*\[(.*?)\]', contract_src, re.DOTALL)
        extra: set[str] = set()
        if m:
            extra = set(re.findall(r'"([a-z_][a-z_0-9]*)"', m.group(1)))
        # 合并 NODE_PROGRESS 键名
        m2 = re.search(r'NODE_PROGRESS[^=]*=\s*\{(.*?)\n\}', contract_src, re.DOTALL)
        progress_keys: set[str] = set()
        if m2:
            progress_keys = set(re.findall(r'"([a-z_][a-z_0-9]*)"', m2.group(1)))
        return progress_keys | extra

    def test_contract_file_exists(self):
        """workflow_contract.py 文件必须存在"""
        assert CONTRACT_FILE.exists(), (
            f"workflow_contract.py 不存在: {CONTRACT_FILE}\n"
            "请创建该文件以建立单一契约源（F-02）"
        )

    def test_no_deprecated_nodes_in_progress_map(self, contract_progress_nodes: set[str]):
        """
        进度映射中不应包含已废弃节点（F-06）

        已废弃节点：
          - analysis_review（v2.2 废弃）
          - progressive_step2_info_gather（已重命名为 progressive_step2_radar）
          - progressive_step3_radar（已重命名为 progressive_step3_gap_filling）
        """
        _DEPRECATED_NODES = {
            "analysis_review",
            "progressive_step2_info_gather",
            "progressive_step3_radar",
            "role_selection_quality_review",
            "task_assignment_review",
        }
        deprecated_found = contract_progress_nodes & _DEPRECATED_NODES
        assert not deprecated_found, (
            f"NODE_PROGRESS 中发现已废弃节点（F-06）：{deprecated_found}\n"
            "请从 workflow_contract.py 的 NODE_PROGRESS 中移除这些废弃节点。"
        )

    def test_critical_nodes_in_contract(self, contract_nodes: set[str]):
        """核心主链路节点必须在契约中"""
        critical = {
            "unified_input_validator_initial",
            "requirements_analyst",
            "progressive_step2_radar",       # 真实节点名（非旧名 info_gather）
            "progressive_step3_gap_filling",  # 真实节点名（非旧名 radar）
            "questionnaire_summary",
            "project_director",
            "quality_preflight",
            "batch_executor",
            "batch_aggregator",
            "result_aggregator",
            "report_guard",
            "pdf_generator",
        }
        missing = critical - contract_nodes
        assert not missing, (
            f"核心节点未在 workflow_contract.ACTIVE_NODE_NAMES 中：{missing}\n"
            "请同步更新 workflow_contract.py"
        )

    def test_all_registered_nodes_in_contract(self, registered_nodes: set[str], contract_nodes: set[str]):
        """
        main_workflow.py 中注册的所有节点都应在契约中（F-02）

        允许契约包含主图之外的辅助节点，但主图节点不能缺失。
        """
        missing = registered_nodes - contract_nodes
        assert not missing, (
            f"main_workflow.py 注册了以下节点，但未在 workflow_contract.ACTIVE_NODE_NAMES 中（F-02）：\n"
            f"{sorted(missing)}\n"
            "请同步更新 workflow_contract.py"
        )

    def test_workflow_runner_imports_from_contract(self):
        """
        workflow_runner.py 必须从 workflow_contract 导入进度映射，
        不得维护手工副本（F-02）
        """
        assert WORKFLOW_RUNNER_FILE.exists(), f"workflow_runner.py 不存在: {WORKFLOW_RUNNER_FILE}"
        src = WORKFLOW_RUNNER_FILE.read_text(encoding="utf-8")

        assert "from intelligent_project_analyzer.workflow.workflow_contract import NODE_PROGRESS" in src, (
            "workflow_runner.py 应从 workflow_contract 导入 NODE_PROGRESS（F-02），"
            "而不是手工维护副本。"
        )

    def test_no_hardcoded_progress_dict_in_runner(self):
        """
        workflow_runner.py 不应再存在手工维护的 node_progress_map 字典（F-02）

        注意：允许存在 node_progress_map = NODE_PROGRESS（赋值引用），
        禁止的是 node_progress_map = { ... }（字面量）。
        """
        src = WORKFLOW_RUNNER_FILE.read_text(encoding="utf-8")

        # 检查是否仍有硬编码的字典字面量（包含废弃节点名作为键）
        deprecated_in_runner = [
            '"progressive_step2_info_gather"',
            '"progressive_step3_radar"',
            '"analysis_review": 0.',  # 只匹配赋值给进度值，避免误判注释
        ]
        for pattern in deprecated_in_runner:
            assert pattern not in src, (
                f"workflow_runner.py 仍包含废弃节点引用 {pattern!r}（F-06）\n"
                "请确认已用契约源替换手工进度映射。"
            )
