"""
增量路由器 / Delta 分派节点

Copilot 生成（2026-03-15）

职责：
  用户在项目交付后发出修改指令时，本节点判断该指令属于：
    - 局部增量（Delta）：不触碰 S3/S4 战略层 → 直接重入实施执行
    - 重大派生（Derived）：触碰红线或战略层 → 开辟新项目态（DerivedProject）

判断依据：
  1. 变更字段的影响图谱（ImpactGraph）
  2. 是否触碰 strategy_zones.frozen 区域
  3. 是否触碰 boundaries_and_redlines

执行策略：
  - Delta → 路由到 delivery_compiler（delta 模式）
  - Derived → 路由到 gate_node（新一轮项目态入口）
  - 无法判断 → 路由到 conversation_engine 追问用户
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.types import Command
from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    DeltaDelivery,
    ImpactGraph,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState


# ---------------------------------------------------------------------------
# 变更信号词
# ---------------------------------------------------------------------------

_DELTA_KEYWORDS = (
    "材质", "颜色", "色彩", "尺寸", "换成", "改成", "调整一下",
    "微调", "局部", "换个", "细节",
)

_DERIVED_KEYWORDS = (
    "从零", "推翻", "改风格", "加层", "减层", "加两层", "重做",
    "重新设计", "整个方案", "全部重来", "换方向", "改变核心", "核心功能定位",
    "平行版本", "大胆版本",
)

_REDLINE_MARKERS = (
    "容积率", "退红线", "消防", "日照", "限高",
    "结构体系", "地基", "选址重选",
)


# ---------------------------------------------------------------------------
# DeltaRouter
# ---------------------------------------------------------------------------


class DeltaRouter:
    """
    增量路由器节点。

    LangGraph 注册示例：
        router = DeltaRouter()
        graph.add_node("delta_router", router.route)
    """

    def route(
        self, state: ProjectAnalysisState
    ) -> Command[
        Literal[
            "delta_delivery",
            "derived_project",
            "conversation_engine",
        ]
    ]:
        session_id: str = state.get("session_id", "unknown")
        user_input: str = state.get("user_input", "")
        taskbook_raw: Optional[Dict[str, Any]] = state.get("design_task_book") or {}
        archive_raw: Optional[Dict[str, Any]] = state.get("project_archive") or {}

        logger.info(f"[{session_id}] DeltaRouter 判断: {user_input[:60]}")

        if not self._is_project_frozen(state):
            logger.info(f"[{session_id}] DeltaRouter → conversation_engine（项目尚未冻结）")
            return Command(
                goto="conversation_engine",
                update={
                    "system_mode": "conversation",
                    "delta_router_status": "not_frozen",
                    "updated_at": datetime.now().isoformat(),
                },
            )

        # ── 计算影响图谱 ─────────────────────────────────────────────
        impact = self._compute_impact(user_input, taskbook_raw)

        # ── 路由决策 ──────────────────────────────────────────────────
        if impact.requires_derived_project:
            return self._route_derived(state, impact, session_id)

        if self._is_clear_delta(user_input, impact):
            return self._route_delta(state, impact, session_id)

        # 不确定 → 对话追问
        logger.info(f"[{session_id}] DeltaRouter → conversation_engine（意图不明确）")
        return Command(
            goto="conversation_engine",
            update={
                "system_mode": "conversation",
                "impact_graph": impact.model_dump(),
                "updated_at": datetime.now().isoformat(),
            },
        )

    # ------------------------------------------------------------------
    # 路由分支
    # ------------------------------------------------------------------

    def _route_delta(
        self,
        state: ProjectAnalysisState,
        impact: ImpactGraph,
        session_id: str,
    ) -> Command:
        user_input: str = state.get("user_input", "")
        logger.info(f"[{session_id}] DeltaRouter → 局部增量 delta_delivery")

        delta = DeltaDelivery(
            delta_target=user_input[:200],
            original_ref=state.get("session_id", ""),
            modified_fields=impact.affected_zones,
            impact_scope=impact.dependencies,
            delta_result={},
        )

        return Command(
            goto="delta_delivery",
            update={
                "is_delta_modification": True,
                "delta_router_state": {
                    "delta": delta.model_dump(),
                    "impact": impact.model_dump(),
                    "routed_at": datetime.now().isoformat(),
                },
                "impact_graph": impact.model_dump(),
                "updated_at": datetime.now().isoformat(),
            },
        )

    def _route_derived(
        self,
        state: ProjectAnalysisState,
        impact: ImpactGraph,
        session_id: str,
    ) -> Command:
        import uuid

        logger.info(f"[{session_id}] DeltaRouter → 重大派生 derived_project")

        # DerivedProjectNode 会自行创建 DerivedProject + 重置状态，这里只需传入影响图谱
        return Command(
            goto="derived_project",
            update={
                "is_delta_modification": False,
                "parent_project_id": session_id,
                "impact_graph": impact.model_dump(),
                "updated_at": datetime.now().isoformat(),
            },
        )

    # ------------------------------------------------------------------
    # 影响图谱计算
    # ------------------------------------------------------------------

    def _compute_impact(
        self, user_input: str, taskbook_raw: Dict[str, Any]
    ) -> ImpactGraph:
        zones: Dict[str, Any] = taskbook_raw.get("strategy_zones", {})
        frozen_items: List[str] = zones.get("frozen", [])
        redlines: List[str] = taskbook_raw.get("boundaries_and_redlines", [])

        # 变更字段（从输入中提取核心名词）
        changed_field = self._extract_changed_field(user_input)

        # 受影响区域判断
        affected_zones: List[str] = []
        for zone_name, zone_items in zones.items():
            if isinstance(zone_items, list) and any(
                changed_field and changed_field in item
                for item in zone_items
            ):
                affected_zones.append(zone_name)

        # 红线告警（触碰冻结项或硬约束）
        redline_alerts: List[str] = []
        for frozen in frozen_items:
            if changed_field and changed_field in frozen:
                redline_alerts.append(f"触碰冻结项: {frozen[:50]}")
        for redline in redlines:
            if any(m in user_input for m in _REDLINE_MARKERS):
                redline_alerts.append(f"触碰红线: {redline[:50]}")

        # 硬约束词 → 强制派生
        requires_derived = any(m in user_input for m in _REDLINE_MARKERS)
        if not requires_derived and any(kw in user_input for kw in _DERIVED_KEYWORDS):
            requires_derived = True
        if not requires_derived and redline_alerts:
            requires_derived = True

        return ImpactGraph(
            changed_field=changed_field or user_input[:30],
            dependencies=["execution_orchestrator"],
            affected_zones=affected_zones,
            redline_alerts=redline_alerts,
            requires_derived_project=requires_derived,
        )

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _is_project_frozen(self, state: ProjectAnalysisState) -> bool:
        if state.get("requirements_frozen") is True:
            return True

        taskbook = state.get("design_task_book") or {}
        if isinstance(taskbook, dict) and taskbook.get("frozen") is True:
            return True

        archive = state.get("project_archive") or {}
        if isinstance(archive, dict):
            if archive.get("design_task_book_snapshot") or archive.get("delivery_bundle"):
                return True

            archived_taskbook = archive.get("design_task_book") or {}
            if (
                isinstance(archived_taskbook, dict)
                and archived_taskbook.get("frozen") is True
            ):
                return True

        return False

    def _is_clear_delta(self, text: str, impact: ImpactGraph) -> bool:
        return (
            any(kw in text for kw in _DELTA_KEYWORDS)
            and not impact.requires_derived_project
            and len(impact.redline_alerts) == 0
        )

    def _extract_changed_field(self, text: str) -> Optional[str]:
        """简单地从输入中提取最可能的变更主词（最长的两字以上名词）。"""
        tokens = re.split(r"[，。！？、\s换改调]+", text)
        candidates = [t for t in tokens if len(t) >= 2]
        return candidates[0] if candidates else None
