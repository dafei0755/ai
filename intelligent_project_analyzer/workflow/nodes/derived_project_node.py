"""
改轴派生项目节点

Copilot 生成（2026-03-15）

职责：
  当用户修改意图触碰了战略红线或 S3/S4 战略层时，本节点负责：
    1. 创建 DerivedProject 对象（含父项目引用 + 分叉点信息）
    2. 将父项目档案挂载为派生项目的继承上下文
    3. 重置项目态主链入口状态（清除旧需求基线）
    4. 保留用户当前输入作为新的 RawBriefPacket
    5. 路由到 gatekeeper_v2 开启全新项目态（重走门禁 + S1-S5）

与 DeltaDeliveryNode 的区别：
  - DeltaDelivery：不触碰战略层，仅重跑局部单元（跳过 S1-S5）
  - DerivedProject：触碰战略核心，重开独立项目上下文（完整 S1-S5）
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.types import Command
from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    DerivedProject,
    ImpactGraph,
    ProjectArchive,
    RawBriefPacket,
)
from intelligent_project_analyzer.core.state import AnalysisStage, ProjectAnalysisState


# ---------------------------------------------------------------------------
# DerivedProjectNode
# ---------------------------------------------------------------------------


class DerivedProjectNode:
    """
    改轴派生项目节点。

    执行后路由到 gatekeeper_v2，开启全新项目态（完整 S1-S5）。

    LangGraph 注册示例：
        node = DerivedProjectNode()
        graph.add_node("derived_project", node.execute)
        # derived_project 使用 Command goto="gatekeeper_v2"
    """

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def execute(self, state: ProjectAnalysisState) -> Command:
        """
        改轴派生主逻辑。

        前提：
          - state["impact_graph"] 已由 DeltaRouter 填充
          - state["parent_project_id"] 已设置（或从 session_id 推断）
        """
        session_id: str = state.get("session_id", "unknown")
        user_input: str = state.get("user_input", "")
        logger.info(f"[{session_id}] DerivedProjectNode 开始（改轴派生）")

        impact_raw: Optional[Dict[str, Any]] = state.get("impact_graph")
        archive_raw: Optional[Dict[str, Any]] = state.get("project_archive")
        parent_id: str = state.get("parent_project_id") or session_id

        impact = ImpactGraph(**impact_raw) if impact_raw else ImpactGraph(changed_field="unknown")

        # ── 创建新会话 ID ─────────────────────────────────────────────
        new_session_id = f"derived_{session_id}_{uuid.uuid4().hex[:8]}"
        logger.info(
            f"[{session_id}] 新派生项目: {new_session_id} | "
            f"分叉点: {impact.changed_field} | "
            f"红线: {impact.redline_alerts}"
        )

        # ── 构建 DerivedProject ───────────────────────────────────────
        derived = DerivedProject(
            parent_project_id=parent_id,
            inheritance_mode=self._decide_inheritance_mode(impact),
            diverge_point=impact.changed_field,
            new_brief_packet=self._build_new_brief(
                user_input=user_input,
                parent_id=parent_id,
                impact=impact,
                archive_raw=archive_raw,
            ),
            new_session_id=new_session_id,
        )

        # ── 构建新项目的继承上下文（注入 RawBriefPacket.prefill_from_drafts）──
        prefill = self._build_prefill(
            derived=derived,
            impact=impact,
            archive_raw=archive_raw,
        )
        if derived.new_brief_packet:
            derived.new_brief_packet.prefill_from_drafts = prefill

        logger.info(
            f"[{session_id}] DerivedProject 创建完成 — "
            f"inheritance={derived.inheritance_mode}, "
            f"prefill_keys={list(prefill.keys())}"
        )

        # ── 构建回归对话态并重入门禁所需的 state 更新 ────────────────
        state_updates = self._build_state_reset(
            derived=derived,
            new_session_id=new_session_id,
            archive_raw=archive_raw,
        )

        return Command(
            goto="gatekeeper_v2",
            update=state_updates,
        )

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _decide_inheritance_mode(self, impact: ImpactGraph) -> str:
        """根据红线情况决定继承模式。"""
        if impact.redline_alerts:
            # 触碰红线 → 仅软继承（不携带冻结区策略）
            return "soft"
        if len(impact.affected_zones) >= 3:
            # 大面积影响 → 部分继承
            return "partial"
        return "partial"

    def _build_new_brief(
        self,
        user_input: str,
        parent_id: str,
        impact: ImpactGraph,
        archive_raw: Optional[Dict[str, Any]],
    ) -> RawBriefPacket:
        """基于用户当前输入构建新 RawBriefPacket。"""
        # 从父档案中提取有用的背景信息
        parent_context: Dict[str, Any] = {}
        if archive_raw:
            taskbook_snap = archive_raw.get("design_task_book_snapshot") or {}
            parent_context = {
                "parent_core_proposition": taskbook_snap.get("core_proposition", ""),
                "parent_boundaries": taskbook_snap.get("boundaries_and_redlines", []),
            }

        return RawBriefPacket(
            raw_user_prompt=user_input,
            initial_context={
                "derived_from": parent_id,
                "diverge_point": impact.changed_field,
                "redline_alerts": impact.redline_alerts,
                **parent_context,
            },
            session_or_project_stub=f"derived:{parent_id}",
        )

    def _build_prefill(
        self,
        derived: DerivedProject,
        impact: ImpactGraph,
        archive_raw: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """构建预填充信号（对话态草稿 → 新项目态起始输入）。"""
        prefill: Dict[str, Any] = {
            "parent_project_id": derived.parent_project_id,
            "diverge_point": derived.diverge_point,
            "inheritance_mode": derived.inheritance_mode,
            "redline_alerts": impact.redline_alerts,
            "affected_zones": impact.affected_zones,
        }

        if archive_raw and derived.inheritance_mode != "soft":
            taskbook_snap = archive_raw.get("design_task_book_snapshot") or {}
            # 在非软继承时，保留父项目的边界与红线信息
            prefill["inherited_boundaries"] = taskbook_snap.get("boundaries_and_redlines", [])

            blueprint_snap = archive_raw.get("execution_blueprint_snapshot") or {}
            # 保留专家责任模板
            prefill["inherited_expert_roles"] = list(
                blueprint_snap.get("expert_responsibility", {}).keys()
            )

        return prefill

    def _build_state_reset(
        self,
        derived: DerivedProject,
        new_session_id: str,
        archive_raw: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        重置项目态主链字段，让新项目从门禁干净地重新开始。

        关键规则：
        - 必须清除旧的冻结基线（design_task_book, execution_blueprint, requirements_frozen）
        - 不清除 delivery_bundle / project_archive（历史档案保留，供对话态参照）
        - 写入新的 parent_project_id 和 raw_brief_packet
        """
        brief = derived.new_brief_packet
        return {
            # ── 派生项目标识 ───────────────────────────────────────────
            "parent_project_id": derived.parent_project_id,
            "session_id": new_session_id,  # 切换到新会话 ID

            # ── 新 Brief（携带父项目上下文和分叉点信息） ──────────────
            "raw_brief_packet": brief.model_dump() if brief else None,
            "user_input": brief.raw_user_prompt if brief else "",

            # ── 重置项目态冻结状态 ─────────────────────────────────────
            "requirements_frozen": False,
            "design_task_book": None,
            "execution_blueprint": None,
            "gate_decision": None,
            "stage_deliverables_v2": None,
            "execution_review_log": None,
            "execution_halted": False,
            "is_delta_modification": False,
            "delta_router_state": None,

            # ── 切换到项目态主链 ───────────────────────────────────────
            "system_mode": "project",
            "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,

            "updated_at": datetime.now().isoformat(),
        }
