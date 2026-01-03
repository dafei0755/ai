# intelligent_project_analyzer/services/device_session_manager.py
"""
设备会话管理器
用于限制同一账号只能在一台设备登录（方案B：设备绑定）

v3.0.24 新增
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

# 使用 redis.asyncio 代替 aioredis（兼容性更好）
try:
    from redis.asyncio import Redis
except ImportError:
    from redis import asyncio as Redis


class DeviceSessionManager:
    """
    设备会话管理器（单例模式 - P1优化）

    功能：
    1. 记录用户当前有效设备
    2. 新设备登录时踢出旧设备
    3. 验证设备是否被踢出

    存储格式（Redis）：
    - Key: device:user:{user_id}
    - Value: {"device_id": "xxx", "login_time": "...", "device_info": "..."}
    - TTL: 与 JWT 过期时间一致（默认 7 天）

    性能优化（v7.120 P1）：
    - 使用__new__实现真单例，避免重复初始化
    - 预期性能：4.05s → 0.05s
    """

    DEVICE_PREFIX = "device:user:"
    DEFAULT_TTL = 60 * 60 * 24 * 7  # 7 天

    _instance = None
    _lock = None

    def __new__(cls):
        """单例模式：确保全局只有一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # __init__可能被多次调用，只初始化一次
        if hasattr(self, "_init_done"):
            return
        self._init_done = True

        self.redis_client: Optional[Redis] = None
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.device_ttl = int(os.getenv("JWT_EXPIRY", str(self.DEFAULT_TTL)))
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化 Redis 连接"""
        if self._initialized:
            return True

        try:
            # 使用 Redis.from_url（redis.asyncio 兼容 aioredis API）
            self.redis_client = Redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            await self.redis_client.ping()
            self._initialized = True
            logger.info("✅ DeviceSessionManager Redis 连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ DeviceSessionManager Redis 连接失败: {e}")
            return False

    async def close(self):
        """关闭 Redis 连接"""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False

    def _get_key(self, user_id: int) -> str:
        """获取用户设备的 Redis Key"""
        return f"{self.DEVICE_PREFIX}{user_id}"

    async def register_device(self, user_id: int, device_id: str, device_info: Optional[str] = None) -> Dict[str, Any]:
        """
        注册新设备登录

        如果已有其他设备登录，旧设备将被踢出

        Args:
            user_id: 用户 ID
            device_id: 设备唯一标识
            device_info: 设备信息（浏览器、操作系统等）

        Returns:
            {
                "success": True,
                "kicked_device": "old_device_id" or None,
                "message": "..."
            }
        """
        if not self._initialized:
            await self.initialize()

        key = self._get_key(user_id)

        try:
            # 检查是否有旧设备
            old_data_str = await self.redis_client.get(key)
            old_device_id = None

            if old_data_str:
                old_data = json.loads(old_data_str)
                old_device_id = old_data.get("device_id")

                if old_device_id == device_id:
                    # 同一设备，更新登录时间
                    logger.info(f"🔄 用户 {user_id} 同一设备重新登录: {device_id[:8]}...")
                    old_device_id = None  # 不算踢出
                else:
                    # 不同设备，踢出旧设备
                    logger.warning(f"⚠️ 用户 {user_id} 新设备登录，踢出旧设备: {old_device_id[:8]}...")

            # 保存新设备信息
            new_data = {
                "device_id": device_id,
                "login_time": datetime.utcnow().isoformat(),
                "device_info": device_info or "Unknown",
            }

            await self.redis_client.setex(key, self.device_ttl, json.dumps(new_data))

            logger.info(f"✅ 用户 {user_id} 设备注册成功: {device_id[:8]}...")

            return {
                "success": True,
                "kicked_device": old_device_id,
                "message": "设备登录成功" if not old_device_id else "已踢出其他设备",
            }

        except Exception as e:
            logger.error(f"❌ 设备注册失败: {e}")
            return {"success": False, "kicked_device": None, "message": f"设备注册失败: {str(e)}"}

    async def verify_device(self, user_id: int, device_id: str) -> Dict[str, Any]:
        """
        验证设备是否有效（未被踢出）

        Args:
            user_id: 用户 ID
            device_id: 设备唯一标识

        Returns:
            {
                "valid": True/False,
                "reason": "..." (如果无效)
            }
        """
        if not self._initialized:
            await self.initialize()

        key = self._get_key(user_id)

        try:
            data_str = await self.redis_client.get(key)

            if not data_str:
                # 没有设备记录，可能是旧 Token（无设备ID）
                # 为了向后兼容，允许通过
                logger.debug(f"⚠️ 用户 {user_id} 无设备记录（旧Token兼容模式）")
                return {"valid": True, "reason": "legacy_token"}

            data = json.loads(data_str)
            current_device_id = data.get("device_id")

            if current_device_id == device_id:
                # 设备有效
                return {"valid": True, "reason": "device_match"}
            else:
                # 设备已被踢出
                logger.warning(f"⚠️ 用户 {user_id} 设备已被踢出: {device_id[:8]}... (当前有效: {current_device_id[:8]}...)")
                return {"valid": False, "reason": "device_kicked", "message": "您的账号已在其他设备登录，当前设备已被踢出"}

        except Exception as e:
            logger.error(f"❌ 设备验证失败: {e}")
            # 验证失败时，允许通过（降级处理）
            return {"valid": True, "reason": "verification_error"}

    async def logout_device(self, user_id: int) -> bool:
        """
        登出设备（清除设备记录）

        Args:
            user_id: 用户 ID

        Returns:
            是否成功
        """
        if not self._initialized:
            await self.initialize()

        key = self._get_key(user_id)

        try:
            await self.redis_client.delete(key)
            logger.info(f"✅ 用户 {user_id} 设备已登出")
            return True
        except Exception as e:
            logger.error(f"❌ 设备登出失败: {e}")
            return False

    async def get_device_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户当前登录设备信息

        Args:
            user_id: 用户 ID

        Returns:
            设备信息字典或 None
        """
        if not self._initialized:
            await self.initialize()

        key = self._get_key(user_id)

        try:
            data_str = await self.redis_client.get(key)
            if data_str:
                return json.loads(data_str)
            return None
        except Exception as e:
            logger.error(f"❌ 获取设备信息失败: {e}")
            return None


# 全局单例
_device_manager: Optional[DeviceSessionManager] = None


def get_device_manager() -> DeviceSessionManager:
    """获取设备管理器单例"""
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceSessionManager()
    return _device_manager
