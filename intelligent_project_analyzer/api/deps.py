"""
认证依赖和通用工具函数 (MT-1 提取自 api/server.py)

提取内容：
  - _parse_aspect_ratio        : 宽高比字符串转枚举
  - TTLCache                   : 带TTL的内存缓存类
  - sessions_cache             : 全局会话列表缓存（5s TTL）
  - DEV_MODE                   : 开发模式标志
  - jwt_service                : WordPress JWT 服务实例
  - get_current_user           : 强制JWT认证 FastAPI 依赖
  - get_user_identifier        : 获取用户标识符（字符串）
  - optional_auth              : 可选JWT认证 FastAPI 依赖
  - get_current_user_optional  : optional_auth 的别名
  - sync_checkpoint_to_redis   : LangGraph checkpoint → Redis 同步
  - _serialize_for_json        : 递归JSON序列化工具
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from intelligent_project_analyzer.api._server_proxy import server_proxy as _server
from intelligent_project_analyzer.services.image_generator import ImageAspectRatio
from intelligent_project_analyzer.services.wordpress_jwt_service import WordPressJWTService
from intelligent_project_analyzer.settings import settings

# ============================================================
#  v7.60.4: 宽高比工具
# ============================================================


def _parse_aspect_ratio(ratio_str: str = None) -> ImageAspectRatio:
    """将前端传递的字符串宽高比转换为 ImageAspectRatio 枚举

    Args:
        ratio_str: 宽高比字符串，如 "16:9", "1:1" 等

    Returns:
        ImageAspectRatio 枚举值，默认为 LANDSCAPE
    """
    if not ratio_str:
        return ImageAspectRatio.LANDSCAPE

    mapping = {
        "1:1": ImageAspectRatio.SQUARE,
        "16:9": ImageAspectRatio.LANDSCAPE,
        "9:16": ImageAspectRatio.PORTRAIT,
        "4:3": ImageAspectRatio.WIDE,
        "21:9": ImageAspectRatio.ULTRAWIDE,
    }
    return mapping.get(ratio_str, ImageAspectRatio.LANDSCAPE)


# ============================================================
#  v7.120 P1优化: TTL缓存工具类
# ============================================================


class TTLCache:
    """简单的带TTL的异步缓存（内存级别）"""

    def __init__(self, ttl_seconds: int = 5):
        self._cache = {}
        self._timestamps = {}
        self.ttl = ttl_seconds

    def get(self, key: str):
        if key in self._cache:
            age = time.time() - self._timestamps[key]
            if age < self.ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def invalidate(self, key: str = None):
        """使缓存失效"""
        if key:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
        else:
            self._cache.clear()
            self._timestamps.clear()


# 全局会话列表缓存（5秒TTL，适合高频刷新场景）
sessions_cache = TTLCache(ttl_seconds=5)


# ============================================================
#  v7.35: 开发模式标志 & JWT 服务
# ============================================================

# 兼容：显式 DEV_MODE=true 或 ENVIRONMENT=dev（单测/本地开发常用）
DEV_MODE = (
    os.getenv("DEV_MODE", "false").lower() == "true"
    or os.getenv("ENVIRONMENT", "").lower() == "dev"
    or getattr(settings, "environment", None) == "dev"
)

# 初始化 JWT 服务
jwt_service = WordPressJWTService()


# ============================================================
#  认证依赖函数
# ============================================================


async def get_current_user(request: Request) -> dict:
    """
    FastAPI 依赖函数：从请求头验证 JWT Token 并返回用户信息

    用于保护需要认证的端点

     v7.35: 支持开发模式，接受 "dev-token-mock" 作为有效 Token
    """
    auth_header = request.headers.get("Authorization", "")
    #  开发/测试环境：允许不带 Token 直接访问（便于本地调试与自动化测试）
    # 生产环境 DEV_MODE=False 时不会生效。
    if DEV_MODE and (not auth_header or not auth_header.startswith("Bearer ")):
        logger.info(" [DEV_MODE] 未提供 Token，使用开发测试用户")
        return {
            "user_id": 9999,
            "username": "dev_user",
            "email": "dev@localhost",
            "name": "开发测试用户",
            "roles": ["administrator"],
        }

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 Token")

    token = auth_header[7:]  # 移除 "Bearer " 前缀

    #  v7.35: 开发模式支持 - 接受 mock token
    if DEV_MODE and token == "dev-token-mock":
        logger.info(" [DEV_MODE] 使用开发测试用户")
        return {
            "user_id": 9999,
            "username": "dev_user",
            "email": "dev@localhost",
            "name": "开发测试用户",
            "roles": ["administrator"],
        }

    payload = jwt_service.verify_jwt_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    #  v7.200: 兼容部分JWT使用标准字段 sub 作为用户名/主体
    # 与 optional_auth 函数保持一致，确保会话创建和查询使用相同的用户名解析逻辑
    resolved_username = payload.get("sub") or payload.get("username")

    return {
        "user_id": payload.get("user_id"),
        "username": resolved_username,
        "email": payload.get("email"),
        "name": payload.get("display_name") or payload.get("name"),
        "roles": payload.get("roles", []),
    }


def get_user_identifier(current_user: dict) -> str:
    """
     v7.335: 统一获取用户标识符（用户名字符串）- 修复间歇性历史记录不可见问题

    【核心修复】开发模式下强制返回固定标识符，解决 username/user_id 不一致导致的间歇性问题。

    优先级：
    - 开发模式：固定返回 "dev_user"
    - 生产模式：sub > username > str(user_id) > "unknown"

    注意：返回的是用户名字符串，不是数字ID。
    会话的 user_id 字段存储的就是这个用户名字符串。

    用于：
    - 会话创建时设置 user_id（存储用户名）
    - 会话列表过滤
    - 权限验证
    - 归档会话过滤

    Args:
        current_user: 从 get_current_user 或 optional_auth 返回的用户字典

    Returns:
        用户标识符字符串（永不为空）
    """
    if not current_user:
        return "unknown"

    #  v7.335: 开发模式下强制返回固定标识符，确保与存储的 user_id 一致
    if DEV_MODE:
        # 始终返回 "dev_user"，避免 username 和 str(user_id) 之间的不一致
        return "dev_user"

    # 生产模式：优先使用 sub（JWT标准字段），然后是 username
    # 注意：get_current_user 已经处理了 sub，但为了防御性编程仍然检查
    identifier = current_user.get("sub") or current_user.get("username")

    # 如果都没有，使用 user_id 的字符串形式
    if not identifier:
        user_id = current_user.get("user_id")
        identifier = str(user_id) if user_id else "unknown"

    return identifier


#  v7.130: 可选认证依赖函数（Token存在则验证，不存在也允许访问）
async def optional_auth(request: Request) -> dict | None:
    """
    可选认证依赖函数：如果有JWT Token则验证，没有也不报错

    用于支持登录和未登录用户都能访问的端点
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None  # 未提供 Token，返回 None

    token = auth_header[7:]

    # 开发模式支持
    if DEV_MODE and token == "dev-token-mock":
        return {
            "user_id": 9999,
            "username": "dev_user",
            "email": "dev@localhost",
            "name": "开发测试用户",
            "roles": ["administrator"],
        }

    payload = jwt_service.verify_jwt_token(token)

    if not payload:
        return None  # Token无效，返回None而不是抛异常

    # ️ 兼容：部分JWT使用标准字段 sub 作为用户名/主体
    # 在某些SSO实现里，username 字段可能为空或为占位值（例如 api），
    # 这会导致会话管理页面显示错误的用户。这里优先使用 sub。
    resolved_username = payload.get("sub") or payload.get("username")

    return {
        "user_id": payload.get("user_id"),
        "username": resolved_username,
        "email": payload.get("email"),
        "name": payload.get("display_name") or payload.get("name"),
        "roles": payload.get("roles", []),
    }


