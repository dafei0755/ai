"""
Redis Store 适配器

实现 LangGraph Store 接口，用于持久化 agent 执行上下文
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as aioredis
from loguru import logger
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
        """
         P1修复: 增强Redis连接容错与重试

        连接到 Redis，失败时自动重试并降级
        """
        import asyncio

        max_retries = 3
        base_delay = 1.0  # 初始延迟1秒

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f" 正在连接Redis (尝试 {attempt}/{max_retries})...")

                #  P1修复: 添加连接超时
                self.redis_client = await asyncio.wait_for(
                    aioredis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        max_connections=50,
                        socket_connect_timeout=5,  #  连接超时5秒
                        socket_timeout=10,  #  操作超时10秒
                        retry_on_timeout=True,  #  超时自动重试
                    ),
                    timeout=10.0,
                )

                #  P1修复: 验证连接（带超时）
                await asyncio.wait_for(self.redis_client.ping(), timeout=3.0)

                self.is_connected = True
                self._memory_mode = False
                logger.success(f" Redis Store 连接成功")
                return True

            except asyncio.TimeoutError:
                logger.warning(f"️ Redis连接超时 (尝试 {attempt}/{max_retries})")

            except RedisError as redis_err:
                logger.warning(f" Redis错误: {redis_err} (尝试 {attempt}/{max_retries})")

            except Exception as e:
                logger.warning(f"️ Redis Store 连接失败: {e} (尝试 {attempt}/{max_retries})")

            #  P1修复: 指数退避重试
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))  # 1s, 2s, 4s
                logger.info(f" 等待 {delay:.1f}秒后重试...")
                await asyncio.sleep(delay)

        #  P1修复: 所有重试失败，降级到内存模式
        logger.error(" Redis连接失败，已达最大重试次数")

        if self.fallback_to_memory:
            logger.warning(" Redis Store 回退到内存模式")
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

    async def put(self, namespace: Tuple[str, ...], key: str, value: Dict[str, Any]) -> None:
        """
         P1修复: 增强写入容错，Redis失败时自动降级

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

            #  P1修复: Redis写入带超时与异常处理
            redis_key = self._make_key(namespace, key)

            import asyncio

            await asyncio.wait_for(
                self.redis_client.set(redis_key, json.dumps(value, ensure_ascii=False)), timeout=5.0  #  写入超时5秒
            )
            logger.debug(f" [Store] 写入: {redis_key}")

        except asyncio.TimeoutError:
            logger.error(f"️ Store写入超时: {namespace}/{key}")
            #  P1修复: 超时时切换到内存模式
            if self.fallback_to_memory and not self._memory_mode:
                logger.warning(" 检测到Redis超时，降级到内存模式")
                self._memory_mode = True
                # 递归调用，使用内存模式重试
                await self.put(namespace, key, value)

        except (RedisError, ConnectionError) as redis_err:
            logger.error(f" Store写入Redis错误: {namespace}/{key}, 错误: {redis_err}")
            #  P1修复: Redis错误时切换到内存模式
            if self.fallback_to_memory and not self._memory_mode:
                logger.warning(" 检测到Redis连接错误，降级到内存模式")
                self._memory_mode = True
                self.is_connected = False
                await self.put(namespace, key, value)

        except Exception as e:
            logger.error(f" Store 写入失败: {namespace}/{key}, 错误: {e}")

    async def get(self, namespace: Tuple[str, ...], key: str) -> Optional[Dict[str, Any]]:
        """
         P1修复: 增强读取容错，Redis失败时自动降级

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

            #  P1修复: Redis读取带超时
            redis_key = self._make_key(namespace, key)

            import asyncio

            data = await asyncio.wait_for(self.redis_client.get(redis_key), timeout=5.0)  #  读取超时5秒

            if data:
                return json.loads(data)
            return None

        except asyncio.TimeoutError:
            logger.error(f"️ Store读取超时: {namespace}/{key}")
            #  P1修复: 超时时切换到内存模式
            if self.fallback_to_memory and not self._memory_mode:
                logger.warning(" 检测到Redis超时，降级到内存模式")
                self._memory_mode = True
                return await self.get(namespace, key)
            return None

        except (RedisError, ConnectionError) as redis_err:
            logger.error(f" Store读取Redis错误: {namespace}/{key}, 错误: {redis_err}")
            #  P1修复: Redis错误时切换到内存模式
            if self.fallback_to_memory and not self._memory_mode:
                logger.warning(" 检测到Redis连接错误，降级到内存模式")
                self._memory_mode = True
                self.is_connected = False
                return await self.get(namespace, key)
            return None

        except Exception as e:
            logger.error(f" Store 读取失败: {namespace}/{key}, 错误: {e}")
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
            logger.debug(f"️ [Store] 删除: {redis_key}")

        except Exception as e:
            logger.error(f" Store 删除失败: {namespace}/{key}, 错误: {e}")

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
            logger.error(f" Store 列出命名空间失败: {e}")
            return []

    async def search(
        self, namespace: Tuple[str, ...], filter: Optional[Dict[str, Any]] = None, limit: int = 10, offset: int = 0
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
                return items[offset : offset + limit]

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
            logger.error(f" Store 搜索失败: {namespace}, 错误: {e}")
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
