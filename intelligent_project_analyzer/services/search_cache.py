"""
搜索结果缓存服务 (v7.174)

基于Redis的搜索结果缓存，减少重复API调用，提升响应速度。

功能：
1. 查询级别缓存 - 相同查询复用结果
2. 可配置TTL - 支持不同场景的过期时间
3. 命中率统计 - 监控缓存效果
4. 内存/Redis双模式 - 支持单机和分布式环境

配置环境变量：
- SEARCH_CACHE_ENABLED: 是否启用缓存 (默认: true)
- SEARCH_CACHE_TTL: 缓存过期时间秒数 (默认: 3600, 即1小时)
- SEARCH_CACHE_MAX_SIZE: 内存缓存最大条目数 (默认: 1000)
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict

from loguru import logger


@dataclass
class CacheStats:
    """缓存统计信息"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_saved_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{self.hit_rate:.2%}",
            "total_saved_time_ms": round(self.total_saved_time_ms, 2),
        }


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: float
    ttl: int
    query: str
    tool: str
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """更新命中次数"""
        self.hit_count += 1


class SearchCache:
    """
    搜索结果缓存服务

    支持内存缓存和Redis两种模式
    """

    def __init__(
        self,
        enabled: bool = True,
        ttl: int = 3600,
        max_size: int = 1000,
        redis_url: str | None = None,
    ):
        """
        初始化搜索缓存

        Args:
            enabled: 是否启用缓存
            ttl: 缓存过期时间（秒），默认1小时
            max_size: 内存缓存最大条目数
            redis_url: Redis连接URL，为None时使用内存缓存
        """
        self.enabled = enabled
        self.ttl = ttl
        self.max_size = max_size
        self.redis_url = redis_url

        # 内存缓存
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()

        # Redis客户端（懒加载）
        self._redis_client = None
        self._use_redis = False

        if redis_url:
            self._init_redis(redis_url)

        logger.info(
            f" SearchCache initialized: enabled={enabled}, ttl={ttl}s, "
            f"max_size={max_size}, redis={'enabled' if self._use_redis else 'disabled'}"
        )

    def _init_redis(self, redis_url: str) -> None:
        """初始化Redis连接"""
        try:
            import redis

            self._redis_client = redis.from_url(redis_url)
            self._redis_client.ping()
            self._use_redis = True
            logger.info(f" Redis缓存已连接: {redis_url}")
        except ImportError:
            logger.warning("️ redis库未安装，使用内存缓存。安装: pip install redis")
        except Exception as e:
            logger.warning(f"️ Redis连接失败，降级到内存缓存: {e}")

    def _generate_key(self, query: str, tool: str, **kwargs) -> str:
        """
        生成缓存键

        Args:
            query: 搜索查询
            tool: 搜索工具名称（bocha/tavily/serper）
            **kwargs: 其他影响结果的参数

        Returns:
            唯一缓存键
        """
        # 构建键的原始内容
        key_parts = {
            "query": query.strip().lower(),
            "tool": tool.lower(),
            **{k: v for k, v in sorted(kwargs.items()) if v is not None},
        }
        key_str = json.dumps(key_parts, sort_keys=True, ensure_ascii=False)

        # 生成哈希
        hash_key = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        return f"search:{tool}:{hash_key}"

    def get(self, query: str, tool: str, **kwargs) -> Dict[str, Any] | None:
        """
        获取缓存结果

        Args:
            query: 搜索查询
            tool: 搜索工具名称
            **kwargs: 其他参数

        Returns:
            缓存的搜索结果，或None（未命中/已过期）
        """
        if not self.enabled:
            return None

        key = self._generate_key(query, tool, **kwargs)

        try:
            if self._use_redis:
                return self._get_from_redis(key)
            else:
                return self._get_from_memory(key)
        except Exception as e:
            logger.warning(f"️ 缓存读取失败: {e}")
            self._stats.misses += 1
            return None

    def _get_from_memory(self, key: str) -> Dict[str, Any] | None:
        """从内存缓存获取"""
        entry = self._memory_cache.get(key)

        if entry is None:
            self._stats.misses += 1
            return None

        if entry.is_expired:
            del self._memory_cache[key]
            self._stats.misses += 1
            self._stats.evictions += 1
            logger.debug(f"️ 缓存过期: {key}")
            return None

        # 命中
        entry.touch()
        self._stats.hits += 1
        logger.debug(f" 缓存命中: {key} (命中次数: {entry.hit_count})")

        return entry.value

    def _get_from_redis(self, key: str) -> Dict[str, Any] | None:
        """从Redis缓存获取"""
        data = self._redis_client.get(key)

        if data is None:
            self._stats.misses += 1
            return None

        try:
            value = json.loads(data)
            self._stats.hits += 1
            logger.debug(f" Redis缓存命中: {key}")
            return value
        except json.JSONDecodeError:
            self._stats.misses += 1
            return None

    def set(self, query: str, tool: str, value: Dict[str, Any], ttl: int | None = None, **kwargs) -> bool:
        """
        设置缓存

        Args:
            query: 搜索查询
            tool: 搜索工具名称
            value: 搜索结果
            ttl: 可选的自定义TTL
            **kwargs: 其他参数

        Returns:
            是否设置成功
        """
        if not self.enabled:
            return False

        key = self._generate_key(query, tool, **kwargs)
        effective_ttl = ttl or self.ttl

        try:
            if self._use_redis:
                return self._set_to_redis(key, value, effective_ttl)
            else:
                return self._set_to_memory(key, value, effective_ttl, query, tool)
        except Exception as e:
            logger.warning(f"️ 缓存写入失败: {e}")
            return False

    def _set_to_memory(self, key: str, value: Dict[str, Any], ttl: int, query: str, tool: str) -> bool:
        """写入内存缓存"""
        # 检查容量，必要时淘汰旧条目
        if len(self._memory_cache) >= self.max_size:
            self._evict_oldest()

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
            query=query,
            tool=tool,
        )
        self._memory_cache[key] = entry
        logger.debug(f" 缓存已保存: {key} (TTL: {ttl}s)")

        return True

    def _set_to_redis(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        """写入Redis缓存"""
        data = json.dumps(value, ensure_ascii=False)
        self._redis_client.setex(key, ttl, data)
        logger.debug(f" Redis缓存已保存: {key} (TTL: {ttl}s)")
        return True

    def _evict_oldest(self) -> None:
        """淘汰最旧的缓存条目"""
        if not self._memory_cache:
            return

        # 找到最旧的条目
        oldest_key = min(self._memory_cache.keys(), key=lambda k: self._memory_cache[k].created_at)
        del self._memory_cache[oldest_key]
        self._stats.evictions += 1
        logger.debug(f"️ 缓存淘汰: {oldest_key}")

    def invalidate(self, query: str, tool: str, **kwargs) -> bool:
        """
        使指定缓存失效

        Args:
            query: 搜索查询
            tool: 搜索工具名称
            **kwargs: 其他参数

        Returns:
            是否成功删除
        """
        key = self._generate_key(query, tool, **kwargs)

        try:
            if self._use_redis:
                self._redis_client.delete(key)
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
            logger.debug(f"️ 缓存已失效: {key}")
            return True
        except Exception as e:
            logger.warning(f"️ 缓存失效操作失败: {e}")
            return False

    def clear_all(self) -> int:
        """
        清空所有缓存

        Returns:
            清除的条目数
        """
        count = 0

        try:
            if self._use_redis:
                # 只清除搜索相关的键
                keys = self._redis_client.keys("search:*")
                if keys:
                    count = self._redis_client.delete(*keys)
            else:
                count = len(self._memory_cache)
                self._memory_cache.clear()

            logger.info(f"️ 已清空 {count} 个缓存条目")
            return count
        except Exception as e:
            logger.error(f" 清空缓存失败: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            **self._stats.to_dict(),
            "cache_size": len(self._memory_cache) if not self._use_redis else "N/A (Redis)",
            "max_size": self.max_size,
            "ttl": self.ttl,
            "enabled": self.enabled,
            "backend": "redis" if self._use_redis else "memory",
        }

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目（仅内存模式）

        Returns:
            清理的条目数
        """
        if self._use_redis:
            return 0  # Redis自动处理过期

        expired_keys = [key for key, entry in self._memory_cache.items() if entry.is_expired]

        for key in expired_keys:
            del self._memory_cache[key]
            self._stats.evictions += 1

        if expired_keys:
            logger.info(f" 已清理 {len(expired_keys)} 个过期缓存条目")

        return len(expired_keys)


# 全局单例
_search_cache: SearchCache | None = None


def get_search_cache() -> SearchCache:
    """获取搜索缓存单例"""
    global _search_cache

    if _search_cache is None:
        import os

        enabled = os.getenv("SEARCH_CACHE_ENABLED", "true").lower() == "true"
        ttl = int(os.getenv("SEARCH_CACHE_TTL", "3600"))
        max_size = int(os.getenv("SEARCH_CACHE_MAX_SIZE", "1000"))
        redis_url = os.getenv("REDIS_URL")

        _search_cache = SearchCache(
            enabled=enabled,
            ttl=ttl,
            max_size=max_size,
            redis_url=redis_url,
        )

    return _search_cache


def cached_search(tool: str, ttl: int | None = None):
    """
    搜索缓存装饰器

    用法:
        @cached_search(tool="bocha")
        async def search(query: str, count: int = 10) -> Dict:
            ...
    """

    def decorator(func):
        async def wrapper(query: str, *args, **kwargs):
            cache = get_search_cache()

            # 尝试从缓存获取
            cached_result = cache.get(query, tool, **kwargs)
            if cached_result is not None:
                return cached_result

            # 执行搜索
            result = await func(query, *args, **kwargs)

            # 缓存结果
            if result:
                cache.set(query, tool, result, ttl=ttl, **kwargs)

            return result

        return wrapper

    return decorator
