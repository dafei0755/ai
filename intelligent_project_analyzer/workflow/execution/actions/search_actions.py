"""
execution/actions/search_actions.py — 搜索类原子动作

Copilot 生成（2026-03-22）

原子动作：
  - search_web_action     ：广域网搜索（真实实现时对接搜索 API）
  - query_knowledge_base  ：私有 RAG 知识库检索（对接向量存储）

设计原则：
  - 无状态纯函数，无副作用
  - 不直接调用门控，由 skills 层负责门控
  - 所有 I/O 通过参数传入，便于单元测试 mock
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 搜索动作
# ---------------------------------------------------------------------------


def search_web_action(
    query: str,
    max_results: int = 5,
    search_client: Optional[Any] = None,
) -> List[Dict[str, str]]:
    """
    广域网搜索。

    参数:
      query         — 搜索关键词
      max_results   — 最大返回条数（默认 5）
      search_client — 搜索 API 客户端（如 Bocha/Bing）；None 时返回空列表（测试模式）

    返回:
      [{"title": ..., "url": ..., "snippet": ...}]
    """
    if search_client is None:
        # 未注入搜索客户端时不发起真实请求（安全兜底）
        return []

    try:
        raw_results = search_client.search(query, max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", "")[:300],
            }
            for r in raw_results[:max_results]
        ]
    except Exception as exc:
        return [{"title": "search_error", "url": "", "snippet": str(exc)[:200]}]


def query_knowledge_base(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    vector_store: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    私有知识库 RAG 检索。

    参数:
      query        — 检索问题
      filters      — 元数据过滤条件（如 {"project_type": "住宅"}）
      top_k        — 返回最相关条数
      vector_store — 向量存储客户端；None 时返回空列表（测试模式）

    返回:
      [{"doc_id": ..., "content": ..., "score": ...}]
    """
    if vector_store is None:
        return []

    try:
        results = vector_store.similarity_search(
            query, k=top_k, filter=filters or {}
        )
        return [
            {
                "doc_id": getattr(r, "metadata", {}).get("doc_id", ""),
                "content": getattr(r, "page_content", "")[:500],
                "score": getattr(r, "score", 0.0),
            }
            for r in results
        ]
    except Exception as exc:
        return [{"doc_id": "rag_error", "content": str(exc)[:200], "score": 0.0}]
