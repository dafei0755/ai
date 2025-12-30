"""
Redis Store 适配器

实现 LangGraph Store 接口，用于持久化 agent 执行上下文
"""

import json
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..settings import settings


class RedisStore:
    """
    Redis Store 适配器
    
    兼容 LangGraph Store 接口，用于存储 agent 上下文、本体论数据等
    """
    
    STORE_PREFIX = "store:"
    NAMESPACE_SEPARATOR = ":"
    
    def __init__(self, redis_url: Optional[str] = None, fallback_to_memory: bool = True):
        """
        初始化 Redis Store
        
        Args:
            redis_url: Redis 连接 URL
            fallback_to_memory: 连接失败时是否回退到内存模式
        """
        self.redis_url = redis_url or settings.redis_url
        self.fallback_to_memory = fallback_to_memory
        self.redis_client: Optional[Redis] = None
        self.is_connected = False
        
        # 内存回退存储
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._memory_mode = False
    
    async def connect(self) -> bool:
        """连接到 Redis"""
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )
            
            await self.redis_client.ping()
            self.is_connected = True
            self._memory_mode = False
            logger.info(f"✅ Redis Store 连接成功")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Redis Store 连接失败: {e}")
            
            if self.fallback_to_memory:
                logger.warning("🔄 Redis Store 回退到内存模式")
                self._memory_mode = True
                return True
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
    
    def _make_key(self, namespace: Tuple[str, ...], key: str) -> str:
        """
        生成 Redis 键名
        
        Args:
            namespace: 命名空间元组，如 ("session", "agent_context")
            key: 键名
        
        Returns:
            完整的 Redis 键名
        """
        namespace_str = self.NAMESPACE_SEPARATOR.join(namespace)
        return f"{self.STORE_PREFIX}{namespace_str}{self.NAMESPACE_SEPARATOR}{key}"
    
    async def put(
        self, 
        namespace: Tuple[str, ...], 
        key: str, 
        value: Dict[str, Any]
    ) -> None:
        """
        存储数据
        
        Args:
            namespace: 命名空间元组
            key: 键名
            value: 要存储的值（字典）
        """
        try:
            if self._memory_mode:
                # 内存模式
                namespace_key = self.NAMESPACE_SEPARATOR.join(namespace)
                if namespace_key not in self._memory_store:
                    self._memory_store[namespace_key] = {}
                self._memory_store[namespace_key][key] = value
                return
            
            # Redis 模式
            redis_key = self._make_key(namespace, key)
            await self.redis_client.set(
                redis_key,
                json.dumps(value, ensure_ascii=False)
            )
            logger.debug(f"📝 [Store] 写入: {redis_key}")
            
        except Exception as e:
            logger.error(f"❌ Store 写入失败: {namespace}/{key}, 错误: {e}")
    
    async def get(
        self, 
        namespace: Tuple[str, ...], 
        key: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取数据
        
        Args:
            namespace: 命名空间元组
            key: 键名
        
        Returns:
            存储的值（不存在返回 None）
        """
        try:
            if self._memory_mode:
                # 内存模式
                namespace_key = self.NAMESPACE_SEPARATOR.join(namespace)
                return self._memory_store.get(namespace_key, {}).get(key)
            
            # Redis 模式
            redis_key = self._make_key(namespace, key)
            data = await self.redis_client.get(redis_key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Store 读取失败: {namespace}/{key}, 错误: {e}")
            return None
    
    async def delete(self, namespace: Tuple[str, ...], key: str) -> None:
        """
        删除数据
        
        Args:
            namespace: 命名空间元组
            key: 键名
        """
        try:
            if self._memory_mode:
                # 内存模式
                namespace_key = self.NAMESPACE_SEPARATOR.join(namespace)
                if namespace_key in self._memory_store and key in self._memory_store[namespace_key]:
                    del self._memory_store[namespace_key][key]
                return
            
            # Redis 模式
            redis_key = self._make_key(namespace, key)
            await self.redis_client.delete(redis_key)
            logger.debug(f"🗑️ [Store] 删除: {redis_key}")
            
        except Exception as e:
            logger.error(f"❌ Store 删除失败: {namespace}/{key}, 错误: {e}")
    
    async def list_namespaces(self, prefix: Tuple[str, ...] = ()) -> List[Tuple[str, ...]]:
        """
        列出所有命名空间
        
        Args:
            prefix: 命名空间前缀
        
        Returns:
            命名空间列表
        """
        try:
            if self._memory_mode:
                # 内存模式
                prefix_str = self.NAMESPACE_SEPARATOR.join(prefix) if prefix else ""
                namespaces = set()
                
                for namespace_key in self._memory_store.keys():
                    if not prefix_str or namespace_key.startswith(prefix_str):
                        namespaces.add(tuple(namespace_key.split(self.NAMESPACE_SEPARATOR)))
                
                return list(namespaces)
            
            # Redis 模式
            prefix_pattern = f"{self.STORE_PREFIX}"
            if prefix:
                prefix_pattern += self.NAMESPACE_SEPARATOR.join(prefix) + self.NAMESPACE_SEPARATOR
            prefix_pattern += "*"
            
            namespaces = set()
            async for key in self.redis_client.scan_iter(match=prefix_pattern):
                # 提取命名空间部分
                key_without_prefix = key.replace(self.STORE_PREFIX, "")
                parts = key_without_prefix.split(self.NAMESPACE_SEPARATOR)
                if len(parts) > 1:
                    namespace = tuple(parts[:-1])  # 最后一个是键名，前面是命名空间
                    namespaces.add(namespace)
            
            return list(namespaces)
            
        except Exception as e:
            logger.error(f"❌ Store 列出命名空间失败: {e}")
            return []
    
    async def search(
        self, 
        namespace: Tuple[str, ...],
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        搜索数据（简化实现）
        
        Args:
            namespace: 命名空间
            filter: 过滤条件（当前未实现）
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            (key, value) 元组列表
        """
        try:
            if self._memory_mode:
                # 内存模式
                namespace_key = self.NAMESPACE_SEPARATOR.join(namespace)
                if namespace_key not in self._memory_store:
                    return []
                
                items = list(self._memory_store[namespace_key].items())
                return items[offset:offset + limit]
            
            # Redis 模式 - 扫描命名空间下的所有键
            pattern = self._make_key(namespace, "*")
            results = []
            count = 0
            
            async for redis_key in self.redis_client.scan_iter(match=pattern):
                if count < offset:
                    count += 1
                    continue
                
                if len(results) >= limit:
                    break
                
                # 提取原始键名
                key_parts = redis_key.split(self.NAMESPACE_SEPARATOR)
                original_key = key_parts[-1]
                
                # 获取值
                data = await self.redis_client.get(redis_key)
                if data:
                    value = json.loads(data)
                    results.append((original_key, value))
                
                count += 1
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Store 搜索失败: {namespace}, 错误: {e}")
            return []


# 全局单例实例
_store: Optional[RedisStore] = None


async def get_redis_store() -> RedisStore:
    """
    获取全局 Redis Store 实例（单例模式）
    
    Returns:
        RedisStore 实例
    """
    global _store
    
    if _store is None:
        _store = RedisStore()
        await _store.connect()
    
    return _store
