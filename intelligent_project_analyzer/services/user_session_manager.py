# -*- coding: utf-8 -*-
"""
用户会话隔离管理器

确保每个用户的进度、会话、限流完全隔离：
1. 用户级别的会话列表
2. 用户级别的进度跟踪
3. 用户级别的限流配额
4. 用户级别的 WebSocket 连接
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger

from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager


@dataclass
class UserProgress:
    """用户进度信息"""
    user_id: str
    session_id: str
    status: str = "idle"  # idle, running, waiting, completed, failed
    progress: float = 0.0
    current_stage: str = ""
    detail: str = ""
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "detail": self.detail,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }


class UserSessionManager:
    """
    用户会话隔离管理器
    
    确保：
    - 每个用户看到自己的进度
    - 每个用户有独立的会话列表
    - 每个用户有独立的限流配额
    - 用户 A 的操作不会影响用户 B
    
    Usage:
        manager = UserSessionManager()
        await manager.connect()
        
        # 创建用户会话
        session_id = await manager.create_user_session("user123", "分析我的项目")
        
        # 更新进度
        await manager.update_progress("user123", session_id, progress=0.5, stage="分析中")
        
        # 获取用户的所有会话
        sessions = await manager.get_user_sessions("user123")
    """
    
    # Redis Key 前缀
    USER_SESSIONS_PREFIX = "user:sessions:"      # user:sessions:{user_id} -> [session_id1, session_id2]
    USER_PROGRESS_PREFIX = "user:progress:"      # user:progress:{user_id}:{session_id} -> progress_data
    USER_ACTIVE_PREFIX = "user:active:"          # user:active:{user_id} -> current_session_id
    USER_QUOTA_PREFIX = "user:quota:"            # user:quota:{user_id} -> quota_data
    
    # 配置
    MAX_SESSIONS_PER_USER = 10          # 每用户最多保留的会话数
    MAX_CONCURRENT_PER_USER = 2         # 每用户最多同时运行的分析数
    USER_SESSION_TTL = 86400 * 7        # 用户会话保留 7 天
    
    def __init__(self):
        self._session_manager: Optional[RedisSessionManager] = None
        self._local_cache: Dict[str, Dict] = {}  # 本地缓存，减少 Redis 查询
    
    async def connect(self):
        """连接 Redis"""
        self._session_manager = RedisSessionManager()
        await self._session_manager.connect()
        logger.info("✅ 用户会话隔离管理器已连接")
    
    async def disconnect(self):
        """断开连接"""
        if self._session_manager:
            await self._session_manager.disconnect()
    
    # ==================== 会话管理 ====================
    
    async def create_user_session(
        self,
        user_id: str,
        user_input: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        为用户创建新会话
        
        Args:
            user_id: 用户ID
            user_input: 用户输入
            session_id: 可选的会话ID，如果不提供则自动生成
            
        Returns:
            会话ID
        """
        import uuid
        
        if not session_id:
            session_id = f"{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        # 检查用户并发限制
        active_count = await self._get_user_active_count(user_id)
        if active_count >= self.MAX_CONCURRENT_PER_USER:
            logger.warning(f"⚠️ 用户 {user_id} 已达并发上限 ({active_count}/{self.MAX_CONCURRENT_PER_USER})")
            # 不阻止，只警告
        
        # 创建会话
        await self._session_manager.create(session_id, {
            "session_id": session_id,
            "user_id": user_id,
            "user_input": user_input,
            "status": "initializing",
            "progress": 0.0,
            "created_at": datetime.now().isoformat()
        })
        
        # 添加到用户会话列表
        await self._add_to_user_sessions(user_id, session_id)
        
        # 设置用户当前活跃会话
        await self._set_user_active_session(user_id, session_id)
        
        # 初始化进度
        await self.update_progress(user_id, session_id, status="initializing", progress=0.0)
        
        logger.info(f"✅ 用户 {user_id} 创建会话: {session_id}")
        return session_id
    
    async def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            会话列表
        """
        key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        
        try:
            # 获取会话ID列表
            session_ids = await self._session_manager.redis_client.lrange(key, 0, limit - 1)
            
            # 获取每个会话的详情
            sessions = []
            for sid in session_ids:
                session = await self._session_manager.get(sid)
                if session:
                    sessions.append({
                        "session_id": sid,
                        "status": session.get("status"),
                        "progress": session.get("progress", 0),
                        "created_at": session.get("created_at"),
                        "user_input": session.get("user_input", "")[:100]  # 截断
                    })
            
            return sessions
            
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return []
    
    async def get_user_active_session(self, user_id: str) -> Optional[str]:
        """获取用户当前活跃会话"""
        key = f"{self.USER_ACTIVE_PREFIX}{user_id}"
        try:
            return await self._session_manager.redis_client.get(key)
        except:
            return None
    
    # ==================== 进度管理 ====================
    
    async def update_progress(
        self,
        user_id: str,
        session_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        stage: Optional[str] = None,
        detail: Optional[str] = None
    ):
        """
        更新用户会话进度
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            status: 状态
            progress: 进度 (0.0 - 1.0)
            stage: 当前阶段
            detail: 详细信息
        """
        key = f"{self.USER_PROGRESS_PREFIX}{user_id}:{session_id}"
        
        # 获取现有进度
        try:
            existing = await self._session_manager.redis_client.hgetall(key)
        except:
            existing = {}
        
        # 更新字段
        update_data = {
            "updated_at": datetime.now().isoformat()
        }
        if status is not None:
            update_data["status"] = status
        if progress is not None:
            update_data["progress"] = str(progress)
        if stage is not None:
            update_data["current_stage"] = stage
        if detail is not None:
            update_data["detail"] = detail
        
        try:
            await self._session_manager.redis_client.hset(key, mapping=update_data)
            await self._session_manager.redis_client.expire(key, self.USER_SESSION_TTL)
            
            # 同时更新主会话
            await self._session_manager.update(session_id, {
                k: v for k, v in update_data.items() if k != "updated_at"
            })
            
        except Exception as e:
            logger.error(f"更新进度失败: {e}")
    
    async def get_progress(self, user_id: str, session_id: str) -> Optional[UserProgress]:
        """
        获取用户会话进度
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            进度信息
        """
        key = f"{self.USER_PROGRESS_PREFIX}{user_id}:{session_id}"
        
        try:
            data = await self._session_manager.redis_client.hgetall(key)
            if not data:
                return None
            
            return UserProgress(
                user_id=user_id,
                session_id=session_id,
                status=data.get("status", "unknown"),
                progress=float(data.get("progress", 0)),
                current_stage=data.get("current_stage", ""),
                detail=data.get("detail", ""),
                started_at=data.get("started_at"),
                updated_at=data.get("updated_at")
            )
        except Exception as e:
            logger.error(f"获取进度失败: {e}")
            return None
    
    async def get_all_user_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有会话的进度"""
        sessions = await self.get_user_sessions(user_id)
        
        progress_list = []
        for session in sessions:
            progress = await self.get_progress(user_id, session["session_id"])
            if progress:
                progress_list.append(progress.to_dict())
            else:
                progress_list.append({
                    "session_id": session["session_id"],
                    "status": session.get("status", "unknown"),
                    "progress": session.get("progress", 0)
                })
        
        return progress_list
    
    # ==================== 配额管理 ====================
    
    async def check_user_quota(self, user_id: str) -> Dict[str, Any]:
        """
        检查用户配额
        
        Returns:
            配额信息
        """
        active_count = await self._get_user_active_count(user_id)
        sessions = await self.get_user_sessions(user_id)
        
        return {
            "user_id": user_id,
            "active_sessions": active_count,
            "max_concurrent": self.MAX_CONCURRENT_PER_USER,
            "can_start_new": active_count < self.MAX_CONCURRENT_PER_USER,
            "total_sessions": len(sessions),
            "max_sessions": self.MAX_SESSIONS_PER_USER
        }
    
    async def increment_user_usage(self, user_id: str, tokens_used: int = 0):
        """记录用户使用量（用于计费或限额）"""
        key = f"{self.USER_QUOTA_PREFIX}{user_id}"
        
        try:
            pipe = self._session_manager.redis_client.pipeline()
            pipe.hincrby(key, "total_requests", 1)
            pipe.hincrby(key, "total_tokens", tokens_used)
            pipe.hset(key, "last_used", datetime.now().isoformat())
            await pipe.execute()
        except Exception as e:
            logger.error(f"记录用户使用量失败: {e}")
    
    async def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """获取用户使用量统计"""
        key = f"{self.USER_QUOTA_PREFIX}{user_id}"
        
        try:
            data = await self._session_manager.redis_client.hgetall(key)
            return {
                "user_id": user_id,
                "total_requests": int(data.get("total_requests", 0)),
                "total_tokens": int(data.get("total_tokens", 0)),
                "last_used": data.get("last_used")
            }
        except:
            return {"user_id": user_id, "total_requests": 0, "total_tokens": 0}
    
    # ==================== 内部方法 ====================
    
    async def _add_to_user_sessions(self, user_id: str, session_id: str):
        """添加会话到用户列表"""
        key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        
        try:
            # 添加到列表头部
            await self._session_manager.redis_client.lpush(key, session_id)
            
            # 限制列表长度
            await self._session_manager.redis_client.ltrim(key, 0, self.MAX_SESSIONS_PER_USER - 1)
            
            # 设置过期时间
            await self._session_manager.redis_client.expire(key, self.USER_SESSION_TTL)
            
        except Exception as e:
            logger.error(f"添加用户会话失败: {e}")
    
    async def _set_user_active_session(self, user_id: str, session_id: str):
        """设置用户当前活跃会话"""
        key = f"{self.USER_ACTIVE_PREFIX}{user_id}"
        
        try:
            await self._session_manager.redis_client.set(key, session_id, ex=3600)  # 1小时过期
        except Exception as e:
            logger.error(f"设置活跃会话失败: {e}")
    
    async def _get_user_active_count(self, user_id: str) -> int:
        """获取用户当前运行中的会话数"""
        sessions = await self.get_user_sessions(user_id)
        
        active_count = 0
        for session in sessions:
            if session.get("status") in ["running", "waiting_for_input", "initializing"]:
                active_count += 1
        
        return active_count
    
    async def cleanup_user_sessions(self, user_id: str):
        """清理用户过期会话"""
        sessions = await self.get_user_sessions(user_id, limit=50)
        
        for session in sessions:
            status = session.get("status")
            if status in ["completed", "failed", "cancelled"]:
                # 可以选择删除或保留
                pass


# 全局实例
_user_session_manager: Optional[UserSessionManager] = None


async def get_user_session_manager() -> UserSessionManager:
    """获取用户会话管理器实例"""
    global _user_session_manager
    
    if _user_session_manager is None:
        _user_session_manager = UserSessionManager()
        await _user_session_manager.connect()
    
    return _user_session_manager