#  v7.189: 导出别名供其他模块使用（如search_routes.py）
get_current_user_optional = optional_auth


# ============================================================
#  v7.145: Checkpoint → Redis 数据同步
# ============================================================


async def sync_checkpoint_to_redis(session_id: str) -> bool:
    """
    从 checkpoint 数据库同步关键字段到 Redis

    解决问题：
    - LangGraph 工作流数据保存在 checkpoint（MessagePack 格式）
    - Redis 会话管理器只有基础元数据
    - 归档时从 Redis 获取数据导致不完整

    Args:
        session_id: 会话ID

    Returns:
        是否同步成功
    """
    try:
        from .workflow_runner import get_or_create_async_checkpointer

        #  v7.146: 复用全局 checkpointer 实例，避免误用异步上下文管理器
        checkpointer = await get_or_create_async_checkpointer()
        if not checkpointer:
            logger.error(f" [v7.146] 无法获取 checkpointer 实例: {session_id}")
            return False

        config = {"configurable": {"thread_id": session_id}}
        checkpoint = await checkpointer.aget(config)

        if not checkpoint:
            logger.warning(f"️ [v7.145] 未找到 checkpoint 数据: {session_id}")
            return False

        # 提取关键字段
        state = checkpoint["channel_values"]
        sync_data = {}

        # 同步工作流状态字段
        key_fields = [
            "structured_requirements",
            "restructured_requirements",
            "strategic_analysis",
            "execution_batches",
            "total_batches",
            "current_batch",
            "active_agents",
            "agent_results",
            "final_report",
            "aggregated_results",
            "pdf_path",
            #  v7.153: 添加问卷流程相关字段，确保进度正确同步
            "progressive_questionnaire_step",
            "progressive_questionnaire_completed",
            "questionnaire_summary_completed",
            "confirmed_core_tasks",
            "gap_filling_answers",
            "selected_dimensions",
            "radar_dimension_values",
            "requirements_confirmed",
            "requirements_summary_text",
        ]

        for field in key_fields:
            value = state.get(field)
            if value is not None:
                sync_data[field] = value

        # 更新 Redis
        if sync_data:
            sm = await _server._get_session_manager()
            await sm.update(session_id, sync_data)
            logger.info(f" [v7.145] 同步 {len(sync_data)} 个字段到 Redis: {session_id}")
            logger.debug(f"   同步字段: {list(sync_data.keys())}")
            return True
        else:
            logger.warning(f"️ [v7.145] checkpoint 无可同步数据: {session_id}")
            return False

    except Exception as e:
        logger.error(f" [v7.146] checkpoint 同步失败: {session_id}, 错误类型: {type(e).__name__}, 详情: {e}")
        return False


# ============================================================
#  JSON 序列化工具
# ============================================================


def _serialize_for_json(data: Any) -> Any:
    from langgraph.types import Command, Interrupt

    if isinstance(data, Command):
        return {
            "__type__": "Command",
            "goto": data.goto,
            "update": _serialize_for_json(data.update) if data.update else None,
        }
    if isinstance(data, Interrupt):
        value = getattr(data, "value", None)
        return {
            "__type__": "Interrupt",
            "value": _serialize_for_json(value) if value is not None else None,
        }
    if isinstance(data, BaseModel):
        #  Phase 0优化: 排除None和默认值以减少token消耗
        return _serialize_for_json(data.model_dump(exclude_none=True, exclude_defaults=True))
    if isinstance(data, dict):
        return {k: _serialize_for_json(v) for k, v in data.items()}
    if isinstance(data, list | tuple):
        return [_serialize_for_json(item) for item in data]
    if isinstance(data, datetime):
        return data.isoformat()
    return data
