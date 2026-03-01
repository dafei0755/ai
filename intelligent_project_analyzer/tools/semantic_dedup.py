"""
语义去重模块 (v7.197)

使用 Embedding 相似度进行语义级别的去重，替代简单的前缀匹配。

特性：
- 支持多种 Embedding 模型（本地/API）
- LRU 缓存避免重复计算
- 余弦相似度阈值可配置
- 支持中英文混合内容

作者: AI Assistant
日期: 2026-01-10
"""

import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

# 配置
SEMANTIC_DEDUP_ENABLED = os.getenv("SEMANTIC_DEDUP_ENABLED", "true").lower() == "true"
SEMANTIC_DEDUP_THRESHOLD = float(os.getenv("SEMANTIC_DEDUP_THRESHOLD", "0.85"))
SEMANTIC_DEDUP_MODEL = os.getenv("SEMANTIC_DEDUP_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "500"))

# Embedding 模型（延迟加载）
_embedding_model = None
_model_available = None


def _get_embedding_model():
    """获取 Embedding 模型（延迟加载，单例）"""
    global _embedding_model, _model_available

    if _model_available is False:
        return None

    if _embedding_model is not None:
        return _embedding_model

    try:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(SEMANTIC_DEDUP_MODEL)
        _model_available = True
        logger.info(f" [SemanticDedup] Embedding 模型加载成功: {SEMANTIC_DEDUP_MODEL}")
        return _embedding_model
    except ImportError:
        logger.warning("️ [SemanticDedup] sentence-transformers 未安装，回退到前缀去重")
        _model_available = False
        return None
    except Exception as e:
        logger.warning(f"️ [SemanticDedup] Embedding 模型加载失败: {e}")
        _model_available = False
        return None


class EmbeddingCache:
    """Embedding 缓存（LRU）"""

    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._max_size = max_size

    def get(self, text: str) -> Optional[np.ndarray]:
        if text in self._cache:
            self._cache.move_to_end(text)
            return self._cache[text]
        return None

    def set(self, text: str, embedding: np.ndarray) -> None:
        if text in self._cache:
            self._cache.move_to_end(text)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
        self._cache[text] = embedding

    def clear(self) -> None:
        self._cache.clear()


# 全局缓存
_embedding_cache = EmbeddingCache(max_size=EMBEDDING_CACHE_SIZE)


def compute_embedding(text: str) -> Optional[np.ndarray]:
    """
    计算文本的 Embedding 向量

    Args:
        text: 输入文本

    Returns:
        Embedding 向量，如果模型不可用则返回 None
    """
    if not text or not SEMANTIC_DEDUP_ENABLED:
        return None

    # 检查缓存
    cached = _embedding_cache.get(text)
    if cached is not None:
        return cached

    # 获取模型
    model = _get_embedding_model()
    if model is None:
        return None

    try:
        # 截断过长文本（模型通常有最大长度限制）
        truncated = text[:512]
        embedding = model.encode(truncated, convert_to_numpy=True)

        # 缓存结果
        _embedding_cache.set(text, embedding)

        return embedding
    except Exception as e:
        logger.warning(f"️ [SemanticDedup] Embedding 计算失败: {e}")
        return None


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    计算余弦相似度

    Args:
        vec1: 向量1
        vec2: 向量2

    Returns:
        相似度 (0-1)
    """
    if vec1 is None or vec2 is None:
        return 0.0

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


def semantic_deduplicate(
    results: List[Dict[str, Any]],
    threshold: float = SEMANTIC_DEDUP_THRESHOLD,
    content_key: str = "content",
    fallback_key: str = "snippet",
) -> Tuple[List[Dict[str, Any]], int]:
    """
    语义去重

    使用 Embedding 相似度判断内容是否重复。

    Args:
        results: 搜索结果列表
        threshold: 相似度阈值（超过则认为重复）
        content_key: 内容字段名
        fallback_key: 备选内容字段名

    Returns:
        (去重后的结果列表, 移除的数量)
    """
    if not results:
        return [], 0

    if not SEMANTIC_DEDUP_ENABLED:
        logger.debug("️ [SemanticDedup] 语义去重已禁用")
        return results, 0

    model = _get_embedding_model()
    if model is None:
        logger.debug("️ [SemanticDedup] 模型不可用，跳过语义去重")
        return results, 0

    unique_results: List[Dict[str, Any]] = []
    unique_embeddings: List[np.ndarray] = []
    removed_count = 0

    for result in results:
        # 获取内容
        content = result.get(content_key) or result.get(fallback_key) or ""
        if not content:
            # 无内容，保留
            unique_results.append(result)
            continue

        # 计算 Embedding
        embedding = compute_embedding(content)
        if embedding is None:
            # Embedding 计算失败，保留
            unique_results.append(result)
            continue

        # 检查与已有结果的相似度
        is_duplicate = False
        for existing_embedding in unique_embeddings:
            similarity = cosine_similarity(embedding, existing_embedding)
            if similarity >= threshold:
                is_duplicate = True
                logger.debug(f" [SemanticDedup] 语义重复 (相似度={similarity:.3f}) | " f"内容前50字: {content[:50]}...")
                break

        if is_duplicate:
            removed_count += 1
            result["_semantic_duplicate"] = True
        else:
            unique_results.append(result)
            unique_embeddings.append(embedding)

    if removed_count > 0:
        logger.info(f" [SemanticDedup] 语义去重完成 | 移除={removed_count} | 保留={len(unique_results)}")

    return unique_results, removed_count


def batch_compute_embeddings(texts: List[str]) -> List[Optional[np.ndarray]]:
    """
    批量计算 Embedding（更高效）

    Args:
        texts: 文本列表

    Returns:
        Embedding 向量列表
    """
    if not texts or not SEMANTIC_DEDUP_ENABLED:
        return [None] * len(texts)

    model = _get_embedding_model()
    if model is None:
        return [None] * len(texts)

    try:
        # 截断过长文本
        truncated = [t[:512] if t else "" for t in texts]
        embeddings = model.encode(truncated, convert_to_numpy=True)

        # 缓存结果
        for text, embedding in zip(texts, embeddings):
            if text:
                _embedding_cache.set(text, embedding)

        return list(embeddings)
    except Exception as e:
        logger.warning(f"️ [SemanticDedup] 批量 Embedding 计算失败: {e}")
        return [None] * len(texts)


def clear_cache() -> None:
    """清理 Embedding 缓存"""
    _embedding_cache.clear()
    logger.debug("️ [SemanticDedup] Embedding 缓存已清理")


def get_cache_stats() -> Dict[str, int]:
    """获取缓存统计"""
    return {
        "cache_size": len(_embedding_cache._cache),
        "max_size": EMBEDDING_CACHE_SIZE,
    }
