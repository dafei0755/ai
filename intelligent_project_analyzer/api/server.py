# -*- coding: utf-8 -*-
"""
FastAPI 后端服务器

提供 RESTful API 接口，支持前后端分离架构
"""

import asyncio
import io
import json
import math  # v7.109: 用于分页诊断日志
import os
import re
import sys
import uuid
from collections import OrderedDict, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from types import MethodType
from typing import Any, Dict, List, Optional, Set, Tuple

# 设置输出编码为 UTF-8
if sys.platform == "win32":
    # Do NOT replace sys.stdout/sys.stderr with new TextIOWrapper objects at import time.
    # Doing so can close the underlying stream later (pytest/colorama/loggers then crash with
    # "ValueError: I/O operation on closed file"). Prefer reconfigure when available.
    for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

import time
from functools import wraps

from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

#  v7.120: 初始化生产级日志系统（环境感知配置）
from intelligent_project_analyzer.config.logging_config import setup_logging

#  导入GeoIP服务（IP地理位置识别）
from intelligent_project_analyzer.services.geoip_service import get_geoip_service

#  v7.60.4: 导入 ImageAspectRatio 枚举用于类型转换
from intelligent_project_analyzer.services.image_generator import ImageAspectRatio

setup_logging()

# 日志文件输出配置，确保主流程日志完整写入 logs/server.log
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 主日志文件（所有级别）- 启用压缩
logger.add(
    str(log_dir / "server.log"),
    rotation="10 MB",
    retention="10 days",
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=True,
    compression="zip",  #  轮转时自动压缩为 .zip 文件
    level="INFO",
)

# 认证相关日志（方便 SSO 调试）- 启用压缩
logger.add(
    str(log_dir / "auth.log"),
    rotation="5 MB",
    retention="7 days",
    encoding="utf-8",
    enqueue=True,
    compression="zip",  #  自动压缩
    filter=lambda record: "auth" in record["name"].lower()
    or "sso" in record["message"].lower()
    or "token" in record["message"].lower(),
    level="DEBUG",
)

# 错误日志（只记录 ERROR 及以上）- 启用压缩
logger.add(
    str(log_dir / "errors.log"),
    rotation="5 MB",
    retention="30 days",
    encoding="utf-8",
    enqueue=True,
    compression="zip",  #  自动压缩
    level="ERROR",
)

#  启用告警监控（拦截错误日志）
from intelligent_project_analyzer.api.alert_monitor import alert_monitor, alert_sink

logger.add(alert_sink, level="ERROR")
from typing import List

from fpdf import FPDF


#  v7.60.4: 辅助函数 - 将前端传递的字符串宽高比转换为 ImageAspectRatio 枚举
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


# HTML PDF 生成器
from intelligent_project_analyzer.api.html_pdf_generator import HTMLPDFGenerator
from intelligent_project_analyzer.api.html_pdf_generator import generate_expert_report_pdf as generate_html_pdf

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command, Interrupt

#  v3.8新增: 对话智能体
from intelligent_project_analyzer.agents.conversation_agent import ConversationAgent, ConversationContext

#  v7.15新增: 追问智能体 (LangGraph)
from intelligent_project_analyzer.agents.followup_agent import FollowupAgent
from intelligent_project_analyzer.core.state import StateManager

#  v3.7新增: 文件处理服务
from intelligent_project_analyzer.services.file_processor import build_combined_input, file_processor

#  v3.11新增: 追问历史管理器
from intelligent_project_analyzer.services.followup_history_manager import FollowupHistoryManager

#  Redis 会话管理器
from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

#  v3.6新增: 会话归档管理器
from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager

#  v7.10新增: WordPress JWT 认证服务
from intelligent_project_analyzer.services.wordpress_jwt_service import WordPressJWTService

#  使用新的统一配置 - 不再需要load_dotenv()
from intelligent_project_analyzer.settings import settings
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

# 初始化 JWT 服务
jwt_service = WordPressJWTService()


# � v7.145: Checkpoint 到 Redis 数据同步函数
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
            session_manager = await _get_session_manager()
            await session_manager.update(session_id, sync_data)
            logger.info(f" [v7.145] 同步 {len(sync_data)} 个字段到 Redis: {session_id}")
            logger.debug(f"   同步字段: {list(sync_data.keys())}")
            return True
        else:
            logger.warning(f"️ [v7.145] checkpoint 无可同步数据: {session_id}")
            return False

    except Exception as e:
        logger.error(f" [v7.146] checkpoint 同步失败: {session_id}, 错误类型: {type(e).__name__}, 详情: {e}")
        return False


# � v7.120 P1优化: TTL缓存工具类（用于会话列表缓存 4.09s→0.05s）
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

#  v7.35: 开发模式检测
# 兼容：显式 DEV_MODE=true 或 ENVIRONMENT=dev（单测/本地开发常用）
DEV_MODE = (
    os.getenv("DEV_MODE", "false").lower() == "true"
    or os.getenv("ENVIRONMENT", "").lower() == "dev"
    or getattr(settings, "environment", None) == "dev"
)


#  认证依赖函数
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
async def optional_auth(request: Request) -> Optional[dict]:
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


# 全局变量存储工作流实例
workflows: Dict[str, MainWorkflow] = {}

# LangGraph 检查点存储（异步版，全局复用）
async_checkpointer: Optional[BaseCheckpointSaver[str]] = None
async_checkpointer_lock: Optional[asyncio.Lock] = None

#  Redis 会话管理器实例（替代内存字典）
session_manager: Optional[RedisSessionManager] = None


async def _get_session_manager() -> RedisSessionManager:
    """获取会话管理器（支持在未触发生命周期事件时惰性初始化）。

    说明：在使用 ASGITransport/某些测试客户端时，FastAPI lifespan 可能不会自动触发，
    导致全局 session_manager 仍为 None。这里提供一个安全兜底。
    """
    global session_manager
    if session_manager is None:
        session_manager = RedisSessionManager()
        # connect() 内部会在 Redis 不可用时回退到内存模式（fallback_to_memory=True）。
        try:
            await session_manager.connect()
        except Exception as e:
            logger.warning(f"️ session_manager 惰性初始化失败: {e}")
    return session_manager


#  v3.6新增: 会话归档管理器实例
archive_manager: Optional[SessionArchiveManager] = None

#  v3.11新增: 追问历史管理器实例
followup_history_manager: Optional[FollowupHistoryManager] = None

# WebSocket 连接管理
websocket_connections: Dict[str, List[WebSocket]] = {}  # session_id -> [websocket1, websocket2, ...]

# Redis Pub/Sub 支持
import redis.asyncio as aioredis

redis_pubsub_client: Optional[aioredis.Redis] = None
redis_pubsub_task: Optional[asyncio.Task] = None

#  v7.1.2新增: PDF 缓存（性能优化）
from cachetools import TTLCache

pdf_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)  # 100项，1小时过期


