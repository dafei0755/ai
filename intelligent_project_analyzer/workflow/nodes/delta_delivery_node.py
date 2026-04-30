"""
局部增量交付节点

Copilot 生成（2026-03-15）

职责：
  用户对已交付项目发出局部修改指令（不触碰 S3/S4 战略层）时，
  本节点负责：
    1. 从 delta_router_state 提取增量规格（DeltaDelivery + ImpactGraph）
    2. 仅重跑 ImpactGraph.affected_zones 覆盖的执行单元（跳过 S1-S5）
    3. 将增量结果写入 DeltaDelivery.delta_result
    4. 将版本条目追加到现有 DeliveryBundle.version_lineage
    5. 系统保持 / 回落到对话态，等待用户进一步操作

典型路径（不同于完整执行链）：
  DeltaRouter → DeltaDeliveryNode → DeliveryCompiler（增量模式）→ 对话态
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    DeltaDelivery,
    DeliveryBundle,
    ImpactGraph,
    ProjectArchive,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState


# ---------------------------------------------------------------------------
# DeltaDeliveryNode
# ---------------------------------------------------------------------------


class DeltaDeliveryNode:
    """
    局部增量交付节点。

    LangGraph 注册示例：
        node = DeltaDeliveryNode()
        graph.add_node("delta_delivery", node.execute)
        graph.add_edge("delta_delivery", "conversation_engine")
    """

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        增量执行主逻辑。

        前提：
          - state["is_delta_modification"] == True
          - state["delta_router_state"] 已由 DeltaRouter 填充
          - state["delivery_bundle"] 存在（有历史交付物可参照）
        """
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] DeltaDeliveryNode 开始（局部增量）")

        delta_router_state: Optional[Dict[str, Any]] = state.get("delta_router_state")
        if not delta_router_state:
            logger.warning(f"[{session_id}] delta_router_state 缺失，退出增量执行")
            return {
                "execution_error": "delta_router_state 缺失，无法执行增量",
                "system_mode": "conversation",
                "updated_at": datetime.now().isoformat(),
            }

        delta_raw: Dict[str, Any] = delta_router_state.get("delta") or {}
        impact_raw: Dict[str, Any] = delta_router_state.get("impact") or {}

        delta = DeltaDelivery(**delta_raw) if delta_raw else DeltaDelivery(
            delta_target=state.get("user_input", ""),
            original_ref=session_id,
        )
        impact = ImpactGraph(**impact_raw) if impact_raw else ImpactGraph(changed_field="unknown")

        logger.info(
            f"[{session_id}] 增量目标: {delta.delta_target[:60]} | "
            f"受影响区域: {impact.affected_zones}"
        )

        # ── 仅重跑受影响区域 ─────────────────────────────────────────
        partial_results = self._execute_affected_zones(
            affected_zones=impact.affected_zones,
            delta=delta,
            state=state,
            session_id=session_id,
        )

        # ── 更新 DeltaDelivery ────────────────────────────────────────
        delta.delta_result = {
            "partial_results": partial_results,
            "executed_at": datetime.now().isoformat(),
            "affected_zones": impact.affected_zones,
        }

        # ── 追加到现有 DeliveryBundle 版本树 ─────────────────────────
        updated_bundle = self._append_delta_to_bundle(delta, impact, state, session_id)

        # ── 更新 ProjectArchive（对话态注入用）───────────────────────
        updated_archive = self._refresh_archive(updated_bundle, delta, state, session_id)

        logger.info(
            f"[{session_id}] DeltaDeliveryNode 完成 — "
            f"版本: {updated_bundle.version_lineage[-1] if updated_bundle.version_lineage else '?'}"
        )

        return {
            "delivery_bundle": updated_bundle.model_dump(),
            "project_archive": updated_archive.model_dump() if updated_archive else None,
            "is_delta_modification": False,   # 增量执行后重置标志
            "delta_router_state": None,
            "system_mode": "conversation",
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 仅重跑受影响区域
    # ------------------------------------------------------------------

    def _execute_affected_zones(
        self,
        affected_zones: List[str],
        delta: DeltaDelivery,
        state: ProjectAnalysisState,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        针对 ImpactGraph.affected_zones 执行轻量重跑。

        当前版本为规则占位实现；接入技能层（execution/skills/）后可替换为真实调用。
        """
        if not affected_zones:
            logger.info(f"[{session_id}] 无受影响区域，跳过重跑")
            return []

        results = []
        for zone in affected_zones:
            logger.info(f"[{session_id}]   重跑区域: {zone}")
            result = {
                "zone": zone,
                "delta_target": delta.delta_target[:100],
                "result_type": "delta_output",
                "content": f"[增量重跑占位] 区域 '{zone}' 已根据修改指令重新生成。",
                "generated_at": datetime.now().isoformat(),
            }
            results.append(result)

        logger.info(f"[{session_id}] 增量重跑完成，共 {len(results)} 个区域")
        return results

    # ------------------------------------------------------------------
    # 追加版本树条目
    # ------------------------------------------------------------------

    def _append_delta_to_bundle(
        self,
        delta: DeltaDelivery,
        impact: ImpactGraph,
        state: ProjectAnalysisState,
        session_id: str,
    ) -> DeliveryBundle:
        """将增量结果追加到现有 DeliveryBundle 的版本树中。"""
        existing_raw: Optional[Dict[str, Any]] = state.get("delivery_bundle")

        if existing_raw:
            bundle = DeliveryBundle(**existing_raw)
        else:
            # 首次增量（不应发生，但做好兜底）
            logger.warning(f"[{session_id}] delivery_bundle 不存在，创建空包")
            bundle = DeliveryBundle()

        # 推进版本号
        existing_versions = bundle.version_lineage
        if existing_versions:
            last_ver = existing_versions[-1]
            # v1.0 → v1.1 → v1.2
            parts = last_ver.lstrip("v").split(".")
            if len(parts) == 2:
                new_ver = f"v{parts[0]}.{int(parts[1]) + 1}"
            else:
                new_ver = f"{last_ver}-delta"
        else:
            new_ver = "v1.0-delta"

        bundle.version_lineage = existing_versions + [new_ver]

        # 追加阶段交付物
        bundle.stage_deliverables.append({
            "version": new_ver,
            "type": "delta_delivery",
            "delta_target": delta.delta_target[:200],
            "modified_fields": delta.modified_fields,
            "impact_scope": delta.impact_scope,
            "delta_result": delta.delta_result,
            "redline_alerts": impact.redline_alerts,
        })

        # 更新风险摘要
        if impact.redline_alerts:
            bundle.risk_summary["delta_redline_alerts"] = impact.redline_alerts

        logger.info(f"[{session_id}] 版本树追加: {new_ver}")
        return bundle

    # ------------------------------------------------------------------
    # 刷新 ProjectArchive
    # ------------------------------------------------------------------

    def _refresh_archive(
        self,
        bundle: DeliveryBundle,
        delta: DeltaDelivery,
        state: ProjectAnalysisState,
        session_id: str,
    ) -> Optional[ProjectArchive]:
        """用最新 DeliveryBundle 刷新 ProjectArchive，保持对话态上下文同步。"""
        archive_raw: Optional[Dict[str, Any]] = state.get("project_archive")
        if not archive_raw:
            return None

        try:
            archive = ProjectArchive(**archive_raw)
        except Exception:
            logger.warning(f"[{session_id}] project_archive 反序列失败，跳过刷新")
            return None

        archive.delivery_bundle = bundle
        archive.decision_records.append({
            "type": "delta_modification",
            "delta_target": delta.delta_target[:200],
            "version": bundle.version_lineage[-1] if bundle.version_lineage else "?",
            "recorded_at": datetime.now().isoformat(),
        })

        return archive
