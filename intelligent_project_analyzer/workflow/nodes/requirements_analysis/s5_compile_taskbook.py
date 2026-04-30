"""
S5 编译任务书节点

Copilot 生成（2026-03-15）

输入: 全部 S1-S4 产出字段
输出:
  - design_task_book: DesignTaskBook（序列化为 dict，冻结）
  - execution_blueprint: ExecutionBlueprint（序列化为 dict，冻结）
  - requirements_frozen: True  ← S1-S5 链路出口的关键标志

这是需求分析子图的出口节点。
一旦 requirements_frozen=True，后续节点禁止覆写 design_task_book。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    DAGNode,
    DesignTaskBook,
    ExecutionBlueprint,
    ReviewGate,
    StrategyZone,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState


class S5CompileTaskbookNode:
    """
    S5 编译任务书节点。

    LangGraph 注册示例：
        s5 = S5CompileTaskbookNode()
        graph.add_node("requirements_s5", s5.execute)
    """

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] S5 编译任务书开始")

        # ── 从上游节点收集数据 ────────────────────────────────────────
        locked_goals: List[Dict[str, Any]] = state.get("locked_goals") or []
        hard_redlines: List[str] = state.get("hard_redlines") or []
        strategy_framework: Dict[str, Any] = state.get("strategy_framework") or {}
        tactical_breakdown: Dict[str, Any] = state.get("tactical_breakdown") or {}
        structured_brief: Dict[str, Any] = state.get("structured_brief_parts") or {}

        # ── 编译 DesignTaskBook ───────────────────────────────────────
        task_book = self._compile_task_book(
            locked_goals, hard_redlines, strategy_framework, structured_brief
        )

        # ── 编译 ExecutionBlueprint ───────────────────────────────────
        blueprint = self._compile_blueprint(tactical_breakdown)

        ts = datetime.now().isoformat()
        logger.info(
            f"[{session_id}] S5 完成 — "
            f"DesignTaskBook frozen={task_book.frozen}, "
            f"ExecutionBlueprint frozen={blueprint.frozen}"
        )

        return {
            "design_task_book": task_book.model_dump(),
            "execution_blueprint": blueprint.model_dump(),
            "requirements_frozen": True,
            "updated_at": ts,
        }

    # ------------------------------------------------------------------

    def _compile_task_book(
        self,
        goals: List[Dict[str, Any]],
        redlines: List[str],
        framework: Dict[str, Any],
        brief: Dict[str, Any],
    ) -> DesignTaskBook:
        # 核心命题：从 primary 目标提炼
        primary_goals = [
            g["description"]
            for g in goals
            if isinstance(g, dict) and g.get("priority") == "primary" and g.get("status") == "locked"
        ]
        core_prop = primary_goals[0] if primary_goals else "项目核心命题待确认"

        # 策略分区
        zones_raw = framework.get("strategy_zones", {})
        zone = StrategyZone(
            frozen=zones_raw.get("frozen", []),
            expanded=zones_raw.get("expanded", []),
            traced=zones_raw.get("traced", []),
            escalated=zones_raw.get("escalated", []),
        )

        return DesignTaskBook(
            project_intent=brief.get("raw_text_summary", "（来自 S1 解构）"),
            core_proposition=core_prop,
            strategy_zones=zone,
            boundaries_and_redlines=redlines,
            risk_and_rationale={
                "compiled_goals_count": len(goals),
                "open_pending": sum(1 for g in goals if isinstance(g, dict) and g.get("status") == "pending_input"),
            },
            frozen=True,
        )

    def _compile_blueprint(
        self, tactical: Dict[str, Any]
    ) -> ExecutionBlueprint:
        # DAG 节点反序列化
        dag_raw: List[Dict[str, Any]] = tactical.get("deliverable_dag", [])
        dag_nodes: List[DAGNode] = [DAGNode(**n) for n in dag_raw]

        # ReviewGate 反序列化
        gates_raw: List[Dict[str, Any]] = tactical.get("review_gates", [])
        review_gates: List[ReviewGate] = [ReviewGate(**g) for g in gates_raw]

        # 任务链骨架（按 DAG 顺序提取名称）
        chain_skeleton: List[str] = [n.name for n in dag_nodes]

        expert_resp: Dict[str, List[str]] = tactical.get("expert_responsibility", {})

        return ExecutionBlueprint(
            deliverable_dag=dag_nodes,
            task_chain_skeleton=chain_skeleton,
            expert_responsibility=expert_resp,
            review_gates=review_gates,
            dependency_and_reflow_rules={
                "reflow_trigger": "ReviewGate REJECT → 回退到最近 frozen 节点"
            },
            budget_guard={role: 5 for role in expert_resp},
            frozen=True,
        )