def _serialize_for_json(data: Any) -> Any:
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
    if isinstance(data, (list, tuple)):
        return [_serialize_for_json(item) for item in data]
    if isinstance(data, datetime):
        return data.isoformat()
    return data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global session_manager, archive_manager, followup_history_manager, redis_pubsub_client, redis_pubsub_task

    # 启动时
    print("=" * 60)
    print("   智能项目分析系统 - API 服务器")
    print("=" * 60)
    print()

    #  初始化 Redis 会话管理器
    try:
        session_manager = RedisSessionManager()
        await session_manager.connect()
        print(" Redis 会话管理器已启动")
    except Exception as e:
        logger.error(f" Redis 会话管理器启动失败: {e}")
        print("️ Redis 会话管理器启动失败（使用内存模式）")

    #  v3.11新增: 初始化追问历史管理器
    try:
        followup_history_manager = FollowupHistoryManager(session_manager)
        print(" 追问历史管理器已启动")
    except Exception as e:
        logger.error(f" 追问历史管理器启动失败: {e}")
        print("️ 追问历史管理器启动失败（追问功能受限）")

    #  v3.6新增: 初始化会话归档管理器
    try:
        archive_manager = SessionArchiveManager()
        print(" 会话归档管理器已启动（永久保存功能已启用）")
    except Exception as e:
        logger.error(f" 会话归档管理器启动失败: {e}")
        print("️ 会话归档管理器启动失败（无法使用永久保存功能）")

    #  初始化 Redis Pub/Sub（用于 WebSocket 多实例广播）
    try:
        redis_pubsub_client = await aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        # 启动订阅监听任务
        redis_pubsub_task = asyncio.create_task(subscribe_to_redis_pubsub())
        print(" Redis Pub/Sub 已启动")
    except Exception as e:
        logger.warning(f"️ Redis Pub/Sub 启动失败: {e}")
        print("️ Redis Pub/Sub 启动失败（WebSocket 仅支持单实例）")

    #  v7.1.2新增: 初始化 Playwright 浏览器池（PDF 生成性能优化）
    try:
        from intelligent_project_analyzer.api.html_pdf_generator import get_browser_pool

        browser_pool = get_browser_pool()
        await browser_pool.initialize()
        print(" Playwright 浏览器池已启动（PDF 生成性能优化）")
    except Exception as e:
        logger.warning(f"️ Playwright 浏览器池启动失败: {e}")
        print("️ Playwright 浏览器池启动失败（PDF 生成将使用备用方案）")

    #  v7.120 P1优化: 预初始化设备会话管理器（消除4.05s延迟）
    try:
        from intelligent_project_analyzer.services.device_session_manager import get_device_manager

        device_manager = get_device_manager()
        await device_manager.initialize()
        print(" 设备会话管理器已预初始化（P1优化: 4.05s→0.05s）")
    except Exception as e:
        logger.warning(f"️ 设备会话管理器预初始化失败: {e}")
        print("️ 设备会话管理器预初始化失败（设备检查可能较慢）")

    print(" 服务器启动成功")
    print(" API 文档: http://localhost:8000/docs")
    print(" 健康检查: http://localhost:8000/health")
    print()

    #  v7.105: 预热会话缓存（消除首次请求延迟）
    try:
        import time

        logger.info(" 预热会话列表缓存...")
        start_time = time.time()
        sessions = await session_manager.get_all_sessions()
        elapsed = time.time() - start_time
        logger.info(f" 缓存预热完成: {len(sessions)} 个会话 ({elapsed:.1f}秒)")
    except Exception as e:
        logger.warning(f"️ 缓存预热失败: {e}")

    #  Fix 1.4: 启动时清理旧会话（24小时前的已完成会话）
    try:
        logger.info(" 清理旧会话...")
        cleaned = await session_manager.cleanup_old_sessions(max_age_hours=24)
        if cleaned > 0:
            logger.info(f" 启动清理完成: 删除 {cleaned} 个旧会话")
        else:
            logger.info(" 启动清理完成: 无需清理")
    except Exception as e:
        logger.warning(f"️ 启动清理失败: {e}")

    yield

    # 关闭时
    print("\n 服务器关闭中...")

    #  v7.1.2新增: 关闭 Playwright 浏览器池
    try:
        from intelligent_project_analyzer.api.html_pdf_generator import PlaywrightBrowserPool

        await PlaywrightBrowserPool.cleanup()
        print(" Playwright 浏览器池已关闭")
    except Exception as e:
        logger.warning(f"️ Playwright 浏览器池关闭失败: {e}")

    #  关闭 Redis Pub/Sub
    if redis_pubsub_task:
        redis_pubsub_task.cancel()
        try:
            await redis_pubsub_task
        except asyncio.CancelledError:
            pass

    if redis_pubsub_client:
        await redis_pubsub_client.close()

    #  关闭 Redis 会话管理器
    if session_manager:
        await session_manager.disconnect()

    #  v3.6新增: 关闭归档管理器（关闭数据库连接）
    if archive_manager:
        # SessionArchiveManager 使用 SQLAlchemy，引擎会自动管理连接池
        # 不需要显式关闭，但记录日志
        logger.info(" 会话归档管理器已关闭")

    print(" 服务器已关闭")


# 创建 FastAPI 应用
from intelligent_project_analyzer.versioning import PRODUCT_VERSION as _api_version
app = FastAPI(title="智能项目分析系统 API", description="基于 LangGraph 的多智能体协作分析平台", version=_api_version, lifespan=lifespan)

#  添加性能监控中间件
from intelligent_project_analyzer.api.performance_monitor import performance_monitoring_middleware

app.middleware("http")(performance_monitoring_middleware)

# 配置 CORS
# 注意：allow_origins=["*"] 与 allow_credentials=True 同时设置违反浏览器 CORS 规范
# JWT Bearer Token 不需要 credentials 模式（credentials=True 仅用于 Cookie 认证）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # JWT Bearer Token 不需要 credentials 模式
    allow_methods=["*"],
    allow_headers=["*"],
)

#  挂载静态文件目录（用于专家生成的图片）
try:
    # 确保目录存在
    data_dir = Path(__file__).parent.parent.parent / "data"
    archived_images_dir = data_dir / "archived_images"
    uploads_dir = data_dir / "uploads"
    generated_images_dir = data_dir / "generated_images"  #  v7.108
    followup_images_dir = data_dir / "followup_images"  #  v7.108.2

    archived_images_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    generated_images_dir.mkdir(parents=True, exist_ok=True)  #  v7.108
    followup_images_dir.mkdir(parents=True, exist_ok=True)  #  v7.108.2

    # 挂载静态文件服务
    app.mount("/archived_images", StaticFiles(directory=str(archived_images_dir)), name="archived_images")
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
    app.mount("/generated_images", StaticFiles(directory=str(generated_images_dir)), name="generated_images")  #  v7.108
    app.mount("/followup_images", StaticFiles(directory=str(followup_images_dir)), name="followup_images")  #  v7.108.2

    logger.info(f" 静态文件服务已挂载: /archived_images -> {archived_images_dir}")
    logger.info(f" 静态文件服务已挂载: /uploads -> {uploads_dir}")
    logger.info(f" 静态文件服务已挂载: /generated_images -> {generated_images_dir}")  #  v7.108
    logger.info(f" 静态文件服务已挂载: /followup_images -> {followup_images_dir}")  #  v7.108.2
except Exception as e:
    logger.warning(f"️ 静态文件服务挂载失败: {e}")

#  v7.10新增: 注册 WordPress JWT 认证路由
try:
    from intelligent_project_analyzer.api.auth_routes import router as auth_router

    app.include_router(auth_router)
    logger.info(" WordPress JWT 认证路由已注册")
except Exception as e:
    logger.warning(f"️ WordPress JWT 认证路由加载失败: {e}")

#  v7.10.1新增: 注册 WPCOM Member 会员信息路由
try:
    from intelligent_project_analyzer.api.member_routes import router as member_router

    app.include_router(member_router)
    logger.info(" WPCOM Member 会员信息路由已注册")
except Exception as e:
    logger.warning(f"️ WPCOM Member 会员信息路由加载失败: {e}")

#  v7.11新增: 注册性能和告警统计API路由
try:
    from intelligent_project_analyzer.api.metrics_routes import router as metrics_router

    app.include_router(metrics_router)
    logger.info(" 性能和告警统计API路由已注册")
except Exception as e:
    logger.warning(f"️ 性能和告警统计API路由加载失败: {e}")

#  管理员后台路由（仅限管理员访问）
try:
    from intelligent_project_analyzer.api.admin_routes import router as admin_router

    app.include_router(admin_router)
    logger.info(" 管理员后台路由已注册")
except Exception as e:
    logger.warning(f"️ 管理员后台路由加载失败: {e}")

#  v7.141: Milvus 知识库管理路由
try:
    from intelligent_project_analyzer.api.milvus_admin_routes import router as milvus_admin_router

    app.include_router(milvus_admin_router)
    logger.info(" Milvus 知识库管理路由已注册")
except Exception as e:
    logger.warning(f"️ Milvus 知识库管理路由加载失败: {e}")

#  v7.141.3: 知识库配额管理路由
try:
    from intelligent_project_analyzer.api.quota_routes import router as quota_router

    app.include_router(quota_router)
    logger.info(" 知识库配额管理路由已注册")
except Exception as e:
    logger.warning(f"️ 知识库配额管理路由加载失败: {e}")

#  v7.160: 搜索模式路由（博查AI Search + DeepSeek-R1）
try:
    from intelligent_project_analyzer.api.search_routes import router as search_router

    app.include_router(search_router)
    logger.info(" 搜索模式路由已注册")
except Exception as e:
    logger.warning(f"️ 搜索模式路由加载失败: {e}")

#  v7.216: 搜索质量监控路由
try:
    from intelligent_project_analyzer.api.search_quality_routes import router as search_quality_router

    app.include_router(search_quality_router, prefix="/api/admin")
    logger.info(" 搜索质量监控路由已注册")
except Exception as e:
    logger.warning(f"️ 搜索质量监控路由加载失败: {e}")

#  v3.9新增: 注册 Celery 路由（可选）
try:
    from intelligent_project_analyzer.api.celery_routes import register_celery_routes

    register_celery_routes(app)
except ImportError as e:
    logger.warning(f"️ Celery 路由未加载（可选功能）: {e}")

#  v7.500: 注册维度学习系统路由
try:
    from intelligent_project_analyzer.api.routes.admin_dashboard_routes import router as admin_dashboard_router

    app.include_router(
        admin_dashboard_router, prefix="/api/admin/dimension-learning", tags=["Admin - Dimension Learning"]
    )
    logger.info(" 维度学习系统路由已注册")
except Exception as e:
    logger.warning(f"️ 维度学习系统路由加载失败: {e}")

