"""
交付编译器

Copilot 生成（2026-03-15）

职责：
  - 将 ExecutionOrchestrator 产出的 stage_deliverables_v2 聚合为 DeliveryBundle
  - 生成版本树条目（version_lineage）
  - 产出 insight_records（风险 + 关键决策）
  - 设置 system_mode 回落到 "conversation"
  - 将项目档案写入 project_archive（供对话态注入上下文用）

这是实施执行阶段的出口节点，执行完成后系统自然回落到对话态。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    DeliveryBundle,
    ProjectArchive,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState


# ---------------------------------------------------------------------------
# DeliveryCompiler
# ---------------------------------------------------------------------------


class DeliveryCompiler:
    """
    交付编译器节点。

    LangGraph 注册示例：
        compiler = DeliveryCompiler()
        graph.add_node("delivery_compiler", compiler.execute)
    """

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        交付编译主逻辑。

        前提: state.stage_deliverables_v2 已由 ExecutionOrchestrator 填充
        """
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] DeliveryCompiler 开始")

        stage_deliverables: List[Dict[str, Any]] = state.get("stage_deliverables_v2") or []
        review_log: List[Dict[str, Any]] = state.get("execution_review_log") or []
        execution_halted: bool = state.get("execution_halted") or False
        taskbook_raw: Optional[Dict[str, Any]] = state.get("design_task_book") or {}
        blueprint_raw: Optional[Dict[str, Any]] = state.get("execution_blueprint") or {}

        # ── 最终交付物（已通过 ReviewGate 的节点） ───────────────────
        final_deliverables = self._filter_final_deliverables(stage_deliverables, review_log)

        # ── insight_records（决策 + 风险） ────────────────────────────
        insight_records = self._compile_insights(stage_deliverables, review_log, execution_halted)

        # ── 风险摘要 ──────────────────────────────────────────────────
        risk_summary = self._compile_risk_summary(review_log, execution_halted)

        # ── 版本树 ────────────────────────────────────────────────────
        existing_lineage: List[str] = []
        existing_bundle_raw: Optional[Dict[str, Any]] = state.get("delivery_bundle")
        if existing_bundle_raw:
            existing_lineage = existing_bundle_raw.get("version_lineage", [])
        version_tag = f"v{len(existing_lineage) + 1}.0"
        version_lineage = existing_lineage + [version_tag]

        bundle = DeliveryBundle(
            final_deliverables=final_deliverables,
            stage_deliverables=stage_deliverables,
            insight_records=insight_records,
            risk_summary=risk_summary,
            version_lineage=version_lineage,
            explanation_materials={
                "core_proposition": taskbook_raw.get("core_proposition", ""),
                "strategy_zones": taskbook_raw.get("strategy_zones", {}),
                "task_chain": blueprint_raw.get("task_chain_skeleton", []),
            },
        )

        # ── ProjectArchive（注入对话态上下文用） ────────────────────
        archive = ProjectArchive(
            session_id=session_id,
            delivery_bundle=bundle,
            design_task_book_snapshot=taskbook_raw,
            execution_blueprint_snapshot=blueprint_raw,
            decision_records=insight_records,
            archived_at=datetime.now().isoformat(),
        )

        logger.info(
            f"[{session_id}] DeliveryCompiler 完成 — "
            f"final={len(final_deliverables)}, "
            f"version={version_tag}, "
            f"halted={execution_halted}"
        )

        return {
            "delivery_bundle": bundle.model_dump(),
            "project_archive": archive.model_dump(),
            # 回落到对话态（带完整项目上下文）
            "system_mode": "conversation",
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _filter_final_deliverables(
        self,
        stage_deliverables: List[Dict[str, Any]],
        review_log: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """过滤出通过所有 ReviewGate 的最终交付物。"""
        rejected_nodes = {
            r["after_node_id"]
            for r in review_log
            if r.get("verdict") == "rejected"
        }
        return [
            d for d in stage_deliverables
            if d.get("node_id") not in rejected_nodes
            and d.get("status") == "completed"
        ]

    def _compile_insights(
        self,
        stage_deliverables: List[Dict[str, Any]],
        review_log: List[Dict[str, Any]],
        halted: bool,
    ) -> List[Dict[str, Any]]:
        insights: List[Dict[str, Any]] = []

        for d in stage_deliverables:
            result = d.get("result") or {}
            key_decisions = result.get("key_decisions") or []
            for decision in key_decisions:
                insights.append({
                    "type": "decision",
                    "node_id": d.get("node_id"),
                    "content": decision,
                })

        for r in review_log:
            if r.get("verdict") == "rejected":
                insights.append({
                    "type": "review_rejection",
                    "gate_id": r.get("gate_id"),
                    "reason": r.get("reason"),
                })

        if halted:
            insights.append({
                "type": "execution_halted",
                "reason": "ReviewGate 拒绝导致执行中止，需人工介入后续步骤",
            })

        return insights

    def _compile_risk_summary(
        self,
        review_log: List[Dict[str, Any]],
        halted: bool,
    ) -> Dict[str, Any]:
        failed_gates = [r for r in review_log if r.get("verdict") == "rejected"]
        return {
            "execution_halted": halted,
            "failed_gates_count": len(failed_gates),
            "failed_gates": [r.get("gate_id") for r in failed_gates],
            "risk_level": "high" if halted else ("medium" if failed_gates else "low"),
            "summary": (
                "执行被中止，需人工介入"
                if halted
                else (f"{len(failed_gates)} 个门禁拒绝，已跳过相关节点" if failed_gates else "执行完成，无高风险事项")
            ),
        }
