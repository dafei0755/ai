"""
需求分析师唯一主实现验证测试 (F-01)

验证工作流主路径只调用 RequirementsAnalystAgentV2，
旧 RequirementsAnalystAgent 未被任何活跃工作流节点直接导入。

对应架构决策：
- 主实现：RequirementsAnalystAgentV2（requirements_analyst_agent.py）
- Phase2 策略：始终执行（should_execute_phase2 永远返回 "phase2"）
- 旧实现：RequirementsAnalystAgent（requirements_analyst.py）已标记 HISTORICAL，
  计划 2026-04-04 删除
"""
import ast
import importlib
from pathlib import Path

import pytest


@pytest.mark.unit
class TestRequirementsAnalystUniqueness:
    """验证 RequirementsAnalyst 唯一主实现约束"""

    def test_requirements_nodes_imports_v2_not_v1(self):
        """requirements_nodes.py 只导入 RequirementsAnalystAgentV2，不直接导入旧 RequirementsAnalystAgent"""
        nodes_file = Path(
            "intelligent_project_analyzer/workflow/nodes/requirements_nodes.py"
        )
        assert nodes_file.exists(), f"requirements_nodes.py 文件不存在: {nodes_file}"

        source = nodes_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        v1_imports = []
        v2_imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                for name in names:
                    if name == "RequirementsAnalystAgent":
                        v1_imports.append(f"from {module} import {name}")
                    if name == "RequirementsAnalystAgentV2":
                        v2_imports.append(f"from {module} import {name}")

        assert len(v1_imports) == 0, (
            f"requirements_nodes.py 不应直接导入旧 RequirementsAnalystAgent（F-01）。"
            f"发现导入: {v1_imports}"
        )
        assert len(v2_imports) > 0, (
            "requirements_nodes.py 应导入 RequirementsAnalystAgentV2，但未找到。"
            "请确认主工作流节点使用的是 V2 实现。"
        )

    def test_phase2_routing_always_executes(self):
        """should_execute_phase2 路由函数始终返回 'phase2'（F-01 契约验证）"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import (
            should_execute_phase2,
        )

        # 测试各种可能的输入状态
        test_cases = [
            {"info_status": "sufficient", "node_path": []},
            {"info_status": "insufficient", "node_path": []},
            {"info_status": "unknown", "node_path": []},
            {},  # 空状态
        ]

        for state in test_cases:
            result = should_execute_phase2(state)
            assert result == "phase2", (
                f"should_execute_phase2 对输入 {state} 返回 {result!r}，"
                f"应始终返回 'phase2'（设计决策：Phase2 绝不跳过）"
            )

    def test_v1_agent_has_historical_marker(self):
        """旧 RequirementsAnalystAgent 文件头部应包含 HISTORICAL 标记"""
        ra_file = Path("intelligent_project_analyzer/agents/requirements_analyst.py")
        assert ra_file.exists(), f"requirements_analyst.py 不存在: {ra_file}"

        # 读取前 10 行检查 HISTORICAL 标记
        lines = ra_file.read_text(encoding="utf-8").splitlines()[:10]
        header = "\n".join(lines)

        assert "HISTORICAL" in header, (
            "requirements_analyst.py 应在文件头部标注 HISTORICAL 标记，"
            "以表明这是已被 V2 取代的历史实现。"
            f"当前头部内容:\n{header}"
        )

    def test_v2_is_importable_and_executable(self):
        """RequirementsAnalystAgentV2 可正常导入且类存在"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import (
            RequirementsAnalystAgentV2,
        )

        assert RequirementsAnalystAgentV2 is not None
        assert callable(RequirementsAnalystAgentV2)
        # 验证关键方法存在
        assert hasattr(RequirementsAnalystAgentV2, "execute"), "V2 应有 execute 方法"

    def test_main_workflow_node_uses_v2(self):
        """主工作流中实际创建的 RA 实例是 V2（通过源码静态分析）"""
        nodes_file = Path(
            "intelligent_project_analyzer/workflow/nodes/requirements_nodes.py"
        )
        source = nodes_file.read_text(encoding="utf-8")

        # 工作流节点中应该使用 V2 实例化
        assert "RequirementsAnalystAgentV2(" in source, (
            "requirements_nodes.py 中应调用 RequirementsAnalystAgentV2(...) 进行实例化，"
            "但未找到对应调用。"
        )
        # 不应该直接实例化旧 V1
        assert "RequirementsAnalystAgent(" not in source.replace(
            "RequirementsAnalystAgentV2(", ""
        ), (
            "requirements_nodes.py 中不应直接实例化旧 RequirementsAnalystAgent（F-01）。"
        )