#  v8.4: 注册半迁移路由 — 完成 server.py 收口
#  下列路由此前已拆分到独立文件，但未 include_router 注册，
#  导致"写了新代码但仍在用旧实现"的半迁移状态。
_pending_routers = [
    ("intelligent_project_analyzer.api.monitoring_routes", "monitoring_router", "监控/健康检查"),
    ("intelligent_project_analyzer.api.session_routes", "session_router", "会话管理"),
    ("intelligent_project_analyzer.api.image_routes", "image_router", "图片管理"),
    ("intelligent_project_analyzer.api.four_step_flow_routes", "four_step_flow_router", "四步搜索流程"),
    ("intelligent_project_analyzer.api.external_data_routes", "external_data_router", "外部数据"),
]
for _mod_path, _alias, _label in _pending_routers:
    try:
        import importlib as _il

        _mod = _il.import_module(_mod_path)
        app.include_router(_mod.router)
        logger.info(f" {_label}路由已注册")
    except Exception as e:
        logger.warning(f"️ {_label}路由加载失败: {e}")

#  v8.4 完成收口: 注册主分析路由 + WebSocket 路由
for _mod_path2, _label2 in [
    ("intelligent_project_analyzer.api.analysis_routes", "主分析流程"),
    ("intelligent_project_analyzer.api.ws_routes", "WebSocket"),
]:
    try:
        import importlib as _il2

        _mod2 = _il2.import_module(_mod_path2)
        app.include_router(_mod2.router)
        logger.info(f" {_label2}路由已注册")
    except Exception as e:
        logger.warning(f"️ {_label2}路由加载失败: {e}")


# ==================== 数据模型 ====================


class AnalysisRequest(BaseModel):
    """分析请求"""

    # Backward compatible aliases:
    # - legacy clients use `requirement` instead of `user_input`
    # - some clients may send `username`/`userId` etc; we only normalize what we actually need
    model_config = ConfigDict(populate_by_name=True, coerce_numbers_to_str=True)

    user_input: str = Field(validation_alias=AliasChoices("user_input", "requirement"))
    user_id: str = Field(default="web_user", validation_alias=AliasChoices("user_id", "username"))  # 用户ID
    #  v7.39: 分析模式 - normal(深度思考) 或 deep_thinking(深度思考pro)
    # 深度思考pro模式会为每个专家生成概念图像
    analysis_mode: str = Field(default="normal", validation_alias=AliasChoices("analysis_mode", "mode"))

    # Optional legacy field: accepted but currently not used by backend.
    domain: Optional[str] = None


