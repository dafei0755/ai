"""
Redis 会话管理器

负责会话的持久化存储、分布式锁、TTL 管理
解决并发会话竞争问题
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from langgraph.types import Interrupt
from loguru import logger
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.asyncio.lock import Lock
from redis.exceptions import LockError, RedisError

from ..settings import settings

# Legacy compatibility: expose `redis` attribute for older tests that patch the module
redis = aioredis


# 自定义 JSON 编码器，处理 Pydantic 模型
class PydanticEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            #  Phase 0优化: 排除None和默认值以减少token消耗
            return obj.model_dump(exclude_none=True, exclude_defaults=True)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class RedisSessionManager:
    """Redis 会话管理器"""

    async def save_state_async(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """兼容旧版接口的异步 save_state，自动选择创建或更新."""

        existing = await self.get(session_id)
        if existing:
            return await self.update(session_id, session_data)
        return await self.create(session_id, session_data)

    def save_state(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """同步 save_state 兼容方法（仅在无事件循环时调用）"""

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            raise RuntimeError("save_state 仅支持在无事件循环的上下文中调用；请改用 save_state_async")

        return asyncio.run(self.save_state_async(session_id, session_data))

    @staticmethod
    def _sanitize_for_json(payload: Any) -> Any:
        """递归移除无法序列化到 JSON 的对象（例如 Interrupt）"""

        if isinstance(payload, Interrupt):
            return RedisSessionManager._sanitize_for_json(getattr(payload, "value", None))

        if isinstance(payload, dict):
            return {key: RedisSessionManager._sanitize_for_json(value) for key, value in payload.items()}

        if isinstance(payload, list):
            return [RedisSessionManager._sanitize_for_json(item) for item in payload]

        if isinstance(payload, tuple):
            return [RedisSessionManager._sanitize_for_json(item) for item in payload]

        if isinstance(payload, set):
            return [RedisSessionManager._sanitize_for_json(item) for item in payload]

        return payload

    # 常量配置
    SESSION_PREFIX = "session:"
    LOCK_PREFIX = "lock:session:"
    WEBSOCKET_PREFIX = "ws:session:"
    SESSION_TTL = 604800  #  v3.6优化: 会话过期时间从1小时延长到7天（604800秒）
    LOCK_TIMEOUT = 60  #  Fix 1.2: 锁超时时间从30秒增加到60秒

    def __init__(self, redis_url: Optional[str] = None, fallback_to_memory: bool = True):
        """
        初始化 Redis 会话管理器

        Args:
            redis_url: Redis 连接 URL（默认从 settings 读取）
            fallback_to_memory: Redis 连接失败时是否回退到内存模式
        """
        self.redis_url = redis_url or settings.redis_url
        self.fallback_to_memory = fallback_to_memory
        self.redis_client: Optional[Redis] = None
        self.is_connected = False

        # 内存回退存储（仅用于开发环境）
        self._memory_sessions: Dict[str, Dict[str, Any]] = {}
        self._memory_mode = False

        #  v7.105: 添加会话列表缓存（10分钟TTL）
        self._sessions_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 600  #  v7.118: 从5分钟增加到10分钟，减少Redis查询频率

        #  性能优化: 状态查询缓存配置
        self.STATUS_CACHE_PREFIX = "status_cache:"
        self.STATUS_CACHE_TTL = 30  # 状态缓存30秒

    async def connect(self) -> bool:
        """
        连接到 Redis

        Returns:
            是否成功连接
        """
        try:
            # 创建连接池配置
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=10,  # 保持连接超时10秒
                socket_timeout=30,  #  Fix 1.3: 操作超时从10秒增加到30秒
                retry_on_timeout=True,  # 启用超时重试
                retry_on_error=[ConnectionError, TimeoutError],  #  Fix 1.3: 增加连接错误重试
            )

            # 测试连接
            await self.redis_client.ping()
            self.is_connected = True
            self._memory_mode = False
            logger.info(f" Redis 连接成功: {self.redis_url}")
            return True

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"️ Redis 连接失败: {e}")

            if self.fallback_to_memory:
                logger.warning(" 回退到内存模式（仅适用于开发环境）")
                self._memory_mode = True
                self.is_connected = False
                return True  # 内存模式视为"成功"
            else:
                logger.error(" Redis 不可用且未启用回退模式")
                return False

    async def disconnect(self):
        """断开 Redis 连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info(" Redis 连接已关闭")

    def _get_session_key(self, session_id: str) -> str:
        """获取会话键名"""
        return f"{self.SESSION_PREFIX}{session_id}"

    def _get_lock_key(self, session_id: str) -> str:
        """获取锁键名"""
        return f"{self.LOCK_PREFIX}{session_id}"

    async def create(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        创建新会话

        Args:
            session_id: 会话 ID
            session_data: 会话数据

        Returns:
            是否创建成功
        """
        try:
            # 添加创建时间
            session_data["created_at"] = datetime.now().isoformat()
            session_data["session_id"] = session_id
            sanitized_data = self._sanitize_for_json(session_data)

            if self._memory_mode:
                # 内存模式
                self._memory_sessions[session_id] = sanitized_data
                logger.debug(f" [内存] 创建会话: {session_id}")
                self._invalidate_cache()  #  Fix 1.4: 清除缓存
                return True

            # Redis 模式
            key = self._get_session_key(session_id)
            await self.redis_client.setex(
                key, self.SESSION_TTL, json.dumps(sanitized_data, ensure_ascii=False, cls=PydanticEncoder)
            )
            logger.debug(f" [Redis] 创建会话: {session_id} (TTL={self.SESSION_TTL}s)")
            self._invalidate_cache()  #  Fix 1.4: 清除缓存
            return True

        except Exception as e:
            logger.error(f" 创建会话失败: {session_id}, 错误: {e}")
            return False

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话数据

        Args:
            session_id: 会话 ID

        Returns:
            会话数据（不存在返回 None）
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if self._memory_mode:
                    # 内存模式
                    return self._memory_sessions.get(session_id)

                # Redis 模式
                key = self._get_session_key(session_id)
                data = await self.redis_client.get(key)

                if data:
                    return json.loads(data)
                return None

            except (RedisError, ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"️ 获取会话失败 (尝试 {attempt + 1}/{max_retries}): {e}, 重试中...")
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error(f" 获取会话失败 (最终): {session_id}, 错误: {e}")
                    return None
            except Exception as e:
                logger.error(f" 获取会话失败 (未知错误): {session_id}, 错误: {e}")
                return None

    async def update(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新会话数据（合并更新）

        Args:
            session_id: 会话 ID
            updates: 要更新的字段

        Returns:
            是否更新成功
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if self._memory_mode:
                    # 内存模式
                    if session_id not in self._memory_sessions:
                        logger.warning(f"️ 会话不存在: {session_id}")
                        return False

                    sanitized_updates = self._sanitize_for_json(updates)
                    self._memory_sessions[session_id].update(sanitized_updates)
                    logger.debug(f" [内存] 更新会话: {session_id}")
                    return True

                # Redis 模式 - 使用分布式锁防止并发冲突
                lock = Lock(self.redis_client, self._get_lock_key(session_id), timeout=self.LOCK_TIMEOUT)

                try:
                    async with lock:
                        session_data = await self.get(session_id)
                        if not session_data:
                            logger.warning(f"️ 会话不存在: {session_id}")
                            return False

                        # 合并更新
                        sanitized_updates = self._sanitize_for_json(updates)
                        session_data.update(sanitized_updates)
                        sanitized_session = self._sanitize_for_json(session_data)

                        # 写回 Redis 并刷新 TTL
                        key = self._get_session_key(session_id)
                        await self.redis_client.setex(
                            key,
                            self.SESSION_TTL,
                            json.dumps(sanitized_session, ensure_ascii=False, cls=PydanticEncoder),
                        )

                        logger.debug(f" [Redis] 更新会话: {session_id}")
                        self._invalidate_cache()  #  Fix 1.4: 清除缓存
                        await self._invalidate_status_cache(session_id)  #  性能优化: 失效状态缓存
                        return True

                except LockError as e:
                    #  Fix 1.2: Separate handling for lock errors
                    if "no longer owned" in str(e):
                        logger.warning(f"️ 更新会话时锁已过期 (尝试 {attempt + 1}/{max_retries}): {session_id}")
                        # Data was likely written before lock expired
                        if attempt == 0:  # Only log info once
                            logger.info(f"ℹ️ 会话更新可能已完成，尽管锁释放失败")
                        return True  # Treat as success since data was written
                    else:
                        # Lock acquisition failed - will retry
                        logger.warning(f"️ 获取锁失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        raise  # Re-raise to trigger retry logic

            except (RedisError, ConnectionError, TimeoutError, LockError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"️ 更新会话失败 (尝试 {attempt + 1}/{max_retries}): {e}, 重试中...")
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error(f" 更新会话失败 (最终): {session_id}, 错误: {e}")
                    return False
            except Exception as e:
                logger.error(f" 更新会话失败 (未知错误): {session_id}, 错误: {e}")
                return False

    async def _invalidate_status_cache(self, session_id: str) -> None:
        """
        使状态缓存失效

         性能优化: 在会话更新时清除缓存，确保数据一致性

        Args:
            session_id: 会话 ID
        """
        if self._memory_mode or not self.redis_client:
            return

        try:
            cache_key = f"{self.STATUS_CACHE_PREFIX}{session_id}"
            await self.redis_client.delete(cache_key)
            logger.debug(f"️ 清除状态缓存: {session_id}")
        except Exception as e:
            logger.warning(f"️ 清除状态缓存失败: {session_id}, 错误: {e}")

    async def get_status_with_cache(self, session_id: str, include_history: bool = False) -> Optional[Dict[str, Any]]:
        """
        带缓存的状态查询

         性能优化: 使用 Redis 缓存减少序列化开销
        预期性能提升: 2.03s → <500ms

        Args:
            session_id: 会话 ID
            include_history: 是否包含完整 history（影响缓存策略）

        Returns:
            会话状态数据
        """
        # 内存模式直接查询
        if self._memory_mode:
            return await self.get(session_id)

        # 如果需要完整 history，跳过缓存（history 太大，不适合缓存）
        if include_history:
            return await self.get(session_id)

        try:
            cache_key = f"{self.STATUS_CACHE_PREFIX}{session_id}"

            # 尝试从缓存读取
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.debug(f" 命中状态缓存: {session_id}")
                return json.loads(cached_data)

            # 缓存未命中，从数据库查询
            logger.debug(f" 未命中状态缓存: {session_id}，查询数据库")
            session_data = await self.get(session_id)

            if session_data:
                # 写入缓存（排除 history 以减少缓存大小）
                cache_data = {k: v for k, v in session_data.items() if k != "history"}
                await self.redis_client.setex(
                    cache_key, self.STATUS_CACHE_TTL, json.dumps(cache_data, ensure_ascii=False, cls=PydanticEncoder)
                )
                logger.debug(f" 写入状态缓存: {session_id}, TTL={self.STATUS_CACHE_TTL}s")

            return session_data

        except Exception as e:
            # 缓存失败时回退到直接查询
            logger.warning(f"️ 状态缓存操作失败: {session_id}, 回退到直接查询, 错误: {e}")
            return await self.get(session_id)

    async def cleanup_invalid_user_sessions(self, user_id: str) -> int:
        """
        清理用户索引中的无效会话（会话数据不存在但索引残留）

         v7.106.1: 自动清理幽灵会话索引

        Args:
            user_id: 用户ID

        Returns:
            清理的无效会话数量
        """
        if self._memory_mode:
            return 0

        try:
            user_sessions_key = f"user:sessions:{user_id}"
            # 获取用户索引列表中的所有会话ID
            session_ids = await self.redis_client.lrange(user_sessions_key, 0, -1)

            if not session_ids:
                return 0

            invalid_count = 0
            for session_id in session_ids:
                # 检查会话是否存在
                session_key = self._get_session_key(session_id)
                exists = await self.redis_client.exists(session_key)

                if not exists:
                    # 会话不存在，从用户索引中移除
                    await self.redis_client.lrem(user_sessions_key, 1, session_id)
                    invalid_count += 1
                    logger.info(f" 清理无效会话索引: {session_id} (用户: {user_id})")

            if invalid_count > 0:
                logger.info(f" 清理完成: {invalid_count} 个无效会话索引 (用户: {user_id})")

            return invalid_count
        except Exception as e:
            logger.error(f" 清理无效会话索引失败 (用户: {user_id}): {e}")
            return 0

    async def delete(self, session_id: str) -> bool:
        """
        删除会话（含分布式锁保护和级联删除）

         v7.106: 添加分布式锁、级联删除用户索引、进度数据、活跃会话标记

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        lock_key = f"lock:delete:{session_id}"
        lock = None

        try:
            #  v7.106: 获取分布式锁（防止并发删除）
            if not self._memory_mode:
                lock = self.redis_client.lock(lock_key, timeout=10)
                acquired = await lock.acquire(blocking_timeout=3)
                if not acquired:
                    logger.warning(f"️ 获取删除锁失败（会话可能正在被删除）: {session_id}")
                    return False

            # 1. 获取会话信息（需要user_id）
            session = await self.get(session_id)
            if not session:
                logger.debug(f"️ 会话不存在（已删除）: {session_id}")
                return True

            user_id = session.get("user_id")

            # 2. 删除主会话数据
            if self._memory_mode:
                if session_id in self._memory_sessions:
                    del self._memory_sessions[session_id]
                    logger.debug(f"️ [内存] 删除会话: {session_id}")
            else:
                key = self._get_session_key(session_id)
                await self.redis_client.delete(key)
                logger.debug(f"️ [Redis] 删除主会话数据: {session_id}")

            #  3. 删除用户索引（关键！避免用户面板显示幽灵会话）
            if user_id and not self._memory_mode:
                user_sessions_key = f"user:sessions:{user_id}"
                removed = await self.redis_client.lrem(user_sessions_key, 1, session_id)
                logger.debug(f"️ 删除用户索引: {user_sessions_key}, 移除数: {removed}")

            #  4. 删除用户进度数据
            if user_id and not self._memory_mode:
                progress_key = f"user:progress:{user_id}:{session_id}"
                await self.redis_client.delete(progress_key)
                logger.debug(f"️ 删除进度数据: {progress_key}")

            #  5. 清除活跃会话标记（如果是当前活跃会话）
            if user_id and not self._memory_mode:
                active_key = f"user:active:{user_id}"
                current_active = await self.redis_client.get(active_key)
                if current_active and current_active == session_id:
                    await self.redis_client.delete(active_key)
                    logger.debug(f"️ 清除活跃会话标记: {active_key}")

            # 6. 清除缓存
            self._invalidate_cache()

            #  v7.131: 清理 Playwright 浏览器池资源（会话删除时）
            try:
                from intelligent_project_analyzer.api.html_pdf_generator import PlaywrightBrowserPool

                await asyncio.wait_for(PlaywrightBrowserPool.cleanup(), timeout=10.0)
                logger.debug(f" Playwright 浏览器池已清理（会话删除）: {session_id}")
            except asyncio.TimeoutError:
                logger.warning(f"️ 删除会话时清理浏览器池超时: {session_id}")
            except Exception as e:
                logger.debug(f" 删除会话时清理浏览器池失败: {session_id}, {e}")

            logger.info(f" 会话及关联数据已删除: {session_id}, 用户: {user_id or 'N/A'}")
            return True

        except Exception as e:
            logger.error(f" 删除会话失败: {session_id}, 错误: {e}", exc_info=True)
            return False
        finally:
            # 释放分布式锁
            if lock:
                try:
                    await lock.release()
                except Exception as e:
                    logger.warning(f"️ 释放删除锁失败: {e}")

    async def exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_id: 会话 ID

        Returns:
            是否存在
        """
        try:
            if self._memory_mode:
                return session_id in self._memory_sessions

            key = self._get_session_key(session_id)
            return await self.redis_client.exists(key) > 0

        except Exception as e:
            logger.error(f" 检查会话存在性失败: {session_id}, 错误: {e}")
            return False

    async def extend_ttl(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        延长会话过期时间（用于活跃会话续期）

        Args:
            session_id: 会话 ID
            ttl: 新的 TTL（秒），默认使用 SESSION_TTL

        Returns:
            是否成功
        """
        try:
            if self._memory_mode:
                # 内存模式不需要 TTL
                return True

            ttl = ttl or self.SESSION_TTL
            key = self._get_session_key(session_id)
            await self.redis_client.expire(key, ttl)
            logger.debug(f" [Redis] 延长会话 TTL: {session_id} → {ttl}s")
            return True

        except Exception as e:
            logger.error(f" 延长会话 TTL 失败: {session_id}, 错误: {e}")
            return False

    async def list_all_sessions(self) -> List[str]:
        """
        列出所有会话 ID（用于管理和调试）

        Returns:
            会话 ID 列表
        """
        try:
            if self._memory_mode:
                return list(self._memory_sessions.keys())

            # Redis 模式 - 使用 SCAN 遍历（避免阻塞）
            session_keys = []
            async for key in self.redis_client.scan_iter(match=f"{self.SESSION_PREFIX}*"):
                session_id = key.replace(self.SESSION_PREFIX, "")
                session_keys.append(session_id)

            return session_keys

        except Exception as e:
            logger.error(f" 列出会话失败: {e}")
            return []

    async def cleanup_expired(self) -> int:
        """
        清理过期会话（Redis 自动清理，此方法用于内存模式）

        Returns:
            清理的会话数量
        """
        if not self._memory_mode:
            # Redis 模式自动处理 TTL，无需手动清理
            return 0

        # 内存模式 - 手动清理（开发环境）
        try:
            count = 0
            now = datetime.now()
            expired_sessions = []

            for session_id, data in self._memory_sessions.items():
                created_at = datetime.fromisoformat(data.get("created_at", now.isoformat()))
                if now - created_at > timedelta(seconds=self.SESSION_TTL):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self._memory_sessions[session_id]
                count += 1

            if count > 0:
                logger.info(f" [内存] 清理过期会话: {count} 个")

            return count

        except Exception as e:
            logger.error(f" 清理过期会话失败: {e}")
            return 0

    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        获取所有会话列表

        Returns:
            会话列表
        """
        try:
            if self._memory_mode:
                # 内存模式 - 直接返回所有会话
                return list(self._memory_sessions.values())

            #  v7.105: 检查缓存
            if self._sessions_cache and self._cache_timestamp:
                cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
                if cache_age < self._cache_ttl:
                    logger.debug(f" 使用会话列表缓存 (age: {cache_age:.1f}s)")
                    return self._sessions_cache

            #  v7.106: 性能优化 - 批量获取会话
            # 第1步：快速扫描所有键（只获取键名，不获取值）
            all_keys = []
            pattern = f"{self.SESSION_PREFIX}*"
            async for key in self.redis_client.scan_iter(match=pattern, count=1000):
                # 解码键名（bytes -> str）
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                #  只保留主会话键（排除子键如 :ffollowup_history）
                # 会话键格式: session:api-20251201211627-35b71dec
                # 子键格式: session:api-20251201211627-35b71dec:ffollowup_history
                if ":" not in key_str.replace(self.SESSION_PREFIX, "", 1):
                    all_keys.append(key_str)

            if not all_keys:
                logger.debug(" 未找到任何会话")
                return []

            # 第2步： Fix 1.5 + v7.118: 分块批量获取会话数据（使用Pipeline优化）
            CHUNK_SIZE = 30  #  v7.118: 从20增加到30，减少批次数
            num_chunks = (len(all_keys) + CHUNK_SIZE - 1) // CHUNK_SIZE
            logger.debug(f" 批量获取 {len(all_keys)} 个会话数据（分 {num_chunks} 批）...")

            sessions = []
            try:
                for i in range(0, len(all_keys), CHUNK_SIZE):
                    chunk_keys = all_keys[i : i + CHUNK_SIZE]
                    chunk_num = i // CHUNK_SIZE + 1

                    try:
                        # 获取本批次数据
                        chunk_values = await self.redis_client.mget(chunk_keys)

                        for key, value in zip(chunk_keys, chunk_values):
                            if not value:
                                continue

                            try:
                                session = json.loads(value)
                                if isinstance(session, dict):
                                    # Ensure session_id is included
                                    if "session_id" not in session:
                                        session["session_id"] = key.replace(self.SESSION_PREFIX, "")
                                    sessions.append(session)
                                else:
                                    logger.warning(f"️ 会话数据类型错误: {key}, 类型: {type(session)}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"️ 解析会话数据失败: {key}, 错误: {e}")
                                continue

                    except (RedisError, TimeoutError) as e:
                        logger.warning(f"️ 批次 {chunk_num}/{num_chunks} 获取失败: {e}，继续处理下一批")
                        continue

                logger.debug(f" 批量获取完成，有效会话: {len(sessions)}/{len(all_keys)}")
            except Exception as e:
                logger.error(f" 批量获取会话失败: {e}")
                return []

            # 按创建时间倒序排序（最新的在前面）
            #  修复：添加类型检查和默认值
            sessions.sort(key=lambda x: x.get("created_at", "") if isinstance(x, dict) else "", reverse=True)

            #  Fix 1.4: 添加会话统计诊断
            status_counts = {}
            old_sessions = []
            now = datetime.now()

            for session in sessions:
                status = session.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

                # 检查已完成的旧会话
                created_at_str = session.get("created_at", "")
                if created_at_str and status in ["completed", "failed"]:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        age_hours = (now - created_at).total_seconds() / 3600
                        if age_hours > 24:  # 超过24小时
                            old_sessions.append(
                                {
                                    "session_id": session.get("session_id"),
                                    "status": status,
                                    "age_hours": round(age_hours, 1),
                                }
                            )
                    except (ValueError, TypeError):
                        pass

            logger.info(f" Redis 会话统计: {status_counts}")
            if old_sessions:
                logger.warning(f"️ 发现 {len(old_sessions)} 个旧的已完成会话 (>24小时)")
                logger.debug(f"旧会话列表: {old_sessions[:5]}")  # 只记录前5个

            #  v7.105: 更新缓存
            self._sessions_cache = sessions
            self._cache_timestamp = datetime.now()
            logger.debug(f" 会话列表已缓存 ({len(sessions)} 个会话)")

            return sessions

        except Exception as e:
            logger.error(f" 获取所有会话失败: {e}")
            # 返回缓存数据（如果有）
            if self._sessions_cache:
                logger.warning(f"️ 返回缓存数据 ({len(self._sessions_cache)} 个会话)")
                return self._sessions_cache
            return []

    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
         Fix 1.4: 清理已完成的旧会话（归档后删除）

        Args:
            max_age_hours: 会话最大年龄（小时），默认24小时

        Returns:
            清理的会话数
        """
        try:
            all_sessions = await self.get_all_sessions()
            cleaned = 0
            now = datetime.now()

            for session in all_sessions:
                session_id = session.get("session_id")
                status = session.get("status", "")
                created_at_str = session.get("created_at", "")

                # 只清理已完成/失败的会话
                if status not in ["completed", "failed"]:
                    continue

                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_hours = (now - created_at).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        # 归档后删除 (注意: 实际使用时需要集成 session_archive_manager)
                        # 现在只从 Redis 删除
                        await self.delete(session_id)
                        cleaned += 1
                        logger.info(f"️ 清理旧会话: {session_id} (年龄: {age_hours:.1f}小时, 状态: {status})")

                except (ValueError, TypeError) as e:
                    logger.debug(f"️ 跳过会话 {session_id}: 日期解析失败 ({e})")
                    continue

            if cleaned > 0:
                logger.info(f" 清理完成: 删除 {cleaned} 个旧会话")
                # 清除缓存以反映更新
                self._invalidate_cache()

            return cleaned

        except Exception as e:
            logger.error(f" 清理旧会话失败: {e}")
            return 0

    def _invalidate_cache(self):
        """清除会话列表缓存"""
        self._sessions_cache = None
        self._cache_timestamp = None
        logger.debug(" 会话列表缓存已失效")

    async def get_dimension_historical_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
         v7.117: 获取维度使用历史数据（用于智能学习优化）

        从最近的已完成会话中提取维度选择和用户反馈数据，
        供 AdaptiveDimensionGenerator 进行学习优化。

        Args:
            limit: 最大返回记录数，默认100

        Returns:
            历史数据列表，每条包含：
            - session_id: 会话ID
            - selected_dimensions: 选中的维度列表
            - dimension_values: 用户设置的维度值
            - feedback: 用户反馈（如果有）
            - project_type: 项目类型
        """
        try:
            # 获取所有已完成会话
            all_sessions = await self.get_all_sessions()

            # 筛选已完成的会话
            completed_sessions = [s for s in all_sessions if s.get("status") == "completed"]

            # 按创建时间倒序（最新的在前）
            completed_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            historical_data = []

            for session_meta in completed_sessions[:limit]:
                session_id = session_meta.get("session_id")
                if not session_id:
                    continue

                # 获取完整会话数据
                session_data = await self.get(session_id)
                if not session_data:
                    continue

                # 提取维度相关数据
                selected_dimensions = session_data.get("selected_radar_dimensions", [])
                dimension_values = session_data.get("radar_dimension_values", {})

                # 如果没有维度数据，跳过
                if not selected_dimensions and not dimension_values:
                    continue

                # 提取反馈数据（如果有）
                usage_metadata = session_data.get("dimension_usage_metadata", {})
                feedback = usage_metadata.get("feedback") if usage_metadata else None

                historical_data.append(
                    {
                        "session_id": session_id,
                        "selected_dimensions": selected_dimensions,
                        "dimension_values": dimension_values,
                        "feedback": feedback,
                        "project_type": session_data.get("project_type", "unknown"),
                        "created_at": session_meta.get("created_at"),
                    }
                )

            logger.info(f" [历史数据] 加载了 {len(historical_data)} 条维度使用记录 " f"(来自 {len(completed_sessions)} 个已完成会话)")

            return historical_data

        except Exception as e:
            logger.error(f" 获取维度历史数据失败: {e}")
            return []


# 全局单例实例
_session_manager: Optional[RedisSessionManager] = None


async def get_session_manager() -> RedisSessionManager:
    """
    获取全局会话管理器实例（单例模式）

    Returns:
        RedisSessionManager 实例
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = RedisSessionManager()
        await _session_manager.connect()

    return _session_manager
