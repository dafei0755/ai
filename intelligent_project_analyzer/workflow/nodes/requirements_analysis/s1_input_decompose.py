"""
S1 输入解构节点

Copilot 生成（2026-03-15）

输入: state.gate_decision (含 GateDecision.gap_diagnosis) + state.raw_brief_packet
输出:
  - structured_brief_parts: 解构后的多维度输入切片
  - requirement_dimension_raw: 原始维度描述列表（供 S2 使用）
  - system_mode 确认为 "project"

解构维度（6个）：
  functional / spatial / aesthetic / technical / budget / time
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import GateDecision
from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.services.dss_context_injector import build_dss_context_snippet


_DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "functional": ["功能", "使用", "活动", "动线", "流程", "体验"],
    "spatial": ["空间", "面积", "层", "层高", "平面", "剖面", "体量"],
    "aesthetic": ["风格", "氛围", "材质", "色彩", "调性", "美学"],
    "technical": ["结构", "设备", "暖通", "机电", "消防", "规范", "绿建"],
    "budget": ["预算", "造价", "费用", "成本", "投入"],
    "time": ["工期", "时间", "进场", "竣工", "交付时间"],
}


class S1InputDecomposeNode:
    """
    S1 输入解构节点。

    LangGraph 注册示例：
        s1 = S1InputDecomposeNode()
        graph.add_node("requirements_s1", s1.execute)
    """

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] S1 输入解构开始")

        # ── 取原始文本 ────────────────────────────────────────────────
        raw_packet: Optional[Dict[str, Any]] = state.get("raw_brief_packet")
        if raw_packet:
            raw_text: str = raw_packet.get("raw_user_prompt", "")
            prefill: Dict[str, Any] = raw_packet.get("prefill_from_drafts", {})
        else:
            raw_text = state.get("user_input", "")
            prefill = {}

        gate_raw: Optional[Dict[str, Any]] = state.get("gate_decision")
        gap_list: List[Dict[str, Any]] = []
        if gate_raw:
            gap_list = gate_raw.get("gap_diagnosis", [])

        # ── 多维度切片 ────────────────────────────────────────────────
        dimension_slices = self._slice_by_dimension(raw_text, prefill)

        # ── DSS 画像上下文注入（Phase 1 预埋）────────────────────────
        dss_profile: Optional[Dict[str, Any]] = state.get("designer_profile")
        dss_snippet: str = build_dss_context_snippet(dss_profile)

        # ── 缺口诊断补充 ─────────────────────────────────────────────
        open_gaps: List[str] = [
            g.get("description", "") for g in gap_list if g.get("description")
        ]

        # ── requirement_dimension_raw（供 S2 锁定目标用）────────────
        requirement_dimension_raw: List[str] = [
            f"{dim}: {val}"
            for dim, val in dimension_slices.items()
            if val
        ]

        structured_brief: Dict[str, Any] = {
            "dimension_slices": dimension_slices,
            "open_gaps": open_gaps,
            "prefill_hints": prefill,
            "raw_text_summary": raw_text[:200],
            "dss_context": dss_snippet,
            "decomposed_at": datetime.now().isoformat(),
        }

        logger.info(
            f"[{session_id}] S1 完成 — "
            f"切片维度={list(dimension_slices.keys())}, "
            f"缺口={len(open_gaps)}"
        )

        # S1 v1 快照（供 Echo Card 节点消费）
        s1_v1_snapshot = {
            "version": "v1",
            "dimension_slices": dimension_slices,
            "open_gaps": open_gaps,
            "prefill_hints": prefill,
            "snapshot_at": datetime.now().isoformat(),
            "user_overrides": {},
        }

        return {
            "system_mode": "project",
            "structured_brief_parts": structured_brief,
            "requirement_dimension_raw": requirement_dimension_raw,
            "s1_v1_snapshot": s1_v1_snapshot,
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------

    def _slice_by_dimension(
        self, raw_text: str, prefill: Dict[str, Any]
    ) -> Dict[str, str]:
        """按 6 个维度提取关键描述段落。"""
        slices: Dict[str, str] = {}

        for dim, keywords in _DIMENSION_KEYWORDS.items():
            hit_parts: List[str] = []
            for kw in keywords:
                if kw in raw_text:
                    # 截取命中关键词前后 20 字作为上下文片段
                    idx = raw_text.index(kw)
                    snippet = raw_text[max(0, idx - 15): idx + 25].strip()
                    hit_parts.append(snippet)

            # prefill 中有对应 hint 也补入
            prefill_val = prefill.get(f"{dim}_info", "") or prefill.get(dim, "")
            if prefill_val:
                hit_parts.append(str(prefill_val))

            if hit_parts:
                slices[dim] = " / ".join(hit_parts[:3])

        return slices
