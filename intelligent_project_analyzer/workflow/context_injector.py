"""
对话态上下文注入器

Copilot 生成（2026-03-15）

职责：
  项目态执行完成（delivery_compiler 产出 project_archive）后，
  本模块将项目档案（ProjectArchive）注入对话态的可用上下文，
  使对话引擎具备对该项目的完整解释、修订和派生能力。

注入内容（符合架构文档定义）：
  - 完整交付物档案（DeliveryBundle）
  - 版本树与版本关系
  - 决策记录与风险摘要
  - 审阅门记录
  - 已冻结的 DesignTaskBook 与 ExecutionBlueprint

使用方式：
  1. 直接作为 LangGraph 节点（inject_to_state）
  2. 作为工具函数（build_context_summary）供对话引擎在回答时引用

设计原则：
  - 注入是只读的：只追加 injected_context 字段，不修改任何已冻结对象
  - 摘要优先：大体积对象只提取摘要，防止 context window 溢出
  - 分层访问：对话引擎可通过 get_project_context() 按需取完整对象
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import ProjectArchive
from intelligent_project_analyzer.core.state import ProjectAnalysisState


# ---------------------------------------------------------------------------
# 上下文摘要最大长度限制
# ---------------------------------------------------------------------------

_MAX_DELIVERABLE_SUMMARY_LEN = 120
_MAX_REDLINE_COUNT = 6
_MAX_INSIGHT_COUNT = 8


# ---------------------------------------------------------------------------
# ContextInjector
# ---------------------------------------------------------------------------


class ContextInjector:
    """
    对话态上下文注入器。

    LangGraph 注册示例：
        injector = ContextInjector()
        graph.add_node("context_injector", injector.inject_to_state)
    """

    def inject_to_state(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        从 state.project_archive 构建注入摘要，写入 injected_project_context。
        同时将 system_mode 确认为 "conversation"。
        """
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] ContextInjector 开始注入")

        archive_raw: Optional[Dict[str, Any]] = state.get("project_archive")
        if not archive_raw:
            logger.warning(f"[{session_id}] project_archive 为空，跳过注入")
            return {"system_mode": "conversation"}

        # ── 构建摘要 ──────────────────────────────────────────────────
        context_summary = self.build_context_summary(archive_raw)

        logger.info(
            f"[{session_id}] ContextInjector 完成 — "
            f"deliverables={context_summary.get('final_deliverables_count', 0)}, "
            f"version={context_summary.get('current_version', 'v1.0')}"
        )

        return {
            "injected_project_context": context_summary,
            "system_mode": "conversation",
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 摘要构建（供对话引擎引用）
    # ------------------------------------------------------------------

    def build_context_summary(self, archive_raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 ProjectArchive 序列化为对话引擎可用的摘要字典。

        结构：
          {
            "project_id": ...,
            "core_proposition": ...,
            "current_version": ...,
            "final_deliverables_count": ...,
            "final_deliverables_names": [...],
            "key_decisions": [...],
            "risk_level": ...,
            "redlines": [...],
            "strategy_zones_summary": {...},
            "task_chain": [...],
            "version_lineage": [...],
            "archived_at": ...,
          }
        """
        bundle_raw: Dict[str, Any] = archive_raw.get("delivery_bundle") or {}
        taskbook_raw: Dict[str, Any] = (
            archive_raw.get("design_task_book_snapshot") or {}
        )
        blueprint_raw: Dict[str, Any] = (
            archive_raw.get("execution_blueprint_snapshot") or {}
        )
        decision_records: List[Dict[str, Any]] = archive_raw.get("decision_records") or []

        # 最终交付物摘要
        final_deliverables: List[Dict[str, Any]] = bundle_raw.get("final_deliverables") or []
        deliverable_names = [
            d.get("name", d.get("node_id", "（未命名）"))[:60]
            for d in final_deliverables[:10]
        ]

        # 关键决策摘要
        key_decisions = [
            r.get("content", r.get("reason", ""))[:_MAX_DELIVERABLE_SUMMARY_LEN]
            for r in decision_records[:_MAX_INSIGHT_COUNT]
            if r.get("type") in ("decision", "review_rejection")
        ]

        # 风险摘要
        risk_summary: Dict[str, Any] = bundle_raw.get("risk_summary") or {}
        risk_level = risk_summary.get("risk_level", "unknown")

        # 策略分区简化摘要
        zones_raw: Dict[str, Any] = taskbook_raw.get("strategy_zones") or {}
        strategy_zones_summary = {
            zone: items[:_MAX_REDLINE_COUNT]
            for zone, items in zones_raw.items()
            if isinstance(items, list)
        }

        # 红线
        redlines: List[str] = taskbook_raw.get("boundaries_and_redlines") or []

        # 版本线
        version_lineage: List[str] = bundle_raw.get("version_lineage") or []
        current_version = version_lineage[-1] if version_lineage else "v1.0"

        return {
            "project_id": archive_raw.get("session_id", ""),
            "core_proposition": taskbook_raw.get("core_proposition", "（未知）"),
            "project_intent": taskbook_raw.get("project_intent", ""),
            "current_version": current_version,
            "final_deliverables_count": len(final_deliverables),
            "final_deliverables_names": deliverable_names,
            "key_decisions": key_decisions,
            "risk_level": risk_level,
            "risk_summary_text": risk_summary.get("summary", ""),
            "redlines": redlines[:_MAX_REDLINE_COUNT],
            "strategy_zones_summary": strategy_zones_summary,
            "task_chain": (blueprint_raw.get("task_chain_skeleton") or [])[:8],
            "version_lineage": version_lineage,
            "archived_at": archive_raw.get("archived_at", ""),
        }

    # ------------------------------------------------------------------
    # 对话引擎辅助：生成面向用户的项目状态描述
    # ------------------------------------------------------------------

    @staticmethod
    def render_project_status_for_user(context_summary: Dict[str, Any]) -> str:
        """
        将注入的上下文摘要渲染为自然语言描述，
        供对话引擎在回答"上次项目做到哪里了"之类问题时使用。
        """
        prop = context_summary.get("core_proposition", "（未知项目）")
        version = context_summary.get("current_version", "v1.0")
        count = context_summary.get("final_deliverables_count", 0)
        risk = context_summary.get("risk_level", "unknown")
        names = context_summary.get("final_deliverables_names") or []
        deliverables_str = "、".join(names[:4]) + ("…" if len(names) > 4 else "")

        lines = [
            f"项目基线：{prop}（{version}）",
            f"完成交付物：{count} 项（{deliverables_str}）",
            f"整体风险等级：{risk}",
        ]

        key_decisions = context_summary.get("key_decisions") or []
        if key_decisions:
            lines.append(f"关键决策记录：{len(key_decisions)} 条")

        redlines = context_summary.get("redlines") or []
        if redlines:
            lines.append(f"红线约束：{redlines[0][:50]}{'…' if len(redlines) > 1 else ''}")

        return "\n".join(lines)
