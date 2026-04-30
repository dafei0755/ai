"""
execution/skills/evidence_skills.py — E 类取证技能

Copilot 生成（2026-03-22）

技能列表：
  - web_search        (B 类门控)：广域网搜索，返回摘要片段列表
  - rag_query         (A 类门控)：私有知识库检索
  - archive_recall    (A 类门控)：从 ProjectArchive 检索历史决策

所有技能在执行前必须通过 RiskGateEngine.check()，blocked 时直接返回空结果。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.workflow.execution.risk_gates import (
    ActionRequest,
    RiskGateEngine,
)


# ---------------------------------------------------------------------------
# 结果数据结构
# ---------------------------------------------------------------------------


class SearchResult:
    """web_search 返回结果"""

    def __init__(
        self,
        query: str,
        snippets: List[Dict[str, str]],
        blocked: bool = False,
        block_reason: str = "",
    ) -> None:
        self.query = query
        self.snippets = snippets          # [{"title": ..., "url": ..., "snippet": ...}]
        self.blocked = blocked
        self.block_reason = block_reason
        self.retrieved_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "snippets": self.snippets,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "retrieved_at": self.retrieved_at,
        }


class RAGResult:
    """rag_query 返回结果"""

    def __init__(
        self,
        query: str,
        passages: List[Dict[str, Any]],
        blocked: bool = False,
    ) -> None:
        self.query = query
        self.passages = passages          # [{"doc_id", "content", "score"}]
        self.blocked = blocked
        self.retrieved_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "passages": self.passages,
            "blocked": self.blocked,
            "retrieved_at": self.retrieved_at,
        }


class ArchiveRecallResult:
    """archive_recall 返回结果"""

    def __init__(
        self,
        session_id: str,
        matched_records: List[Dict[str, Any]],
    ) -> None:
        self.session_id = session_id
        self.matched_records = matched_records
        self.recalled_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "matched_records": self.matched_records,
            "recalled_at": self.recalled_at,
        }


# ---------------------------------------------------------------------------
# 取证技能
# ---------------------------------------------------------------------------


def web_search(
    query: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> SearchResult:
    """
    B 类门控 — 广域网搜索。

    gate_engine 必须在调用前已初始化（由 ExecutionOrchestrator 传入）。
    实际网络请求由 actions.search_actions.search_web_action 完成，
    本函数仅负责门控 + 结果封装。
    """
    request = ActionRequest(
        action_name="search_web",
        context={"session_id": session_id},
        description=f"广域网搜索: {query[:80]}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        logger.warning(
            f"[{session_id}] web_search 被门控阻断: {outcome.block_reason}"
        )
        return SearchResult(
            query=query,
            snippets=[],
            blocked=True,
            block_reason=outcome.block_reason or "gate_blocked",
        )

    # 实际搜索（Phase E-3 actions 层实现，此处为 stub）
    logger.info(f"[{session_id}] web_search: {query[:80]}")
    snippets: List[Dict[str, str]] = []  # action 层将在此填充
    return SearchResult(query=query, snippets=snippets)


def rag_query(
    query: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    filters: Optional[Dict[str, Any]] = None,
    call_counts: Optional[Dict[str, int]] = None,
) -> RAGResult:
    """
    A 类门控 — 私有知识库检索。

    不阻塞，但记录审计留痕。
    """
    request = ActionRequest(
        action_name="query_knowledge_base",
        context={"session_id": session_id},
        description=f"RAG 检索: {query[:80]}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        logger.warning(f"[{session_id}] rag_query 被门控阻断")
        return RAGResult(query=query, passages=[], blocked=True)

    logger.info(f"[{session_id}] rag_query: {query[:80]}, filters={filters}")
    passages: List[Dict[str, Any]] = []  # action 层填充
    return RAGResult(query=query, passages=passages)


def archive_recall(
    keyword: str,
    archive_raw: Optional[Dict[str, Any]],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ArchiveRecallResult:
    """
    A 类门控 — 从 ProjectArchive 检索历史决策/审查留痕。
    """
    request = ActionRequest(
        action_name="query_knowledge_base",
        context={"session_id": session_id, "source": "archive"},
        description=f"档案回溯: {keyword[:80]}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return ArchiveRecallResult(session_id=session_id, matched_records=[])

    if not archive_raw:
        return ArchiveRecallResult(session_id=session_id, matched_records=[])

    # 简单关键词过滤历史决策记录
    matched: List[Dict[str, Any]] = []
    for record in archive_raw.get("decision_records", []):
        rec_str = str(record)
        if keyword in rec_str:
            matched.append(record)
    for trace in archive_raw.get("review_traces", []):
        if keyword in str(trace):
            matched.append(trace)

    logger.info(
        f"[{session_id}] archive_recall: keyword='{keyword}', matched={len(matched)}"
    )
    return ArchiveRecallResult(session_id=session_id, matched_records=matched)
