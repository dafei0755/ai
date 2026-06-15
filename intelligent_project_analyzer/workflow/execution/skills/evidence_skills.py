"""
execution/skills/evidence_skills.py 鈥?E 绫诲彇璇佹妧鑳?

Copilot 鐢熸垚锛?026-03-22锛?

鎶€鑳藉垪琛細
  - web_search        (B 绫婚棬鎺?锛氬箍鍩熺綉鎼滅储锛岃繑鍥炴憳瑕佺墖娈靛垪琛?
  - rag_query         (A 绫婚棬鎺?锛氱鏈夌煡璇嗗簱妫€绱?
  - archive_recall    (A 绫婚棬鎺?锛氫粠 ProjectArchive 妫€绱㈠巻鍙插喅绛?

鎵€鏈夋妧鑳藉湪鎵ц鍓嶅繀椤婚€氳繃 RiskGateEngine.check()锛宐locked 鏃剁洿鎺ヨ繑鍥炵┖缁撴灉銆?
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
# 缁撴灉鏁版嵁缁撴瀯
# ---------------------------------------------------------------------------


class SearchResult:
    """web_search 杩斿洖缁撴灉"""

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
    """rag_query 杩斿洖缁撴灉"""

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
    """archive_recall 杩斿洖缁撴灉"""

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
# 鍙栬瘉鎶€鑳?
# ---------------------------------------------------------------------------


def web_search(
    query: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> SearchResult:
    """
    B 绫婚棬鎺?鈥?骞垮煙缃戞悳绱€?

    gate_engine 蹇呴』鍦ㄨ皟鐢ㄥ墠宸插垵濮嬪寲锛堢敱 ExecutionOrchestrator 浼犲叆锛夈€?
    瀹為檯缃戠粶璇锋眰鐢?actions.search_actions.search_web_action 瀹屾垚锛?
    鏈嚱鏁颁粎璐熻矗闂ㄦ帶 + 缁撴灉灏佽銆?
    """
    request = ActionRequest(
        action_name="search_web",
        context={"session_id": session_id},
        description=f"骞垮煙缃戞悳绱? {query[:80]}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        logger.warning(
            f"[{session_id}] web_search 琚棬鎺ч樆鏂? {outcome.block_reason}"
        )
        return SearchResult(
            query=query,
            snippets=[],
            blocked=True,
            block_reason=outcome.block_reason or "gate_blocked",
        )

    # 瀹為檯鎼滅储锛圥hase E-3 actions 灞傚疄鐜帮紝姝ゅ涓?stub锛?
    logger.info(f"[{session_id}] web_search: {query[:80]}")
    snippets: List[Dict[str, str]] = []  # action 灞傚皢鍦ㄦ濉厖
    return SearchResult(query=query, snippets=snippets)


def rag_query(
    query: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    filters: Optional[Dict[str, Any]] = None,
    call_counts: Optional[Dict[str, int]] = None,
) -> RAGResult:
    """
    A 绫婚棬鎺?鈥?绉佹湁鐭ヨ瘑搴撴绱€?

    涓嶉樆濉烇紝浣嗚褰曞璁＄暀鐥曘€?
    """
    request = ActionRequest(
        action_name="query_knowledge_base",
        context={"session_id": session_id},
        description=f"RAG 妫€绱? {query[:80]}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        logger.warning(f"[{session_id}] rag_query gate blocked")
        return RAGResult(query=query, passages=[], blocked=True)

    logger.info(f"[{session_id}] rag_query: {query[:80]}, filters={filters}")
    passages: List[Dict[str, Any]] = []  # action 灞傚～鍏?
    return RAGResult(query=query, passages=passages)


def archive_recall(
    keyword: str,
    archive_raw: Optional[Dict[str, Any]],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ArchiveRecallResult:
    """
    A 绫婚棬鎺?鈥?浠?ProjectArchive 妫€绱㈠巻鍙插喅绛?瀹℃煡鐣欑棔銆?
    """
    request = ActionRequest(
        action_name="query_knowledge_base",
        context={"session_id": session_id, "source": "archive"},
        description=f"妗ｆ鍥炴函: {keyword[:80]}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return ArchiveRecallResult(session_id=session_id, matched_records=[])

    if not archive_raw:
        return ArchiveRecallResult(session_id=session_id, matched_records=[])

    # 绠€鍗曞叧閿瘝杩囨护鍘嗗彶鍐崇瓥璁板綍
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
