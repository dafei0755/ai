"""
语义缓存服务 (v7.625 P1-C)

基于向量相似度的智能缓存，用于需求分析结果复用。

核心特性：
1. 语义匹配 - 使用OpenAI Embeddings + Cosine Similarity
2. 相似度阈值 - 默认0.90（高精度匹配）
3. Redis向量存储 - 支持高效向量检索
4. 自动过期 - 7天TTL
5. 命中率统计 - 监控缓存效果

适用场景：
- 设计公司批量提交相似需求
- 同一用户多次调整需求
- 相似项目类型（如多个咖啡馆设计）

预期收益：
- 命中率：40-60%（设计公司场景）
- 响应时间：62s → 0.5s（命中时）
- 成本节省：50%（假设50%命中率）

配置环境变量：
- SEMANTIC_CACHE_ENABLED: 是否启用（默认: true）
- SEMANTIC_CACHE_SIMILARITY_THRESHOLD: 相似度阈值（默认: 0.90）
- SEMANTIC_CACHE_TTL: 缓存过期时间秒数（默认: 604800，即7天）
- OPENAI_API_KEY: OpenAI API密钥（用于生成embeddings）
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
from loguru import logger


@dataclass
class SemanticCacheStats:
    """语义缓存统计信息"""

    hits: int = 0
    misses: int = 0
    total_saved_time_ms: float = 0.0
    total_similarity_checks: int = 0
    avg_similarity_score: float = 0.0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate:.2%}",
            "total_saved_time_ms": round(self.total_saved_time_ms, 2),
            "total_similarity_checks": self.total_similarity_checks,
            "avg_similarity_score": round(self.avg_similarity_score, 4),
        }


@dataclass
class SemanticCacheEntry:
    """语义缓存条目"""

    key: str
    input_text: str
    embedding: List[float]
    output_data: Dict[str, Any]
    created_at: float
    ttl: int
    hit_count: int = 0
    last_similarity: float = 0.0

    def to_redis_dict(self) -> Dict[str, Any]:
        """转换为Redis存储格式"""
        return {
            "key": self.key,
            "input_text": self.input_text,
            "embedding": json.dumps(self.embedding),
            "output_data": json.dumps(self.output_data, ensure_ascii=False),
            "created_at": self.created_at,
            "ttl": self.ttl,
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_redis_dict(cls, data: Dict[str, Any]) -> "SemanticCacheEntry":
        """从Redis格式恢复"""
        return cls(
            key=data["key"],
            input_text=data["input_text"],
            embedding=json.loads(data["embedding"]),
            output_data=json.loads(data["output_data"]),
            created_at=float(data["created_at"]),
            ttl=int(data["ttl"]),
            hit_count=int(data.get("hit_count", 0)),
        )


class SemanticCache:
    """
    语义缓存服务

    使用OpenAI Embeddings + Cosine Similarity实现语义匹配
    """

    def __init__(
        self,
        enabled: bool = True,
        similarity_threshold: float = 0.90,
        ttl: int = 604800,  # 7天
        redis_url: str | None = None,
        openai_api_key: str | None = None,
    ):
        """
        初始化语义缓存

        Args:
            enabled: 是否启用缓存
            similarity_threshold: 相似度阈值（0.0-1.0），默认0.90
            ttl: 缓存过期时间（秒），默认7天
            redis_url: Redis连接URL
            openai_api_key: OpenAI API密钥
        """
        self.enabled = enabled
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        self.redis_url = redis_url
        self.openai_api_key = openai_api_key

        # 统计信息
        self._stats = SemanticCacheStats()

        # Redis客户端
        self._redis_client = None
        self._use_redis = False

        # OpenAI客户端
        self._openai_client = None
        self._use_openai = False

        if redis_url:
            self._init_redis(redis_url)

        if openai_api_key:
            self._init_openai(openai_api_key)

        logger.info(
            f"🧠 SemanticCache initialized: enabled={enabled}, "
            f"threshold={similarity_threshold}, ttl={ttl}s, "
            f"redis={'enabled' if self._use_redis else 'disabled'}, "
            f"openai={'enabled' if self._use_openai else 'disabled'}"
        )

    def _init_redis(self, redis_url: str) -> None:
        """初始化Redis连接"""
        try:
            import redis

            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            self._redis_client.ping()
            self._use_redis = True
            logger.info(f"✅ Redis语义缓存已连接: {redis_url}")
        except ImportError:
            logger.warning("⚠️ redis库未安装，语义缓存不可用。安装: pip install redis")
        except Exception as e:
            logger.warning(f"⚠️ Redis连接失败，语义缓存不可用: {e}")

    def _init_openai(self, api_key: str) -> None:
        """初始化OpenAI客户端"""
        try:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=api_key)
            self._use_openai = True
            logger.info("✅ OpenAI Embeddings已初始化")
        except ImportError:
            logger.warning("⚠️ openai库未安装，语义缓存不可用。安装: pip install openai")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI初始化失败，语义缓存不可用: {e}")

    def _generate_embedding(self, text: str) -> List[float] | None:
        """
        生成文本的向量表示

        Args:
            text: 输入文本

        Returns:
            768维向量，或None（失败时）
        """
        if not self._use_openai:
            return None

        try:
            response = self._openai_client.embeddings.create(
                model="text-embedding-3-small",  # 768维，性价比高
                input=text,
            )
            embedding = response.data[0].embedding
            logger.debug(f"✅ 生成embedding: {len(embedding)}维")
            return embedding
        except Exception as e:
            logger.warning(f"⚠️ 生成embedding失败: {e}")
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度（0.0-1.0）
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        return float(dot_product / (norm_v1 * norm_v2))

    def _generate_cache_key(self, input_text: str) -> str:
        """
        生成缓存键

        Args:
            input_text: 输入文本

        Returns:
            唯一缓存键
        """
        hash_key = hashlib.sha256(input_text.encode()).hexdigest()[:16]
        return f"semantic:requirements:{hash_key}"

    def get(self, input_text: str) -> Tuple[Dict[str, Any], float] | None:
        """
        获取语义缓存结果

        Args:
            input_text: 输入文本（用户需求描述）

        Returns:
            (缓存结果, 相似度分数) 或 None（未命中）
        """
        if not self.enabled or not self._use_redis or not self._use_openai:
            return None

        try:
            # 1. 生成输入文本的embedding
            query_embedding = self._generate_embedding(input_text)
            if query_embedding is None:
                self._stats.misses += 1
                return None

            # 2. 获取所有缓存条目
            cache_keys = self._redis_client.keys("semantic:requirements:*")
            if not cache_keys:
                self._stats.misses += 1
                logger.debug("🔍 语义缓存为空")
                return None

            # 3. 计算相似度，找到最佳匹配
            best_match = None
            best_similarity = 0.0

            for cache_key in cache_keys:
                entry_data = self._redis_client.hgetall(cache_key)
                if not entry_data:
                    continue

                try:
                    entry = SemanticCacheEntry.from_redis_dict(entry_data)

                    # 检查是否过期
                    if time.time() - entry.created_at > entry.ttl:
                        self._redis_client.delete(cache_key)
                        continue

                    # 计算相似度
                    similarity = self._cosine_similarity(query_embedding, entry.embedding)
                    self._stats.total_similarity_checks += 1

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = entry

                except Exception as e:
                    logger.warning(f"⚠️ 解析缓存条目失败: {e}")
                    continue

            # 4. 判断是否命中
            if best_match and best_similarity >= self.similarity_threshold:
                # 命中！
                self._stats.hits += 1
                self._stats.avg_similarity_score = (
                    self._stats.avg_similarity_score * (self._stats.hits - 1) + best_similarity
                ) / self._stats.hits

                # 更新命中次数
                best_match.hit_count += 1
                self._redis_client.hset(best_match.key, "hit_count", best_match.hit_count)

                logger.info(
                    f"✅ 语义缓存命中: similarity={best_similarity:.4f}, "
                    f"hit_count={best_match.hit_count}, "
                    f"input='{input_text[:50]}...'"
                )

                return (best_match.output_data, best_similarity)
            else:
                # 未命中
                self._stats.misses += 1
                logger.debug(
                    f"🔍 语义缓存未命中: best_similarity={best_similarity:.4f} " f"< threshold={self.similarity_threshold}"
                )
                return None

        except Exception as e:
            logger.warning(f"⚠️ 语义缓存读取失败: {e}")
            self._stats.misses += 1
            return None

    def set(
        self,
        input_text: str,
        output_data: Dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """
        设置语义缓存

        Args:
            input_text: 输入文本（用户需求描述）
            output_data: 输出数据（需求分析结果）
            ttl: 可选的自定义TTL

        Returns:
            是否设置成功
        """
        if not self.enabled or not self._use_redis or not self._use_openai:
            return False

        try:
            # 1. 生成embedding
            embedding = self._generate_embedding(input_text)
            if embedding is None:
                return False

            # 2. 创建缓存条目
            cache_key = self._generate_cache_key(input_text)
            effective_ttl = ttl or self.ttl

            entry = SemanticCacheEntry(
                key=cache_key,
                input_text=input_text,
                embedding=embedding,
                output_data=output_data,
                created_at=time.time(),
                ttl=effective_ttl,
            )

            # 3. 存储到Redis（使用Hash结构）
            self._redis_client.hset(cache_key, mapping=entry.to_redis_dict())
            self._redis_client.expire(cache_key, effective_ttl)

            logger.info(f"💾 语义缓存已保存: key={cache_key}, ttl={effective_ttl}s")
            return True

        except Exception as e:
            logger.warning(f"⚠️ 语义缓存写入失败: {e}")
            return False

    def clear_all(self) -> int:
        """
        清空所有语义缓存

        Returns:
            清除的条目数
        """
        if not self._use_redis:
            return 0

        try:
            keys = self._redis_client.keys("semantic:requirements:*")
            if keys:
                count = self._redis_client.delete(*keys)
                logger.info(f"🗑️ 已清空 {count} 个语义缓存条目")
                return count
            return 0
        except Exception as e:
            logger.error(f"❌ 清空语义缓存失败: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        cache_size = 0
        if self._use_redis:
            try:
                cache_size = len(self._redis_client.keys("semantic:requirements:*"))
            except Exception:
                cache_size = -1

        return {
            **self._stats.to_dict(),
            "cache_size": cache_size,
            "similarity_threshold": self.similarity_threshold,
            "ttl": self.ttl,
            "enabled": self.enabled,
            "backend": "redis+openai" if (self._use_redis and self._use_openai) else "disabled",
        }

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目

        Returns:
            清理的条目数
        """
        if not self._use_redis:
            return 0

        try:
            keys = self._redis_client.keys("semantic:requirements:*")
            expired_count = 0

            for key in keys:
                entry_data = self._redis_client.hgetall(key)
                if not entry_data:
                    continue

                try:
                    created_at = float(entry_data.get("created_at", 0))
                    ttl = int(entry_data.get("ttl", 0))

                    if time.time() - created_at > ttl:
                        self._redis_client.delete(key)
                        expired_count += 1
                except Exception:
                    continue

            if expired_count > 0:
                logger.info(f"🗑️ 已清理 {expired_count} 个过期语义缓存条目")

            return expired_count
        except Exception as e:
            logger.error(f"❌ 清理过期缓存失败: {e}")
            return 0


# 全局单例
_semantic_cache: SemanticCache | None = None


def get_semantic_cache() -> SemanticCache:
    """获取语义缓存单例"""
    global _semantic_cache

    if _semantic_cache is None:
        import os

        enabled = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
        similarity_threshold = float(os.getenv("SEMANTIC_CACHE_SIMILARITY_THRESHOLD", "0.90"))
        ttl = int(os.getenv("SEMANTIC_CACHE_TTL", "604800"))  # 7天
        redis_url = os.getenv("REDIS_URL")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        _semantic_cache = SemanticCache(
            enabled=enabled,
            similarity_threshold=similarity_threshold,
            ttl=ttl,
            redis_url=redis_url,
            openai_api_key=openai_api_key,
        )

    return _semantic_cache
