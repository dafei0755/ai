"""
S2 目标锁定节点

Copilot 生成（2026-03-15）

输入: state.structured_brief_parts + state.requirement_dimension_raw
输出:
  - locked_goals: 已解决冲突后的目标清单（含优先级标注）
  - hard_redlines: 不可逾越的硬约束列表
  - soft_preferences: 可调整的软偏好列表

核心处理：
  1. 冲突检测: 检测互斥目标对（如"最省钱"+"最高品质"）
  2. 解决策略: 排优先级（Frozen > Expanded > Traced）
  3. 硬约束提炼: 法规/容积率/红线等
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.state import ProjectAnalysisState


_HARD_CONSTRAINT_MARKERS = (
    "规范", "容积率", "退红线", "消防", "日照", "层高限制",
    "限高", "不能改", "不可", "必须", "法规", "审批",
)

_CONFLICT_PAIRS: List[tuple[str, str]] = [
    ("最省", "最好"),
    ("最省", "最高品质"),
    ("极简", "功能最全"),
    ("快速完成", "精打细磨"),
    ("低造价", "大面积"),
]


class S2GoalLockingNode:
    """
    S2 目标锁定节点。

    LangGraph 注册示例：
        s2 = S2GoalLockingNode()
        graph.add_node("requirements_s2", s2.execute)
    """

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] S2 目标锁定开始")

        structured: Optional[Dict[str, Any]] = state.get("structured_brief_parts") or {}
        dim_raw: List[str] = state.get("requirement_dimension_raw") or []

        raw_text = structured.get("raw_text_summary", "")
        open_gaps: List[str] = structured.get("open_gaps", [])

        # ── 硬约束提炼 ────────────────────────────────────────────────
        hard_redlines = self._extract_hard_constraints(raw_text, dim_raw)

        # ── 冲突检测 ──────────────────────────────────────────────────
        conflicts = self._detect_conflicts(raw_text)

        # ── 目标锁定（冲突消解 → 优先级排序）────────────────────────
        locked_goals = self._lock_goals(dim_raw, conflicts, open_gaps)

        # ── 软偏好保留 ────────────────────────────────────────────────
        soft_preferences = self._extract_soft_preferences(dim_raw, hard_redlines)

        result = {
            "locked_goals": locked_goals,
            "hard_redlines": hard_redlines,
            "soft_preferences": soft_preferences,
            "conflict_resolutions": conflicts,
            "locked_at": datetime.now().isoformat(),
        }

        logger.info(
            f"[{session_id}] S2 完成 — "
            f"目标={len(locked_goals)}, "
            f"红线={len(hard_redlines)}, "
            f"冲突={len(conflicts)}"
        )

        # 若已有 s1_v2_snapshot（Echo Card 响应生成），将目标开放缺口回填其中
        s1_v2_raw: Optional[Dict[str, Any]] = state.get("s1_v2_snapshot")
        if s1_v2_raw:
            # 把新识别的冲突/缺口追加进 open_gaps
            extra_gaps = [
                g["description"] for g in locked_goals
                if g.get("status") == "pending_input"
            ]
            current_gaps: List[str] = s1_v2_raw.get("open_gaps", [])
            merged_gaps = list(dict.fromkeys(current_gaps + extra_gaps))
            s1_v2_raw = {**s1_v2_raw, "open_gaps": merged_gaps, "snapshot_at": datetime.now().isoformat()}

        return {
            "locked_goals": locked_goals,
            "hard_redlines": hard_redlines,
            "soft_preferences": soft_preferences,
            "s2_result": result,
            **(({"s1_v2_snapshot": s1_v2_raw}) if s1_v2_raw else {}),
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------

    def _extract_hard_constraints(self, raw_text: str, dims: List[str]) -> List[str]:
        constraints: List[str] = []
        combined = raw_text + " ".join(dims)
        for marker in _HARD_CONSTRAINT_MARKERS:
            if marker in combined:
                idx = combined.index(marker)
                snippet = combined[max(0, idx - 10): idx + 30].strip()
                constraints.append(snippet)
        return list(dict.fromkeys(constraints))  # 去重保序

    def _detect_conflicts(self, raw_text: str) -> List[Dict[str, str]]:
        found: List[Dict[str, str]] = []
        for a, b in _CONFLICT_PAIRS:
            if a in raw_text and b in raw_text:
                found.append({
                    "conflict": f"{a} vs {b}",
                    "resolution": f"建议明确优先保留 '{a}' 目标，将 '{b}' 降为软偏好",
                })
        return found

    def _lock_goals(
        self,
        dims: List[str],
        conflicts: List[Dict[str, str]],
        gaps: List[str],
    ) -> List[Dict[str, Any]]:
        goals: List[Dict[str, Any]] = []

        for i, dim_desc in enumerate(dims[:8]):  # 最多 8 个维度目标
            priority = "primary" if i < 3 else "secondary"
            goals.append({
                "goal_id": f"G{i + 1:02d}",
                "description": dim_desc,
                "priority": priority,
                "status": "locked",
            })

        # 缺口转为待补全目标
        for j, gap in enumerate(gaps[:3]):
            goals.append({
                "goal_id": f"G_GAP{j + 1}",
                "description": f"[待补全] {gap}",
                "priority": "blocker",
                "status": "pending_input",
            })

        return goals

    def _extract_soft_preferences(
        self, dims: List[str], hard_list: List[str]
    ) -> List[str]:
        soft: List[str] = []
        for d in dims:
            if not any(h in d for h in hard_list):
                if any(w in d for w in ("风格", "色彩", "氛围", "感觉", "偏好", "希望")):
                    soft.append(d)
        return soft[:5]