class ResumeRequest(BaseModel):
    """恢复请求"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    # Backward compatible alias: some older clients used `user_response`
    resume_value: Any = Field(validation_alias=AliasChoices("resume_value", "user_response"))


class FollowupRequest(BaseModel):
    """追问请求（用于已完成的分析报告）"""

    session_id: str
    question: str
    requires_analysis: bool = True  # 是否需要重新分析


class SessionResponse(BaseModel):
    """会话响应"""

    session_id: str
    status: str
    message: str


class AnalysisStatus(BaseModel):
    """分析状态"""

    session_id: str
    status: str  # running, waiting_for_input, completed, failed, rejected
    current_stage: Optional[str] = None
    detail: Optional[str] = None  #  新增：当前节点的详细信息
    progress: float = 0.0
    history: Optional[List[Dict[str, Any]]] = None  #  新增：执行历史
    interrupt_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None  # 添加traceback字段用于调试
    rejection_message: Optional[str] = None  #  拒绝原因提示
    user_input: Optional[str] = None  #  v7.37.7: 用户原始输入


class AnalysisResult(BaseModel):
    """分析结果"""

    session_id: str
    status: str
    # 现行字段
    results: Optional[Any] = None
    final_report: Optional[Any] = None

    # 兼容旧字段（tests/api/test_analysis_endpoints.py 仍在使用）
    final_result: Optional[Any] = None
    agent_results: Optional[Any] = None


#  对话相关数据模型
class ConversationRequest(BaseModel):
    """对话请求"""

    session_id: str
    question: str
    context_hint: Optional[str] = None  # 可选：章节提示


class ConversationResponse(BaseModel):
    """对话响应"""

    answer: str
    intent: str
    references: List[str]


# ==================== 结构化报告类型 ====================


class ExecutiveSummaryResponse(BaseModel):
    """执行摘要响应"""

    project_overview: str = Field(default="", description="项目概述")
    key_findings: List[str] = Field(default_factory=list, description="关键发现列表")
    key_recommendations: List[str] = Field(default_factory=list, description="核心建议列表")
    success_factors: List[str] = Field(default_factory=list, description="成功要素列表")


#  Phase 1.4+ P4: 核心答案响应模型（向后兼容版）
class CoreAnswerResponse(BaseModel):
    """核心答案响应（向后兼容）"""

    question: str = Field(default="", description="从用户输入提取的核心问题")
    answer: str = Field(default="", description="直接明了的核心答案")
    deliverables: List[str] = Field(default_factory=list, description="交付物清单")
    timeline: str = Field(default="", description="预估时间线")
    budget_range: str = Field(default="", description="预算估算范围")


#  v7.0: 单个交付物的责任者答案响应
class DeliverableAnswerResponse(BaseModel):
    """单个交付物的责任者答案响应"""

    deliverable_id: str = Field(default="", description="交付物ID")
    deliverable_name: str = Field(default="", description="交付物名称")
    deliverable_type: str = Field(default="unknown", description="交付物类型")
    owner_role: str = Field(default="", description="责任者角色ID")
    owner_answer: str = Field(default="", description="责任者的核心答案")
    answer_summary: str = Field(default="", description="答案摘要")
    supporters: List[str] = Field(default_factory=list, description="支撑专家列表")
    quality_score: Optional[float] = Field(default=None, description="质量分数")


#  v7.0: 专家支撑链响应
class ExpertSupportChainResponse(BaseModel):
    """专家支撑链响应"""

    role_id: str = Field(default="", description="专家角色ID")
    role_name: str = Field(default="", description="专家名称")
    contribution_type: str = Field(default="support", description="贡献类型")
    contribution_summary: str = Field(default="", description="贡献摘要")
    related_deliverables: List[str] = Field(default_factory=list, description="关联的交付物ID")


#  v7.0: 增强版核心答案响应（支持多交付物）
class CoreAnswerV7Response(BaseModel):
    """
    v7.0 增强版核心答案响应 - 支持多个交付物

    核心理念：
    - 核心答案 = 各责任者的最终交付（不做LLM综合）
    - 每个交付物有一个 primary_owner，其输出即为该交付物的答案
    - 专家支撑链展示非 owner 专家的贡献
    """

    question: str = Field(default="", description="从用户输入提取的核心问题")
    deliverable_answers: List[DeliverableAnswerResponse] = Field(default_factory=list, description="各交付物的责任者答案列表")
    expert_support_chain: List[ExpertSupportChainResponse] = Field(default_factory=list, description="专家支撑链")
    timeline: str = Field(default="待定", description="预估时间线")
    budget_range: str = Field(default="待定", description="预算估算范围")

    # 向后兼容字段
    answer: str = Field(default="", description="综合摘要（向后兼容）")
    deliverables: List[str] = Field(default_factory=list, description="交付物清单（向后兼容）")


#  Phase 1.4+ v4.1: 洞察区块响应模型
class InsightsSectionResponse(BaseModel):
    """洞察区块响应 - 从需求分析师和所有专家中提炼的关键洞察"""

    key_insights: List[str] = Field(default_factory=list, description="3-5条核心洞察")
    cross_domain_connections: List[str] = Field(default_factory=list, description="跨领域关联发现")
    user_needs_interpretation: str = Field(default="", description="对用户需求的深层解读")


#  Phase 1.4+ v4.1: 推敲过程响应模型
class DeliberationProcessResponse(BaseModel):
    """推敲过程响应 - 项目总监的战略分析和决策思路"""

    inquiry_architecture: str = Field(default="", description="选择的探询架构类型")
    reasoning: str = Field(default="", description="为什么选择这个探询架构")
    role_selection: List[str] = Field(default_factory=list, description="选择的专家角色及理由")
    strategic_approach: str = Field(default="", description="整体战略方向")


#  Phase 1.4+ v4.1: 建议区块响应模型
class RecommendationsSectionResponse(BaseModel):
    """建议区块响应 - 整合所有专家的可执行建议"""

    immediate_actions: List[str] = Field(default_factory=list, description="立即可执行的行动")
    short_term_priorities: List[str] = Field(default_factory=list, description="短期优先级")
    long_term_strategy: List[str] = Field(default_factory=list, description="长期战略方向")
    risk_mitigation: List[str] = Field(default_factory=list, description="风险缓解措施")


class ReportSectionResponse(BaseModel):
    """报告章节响应"""

    section_id: str = Field(default="", description="章节ID")
    title: str = Field(default="", description="章节标题")
    content: str = Field(default="", description="章节内容")
    confidence: float = Field(default=0.0, description="置信度")


class ComprehensiveAnalysisResponse(BaseModel):
    """综合分析响应"""

    cross_domain_insights: List[str] = Field(default_factory=list, description="跨领域洞察")
    integrated_recommendations: List[str] = Field(default_factory=list, description="整合建议")
    risk_assessment: List[str] = Field(default_factory=list, description="风险评估")
    implementation_roadmap: List[str] = Field(default_factory=list, description="实施路线图")


class ConclusionsResponse(BaseModel):
    """结论响应"""

    project_analysis_summary: str = Field(default="", description="项目分析总结")
    next_steps: List[str] = Field(default_factory=list, description="下一步行动建议")
    success_metrics: List[str] = Field(default_factory=list, description="成功指标")


class ReviewFeedbackItemResponse(BaseModel):
    """审核反馈项响应"""

    issue_id: str = Field(default="", description="问题ID")
    reviewer: str = Field(default="", description="审核专家")
    issue_type: str = Field(default="", description="问题类型")
    description: str = Field(default="", description="问题描述")
    response: str = Field(default="", description="响应措施")
    status: str = Field(default="", description="状态")
    priority: str = Field(default="medium", description="优先级")


class ReviewFeedbackResponse(BaseModel):
    """审核反馈响应"""

    red_team_challenges: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    blue_team_validations: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    judge_rulings: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    client_decisions: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    iteration_summary: str = Field(default="")


class ReviewRoundDataResponse(BaseModel):
    """审核轮次数据响应"""

    round_number: int = Field(default=0)
    red_score: int = Field(default=0)
    blue_score: int = Field(default=0)
    judge_score: int = Field(default=0)
    issues_found: int = Field(default=0)
    issues_resolved: int = Field(default=0)
    timestamp: str = Field(default="")


class ReviewVisualizationResponse(BaseModel):
    """审核可视化响应"""

    rounds: List[ReviewRoundDataResponse] = Field(default_factory=list)
    final_decision: str = Field(default="")
    total_rounds: int = Field(default=0)
    improvement_rate: float = Field(default=0.0)


class ChallengeItemResponse(BaseModel):
    """单个挑战项响应"""

    expert_id: str = Field(default="", description="专家ID")
    expert_name: str = Field(default="", description="专家名称")
    challenged_item: str = Field(default="", description="质疑的事项")
    challenge_type: str = Field(default="", description="挑战类型: reinterpret/flag_risk/escalate")
    severity: str = Field(default="should-fix", description="严重程度: must-fix/should-fix")
    rationale: str = Field(default="", description="质疑理由")
    proposed_alternative: str = Field(default="", description="建议的替代方案")
    design_impact: str = Field(default="", description="对设计的影响")
    decision: str = Field(default="", description="处理决策: accept/synthesize/escalate")


class ChallengeDetectionResponse(BaseModel):
    """挑战检测响应"""

    has_challenges: bool = Field(default=False, description="是否有挑战")
    total_count: int = Field(default=0, description="挑战总数")
    must_fix_count: int = Field(default=0, description="必须修复的问题数")
    should_fix_count: int = Field(default=0, description="建议修复的问题数")
    challenges: List[ChallengeItemResponse] = Field(default_factory=list, description="挑战列表")
    handling_summary: str = Field(default="", description="处理摘要")


class QuestionnaireResponseItem(BaseModel):
    """单个问卷回答项"""

    question_id: str = Field(default="", description="问题ID")
    question: str = Field(default="", description="问题内容")
    answer: str = Field(default="", description="用户回答")
    context: str = Field(default="", description="问题上下文说明")


class QuestionnaireResponseData(BaseModel):
    """问卷回答数据"""

    responses: List[QuestionnaireResponseItem] = Field(default_factory=list, description="问卷回答列表")
    timestamp: str = Field(default="", description="提交时间")
    analysis_insights: str = Field(default="", description="从回答中提取的关键洞察")


class RequirementsAnalysisResponse(BaseModel):
    """需求分析结果（需求分析师原始输出 - 融合用户修改后的最终版本）"""

    project_overview: str = Field(default="", description="项目概览")
    core_objectives: List[str] = Field(default_factory=list, description="核心目标")
    project_tasks: List[str] = Field(default_factory=list, description="项目任务")
    narrative_characters: List[str] = Field(default_factory=list, description="叙事角色")
    physical_contexts: List[str] = Field(default_factory=list, description="物理环境")
    constraints_opportunities: Dict[str, Any] = Field(default_factory=dict, description="约束与机遇")


class StructuredReportResponse(BaseModel):
    """结构化报告响应"""

    inquiry_architecture: str = Field(default="", description="探询架构类型")
    #  Phase 1.4+ P4: 核心答案（用户最关心的TL;DR）
    #  v7.0: 支持新的多交付物格式和旧格式（向后兼容）
    # 如果有 deliverable_answers 字段，则是 v7.0 格式
    # 否则是旧格式（只有 answer 字段）
    core_answer: Optional[Dict[str, Any]] = Field(default=None, description="核心答案（支持v7.0多交付物格式和旧格式）")
    #  Phase 1.4+ v4.1: 新增洞察、推敲过程、建议区块
    insights: Optional[InsightsSectionResponse] = Field(default=None, description="需求洞察（LLM综合）")
    requirements_analysis: Optional[RequirementsAnalysisResponse] = Field(default=None, description="需求分析结果（需求分析师原始输出）")
    deliberation_process: Optional[DeliberationProcessResponse] = Field(default=None, description="推敲过程")
    recommendations: Optional[RecommendationsSectionResponse] = Field(default=None, description="建议")
    executive_summary: ExecutiveSummaryResponse = Field(default_factory=ExecutiveSummaryResponse)
    sections: List[ReportSectionResponse] = Field(default_factory=list)
    comprehensive_analysis: ComprehensiveAnalysisResponse = Field(default_factory=ComprehensiveAnalysisResponse)
    conclusions: ConclusionsResponse = Field(default_factory=ConclusionsResponse)
    expert_reports: Dict[str, str] = Field(default_factory=dict, description="专家原始报告")
    review_feedback: Optional[ReviewFeedbackResponse] = None
    questionnaire_responses: Optional[QuestionnaireResponseData] = Field(default=None, description="问卷回答数据")
    review_visualization: Optional[ReviewVisualizationResponse] = None
    challenge_detection: Optional[ChallengeDetectionResponse] = Field(default=None, description="挑战检测结果")
    #  v7.4: 执行元数据汇总
    execution_metadata: Optional[Dict[str, Any]] = Field(default=None, description="执行元数据汇总")
    #  v3.0.26: 思维导图内容结构（以内容为中心）
    mindmap_content: Optional[Dict[str, Any]] = Field(default=None, description="思维导图内容结构")
    #  深度思考模式概念图（集中生成）
    generated_images: Optional[List[str]] = Field(default=None, description="AI 概念图（深度思考模式）")
    image_prompts: Optional[List[str]] = Field(default=None, description="AI 概念图提示词（深度思考模式）")
    image_top_constraints: Optional[str] = Field(default=None, description="AI 概念图顶层约束（深度思考模式）")
    #  v7.39: 专家概念图（深度思考pro模式）
    generated_images_by_expert: Optional[Dict[str, Any]] = Field(default=None, description="专家概念图（深度思考pro模式）")
    #  v7.154: 雷达图维度数据
    radar_dimensions: Optional[List[Dict[str, Any]]] = Field(default=None, description="雷达图维度列表")
    radar_dimension_values: Optional[Dict[str, Any]] = Field(default=None, description="雷达图维度值")


class ReportResponse(BaseModel):
    """报告响应（专门用于前端获取报告）"""

    session_id: str
    report_text: str
    report_pdf_path: Optional[str] = None
    created_at: str
    user_input: str = Field(default="", description="用户原始输入")
    suggestions: List[str] = Field(default_factory=list)
    conversation_id: Optional[int] = None
    structured_report: Optional[StructuredReportResponse] = Field(default=None, description="结构化报告数据")


# ==================== 报告数据清洗辅助函数 ====================


def _is_blank_section(section: ReportSectionResponse) -> bool:
    """判断章节内容是否为空或仅包含占位符"""

    content = (section.content or "").strip()
    if not content:
        return True

    normalized = content.strip()
    if normalized in {"{}", "[]", '""'}:
        return True

    try:
        parsed = json.loads(normalized)
    except Exception:
        return False

    if isinstance(parsed, dict):
        return len(parsed) == 0
    if isinstance(parsed, list):
        return len(parsed) == 0
    return False


def _normalize_section_id(raw_identifier: Optional[str], fallback: str) -> str:
    """规范化章节 ID，确保可用于字典键与前端锚点"""

    candidate = (raw_identifier or "").strip()
    if candidate:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", candidate).strip("_").lower()
        if slug:
            return slug

    slug = re.sub(r"[^A-Za-z0-9]+", "_", fallback).strip("_").lower()
    if slug:
        return slug

    return f"section_{uuid.uuid4().hex[:8]}"


def _derive_section_identity(role_id: str, agent_result: Dict[str, Any]) -> Tuple[str, str]:
    """根据智能体输出推断章节 ID 与标题，支持动态角色"""

    metadata = agent_result.get("metadata") or {}

    candidate_ids = [
        metadata.get("section_id"),
        agent_result.get("section_id"),
        agent_result.get("report_section_id"),
    ]

    candidate_titles = [
        metadata.get("section_title"),
        agent_result.get("section_title"),
        agent_result.get("display_name"),
        agent_result.get("role_name"),
    ]

    if role_id == "requirements_analyst":
        candidate_ids.append("requirements_analysis")
        candidate_titles.append("需求分析")

    section_id = _normalize_section_id(next((cid for cid in candidate_ids if cid), None), role_id)
    section_title = next((title for title in candidate_titles if title), None) or role_id

    return section_id, section_title


def _sanitize_structured_data(data: Any) -> Tuple[Any, List[str]]:
    """清理结构化数据，滤除不符合约束的命名项"""

    warnings: List[str] = []

    if not isinstance(data, dict):
        return data, warnings

    sanitized: Dict[str, Any] = {}

    for key, value in data.items():
        if key == "custom_analysis" and isinstance(value, dict):
            cleaned_custom, custom_warnings = _sanitize_custom_analysis(value)
            sanitized[key] = cleaned_custom
            warnings.extend(custom_warnings)
        elif isinstance(value, dict):
            cleaned_value, nested_warnings = _sanitize_structured_data(value)
            sanitized[key] = cleaned_value
            warnings.extend(nested_warnings)
        else:
            sanitized[key] = value

    return sanitized, warnings


def _sanitize_custom_analysis(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """针对定制分析部分的命名长度做约束过滤"""

    sanitized: Dict[str, Any] = {}
    warnings: List[str] = []

    for key, value in data.items():
        if isinstance(value, list):
            valid_entries = []
            removed_entries = []

            for entry in value:
                if isinstance(entry, dict):
                    name = entry.get("命名本身") or entry.get("命名") or entry.get("名称")
                    name_str = name.strip() if isinstance(name, str) else ""
                    if name_str and len(name_str) == 4:
                        valid_entries.append(entry)
                    else:
                        removed_entries.append(name_str or "<未命名>")
                else:
                    valid_entries.append(entry)

            if removed_entries:
                warnings.append(f"{key}: 已移除{len(removed_entries)}个未满足四字要求的命名")

            sanitized[key] = valid_entries

        elif isinstance(value, dict):
            cleaned_value, nested_warnings = _sanitize_custom_analysis(value)
            sanitized[key] = cleaned_value
            warnings.extend(nested_warnings)
        else:
            sanitized[key] = value

    return sanitized, warnings


def _format_agent_payload(agent_result: Dict[str, Any]) -> Optional[OrderedDict]:
    """将智能体输出格式化为结构化payload"""

    if not agent_result:
        return None

    structured_raw = agent_result.get("structured_data") or {}
    structured, validation_warnings = _sanitize_structured_data(structured_raw)
    content = agent_result.get("content")

    payload = OrderedDict()

    if structured:
        payload["structured_data"] = structured

    if isinstance(content, str) and content.strip():
        payload["narrative_summary"] = content.strip()

    if validation_warnings:
        payload["validation_warnings"] = validation_warnings

    return payload if payload else None


def _enrich_sections_with_agent_results(
    sections: List[ReportSectionResponse], session: Dict[str, Any]
) -> List[ReportSectionResponse]:
    """补全或替换缺失的章节内容"""

    agent_results = session.get("agent_results") or {}
    if not agent_results:
        return sections

    active_agents = session.get("active_agents") or list(agent_results.keys())

    section_lookup: Dict[str, ReportSectionResponse] = {}
    unlabeled_sections: List[ReportSectionResponse] = []

    for sec in sections:
        if sec.section_id:
            section_lookup[sec.section_id] = sec
        else:
            unlabeled_sections.append(sec)

    # 收集各章节的补充数据
    section_contributions: Dict[str, OrderedDict] = {}
    section_titles: Dict[str, str] = {}
    section_confidences: Dict[str, List[float]] = defaultdict(list)
    agent_section_sequence: List[str] = []

    for role_id in active_agents:
        agent_result = agent_results.get(role_id) or {}
        payload = _format_agent_payload(agent_result)
        if not payload:
            continue

        section_id, section_title = _derive_section_identity(role_id, agent_result)
        agent_section_sequence.append(section_id)

        source_name = agent_result.get("display_name") or agent_result.get("role_name") or role_id

        section_contributions.setdefault(section_id, OrderedDict())
        section_contributions[section_id][source_name] = payload

        if section_title:
            section_titles.setdefault(section_id, section_title)

        confidence = agent_result.get("confidence")
        try:
            if confidence is not None:
                section_confidences[section_id].append(float(confidence))
        except (TypeError, ValueError):
            pass

    if not section_contributions:
        return sections

    for section_id, payload in section_contributions.items():
        if not payload:
            continue

        section = section_lookup.get(section_id)
        if section is None:
            section = ReportSectionResponse(
                section_id=section_id,
                title=section_titles.get(section_id, section_id),
                content="",
                confidence=0.0,
            )
            section_lookup[section_id] = section

        if not section.title:
            section.title = section_titles.get(section_id, section_id)

        if _is_blank_section(section):
            section.content = json.dumps(payload, ensure_ascii=False, indent=2)

        #  Phase 1.4+: 修复置信度为0%的问题
        # 无论章节内容是否为空，都应该补全confidence值
        confidence_values = section_confidences.get(section_id, [])
        if confidence_values:
            section.confidence = max(confidence_values)
        elif not section.confidence or section.confidence == 0.0:
            # 如果confidence为0或未设置，使用默认值0.8
            section.confidence = 0.8

    ordered_sections: List[ReportSectionResponse] = []
    added_ids: Set[str] = set()

    for section in sections:
        section_id = section.section_id
        if section_id and section_id not in added_ids:
            ordered_sections.append(section)
            added_ids.add(section_id)

    for section_id in agent_section_sequence:
        section = section_lookup.get(section_id)
        if section and section.section_id not in added_ids:
            ordered_sections.append(section)
            added_ids.add(section.section_id)

    for section in section_lookup.values():
        if section.section_id not in added_ids:
            ordered_sections.append(section)
            added_ids.add(section.section_id)

    ordered_sections.extend(unlabeled_sections)

    return ordered_sections


# ==================== 辅助函数 ====================


async def subscribe_to_redis_pubsub():
    """
    订阅 Redis Pub/Sub 频道，用于多实例 WebSocket 消息广播
    """
    if not redis_pubsub_client:
        return

    try:
        pubsub = redis_pubsub_client.pubsub()
        await pubsub.subscribe("workflow:broadcast")

        logger.info(" Redis Pub/Sub 订阅已启动")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    import json

                    data = json.loads(message["data"])
                    session_id = data.get("session_id")
                    payload = data.get("payload")

                    # 本地广播到 WebSocket
                    if session_id in websocket_connections:
                        connections = websocket_connections[session_id]
                        disconnected = []

                        for ws in connections:
                            try:
                                #  Fix 1.1: Check WebSocket state before sending (matches local broadcast logic)
                                if ws.client_state.name != "CONNECTED":
                                    logger.debug(f"️ 跳过非连接状态的WebSocket (state={ws.client_state.name})")
                                    disconnected.append(ws)
                                    continue

                                await ws.send_json(payload)
                            except Exception as e:
                                logger.warning(f"️ WebSocket 发送失败: {e}")
                                disconnected.append(ws)

                        # 清理断开的连接
                        for ws in disconnected:
                            connections.remove(ws)

                except Exception as e:
                    logger.error(f" 处理 Pub/Sub 消息失败: {e}")

    except asyncio.CancelledError:
        logger.info(" Redis Pub/Sub 订阅已停止")
        await pubsub.unsubscribe("workflow:broadcast")
        await pubsub.close()
    except Exception as e:
        logger.error(f" Redis Pub/Sub 订阅失败: {e}")


def _ensure_aiosqlite_is_alive(conn: Any) -> Any:
    """为缺少 is_alive() 方法的 aiosqlite 连接打补丁。"""

    if hasattr(conn, "is_alive") and callable(getattr(conn, "is_alive")):
        return conn

    def _is_alive(self: Any) -> bool:  # pragma: no cover - 简单代理
        thread = getattr(self, "_thread", None)
        running = getattr(self, "_running", False)
        return bool(thread and thread.is_alive() and running)

    conn.is_alive = MethodType(_is_alive, conn)  # type: ignore[attr-defined]
    logger.debug("🩹 AsyncSqliteSaver 兼容补丁：已为 aiosqlite.Connection 注入 is_alive()")
    return conn


async def get_or_create_async_checkpointer() -> Optional[BaseCheckpointSaver[str]]:
    """惰性初始化 AsyncSqliteSaver，所有会话复用同一个连接。"""

    global async_checkpointer, async_checkpointer_lock

    if async_checkpointer is not None:
        return async_checkpointer

    if async_checkpointer_lock is None:
        async_checkpointer_lock = asyncio.Lock()

    async with async_checkpointer_lock:
        if async_checkpointer is not None:
            return async_checkpointer

        try:
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        except ImportError as exc:
            logger.warning(f"️ AsyncSqliteSaver 不可用，回退到同步 SqliteSaver: {exc}")
            return None

        db_path = Path("./data/checkpoints/workflow.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = await aiosqlite.connect(str(db_path))
        conn = _ensure_aiosqlite_is_alive(conn)
        async_checkpointer = AsyncSqliteSaver(conn)
        logger.info(f" AsyncSqliteSaver 初始化成功: {db_path}")
        return async_checkpointer


async def create_workflow() -> Optional[MainWorkflow]:
    """
    创建工作流实例 - 使用 LLMFactory（支持自动降级）

     使用 LLMFactory 创建 LLM，支持运行时降级
    """
    try:
        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        logger.info(" 使用 LLMFactory 创建 LLM（支持自动降级）")

        #  使用 LLMFactory 创建 LLM（自动应用 .env 配置和降级链）
        llm = LLMFactory.create_llm()

        # 默认使用 Dynamic Mode
        config = {
            "mode": "dynamic",
            "enable_role_config": True,
            "post_completion_followup_enabled": settings.post_completion_followup_enabled,
        }

        checkpointer = await get_or_create_async_checkpointer()

        workflow = MainWorkflow(llm, config, checkpointer=checkpointer)
        logger.info(" 工作流创建成功（LLM 降级已启用）")
        return workflow

    except Exception as e:
        logger.error(f" 创建工作流失败: {e}")
        import traceback

        traceback.print_exc()
        return None


async def broadcast_to_websockets(session_id: str, message: Dict[str, Any]):
    """
     v7.133: 增强的WebSocket广播 - 添加连接健康检查和自动清理

    向所有连接到指定会话的 WebSocket 客户端广播消息
     使用 Redis Pub/Sub 支持多实例部署

    Args:
        session_id: 会话 ID
        message: 要发送的消息（字典格式，将被转换为 JSON）
    """
    #  Redis Pub/Sub 模式：发布到 Redis，所有实例监听
    if redis_pubsub_client:
        try:
            import json

            payload = {"session_id": session_id, "payload": message}
            await redis_pubsub_client.publish("workflow:broadcast", json.dumps(payload, ensure_ascii=False))
            logger.debug(f" [v7.133] Redis Pub/Sub 发布成功: {session_id}")
            return
        except Exception as e:
            logger.warning(f"️ [v7.133] Redis Pub/Sub 发布失败，回退到本地广播: {e}")

    #  本地模式：直接广播到本实例的 WebSocket 连接
    if session_id not in websocket_connections:
        logger.debug(f" [v7.133] 未找到会话的WebSocket连接: {session_id}")
        return

    # 获取该会话的所有连接
    connections = websocket_connections[session_id]

    # 存储断开的连接
    disconnected = []
    success_count = 0
    failed_count = 0

    # 广播消息到所有连接
    for ws in connections:
        try:
            from starlette.websockets import WebSocketState

            #  v7.133: 增强连接状态检查
            if ws.client_state != WebSocketState.CONNECTED:
                logger.debug(f"️ [v7.133] WebSocket未连接 (状态: {ws.client_state.name})，标记为断开")
                disconnected.append(ws)
                failed_count += 1
                continue

            #  v7.133: 添加发送超时保护
            import asyncio

            await asyncio.wait_for(ws.send_json(message), timeout=5.0)
            success_count += 1

        except asyncio.TimeoutError:
            logger.warning(f"️ [v7.133] WebSocket 发送超时(5s)，标记为断开")
            disconnected.append(ws)
            failed_count += 1
        except Exception as e:
            error_str = str(e)
            if "not connected" in error_str.lower() or "closed" in error_str.lower():
                logger.debug(f" [v7.133] WebSocket已断开: {type(e).__name__}")
            else:
                logger.warning(f"️ [v7.133] WebSocket 发送失败: {type(e).__name__}: {e}")
            disconnected.append(ws)
            failed_count += 1

    # 清理断开的连接
    for ws in disconnected:
        if ws in connections:
            connections.remove(ws)

    #  v7.133: 记录广播统计
    if success_count > 0 or failed_count > 0:
        logger.debug(
            f" [v7.133] WebSocket广播完成: {session_id} | "
            f"成功={success_count} 失败={failed_count} 消息类型={message.get('type', 'unknown')}"
        )


# Register broadcast function so workflow layer can call it without importing server.py directly.
# This must appear after broadcast_to_websockets is defined (module-level, safe at import time).
from intelligent_project_analyzer.api._broadcast_registry import register_broadcast as _register_broadcast  # noqa: E402
_register_broadcast(broadcast_to_websockets)


async def run_workflow_async(session_id: str, user_input: str):
    """异步执行工作流（仅 Dynamic Mode）"""
    try:
        logger.info(f" [ASYNC] run_workflow_async 开始 | session_id={session_id}")

        #  v7.39: 从 session 获取分析模式
        session_data = await session_manager.get(session_id)
        logger.info(f" [ASYNC] 获取session数据成功 | session_data={session_data is not None}")

        analysis_mode = session_data.get("analysis_mode", "normal") if session_data else "normal"
        user_id = session_data.get("user_id", "api_user") if session_data else "api_user"

        logger.info(f" [ASYNC] 解析模式信息 | analysis_mode={analysis_mode}, user_id={user_id}")

        logger.info(f" [ASYNC] 准备打印工作流启动信息...")

        print(f"\n{'='*60}")
        print(f" 开始执行工作流")
        print(f"Session ID: {session_id}")
        print(f"用户输入: {user_input[:100]}...")
        print(f"运行模式: Dynamic Mode")
        print(f"分析模式: {analysis_mode}")  #  v7.39
        print(f"{'='*60}\n")

        logger.info(f" [ASYNC] 工作流启动信息已打印")

        #  更新会话状态
        logger.info(f" [ASYNC] 准备更新会话状态...")
        await session_manager.update(session_id, {"status": "running", "progress": 0.1})
        logger.info(f" [ASYNC] 会话状态已更新")

        #  广播状态到 WebSocket
        await broadcast_to_websockets(
            session_id, {"type": "status_update", "status": "running", "progress": 0.1, "message": "工作流开始执行"}
        )

        # 创建工作流
        print(f" 创建工作流 (Dynamic Mode)...")
        workflow = await create_workflow()
        if not workflow:
            print(f" 工作流创建失败")
            await session_manager.update(
                session_id, {"status": "failed", "error": "工作流创建失败", "traceback": "工作流创建失败，请检查配置"}
            )
            return

        print(f" 工作流创建成功")
        workflows[session_id] = workflow

        logger.info(f" [ASYNC] 准备创建初始状态...")

        #  v7.156: 从 session_data 提取多模态视觉参考
        visual_references = session_data.get("visual_references") if session_data else None
        visual_style_anchor = session_data.get("visual_style_anchor") if session_data else None

        if visual_references:
            logger.info(f"️ [v7.156] 检测到 {len(visual_references)} 个视觉参考，将注入工作流初始状态")
        if visual_style_anchor:
            logger.info(f" [v7.156] 检测到全局风格锚点: {visual_style_anchor[:100]}...")

        # 创建初始状态 -  v7.39: 传递 analysis_mode,  v7.156: 传递视觉参考
        initial_state = StateManager.create_initial_state(
            user_input=user_input,
            session_id=session_id,
            user_id=user_id,
            analysis_mode=analysis_mode,  #  v7.39
            uploaded_visual_references=visual_references,  #  v7.156: 多模态视觉参考
            visual_style_anchor=visual_style_anchor,  #  v7.156: 全局风格锚点
        )

        logger.info(f" [ASYNC] 初始状态已创建 | visual_refs={len(visual_references) if visual_references else 0}")

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}  # 增加递归限制，默认是25

        logger.info(f" [ASYNC] 准备开始流式执行工作流...")

        # 流式执行工作流
        # 不指定 stream_mode，使用默认模式以正确接收 __interrupt__
        #  添加GraphRecursionError处理
        from langgraph.errors import GraphRecursionError

        events = []
        try:
            logger.info(f" [ASYNC] 进入 astream 循环...")
            logger.info(f" [ASYNC] 调用 workflow.graph.astream()...")

            stream = workflow.graph.astream(initial_state, config)
            logger.info(f" [ASYNC] astream() 返回了流对象: {type(stream)}")

            async for chunk in stream:
                #  诊断日志：检查每个 chunk 的键
                logger.info(f" [STREAM] chunk keys: {list(chunk.keys())}")

                events.append(_serialize_for_json(chunk))

                #  检查是否有 interrupt - 提前检测（在处理其他节点之前）
                if "__interrupt__" in chunk:
                    logger.info(f" [INTERRUPT] Detected! chunk keys: {list(chunk.keys())}")
                    # 提取 interrupt 数据
                    interrupt_tuple = chunk["__interrupt__"]
                    logger.info(f" [INTERRUPT] tuple type: {type(interrupt_tuple)}, content: {interrupt_tuple}")

                    # interrupt_tuple 是一个元组，第一个元素是 Interrupt 对象
                    if interrupt_tuple:
                        interrupt_obj = interrupt_tuple[0] if isinstance(interrupt_tuple, tuple) else interrupt_tuple
                        logger.info(f" [INTERRUPT] obj type: {type(interrupt_obj)}")

                        # 提取 interrupt 的 value
                        interrupt_value = None
                        if hasattr(interrupt_obj, "value"):
                            interrupt_value = interrupt_obj.value
                            logger.info(f" [INTERRUPT] Extracted value from .value attribute")
                        else:
                            interrupt_value = interrupt_obj
                            logger.info(f" [INTERRUPT] Using obj directly as value")

                        logger.info(f" [INTERRUPT] value type: {type(interrupt_value)}")

                        #  v7.119: 更新会话状态为等待用户输入，并记录时间戳
                        import time

                        await session_manager.update(
                            session_id,
                            {
                                "status": "waiting_for_input",
                                "interrupt_data": interrupt_value,
                                "current_node": "interrupt",
                                "interrupt_timestamp": time.time(),  # 记录进入waiting_for_input的时间
                            },
                        )
                        logger.info(f" [INTERRUPT] Session {session_id} updated to waiting_for_input")

                        #  广播 interrupt 到 WebSocket
                        await broadcast_to_websockets(
                            session_id,
                            {"type": "interrupt", "status": "waiting_for_input", "interrupt_data": interrupt_value},
                        )
                        logger.info(f" [INTERRUPT] Broadcasted to WebSocket")
                        return

                #  更新当前节点和详细信息（用于前端进度展示）
                for node_name, node_output in chunk.items():
                    if node_name != "__interrupt__":
                        # 提取详细信息
                        detail = ""
                        if isinstance(node_output, dict):
                            #  优先使用 detail 字段（节点返回的详细描述）
                            if "detail" in node_output:
                                detail = node_output["detail"]
                            # 回退：使用 current_stage
                            elif "current_stage" in node_output:
                                detail = node_output["current_stage"]
                            # 最后：使用 status
                            elif "status" in node_output:
                                detail = node_output["status"]

                        #  更新当前节点、详情和历史记录
                        # 获取当前会话以追加历史
                        current_session = await session_manager.get(session_id)
                        history = current_session.get("history", []) if current_session else []

                        # 添加新记录
                        history.append(
                            {"node": node_name, "detail": detail, "time": datetime.now().strftime("%H:%M:%S")}
                        )

                        #  v7.120: 提取search_references（如果节点更新了此字段）
                        update_data = {"current_node": node_name, "detail": detail, "history": history}

                        # 检查并提取search_references
                        if isinstance(node_output, dict) and "search_references" in node_output:
                            search_refs = node_output["search_references"]
                            if search_refs:  # 只有非空才更新
                                update_data["search_references"] = search_refs
                                logger.info(f" [v7.120] 节点 {node_name} 更新了 {len(search_refs)} 个搜索引用")

                        #  v7.153: 同步问卷流程相关字段到 Redis，修复进度显示异常
                        questionnaire_fields = [
                            "progressive_questionnaire_step",
                            "progressive_questionnaire_completed",
                            "questionnaire_summary_completed",
                            "confirmed_core_tasks",
                            "gap_filling_answers",
                            "selected_dimensions",
                            "radar_dimension_values",
                            "requirements_confirmed",
                            "restructured_requirements",
                            "requirements_summary_text",
                        ]
                        if isinstance(node_output, dict):
                            for field in questionnaire_fields:
                                if field in node_output and node_output[field] is not None:
                                    update_data[field] = node_output[field]
                                    logger.debug(f" [v7.153] 同步问卷字段: {field}")

                        await session_manager.update(session_id, update_data)
                        logger.debug(f"[PROGRESS] 节点: {node_name}, 详情: {detail}")

                        #  诊断日志（2025-11-30）：检查detail提取和广播
                        if node_name == "agent_executor":
                            logger.info(f" [DIAGNOSTIC] agent_executor detail: '{detail}'")
                            logger.info(
                                f" [DIAGNOSTIC] node_output keys: {list(node_output.keys()) if isinstance(node_output, dict) else 'not dict'}"
                            )
                            if isinstance(node_output, dict) and "detail" in node_output:
                                logger.info(f" [DIAGNOSTIC] node_output['detail']: '{node_output['detail']}'")

                        #  广播节点更新到 WebSocket
                        await broadcast_to_websockets(
                            session_id,
                            {
                                "type": "node_update",
                                "current_node": node_name,
                                "detail": detail,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                        #  诊断日志：确认广播内容
                        if node_name == "agent_executor":
                            logger.info(f" [DIAGNOSTIC] Broadcasted node_update with detail: '{detail}'")

                #  更新进度（优化：基于节点名称映射）
                #  获取当前会话数据
                current_session = await session_manager.get(session_id)
                if not current_session:
                    continue

                current_node_name = current_session.get("current_node", "")

                #  v7.21: 定义节点到进度的映射（与 main_workflow.py 实际节点名称对齐）
                #  v7.153: 添加问卷流程节点，修复进度显示异常
                node_progress_map = {
                    # 输入验证阶段 (0-15%)
                    "unified_input_validator_initial": 0.05,  # 5% - 初始输入验证
                    "unified_input_validator_secondary": 0.10,  # 10% - 二次验证
                    # 需求分析阶段 (15-25%)
                    "requirements_analyst": 0.15,  # 15% - 需求分析
                    "feasibility_analyst": 0.18,  # 18% - 可行性分析
                    #  v7.153: 问卷流程阶段 (20-35%)
                    "progressive_step1_core_task": 0.20,  # 20% - Step 1: 核心任务
                    "progressive_step3_gap_filling": 0.25,  # 25% - Step 2: 信息补充
                    "progressive_step2_radar": 0.30,  # 30% - Step 3: 雷达图
                    "questionnaire_summary": 0.35,  # 35% - Step 4: 需求洞察
                    # 项目规划阶段 (35-55%)
                    "project_director": 0.40,  # 40% - 项目总监
                    "role_task_unified_review": 0.45,  # 45% - 角色审核
                    "quality_preflight": 0.50,  # 50% - 质量预检
                    # 专家执行阶段 (55-80%)
                    "batch_executor": 0.55,  # 55% - 批次调度
                    "agent_executor": 0.70,  # 70% - 专家执行
                    "batch_aggregator": 0.75,  # 75% - 批次聚合
                    "batch_router": 0.76,  # 76% - 批次路由
                    "batch_strategy_review": 0.78,  # 78% - 策略审核
                    # 审核聚合阶段 (80-100%)
                    "detect_challenges": 0.80,  # 80% - 挑战检测
                    "analysis_review": 0.85,  # 85% - 分析审核
                    "result_aggregator": 0.90,  # 90% - 结果聚合
                    "report_guard": 0.95,  # 95% - 报告审核
                    "pdf_generator": 0.98,  # 98% - PDF 生成
                }

                # 使用节点映射或回退到计数
                new_progress = node_progress_map.get(current_node_name, min(0.9, len(events) * 0.1))

                #  防止进度回退：只有新进度 ≥ 旧进度时才更新
                old_progress = current_session.get("progress", 0)
                progress = max(new_progress, old_progress if isinstance(old_progress, (int, float)) else 0)

                if new_progress < old_progress:
                    logger.debug(f"️ 检测到进度回退: {old_progress:.0%} → {new_progress:.0%}，使用旧进度 {progress:.0%}")

                #  单次更新 Redis（避免重复写入和竞态条件）
                await session_manager.update(
                    session_id,
                    {
                        "progress": progress,
                        "events": events,
                        "current_node": current_node_name,
                        "detail": current_session.get("detail"),
                        "status": current_session["status"],
                    },
                )

                #  直接使用计算值广播到 WebSocket（避免 Redis 读取竞态）
                #  v7.120: 包含search_references
                broadcast_data = {
                    "type": "status_update",
                    "status": current_session["status"],
                    "progress": progress,
                    "current_node": current_node_name,
                    "detail": current_session.get("detail"),
                }

                # 添加search_references（如果存在）
                search_refs = current_session.get("search_references")
                if search_refs:
                    broadcast_data["search_references"] = search_refs

                await broadcast_to_websockets(session_id, broadcast_data)

            # 检查是否有节点错误或被拒绝
            has_error = False
            error_message = None
            is_rejected = False
            rejection_message = None

            for event in events:
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        # 检查错误
                        if node_output.get("error") or node_output.get("status") == "error":
                            has_error = True
                            error_message = node_output.get("error", f"节点 {node_name} 执行失败")
                            break
                        #  检查被拒绝
                        if (
                            node_output.get("final_status") == "rejected"
                            or node_output.get("current_stage") == "REJECTED"
                        ):
                            is_rejected = True
                            rejection_message = node_output.get("rejection_message", "输入不符合要求")
                            rejection_reason = node_output.get("rejection_reason", "unknown")  # 获取拒绝原因
                            break
                if has_error or is_rejected:
                    break

            # 根据状态设置会话
            if is_rejected:
                await session_manager.update(
                    session_id,
                    {
                        "status": "rejected",
                        "rejection_message": rejection_message,
                        "rejection_reason": rejection_reason,  # 保存拒绝原因
                        "progress": 1.0,
                    },
                )
                logger.info(f" 输入被拒绝: {rejection_message[:100]}...")

                #  获取最新会话数据用于广播
                updated_session = await session_manager.get(session_id)

                #  广播拒绝状态
                await broadcast_to_websockets(
                    session_id,
                    {
                        "type": "status_update",
                        "status": "rejected",
                        "progress": 1.0,
                        "rejection_message": rejection_message,
                        "rejection_reason": rejection_reason,  # 广播拒绝原因
                        "current_node": updated_session.get("current_node") if updated_session else None,
                        "detail": updated_session.get("detail") if updated_session else None,
                    },
                )
            elif has_error:
                await session_manager.update(session_id, {"status": "failed", "error": error_message})
                logger.error(f"工作流失败: {error_message}")

                #  获取最新会话数据
                updated_session = await session_manager.get(session_id)

                #  广播错误状态
                await broadcast_to_websockets(
                    session_id,
                    {
                        "type": "status_update",
                        "status": "failed",
                        "error": error_message,
                        "current_node": updated_session.get("current_node") if updated_session else None,
                        "detail": updated_session.get("detail") if updated_session else None,
                        "progress": updated_session.get("progress") if updated_session else 0,
                    },
                )
            else:
                #  v7.153: 先同步 checkpoint 数据到 Redis，确保 final_report 结构化数据完整
                try:
                    sync_success = await sync_checkpoint_to_redis(session_id)
                    if sync_success:
                        logger.info(f" [v7.153] checkpoint 数据已同步到 Redis（工作流完成）")
                except Exception as sync_error:
                    logger.error(f" [v7.153] checkpoint 同步异常: {sync_error}")

                # 提取最终报告和PDF路径（从 events 中作为备用）
                final_report = None
                pdf_path = None

                for event in events:
                    for node_name, node_output in event.items():
                        if isinstance(node_output, dict):
                            # 提取 final_report
                            if "final_report" in node_output:
                                final_report = node_output["final_report"]
                            # 提取 pdf_path（由 report_generator 节点生成）
                            if "pdf_path" in node_output:
                                pdf_path = node_output["pdf_path"]
                                logger.info(f" 提取到报告路径: {pdf_path}")

                #  更新完成状态（final_report 优先使用 sync 同步的数据）
                update_data = {
                    "status": "completed",
                    "progress": 1.0,
                    "pdf_path": pdf_path,
                }
                # 只有当 sync 没有同步 final_report 时，才使用 events 中的备用值
                if final_report:
                    # 检查 Redis 中是否已有 final_report
                    current_session = await session_manager.get(session_id)
                    if not current_session.get("final_report"):
                        update_data["final_report"] = final_report

                await session_manager.update(session_id, update_data)

                #  获取最新会话数据
                updated_session = await session_manager.get(session_id)

                #  广播完成状态（v7.120: 包含search_references）
                completion_broadcast = {
                    "type": "status_update",
                    "status": "completed",
                    "progress": 1.0,
                    "final_report": final_report or "分析完成",
                    "current_node": updated_session.get("current_node") if updated_session else None,
                    "detail": updated_session.get("detail") if updated_session else None,
                }

                # 添加search_references（如果存在）
                if updated_session and updated_session.get("search_references"):
                    completion_broadcast["search_references"] = updated_session["search_references"]
                    logger.info(f" [v7.120] 完成广播包含 {len(updated_session['search_references'])} 个搜索引用")

                await broadcast_to_websockets(session_id, completion_broadcast)

                #  提取最终状态作为结构化结果（供get_analysis_result使用）
                final_state = None
                challenge_detection = None
                challenge_handling = None

                if events:
                    # 最后一个事件可能包含完整状态
                    last_event = events[-1] if events else {}
                    # 尝试从各个节点提取状态
                    for node_name, node_output in last_event.items():
                        if isinstance(node_output, dict):
                            if "agent_results" in node_output:
                                final_state = node_output
                            #  提取挑战检测数据
                            if "challenge_detection" in node_output:
                                challenge_detection = node_output["challenge_detection"]
                            if "challenge_handling" in node_output:
                                challenge_handling = node_output["challenge_handling"]

                    # 如果最后一个事件没有，遍历所有事件查找
                    if not challenge_detection:
                        for event in events:
                            for node_name, node_output in event.items():
                                if isinstance(node_output, dict):
                                    if "challenge_detection" in node_output and node_output["challenge_detection"]:
                                        challenge_detection = node_output["challenge_detection"]
                                        challenge_handling = node_output.get("challenge_handling")
                                        logger.info(f" 从 {node_name} 提取到挑战检测数据")
                                        break
                            if challenge_detection:
                                break

                #  保存最终状态和事件（包含挑战检测）
                update_data = {"final_state": final_state, "results": events}
                if challenge_detection:
                    update_data["challenge_detection"] = challenge_detection
                    update_data["challenge_handling"] = challenge_handling
                    logger.info(f" 保存挑战检测数据: has_challenges={challenge_detection.get('has_challenges')}")

                await session_manager.update(session_id, update_data)

                #  v3.6新增: 自动归档完成的会话（永久保存）
                if archive_manager:
                    try:
                        #  v7.145: 归档前同步 checkpoint 数据到 Redis
                        sync_success = await sync_checkpoint_to_redis(session_id)
                        if sync_success:
                            logger.info(f" [v7.145] checkpoint 数据已同步，准备归档")

                        # 获取完整会话数据
                        final_session = await session_manager.get(session_id)
                        if final_session:
                            await archive_manager.archive_session(
                                session_id=session_id, session_data=final_session, force=False  # 仅归档completed状态的会话
                            )
                            logger.info(f" 会话已自动归档（永久保存）: {session_id}")
                    except Exception as archive_error:
                        # 归档失败不应影响主流程
                        logger.warning(f"️ 自动归档失败（不影响主流程）: {archive_error}")

        #  处理递归限制错误
        except GraphRecursionError as e:
            logger.warning(f"️ 达到递归限制！会话: {session_id}")
            logger.info(" 尝试获取最佳结果...")

            # 获取当前状态
            #  v7.153: 修复 AsyncSqliteSaver 同步调用错误，使用 aget_state 异步方法
            try:
                current_state = await workflow.graph.aget_state(config)
                state_values = current_state.values

                # 尝试获取最佳结果
                best_result = state_values.get("best_result")
                if best_result:
                    logger.info(f" 找到最佳结果（评分{state_values.get('best_score', 0):.1f}）")
                    # 使用最佳结果更新agent_results
                    state_values["agent_results"] = best_result
                    state_values["metadata"]["forced_completion"] = True
                    state_values["metadata"]["completion_reason"] = "达到递归限制，使用最佳历史结果"
                else:
                    logger.warning("️ 未找到最佳结果，使用当前结果")
                    state_values["metadata"]["forced_completion"] = True
                    state_values["metadata"]["completion_reason"] = "达到递归限制"

                #  更新为完成状态
                await session_manager.update(
                    session_id,
                    {
                        "status": "completed",
                        "progress": 1.0,
                        "results": events,
                        "final_report": "分析已完成（达到递归限制）",
                        "metadata": state_values.get("metadata", {}),
                    },
                )

            except Exception as state_error:
                logger.error(f" 获取状态失败: {state_error}")
                import traceback

                await session_manager.update(
                    session_id,
                    {"status": "failed", "error": f"达到递归限制且无法获取状态: {str(e)}", "traceback": traceback.format_exc()},
                )

    except Exception as e:
        import traceback

        error_msg = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f" [ASYNC] run_workflow_async 异常: {error_msg}")
        logger.error(f" [ASYNC] 异常堆栈:\n{error_traceback}")

        await session_manager.update(session_id, {"status": "failed", "error": error_msg, "traceback": error_traceback})


async def _wait_for_connected(websocket: WebSocket, timeout: float = 2.0) -> bool:
    """
     Fix 1.1 + v7.118: Wait for WebSocket to reach CONNECTED state

    增强版本：添加更详细的状态检查和日志

    Args:
        websocket: WebSocket connection
        timeout: Maximum wait time in seconds

    Returns:
        True if connected, False if timeout
    """
    import asyncio

    from starlette.websockets import WebSocketState

    start = asyncio.get_event_loop().time()
    while websocket.client_state != WebSocketState.CONNECTED:
        elapsed = asyncio.get_event_loop().time() - start
        if elapsed > timeout:
            logger.error(f" WebSocket 连接超时 (state: {websocket.client_state.name}, elapsed: {elapsed:.2f}s)")
            return False
        await asyncio.sleep(0.05)

    logger.debug(f" WebSocket已连接 (耗时: {(asyncio.get_event_loop().time() - start):.2f}s)")
    return True


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")
