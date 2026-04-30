"""
需求分析子图节点包

Copilot 生成（2026-03-15）
包含 S1-S5 五个顺序执行节点：
  S1: 输入解构        — RawBriefPacket → structured_brief_parts
  S2: 目标锁定        — → locked_goals (冲突解决 + 边界确认)
  S3: 策略框架        — → strategy_framework (四区标注)
  S4: 战术分解        — → tactical_breakdown (专家分工 + 交付物 DAG)
  S5: 编译任务书      — → DesignTaskBook + ExecutionBlueprint (冻结)
"""

from intelligent_project_analyzer.workflow.nodes.requirements_analysis.s1_input_decompose import (
    S1InputDecomposeNode,
)
from intelligent_project_analyzer.workflow.nodes.requirements_analysis.s2_goal_locking import (
    S2GoalLockingNode,
)
from intelligent_project_analyzer.workflow.nodes.requirements_analysis.s3_strategy_framework import (
    S3StrategyFrameworkNode,
)
from intelligent_project_analyzer.workflow.nodes.requirements_analysis.s4_tactics_decompose import (
    S4TacticsDecomposeNode,
)
from intelligent_project_analyzer.workflow.nodes.requirements_analysis.s5_compile_taskbook import (
    S5CompileTaskbookNode,
)
from intelligent_project_analyzer.workflow.nodes.requirements_analysis.echo_card_node import (
    EchoCardNode,
)
from intelligent_project_analyzer.workflow.nodes.requirements_analysis.gap_completion_node import (
    GapCompletionNode,
    should_run_gap_completion,
)

__all__ = [
    "S1InputDecomposeNode",
    "S2GoalLockingNode",
    "S3StrategyFrameworkNode",
    "S4TacticsDecomposeNode",
    "S5CompileTaskbookNode",
    "EchoCardNode",
    "GapCompletionNode",
    "should_run_gap_completion",
]
