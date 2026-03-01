"""
搜索结果ID生成器 (v7.164)

为搜索结果生成唯一标识符，便于后续管理和引用。

ID格式: {source_tool}_{timestamp}_{hash}
示例: tavily_20260109143022_a1b2c3d4

功能:
- 基于URL和标题生成稳定的哈希（相同内容生成相同ID）
- 支持去重检测
- 支持批量ID生成
"""

import hashlib
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_search_result_id(
    source_tool: str,
    url: Optional[str] = None,
    title: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> str:
    """
    为单个搜索结果生成唯一ID

    ID格式: {source_tool}_{timestamp}_{hash}

    Args:
        source_tool: 搜索工具名称 (tavily, bocha, arxiv, milvus, serper)
        url: 结果URL（用于生成哈希）
        title: 结果标题（用于生成哈希，当URL不存在时）
        timestamp: 可选的时间戳，默认使用当前时间

    Returns:
        唯一ID字符串

    Example:
        >>> generate_search_result_id("tavily", url="https://example.com/article")
        'tavily_20260109143022_a1b2c3d4'
    """
    # 生成时间戳部分
    if timestamp:
        ts_part = timestamp
    else:
        ts_part = datetime.now().strftime("%Y%m%d%H%M%S")

    # 生成哈希部分（基于URL或标题）
    hash_input = url or title or str(time.time_ns())
    hash_bytes = hashlib.md5(hash_input.encode("utf-8")).hexdigest()[:8]

    # 组合ID
    return f"{source_tool}_{ts_part}_{hash_bytes}"


def generate_stable_search_id(
    source_tool: str,
    url: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """
    生成稳定的搜索结果ID（相同内容生成相同ID，用于去重）

    与 generate_search_result_id 不同，此函数不包含时间戳，
    因此相同的URL/标题总是生成相同的ID。

    ID格式: {source_tool}_{hash}

    Args:
        source_tool: 搜索工具名称
        url: 结果URL
        title: 结果标题

    Returns:
        稳定的ID字符串

    Example:
        >>> generate_stable_search_id("tavily", url="https://example.com")
        'tavily_a1b2c3d4e5f6'
    """
    hash_input = f"{source_tool}:{url or ''}:{title or ''}"
    hash_bytes = hashlib.md5(hash_input.encode("utf-8")).hexdigest()[:12]
    return f"{source_tool}_{hash_bytes}"


def add_ids_to_search_results(
    results: List[Dict[str, Any]],
    source_tool: str,
    use_stable_id: bool = True,
) -> List[Dict[str, Any]]:
    """
    为搜索结果列表批量添加ID

    Args:
        results: 搜索结果列表
        source_tool: 搜索工具名称
        use_stable_id: 是否使用稳定ID（用于去重），默认True

    Returns:
        添加了ID的搜索结果列表

    Example:
        >>> results = [{"title": "Article 1", "url": "https://example.com/1"}]
        >>> add_ids_to_search_results(results, "tavily")
        [{"id": "tavily_a1b2c3d4e5f6", "title": "Article 1", "url": "..."}]
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    for result in results:
        if "id" not in result:
            url = result.get("url")
            title = result.get("title")

            if use_stable_id:
                result["id"] = generate_stable_search_id(source_tool, url, title)
            else:
                result["id"] = generate_search_result_id(source_tool, url, title, timestamp)

    return results


def deduplicate_search_results(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    基于ID去重搜索结果

    Args:
        results: 搜索结果列表（必须包含id字段）

    Returns:
        去重后的搜索结果列表
    """
    seen_ids = set()
    deduplicated = []

    for result in results:
        result_id = result.get("id")
        if result_id and result_id not in seen_ids:
            seen_ids.add(result_id)
            deduplicated.append(result)
        elif not result_id:
            # 没有ID的结果直接保留
            deduplicated.append(result)

    return deduplicated
