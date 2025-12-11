"""
Redis 会话管理器

负责会话的持久化存储、分布式锁、TTL 管理
解决并发会话竞争问题
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.asyncio.lock import Lock
from redis.exceptions import RedisError, LockError
from pydantic import BaseModel
from langgraph.types import Interrupt

from ..settings import settings

# 自定义 JSON 编码器，处理 Pydantic 模型
class PydanticEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class RedisSessionManager:
    """Redis 会话管理器"""

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
    SESSION_TTL = 604800  # 🔥 v3.6优化: 会话过期时间从1小时延长到7天（604800秒）
    LOCK_TIMEOUT = 30  # 锁超时时间：30秒
    
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
                socket_connect_timeout=10,  # 增加连接超时
                socket_timeout=10,          # 增加操作超时
                retry_on_timeout=True       # 启用超时重试
            )
            
            # 测试连接
            await self.redis_client.ping()
            self.is_connected = True
            self._memory_mode = False
            logger.info(f"✅ Redis 连接成功: {self.redis_url}")
            return True
            
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"⚠️ Redis 连接失败: {e}")
            
            if self.fallback_to_memory:
                logger.warning("🔄 回退到内存模式（仅适用于开发环境）")
                self._memory_mode = True
                self.is_connected = False
                return True  # 内存模式视为"成功"
            else:
                logger.error("❌ Redis 不可用且未启用回退模式")
                return False
    
    async def disconnect(self):
        """断开 Redis 连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("👋 Redis 连接已关闭")
    
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
                logger.debug(f"📝 [内存] 创建会话: {session_id}")
                return True
            
            # Redis 模式
            key = self._get_session_key(session_id)
            await self.redis_client.setex(
                key,
                self.SESSION_TTL,
                json.dumps(sanitized_data, ensure_ascii=False, cls=PydanticEncoder)
            )
            logger.debug(f"📝 [Redis] 创建会话: {session_id} (TTL={self.SESSION_TTL}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建会话失败: {session_id}, 错误: {e}")
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
                    logger.warning(f"⚠️ 获取会话失败 (尝试 {attempt + 1}/{max_retries}): {e}, 重试中...")
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error(f"❌ 获取会话失败 (最终): {session_id}, 错误: {e}")
                    return None
            except Exception as e:
                logger.error(f"❌ 获取会话失败 (未知错误): {session_id}, 错误: {e}")
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
                        logger.warning(f"⚠️ 会话不存在: {session_id}")
                        return False
                    
                    sanitized_updates = self._sanitize_for_json(updates)
                    self._memory_sessions[session_id].update(sanitized_updates)
                    logger.debug(f"🔄 [内存] 更新会话: {session_id}")
                    return True
                
                # Redis 模式 - 使用分布式锁防止并发冲突
                lock = Lock(self.redis_client, self._get_lock_key(session_id), timeout=self.LOCK_TIMEOUT)
                
                async with lock:
                    session_data = await self.get(session_id)
                    if not session_data:
                        logger.warning(f"⚠️ 会话不存在: {session_id}")
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
                        json.dumps(sanitized_session, ensure_ascii=False, cls=PydanticEncoder)
                    )
                    
                    logger.debug(f"🔄 [Redis] 更新会话: {session_id}")
                    return True
            
            except (RedisError, ConnectionError, TimeoutError, LockError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ 更新会话失败 (尝试 {attempt + 1}/{max_retries}): {e}, 重试中...")
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error(f"❌ 更新会话失败 (最终): {session_id}, 错误: {e}")
                    return False
            except Exception as e:
                logger.error(f"❌ 更新会话失败 (未知错误): {session_id}, 错误: {e}")
                return False
    
    async def delete(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话 ID
        
        Returns:
            是否删除成功
        """
        try:
            if self._memory_mode:
                # 内存模式
                if session_id in self._memory_sessions:
                    del self._memory_sessions[session_id]
                    logger.debug(f"🗑️ [内存] 删除会话: {session_id}")
                return True
            
            # Redis 模式
            key = self._get_session_key(session_id)
            await self.redis_client.delete(key)
            logger.debug(f"🗑️ [Redis] 删除会话: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除会话失败: {session_id}, 错误: {e}")
            return False
    
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
            logger.error(f"❌ 检查会话存在性失败: {session_id}, 错误: {e}")
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
            logger.debug(f"⏰ [Redis] 延长会话 TTL: {session_id} → {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ 延长会话 TTL 失败: {session_id}, 错误: {e}")
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
            logger.error(f"❌ 列出会话失败: {e}")
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
                logger.info(f"🧹 [内存] 清理过期会话: {count} 个")
            
            return count
            
        except Exception as e:
            logger.error(f"❌ 清理过期会话失败: {e}")
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

            # Redis 模式 - 扫描所有会话键
            sessions = []
            # 🔥 修复：只匹配会话键，不包括追问历史等其他键
            # 会话键格式: session:api-20251201211627-35b71dec
            # 追问历史键格式: session:api-20251201211627-35b71dec:ffollowup_history
            # 使用更精确的模式匹配
            pattern = f"{self.SESSION_PREFIX}*"

            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                # 🔥 跳过追问历史和其他子键
                if ":ffollowup_history" in key or ":" in key.replace(self.SESSION_PREFIX, "", 1):
                    continue

                try:
                    data = await self.redis_client.get(key)
                    if data:
                        session = json.loads(data)
                        # 🔥 修复：确保session是字典类型
                        if isinstance(session, dict):
                            sessions.append(session)
                        else:
                            logger.warning(f"⚠️ 会话数据类型错误: {key}, 类型: {type(session)}")
                except Exception as e:
                    logger.warning(f"⚠️ 解析会话数据失败: {key}, 错误: {e}")
                    continue

            # 按创建时间倒序排序（最新的在前面）
            # 🔥 修复：添加类型检查和默认值
            sessions.sort(key=lambda x: x.get("created_at", "") if isinstance(x, dict) else "", reverse=True)

            return sessions

        except Exception as e:
            logger.error(f"❌ 获取所有会话失败: {e}")
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
