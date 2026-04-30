"""
S3 策略框架节点

Copilot 生成（2026-03-15）

输入: state.locked_goals + state.hard_redlines + state.soft_preferences
输出:
  - strategy_framework: StrategyZone 四区标注结果（dict）
    frozen   — 已验证不可动的决策
    expanded — 可探索的方向空间
    traced   — 需留痕的取舍
    escalated— 超出项目权限、需向上协调

核心原则：
  - Frozen 区：来自硬约束 + priority=primary 且无争议的目标
  - Expanded 区：soft_preferences + secondary 目标
  - Traced 区：冲突消解的取舍记录
  - Escalated 区：涉及外部审批/甲方决策的事项
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import StrategyZone
from intelligent_project_analyzer.core.state import ProjectAnalysisState


_ESCALATION_MARKERS = (
    "审批", "规划局", "甲方确认", "业主决定", "政府", "消防局", "城管",
)


class S3StrategyFrameworkNode:
    """
    S3 策略框架节点。

    LangGraph 注册示例：
        s3 = S3StrategyFrameworkNode()
        graph.add_node("requirements_s3", s3.execute)
    """

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] S3 策略框架开始")

        # 门禁：缺口补全未完成时拒绝推进，防止下游消费残缺信息
        if not state.get("s1_v3_complete"):
            logger.warning(
                f"[{session_id}] S3 门禁：s1_v3_complete=False，缺口尚未补全，中止 S3"
            )
            return {
                "strategy_framework": None,
                "updated_at": datetime.now().isoformat(),
            }

        locked_goals: List[Dict[str, Any]] = state.get("locked_goals") or []
        hard_redlines: List[str] = state.get("hard_redlines") or []
        soft_prefs: List[str] = state.get("soft_preferences") or []
        s2_result: Optional[Dict[str, Any]] = state.get("s2_result") or {}
        conflict_resolutions: List[Dict[str, str]] = s2_result.get("conflict_resolutions", [])

        zone = StrategyZone(
            frozen=self._build_frozen(locked_goals, hard_redlines),
            expanded=self._build_expanded(locked_goals, soft_prefs),
            traced=self._build_traced(conflict_resolutions),
            escalated=self._build_escalated(locked_goals, hard_redlines),
        )

        framework: Dict[str, Any] = {
            "strategy_zones": zone.model_dump(),
            "zone_summary": {
                "frozen_count": len(zone.frozen),
                "expanded_count": len(zone.expanded),
                "traced_count": len(zone.traced),
                "escalated_count": len(zone.escalated),
            },
            "framed_at": datetime.now().isoformat(),
        }

        logger.info(
            f"[{session_id}] S3 完成 — "
            f"frozen={len(zone.frozen)}, expanded={len(zone.expanded)}, "
            f"traced={len(zone.traced)}, escalated={len(zone.escalated)}"
        )

        return {
            "strategy_framework": framework,
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------

    def _build_frozen(
        self, goals: List[Dict[str, Any]], redlines: List[str]
    ) -> List[str]:
        frozen: List[str] = list(redlines)
        for g in goals:
            if g.get("priority") == "primary" and g.get("status") == "locked":
                frozen.append(g["description"])
        return frozen[:12]

    def _build_expanded(
        self, goals: List[Dict[str, Any]], soft_prefs: List[str]
    ) -> List[str]:
        expanded: List[str] = list(soft_prefs)
        for g in goals:
            if g.get("priority") == "secondary":
                expanded.append(g["description"])
        return expanded[:10]

    def _build_traced(
        self, conflict_resolutions: List[Dict[str, str]]
    ) -> List[str]:
        return [r.get("resolution", "") for r in conflict_resolutions if r.get("resolution")]

    def _build_escalated(
        self, goals: List[Dict[str, Any]], redlines: List[str]
    ) -> List[str]:
        escalated: List[str] = []
        combined_text = " ".join(redlines) + " ".join(
            g.get("description", "") for g in goals
        )
        for marker in _ESCALATION_MARKERS:
            if marker in combined_text:
                escalated.append(f"需协调外部事项：含 '{marker}' 相关决策")
        return list(dict.fromkeys(escalated))
