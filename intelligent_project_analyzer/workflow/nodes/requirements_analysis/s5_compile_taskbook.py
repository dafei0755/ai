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


_VERSION_DEPTH_PROFILES: Dict[str, Dict[str, Any]] = {
    "basic": {
        "level": 1,
        "scope": "foundation",
        "taskbook_depth": "basic_directory",
        "focus": ["project_baseline", "hard_constraints", "risk_list"],
    },
    "standard": {
        "level": 2,
        "scope": "decision_ready",
        "taskbook_depth": "preformed_directory",
        "focus": [
            "project_baseline",
            "operating_logic",
            "conversion_constraints",
            "phase_strategy",
        ],
    },
    "professional": {
        "level": 3,
        "scope": "control_ready",
        "taskbook_depth": "evidence_backed_directory",
        "focus": [
            "project_baseline",
            "operating_logic",
            "risk_matrix",
            "multi_party_decision",
            "knowledge_recall",
        ],
    },
}


_DEFAULT_FORMAL_ASSETS = [
    "CAD floor plan",
    "site photos",
    "brand materials",
    "equipment list",
    "budget boundary",
]


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
        entry_contract = self._extract_scheme_advisor_contract(state)

        # ── 编译 DesignTaskBook ───────────────────────────────────────
        task_book = self._compile_task_book(
            locked_goals,
            hard_redlines,
            strategy_framework,
            structured_brief,
            entry_contract,
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
        entry_contract: Dict[str, Any],
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
            selected_version_id=entry_contract["selected_version_id"],
            version_depth=entry_contract["version_depth"],
            strategy_zones=zone,
            boundaries_and_redlines=redlines,
            pending_formal_assets=entry_contract["pending_formal_assets"],
            formal_calibration_items=entry_contract["formal_calibration_items"],
            risk_and_rationale={
                "compiled_goals_count": len(goals),
                "open_pending": sum(1 for g in goals if isinstance(g, dict) and g.get("status") == "pending_input"),
                "formal_assets_status": entry_contract["formal_assets_status"],
                "blocking_missing_assets": [],
            },
            source_trace=entry_contract["source_trace"],
            frozen=True,
        )

    def _extract_scheme_advisor_contract(
        self, state: ProjectAnalysisState
    ) -> Dict[str, Any]:
        raw_packet: Dict[str, Any] = state.get("raw_brief_packet") or {}
        prefill: Dict[str, Any] = raw_packet.get("prefill_from_drafts") or {}
        entry_state: Dict[str, Any] = (
            state.get("scheme_advisor_entry_v2")
            or prefill.get("scheme_advisor_entry_v2")
            or {}
        )
        profile: Dict[str, Any] = (
            entry_state.get("profile")
            or prefill.get("scheme_advisor_profile")
            or {}
        )
        maturity: Dict[str, Any] = profile.get("maturity") or {}

        selected_version = (
            state.get("selected_version")
            or entry_state.get("selected_version")
            or prefill.get("selected_version")
            or entry_state.get("recommended_version")
            or "standard"
        )
        if selected_version not in _VERSION_DEPTH_PROFILES:
            selected_version = "standard"

        pending_assets = (
            state.get("pending_formal_assets")
            or entry_state.get("pending_formal_assets")
            or maturity.get("pending")
            or prefill.get("pending_formal_assets")
            or _DEFAULT_FORMAL_ASSETS
        )
        pending_assets = [str(asset) for asset in pending_assets if str(asset).strip()]

        return {
            "selected_version_id": selected_version,
            "version_depth": _VERSION_DEPTH_PROFILES[selected_version],
            "pending_formal_assets": pending_assets,
            "formal_calibration_items": [
                {
                    "item": asset,
                    "status": "pending_calibration",
                    "blocking_entry": False,
                    "stage": "formal_taskbook",
                }
                for asset in pending_assets
            ],
            "formal_assets_status": "calibration_required" if pending_assets else "complete",
            "source_trace": {
                "scheme_advisor_entry_step": entry_state.get("step"),
                "context_packet_schema_version": (
                    (profile.get("context_packet") or {}).get("schema_version")
                ),
                "selected_version_source": (
                    "scheme_advisor_entry_v2"
                    if entry_state.get("selected_version")
                    else "default"
                ),
                "formal_assets_block_entry": False,
            },
        }

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
