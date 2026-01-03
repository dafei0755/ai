# -*- coding: utf-8 -*-
"""
FastAPI 后端服务器

提供 RESTful API 接口，支持前后端分离架构
"""

import asyncio
import io
import json
import math  # 🔥 v7.109: 用于分页诊断日志
import os
import re
import sys
import uuid
from collections import OrderedDict, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
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

# 🔥 v7.120: 初始化生产级日志系统（环境感知配置）
from intelligent_project_analyzer.config.logging_config import setup_logging

# 🌍 导入GeoIP服务（IP地理位置识别）
from intelligent_project_analyzer.services.geoip_service import get_geoip_service

# 🔥 v7.60.4: 导入 ImageAspectRatio 枚举用于类型转换
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
    compression="zip",  # 🆕 轮转时自动压缩为 .zip 文件
    level="INFO",
)

# 认证相关日志（方便 SSO 调试）- 启用压缩
logger.add(
    str(log_dir / "auth.log"),
    rotation="5 MB",
    retention="7 days",
    encoding="utf-8",
    enqueue=True,
    compression="zip",  # 🆕 自动压缩
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
    compression="zip",  # 🆕 自动压缩
    level="ERROR",
)

# 🆕 启用告警监控（拦截错误日志）
from intelligent_project_analyzer.api.alert_monitor import alert_monitor, alert_sink

logger.add(alert_sink, level="ERROR")
from typing import List

from fpdf import FPDF


# 🔥 v7.60.4: 辅助函数 - 将前端传递的字符串宽高比转换为 ImageAspectRatio 枚举
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

from langgraph.types import Command, Interrupt

# ✅ v3.8新增: 对话智能体
from intelligent_project_analyzer.agents.conversation_agent import ConversationAgent, ConversationContext

# 🔥 v7.15新增: 追问智能体 (LangGraph)
from intelligent_project_analyzer.agents.followup_agent import FollowupAgent
from intelligent_project_analyzer.core.state import StateManager

# ✅ v3.7新增: 文件处理服务
from intelligent_project_analyzer.services.file_processor import build_combined_input, file_processor

# ✅ v3.11新增: 追问历史管理器
from intelligent_project_analyzer.services.followup_history_manager import FollowupHistoryManager

# ✅ Redis 会话管理器
from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

# ✅ v3.6新增: 会话归档管理器
from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager

# ✅ v7.10新增: WordPress JWT 认证服务
from intelligent_project_analyzer.services.wordpress_jwt_service import WordPressJWTService

# ✅ 使用新的统一配置 - 不再需要load_dotenv()
from intelligent_project_analyzer.settings import settings
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

# 初始化 JWT 服务
jwt_service = WordPressJWTService()


# 🔥 v7.120 P1优化: TTL缓存工具类（用于会话列表缓存 4.09s→0.05s）
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

# ✅ v7.35: 开发模式检测
# 兼容：显式 DEV_MODE=true 或 ENVIRONMENT=dev（单测/本地开发常用）
DEV_MODE = (
    os.getenv("DEV_MODE", "false").lower() == "true"
    or os.getenv("ENVIRONMENT", "").lower() == "dev"
    or getattr(settings, "environment", None) == "dev"
)


# 🔒 认证依赖函数
async def get_current_user(request: Request) -> dict:
    """
    FastAPI 依赖函数：从请求头验证 JWT Token 并返回用户信息

    用于保护需要认证的端点

    🔧 v7.35: 支持开发模式，接受 "dev-token-mock" 作为有效 Token
    """
    auth_header = request.headers.get("Authorization", "")
    # 🔧 开发/测试环境：允许不带 Token 直接访问（便于本地调试与自动化测试）
    # 生产环境 DEV_MODE=False 时不会生效。
    if DEV_MODE and (not auth_header or not auth_header.startswith("Bearer ")):
        logger.info("🔧 [DEV_MODE] 未提供 Token，使用开发测试用户")
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

    # 🔧 v7.35: 开发模式支持 - 接受 mock token
    if DEV_MODE and token == "dev-token-mock":
        logger.info("🔧 [DEV_MODE] 使用开发测试用户")
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

    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("roles", []),
    }


# 🆕 v7.130: 可选认证依赖函数（Token存在则验证，不存在也允许访问）
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

    # ⚠️ 兼容：部分JWT使用标准字段 sub 作为用户名/主体
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


# 全局变量存储工作流实例
workflows: Dict[str, MainWorkflow] = {}

# ✅ Redis 会话管理器实例（替代内存字典）
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
            logger.warning(f"⚠️ session_manager 惰性初始化失败: {e}")
    return session_manager


# ✅ v3.6新增: 会话归档管理器实例
archive_manager: Optional[SessionArchiveManager] = None

# ✅ v3.11新增: 追问历史管理器实例
followup_history_manager: Optional[FollowupHistoryManager] = None

# WebSocket 连接管理
websocket_connections: Dict[str, List[WebSocket]] = {}  # session_id -> [websocket1, websocket2, ...]

# Redis Pub/Sub 支持
import redis.asyncio as aioredis

redis_pubsub_client: Optional[aioredis.Redis] = None
redis_pubsub_task: Optional[asyncio.Task] = None

# ✅ v7.1.2新增: PDF 缓存（性能优化）
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
        return _serialize_for_json(data.model_dump())
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
    print("  🤖 智能项目分析系统 - API 服务器")
    print("=" * 60)
    print()

    # ✅ 初始化 Redis 会话管理器
    try:
        session_manager = RedisSessionManager()
        await session_manager.connect()
        print("✅ Redis 会话管理器已启动")
    except Exception as e:
        logger.error(f"❌ Redis 会话管理器启动失败: {e}")
        print("⚠️ Redis 会话管理器启动失败（使用内存模式）")

    # ✅ v3.11新增: 初始化追问历史管理器
    try:
        followup_history_manager = FollowupHistoryManager(session_manager)
        print("✅ 追问历史管理器已启动")
    except Exception as e:
        logger.error(f"❌ 追问历史管理器启动失败: {e}")
        print("⚠️ 追问历史管理器启动失败（追问功能受限）")

    # ✅ v3.6新增: 初始化会话归档管理器
    try:
        archive_manager = SessionArchiveManager()
        print("✅ 会话归档管理器已启动（永久保存功能已启用）")
    except Exception as e:
        logger.error(f"❌ 会话归档管理器启动失败: {e}")
        print("⚠️ 会话归档管理器启动失败（无法使用永久保存功能）")

    # ✅ 初始化 Redis Pub/Sub（用于 WebSocket 多实例广播）
    try:
        redis_pubsub_client = await aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        # 启动订阅监听任务
        redis_pubsub_task = asyncio.create_task(subscribe_to_redis_pubsub())
        print("✅ Redis Pub/Sub 已启动")
    except Exception as e:
        logger.warning(f"⚠️ Redis Pub/Sub 启动失败: {e}")
        print("⚠️ Redis Pub/Sub 启动失败（WebSocket 仅支持单实例）")

    # ✅ v7.1.2新增: 初始化 Playwright 浏览器池（PDF 生成性能优化）
    try:
        from intelligent_project_analyzer.api.html_pdf_generator import get_browser_pool

        browser_pool = get_browser_pool()
        await browser_pool.initialize()
        print("✅ Playwright 浏览器池已启动（PDF 生成性能优化）")
    except Exception as e:
        logger.warning(f"⚠️ Playwright 浏览器池启动失败: {e}")
        print("⚠️ Playwright 浏览器池启动失败（PDF 生成将使用备用方案）")

    # ✅ v7.120 P1优化: 预初始化设备会话管理器（消除4.05s延迟）
    try:
        from intelligent_project_analyzer.services.device_session_manager import get_device_manager

        device_manager = get_device_manager()
        await device_manager.initialize()
        print("✅ 设备会话管理器已预初始化（P1优化: 4.05s→0.05s）")
    except Exception as e:
        logger.warning(f"⚠️ 设备会话管理器预初始化失败: {e}")
        print("⚠️ 设备会话管理器预初始化失败（设备检查可能较慢）")

    print("✅ 服务器启动成功")
    print("📍 API 文档: http://localhost:8000/docs")
    print("📍 健康检查: http://localhost:8000/health")
    print()

    # 🔥 v7.105: 预热会话缓存（消除首次请求延迟）
    try:
        import time

        logger.info("⏳ 预热会话列表缓存...")
        start_time = time.time()
        sessions = await session_manager.get_all_sessions()
        elapsed = time.time() - start_time
        logger.info(f"✅ 缓存预热完成: {len(sessions)} 个会话 ({elapsed:.1f}秒)")
    except Exception as e:
        logger.warning(f"⚠️ 缓存预热失败: {e}")

    # ✅ Fix 1.4: 启动时清理旧会话（24小时前的已完成会话）
    try:
        logger.info("🧹 清理旧会话...")
        cleaned = await session_manager.cleanup_old_sessions(max_age_hours=24)
        if cleaned > 0:
            logger.info(f"✅ 启动清理完成: 删除 {cleaned} 个旧会话")
        else:
            logger.info("✅ 启动清理完成: 无需清理")
    except Exception as e:
        logger.warning(f"⚠️ 启动清理失败: {e}")

    yield

    # 关闭时
    print("\n👋 服务器关闭中...")

    # ✅ v7.1.2新增: 关闭 Playwright 浏览器池
    try:
        from intelligent_project_analyzer.api.html_pdf_generator import PlaywrightBrowserPool

        await PlaywrightBrowserPool.cleanup()
        print("✅ Playwright 浏览器池已关闭")
    except Exception as e:
        logger.warning(f"⚠️ Playwright 浏览器池关闭失败: {e}")

    # ✅ 关闭 Redis Pub/Sub
    if redis_pubsub_task:
        redis_pubsub_task.cancel()
        try:
            await redis_pubsub_task
        except asyncio.CancelledError:
            pass

    if redis_pubsub_client:
        await redis_pubsub_client.close()

    # ✅ 关闭 Redis 会话管理器
    if session_manager:
        await session_manager.disconnect()

    # ✅ v3.6新增: 关闭归档管理器（关闭数据库连接）
    if archive_manager:
        # SessionArchiveManager 使用 SQLAlchemy，引擎会自动管理连接池
        # 不需要显式关闭，但记录日志
        logger.info("📦 会话归档管理器已关闭")

    print("👋 服务器已关闭")


# 创建 FastAPI 应用
app = FastAPI(title="智能项目分析系统 API", description="基于 LangGraph 的多智能体协作分析平台", version="2.0.0", lifespan=lifespan)

# 🆕 添加性能监控中间件
from intelligent_project_analyzer.api.performance_monitor import performance_monitoring_middleware

app.middleware("http")(performance_monitoring_middleware)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 挂载静态文件目录（用于专家生成的图片）
try:
    # 确保目录存在
    data_dir = Path(__file__).parent.parent.parent / "data"
    archived_images_dir = data_dir / "archived_images"
    uploads_dir = data_dir / "uploads"
    generated_images_dir = data_dir / "generated_images"  # 🆕 v7.108
    followup_images_dir = data_dir / "followup_images"  # 🆕 v7.108.2

    archived_images_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    generated_images_dir.mkdir(parents=True, exist_ok=True)  # 🆕 v7.108
    followup_images_dir.mkdir(parents=True, exist_ok=True)  # 🆕 v7.108.2

    # 挂载静态文件服务
    app.mount("/archived_images", StaticFiles(directory=str(archived_images_dir)), name="archived_images")
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
    app.mount(
        "/generated_images", StaticFiles(directory=str(generated_images_dir)), name="generated_images"
    )  # 🆕 v7.108
    app.mount("/followup_images", StaticFiles(directory=str(followup_images_dir)), name="followup_images")  # 🆕 v7.108.2

    logger.info(f"✅ 静态文件服务已挂载: /archived_images -> {archived_images_dir}")
    logger.info(f"✅ 静态文件服务已挂载: /uploads -> {uploads_dir}")
    logger.info(f"✅ 静态文件服务已挂载: /generated_images -> {generated_images_dir}")  # 🆕 v7.108
    logger.info(f"✅ 静态文件服务已挂载: /followup_images -> {followup_images_dir}")  # 🆕 v7.108.2
except Exception as e:
    logger.warning(f"⚠️ 静态文件服务挂载失败: {e}")

# ✅ v7.10新增: 注册 WordPress JWT 认证路由
try:
    from intelligent_project_analyzer.api.auth_routes import router as auth_router

    app.include_router(auth_router)
    logger.info("✅ WordPress JWT 认证路由已注册")
except Exception as e:
    logger.warning(f"⚠️ WordPress JWT 认证路由加载失败: {e}")

# ✅ v7.10.1新增: 注册 WPCOM Member 会员信息路由
try:
    from intelligent_project_analyzer.api.member_routes import router as member_router

    app.include_router(member_router)
    logger.info("✅ WPCOM Member 会员信息路由已注册")
except Exception as e:
    logger.warning(f"⚠️ WPCOM Member 会员信息路由加载失败: {e}")

# ✅ v7.11新增: 注册性能和告警统计API路由
try:
    from intelligent_project_analyzer.api.metrics_routes import router as metrics_router

    app.include_router(metrics_router)
    logger.info("✅ 性能和告警统计API路由已注册")
except Exception as e:
    logger.warning(f"⚠️ 性能和告警统计API路由加载失败: {e}")

# 🔥 管理员后台路由（仅限管理员访问）
try:
    from intelligent_project_analyzer.api.admin_routes import router as admin_router

    app.include_router(admin_router)
    logger.info("✅ 管理员后台路由已注册")
except Exception as e:
    logger.warning(f"⚠️ 管理员后台路由加载失败: {e}")

# ✅ v3.9新增: 注册 Celery 路由（可选）
try:
    from intelligent_project_analyzer.api.celery_routes import register_celery_routes

    register_celery_routes(app)
except ImportError as e:
    logger.warning(f"⚠️ Celery 路由未加载（可选功能）: {e}")


# ==================== 数据模型 ====================


class AnalysisRequest(BaseModel):
    """分析请求"""

    # Backward compatible aliases:
    # - legacy clients use `requirement` instead of `user_input`
    # - some clients may send `username`/`userId` etc; we only normalize what we actually need
    model_config = ConfigDict(populate_by_name=True, coerce_numbers_to_str=True)

    user_input: str = Field(validation_alias=AliasChoices("user_input", "requirement"))
    user_id: str = Field(default="web_user", validation_alias=AliasChoices("user_id", "username"))  # 用户ID
    # 🆕 v7.39: 分析模式 - normal(普通) 或 deep_thinking(深度思考)
    # 深度思考模式会为每个专家生成概念图像
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
    detail: Optional[str] = None  # 🔥 新增：当前节点的详细信息
    progress: float = 0.0
    history: Optional[List[Dict[str, Any]]] = None  # 🔥 新增：执行历史
    interrupt_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None  # 添加traceback字段用于调试
    rejection_message: Optional[str] = None  # 🆕 拒绝原因提示
    user_input: Optional[str] = None  # 🔥 v7.37.7: 用户原始输入


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


# 🆕 对话相关数据模型
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


# 🔥 Phase 1.4+ P4: 核心答案响应模型（向后兼容版）
class CoreAnswerResponse(BaseModel):
    """核心答案响应（向后兼容）"""

    question: str = Field(default="", description="从用户输入提取的核心问题")
    answer: str = Field(default="", description="直接明了的核心答案")
    deliverables: List[str] = Field(default_factory=list, description="交付物清单")
    timeline: str = Field(default="", description="预估时间线")
    budget_range: str = Field(default="", description="预算估算范围")


# 🆕 v7.0: 单个交付物的责任者答案响应
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


# 🆕 v7.0: 专家支撑链响应
class ExpertSupportChainResponse(BaseModel):
    """专家支撑链响应"""

    role_id: str = Field(default="", description="专家角色ID")
    role_name: str = Field(default="", description="专家名称")
    contribution_type: str = Field(default="support", description="贡献类型")
    contribution_summary: str = Field(default="", description="贡献摘要")
    related_deliverables: List[str] = Field(default_factory=list, description="关联的交付物ID")


# 🆕 v7.0: 增强版核心答案响应（支持多交付物）
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


# 🔥 Phase 1.4+ v4.1: 洞察区块响应模型
class InsightsSectionResponse(BaseModel):
    """洞察区块响应 - 从需求分析师和所有专家中提炼的关键洞察"""

    key_insights: List[str] = Field(default_factory=list, description="3-5条核心洞察")
    cross_domain_connections: List[str] = Field(default_factory=list, description="跨领域关联发现")
    user_needs_interpretation: str = Field(default="", description="对用户需求的深层解读")


# 🔥 Phase 1.4+ v4.1: 推敲过程响应模型
class DeliberationProcessResponse(BaseModel):
    """推敲过程响应 - 项目总监的战略分析和决策思路"""

    inquiry_architecture: str = Field(default="", description="选择的探询架构类型")
    reasoning: str = Field(default="", description="为什么选择这个探询架构")
    role_selection: List[str] = Field(default_factory=list, description="选择的专家角色及理由")
    strategic_approach: str = Field(default="", description="整体战略方向")


# 🔥 Phase 1.4+ v4.1: 建议区块响应模型
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
    # 🔥 Phase 1.4+ P4: 核心答案（用户最关心的TL;DR）
    # 🆕 v7.0: 支持新的多交付物格式和旧格式（向后兼容）
    # 如果有 deliverable_answers 字段，则是 v7.0 格式
    # 否则是旧格式（只有 answer 字段）
    core_answer: Optional[Dict[str, Any]] = Field(default=None, description="核心答案（支持v7.0多交付物格式和旧格式）")
    # 🔥 Phase 1.4+ v4.1: 新增洞察、推敲过程、建议区块
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
    # 🆕 v7.4: 执行元数据汇总
    execution_metadata: Optional[Dict[str, Any]] = Field(default=None, description="执行元数据汇总")
    # 🆕 v3.0.26: 思维导图内容结构（以内容为中心）
    mindmap_content: Optional[Dict[str, Any]] = Field(default=None, description="思维导图内容结构")
    # 🆕 普通模式概念图（集中生成）
    generated_images: Optional[List[str]] = Field(default=None, description="AI 概念图（普通模式）")
    image_prompts: Optional[List[str]] = Field(default=None, description="AI 概念图提示词（普通模式）")
    image_top_constraints: Optional[str] = Field(default=None, description="AI 概念图顶层约束（普通模式）")
    # 🆕 v7.39: 专家概念图（深度思考模式）
    generated_images_by_expert: Optional[Dict[str, Any]] = Field(default=None, description="专家概念图（深度思考模式）")


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

        # 🔥 Phase 1.4+: 修复置信度为0%的问题
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

        logger.info("📡 Redis Pub/Sub 订阅已启动")

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
                                # ✅ Fix 1.1: Check WebSocket state before sending (matches local broadcast logic)
                                if ws.client_state.name != "CONNECTED":
                                    logger.debug(f"⏭️ 跳过非连接状态的WebSocket (state={ws.client_state.name})")
                                    disconnected.append(ws)
                                    continue

                                await ws.send_json(payload)
                            except Exception as e:
                                logger.warning(f"⚠️ WebSocket 发送失败: {e}")
                                disconnected.append(ws)

                        # 清理断开的连接
                        for ws in disconnected:
                            connections.remove(ws)

                except Exception as e:
                    logger.error(f"❌ 处理 Pub/Sub 消息失败: {e}")

    except asyncio.CancelledError:
        logger.info("📡 Redis Pub/Sub 订阅已停止")
        await pubsub.unsubscribe("workflow:broadcast")
        await pubsub.close()
    except Exception as e:
        logger.error(f"❌ Redis Pub/Sub 订阅失败: {e}")


def create_workflow() -> Optional[MainWorkflow]:
    """
    创建工作流实例 - 使用 LLMFactory（支持自动降级）

    ✅ 使用 LLMFactory 创建 LLM，支持运行时降级
    """
    try:
        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        logger.info("🔧 使用 LLMFactory 创建 LLM（支持自动降级）")

        # ✅ 使用 LLMFactory 创建 LLM（自动应用 .env 配置和降级链）
        llm = LLMFactory.create_llm()

        # 默认使用 Dynamic Mode
        config = {
            "mode": "dynamic",
            "enable_role_config": True,
            "post_completion_followup_enabled": settings.post_completion_followup_enabled,
        }

        workflow = MainWorkflow(llm, config)
        logger.info("✅ 工作流创建成功（LLM 降级已启用）")
        return workflow

    except Exception as e:
        logger.error(f"❌ 创建工作流失败: {e}")
        import traceback

        traceback.print_exc()
        return None


async def broadcast_to_websockets(session_id: str, message: Dict[str, Any]):
    """
    向所有连接到指定会话的 WebSocket 客户端广播消息
    ✅ 使用 Redis Pub/Sub 支持多实例部署

    Args:
        session_id: 会话 ID
        message: 要发送的消息（字典格式，将被转换为 JSON）
    """
    # 🔥 Redis Pub/Sub 模式：发布到 Redis，所有实例监听
    if redis_pubsub_client:
        try:
            import json

            payload = {"session_id": session_id, "payload": message}
            await redis_pubsub_client.publish("workflow:broadcast", json.dumps(payload, ensure_ascii=False))
            return
        except Exception as e:
            logger.warning(f"⚠️ Redis Pub/Sub 发布失败，回退到本地广播: {e}")

    # 🔥 本地模式：直接广播到本实例的 WebSocket 连接
    if session_id not in websocket_connections:
        return

    # 获取该会话的所有连接
    connections = websocket_connections[session_id]

    # 存储断开的连接
    disconnected = []

    # 广播消息到所有连接
    for ws in connections:
        try:
            # ✅ P0修复: 检查WebSocket连接状态
            if ws.client_state.name != "CONNECTED":
                logger.debug(f"⚠️ WebSocket未连接 (状态: {ws.client_state.name})，标记为断开")
                disconnected.append(ws)
                continue

            await ws.send_json(message)
        except Exception as e:
            logger.warning(f"⚠️ WebSocket 发送失败: {e}")
            disconnected.append(ws)

    # 清理断开的连接
    for ws in disconnected:
        connections.remove(ws)


async def run_workflow_async(session_id: str, user_input: str):
    """异步执行工作流（仅 Dynamic Mode）"""
    try:
        # 🆕 v7.39: 从 session 获取分析模式
        session_data = await session_manager.get(session_id)
        analysis_mode = session_data.get("analysis_mode", "normal") if session_data else "normal"
        user_id = session_data.get("user_id", "api_user") if session_data else "api_user"

        print(f"\n{'='*60}")
        print(f"🚀 开始执行工作流")
        print(f"Session ID: {session_id}")
        print(f"用户输入: {user_input[:100]}...")
        print(f"运行模式: Dynamic Mode")
        print(f"分析模式: {analysis_mode}")  # 🆕 v7.39
        print(f"{'='*60}\n")

        # ✅ 更新会话状态
        await session_manager.update(session_id, {"status": "running", "progress": 0.1})

        # 🔥 广播状态到 WebSocket
        await broadcast_to_websockets(
            session_id, {"type": "status_update", "status": "running", "progress": 0.1, "message": "工作流开始执行"}
        )

        # 创建工作流
        print(f"📦 创建工作流 (Dynamic Mode)...")
        workflow = create_workflow()
        if not workflow:
            print(f"❌ 工作流创建失败")
            await session_manager.update(
                session_id, {"status": "failed", "error": "工作流创建失败", "traceback": "工作流创建失败，请检查配置"}
            )
            return

        print(f"✅ 工作流创建成功")
        workflows[session_id] = workflow

        # 创建初始状态 - 🆕 v7.39: 传递 analysis_mode
        initial_state = StateManager.create_initial_state(
            user_input=user_input, session_id=session_id, user_id=user_id, analysis_mode=analysis_mode  # 🆕 v7.39
        )

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}  # 增加递归限制，默认是25

        # 流式执行工作流
        # 不指定 stream_mode，使用默认模式以正确接收 __interrupt__
        # 🆕 添加GraphRecursionError处理
        from langgraph.errors import GraphRecursionError

        events = []
        try:
            async for chunk in workflow.graph.astream(initial_state, config):
                # 🔧 诊断日志：检查每个 chunk 的键
                logger.info(f"🔍 [STREAM] chunk keys: {list(chunk.keys())}")

                events.append(_serialize_for_json(chunk))

                # 🔥 检查是否有 interrupt - 提前检测（在处理其他节点之前）
                if "__interrupt__" in chunk:
                    logger.info(f"🛑 [INTERRUPT] Detected! chunk keys: {list(chunk.keys())}")
                    # 提取 interrupt 数据
                    interrupt_tuple = chunk["__interrupt__"]
                    logger.info(f"🛑 [INTERRUPT] tuple type: {type(interrupt_tuple)}, content: {interrupt_tuple}")

                    # interrupt_tuple 是一个元组，第一个元素是 Interrupt 对象
                    if interrupt_tuple:
                        interrupt_obj = interrupt_tuple[0] if isinstance(interrupt_tuple, tuple) else interrupt_tuple
                        logger.info(f"🛑 [INTERRUPT] obj type: {type(interrupt_obj)}")

                        # 提取 interrupt 的 value
                        interrupt_value = None
                        if hasattr(interrupt_obj, "value"):
                            interrupt_value = interrupt_obj.value
                            logger.info(f"🛑 [INTERRUPT] Extracted value from .value attribute")
                        else:
                            interrupt_value = interrupt_obj
                            logger.info(f"🛑 [INTERRUPT] Using obj directly as value")

                        logger.info(f"🛑 [INTERRUPT] value type: {type(interrupt_value)}")

                        # ✅ v7.119: 更新会话状态为等待用户输入，并记录时间戳
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
                        logger.info(f"🛑 [INTERRUPT] Session {session_id} updated to waiting_for_input")

                        # 🔥 广播 interrupt 到 WebSocket
                        await broadcast_to_websockets(
                            session_id,
                            {"type": "interrupt", "status": "waiting_for_input", "interrupt_data": interrupt_value},
                        )
                        logger.info(f"🛑 [INTERRUPT] Broadcasted to WebSocket")
                        return

                # 🔥 更新当前节点和详细信息（用于前端进度展示）
                for node_name, node_output in chunk.items():
                    if node_name != "__interrupt__":
                        # 提取详细信息
                        detail = ""
                        if isinstance(node_output, dict):
                            # ✅ 优先使用 detail 字段（节点返回的详细描述）
                            if "detail" in node_output:
                                detail = node_output["detail"]
                            # 回退：使用 current_stage
                            elif "current_stage" in node_output:
                                detail = node_output["current_stage"]
                            # 最后：使用 status
                            elif "status" in node_output:
                                detail = node_output["status"]

                        # ✅ 更新当前节点、详情和历史记录
                        # 获取当前会话以追加历史
                        current_session = await session_manager.get(session_id)
                        history = current_session.get("history", []) if current_session else []

                        # 添加新记录
                        history.append(
                            {"node": node_name, "detail": detail, "time": datetime.now().strftime("%H:%M:%S")}
                        )

                        # 🔥 v7.120: 提取search_references（如果节点更新了此字段）
                        update_data = {"current_node": node_name, "detail": detail, "history": history}

                        # 检查并提取search_references
                        if isinstance(node_output, dict) and "search_references" in node_output:
                            search_refs = node_output["search_references"]
                            if search_refs:  # 只有非空才更新
                                update_data["search_references"] = search_refs
                                logger.info(f"🔍 [v7.120] 节点 {node_name} 更新了 {len(search_refs)} 个搜索引用")

                        await session_manager.update(session_id, update_data)
                        logger.debug(f"[PROGRESS] 节点: {node_name}, 详情: {detail}")

                        # 🔧 诊断日志（2025-11-30）：检查detail提取和广播
                        if node_name == "agent_executor":
                            logger.info(f"🔍 [DIAGNOSTIC] agent_executor detail: '{detail}'")
                            logger.info(
                                f"🔍 [DIAGNOSTIC] node_output keys: {list(node_output.keys()) if isinstance(node_output, dict) else 'not dict'}"
                            )
                            if isinstance(node_output, dict) and "detail" in node_output:
                                logger.info(f"🔍 [DIAGNOSTIC] node_output['detail']: '{node_output['detail']}'")

                        # 🔥 广播节点更新到 WebSocket
                        await broadcast_to_websockets(
                            session_id,
                            {
                                "type": "node_update",
                                "current_node": node_name,
                                "detail": detail,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                        # 🔧 诊断日志：确认广播内容
                        if node_name == "agent_executor":
                            logger.info(f"🔍 [DIAGNOSTIC] Broadcasted node_update with detail: '{detail}'")

                # 🔥 更新进度（优化：基于节点名称映射）
                # ✅ 获取当前会话数据
                current_session = await session_manager.get(session_id)
                if not current_session:
                    continue

                current_node_name = current_session.get("current_node", "")

                # 🎯 v7.21: 定义节点到进度的映射（与 main_workflow.py 实际节点名称对齐）
                node_progress_map = {
                    # 输入验证阶段 (0-15%)
                    "unified_input_validator_initial": 0.05,  # 5% - 初始输入验证
                    "unified_input_validator_secondary": 0.10,  # 10% - 二次验证
                    # 需求分析阶段 (15-35%)
                    "requirements_analyst": 0.15,  # 15% - 需求分析
                    "feasibility_analyst": 0.20,  # 20% - 可行性分析
                    "calibration_questionnaire": 0.25,  # 25% - 问卷
                    "requirements_confirmation": 0.35,  # 35% - 需求确认
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

                # 🔥 防止进度回退：只有新进度 ≥ 旧进度时才更新
                old_progress = current_session.get("progress", 0)
                progress = max(new_progress, old_progress if isinstance(old_progress, (int, float)) else 0)

                if new_progress < old_progress:
                    logger.debug(f"⚠️ 检测到进度回退: {old_progress:.0%} → {new_progress:.0%}，使用旧进度 {progress:.0%}")

                # ✅ 单次更新 Redis（避免重复写入和竞态条件）
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

                # 🔄 直接使用计算值广播到 WebSocket（避免 Redis 读取竞态）
                # 🔥 v7.120: 包含search_references
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
                        # 🆕 检查被拒绝
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
                logger.info(f"✋ 输入被拒绝: {rejection_message[:100]}...")

                # ✅ 获取最新会话数据用于广播
                updated_session = await session_manager.get(session_id)

                # 🔥 广播拒绝状态
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

                # ✅ 获取最新会话数据
                updated_session = await session_manager.get(session_id)

                # 🔥 广播错误状态
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
                # 提取最终报告和PDF路径
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
                                logger.info(f"📄 提取到报告路径: {pdf_path}")

                # ✅ 更新完成状态
                await session_manager.update(
                    session_id,
                    {
                        "status": "completed",
                        "progress": 1.0,
                        "final_report": final_report or "分析完成",
                        "pdf_path": pdf_path,
                    },
                )

                # ✅ 获取最新会话数据
                updated_session = await session_manager.get(session_id)

                # 🔥 广播完成状态（v7.120: 包含search_references）
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
                    logger.info(f"📚 [v7.120] 完成广播包含 {len(updated_session['search_references'])} 个搜索引用")

                await broadcast_to_websockets(session_id, completion_broadcast)

                # 🆕 提取最终状态作为结构化结果（供get_analysis_result使用）
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
                            # 🆕 提取挑战检测数据
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
                                        logger.info(f"🔍 从 {node_name} 提取到挑战检测数据")
                                        break
                            if challenge_detection:
                                break

                # ✅ 保存最终状态和事件（包含挑战检测）
                update_data = {"final_state": final_state, "results": events}
                if challenge_detection:
                    update_data["challenge_detection"] = challenge_detection
                    update_data["challenge_handling"] = challenge_handling
                    logger.info(f"✅ 保存挑战检测数据: has_challenges={challenge_detection.get('has_challenges')}")

                await session_manager.update(session_id, update_data)

                # 🆕 v3.6新增: 自动归档完成的会话（永久保存）
                if archive_manager:
                    try:
                        # 获取完整会话数据
                        final_session = await session_manager.get(session_id)
                        if final_session:
                            await archive_manager.archive_session(
                                session_id=session_id, session_data=final_session, force=False  # 仅归档completed状态的会话
                            )
                            logger.info(f"📦 会话已自动归档（永久保存）: {session_id}")
                    except Exception as archive_error:
                        # 归档失败不应影响主流程
                        logger.warning(f"⚠️ 自动归档失败（不影响主流程）: {archive_error}")

        # 🆕 处理递归限制错误
        except GraphRecursionError as e:
            logger.warning(f"⚠️ 达到递归限制！会话: {session_id}")
            logger.info("📦 尝试获取最佳结果...")

            # 获取当前状态
            try:
                current_state = workflow.graph.get_state(config)
                state_values = current_state.values

                # 尝试获取最佳结果
                best_result = state_values.get("best_result")
                if best_result:
                    logger.info(f"✅ 找到最佳结果（评分{state_values.get('best_score', 0):.1f}）")
                    # 使用最佳结果更新agent_results
                    state_values["agent_results"] = best_result
                    state_values["metadata"]["forced_completion"] = True
                    state_values["metadata"]["completion_reason"] = "达到递归限制，使用最佳历史结果"
                else:
                    logger.warning("⚠️ 未找到最佳结果，使用当前结果")
                    state_values["metadata"]["forced_completion"] = True
                    state_values["metadata"]["completion_reason"] = "达到递归限制"

                # ✅ 更新为完成状态
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
                logger.error(f"❌ 获取状态失败: {state_error}")
                import traceback

                await session_manager.update(
                    session_id,
                    {"status": "failed", "error": f"达到递归限制且无法获取状态: {str(e)}", "traceback": traceback.format_exc()},
                )

    except Exception as e:
        import traceback

        await session_manager.update(
            session_id, {"status": "failed", "error": str(e), "traceback": traceback.format_exc()}
        )


# ==================== API 端点 ====================


@app.get("/")
async def root():
    """根路径"""
    return {"message": "智能项目分析系统 API", "version": "2.0.0", "docs": "/docs"}


@app.get("/api/rate-limit/stats")
async def get_rate_limit_stats():
    """
    获取 LLM API 限流统计

    v3.9新增：监控 LLM API 调用限流状态
    """
    try:
        from intelligent_project_analyzer.services.rate_limiter import rate_limit_manager

        return {"status": "ok", "stats": rate_limit_manager.get_all_stats()}
    except Exception as e:
        return {"status": "error", "error": str(e), "message": "限流模块未初始化"}


@app.get("/api/keys/stats")
async def get_api_key_stats():
    """
    获取 API Key 负载均衡统计

    v3.9新增：监控多 Key 使用状态
    """
    try:
        from intelligent_project_analyzer.services.key_balancer import key_balancer

        return {
            "status": "ok",
            "available_providers": key_balancer.available_providers,
            "stats": key_balancer.get_all_stats(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "message": "Key 负载均衡器未初始化"}


@app.get("/health")
async def health_check():
    """
    🆕 P2优化: 增强健康检查端点 - 返回详细组件状态

    用于负载均衡器和监控系统快速检查服务状态
    返回各组件（Redis/Playwright/LLM）的健康状态
    """
    import time

    start_time = time.time()

    health_status = {"status": "healthy", "timestamp": datetime.now().isoformat(), "components": {}, "metrics": {}}

    try:
        # 1. 检查Redis连接
        redis_healthy = False
        redis_latency = 0
        try:
            redis_start = time.time()
            await session_manager.redis_client.ping()
            redis_latency = (time.time() - redis_start) * 1000
            redis_healthy = True
            health_status["components"]["redis"] = {
                "status": "up",
                "latency_ms": round(redis_latency, 2),
                "mode": "redis",
            }
        except Exception as redis_err:
            health_status["components"]["redis"] = {
                "status": "degraded",
                "mode": "memory_fallback",
                "error": str(redis_err),
            }

        # 2. 检查Playwright浏览器池
        playwright_healthy = False
        try:
            from intelligent_project_analyzer.api.html_pdf_generator import get_browser_pool

            browser_pool = get_browser_pool()
            if browser_pool._initialized and browser_pool._browser:
                playwright_healthy = browser_pool._browser.is_connected()
                health_status["components"]["playwright"] = {
                    "status": "up" if playwright_healthy else "down",
                    "initialized": browser_pool._initialized,
                    "connected": playwright_healthy,
                }
            else:
                health_status["components"]["playwright"] = {
                    "status": "not_initialized",
                    "pdf_generation": "unavailable",
                }
        except Exception as pw_err:
            health_status["components"]["playwright"] = {"status": "error", "error": str(pw_err)}

        # 3. 检查LLM配置
        llm_configured = False
        try:
            from intelligent_project_analyzer.settings import settings as app_settings

            api_key = app_settings.openai_api_key
            if api_key and api_key != "your-api-key-here":
                llm_configured = True
                health_status["components"]["llm"] = {"status": "configured", "provider": "openai"}
            else:
                health_status["components"]["llm"] = {"status": "not_configured", "warning": "OPENAI_API_KEY not set"}
        except Exception as llm_err:
            health_status["components"]["llm"] = {"status": "error", "error": str(llm_err)}

        # 4. 会话统计
        try:
            active_sessions = await session_manager.list_all_sessions()
            health_status["metrics"]["active_sessions"] = len(active_sessions)
            health_status["metrics"]["active_websockets"] = sum(len(conns) for conns in websocket_connections.values())
        except Exception:
            health_status["metrics"]["active_sessions"] = 0
            health_status["metrics"]["active_websockets"] = 0

        # 5. 总体健康判断
        if not redis_healthy and not health_status["components"]["redis"].get("mode") == "memory_fallback":
            health_status["status"] = "degraded"
        if not llm_configured:
            health_status["status"] = "degraded"

        health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return health_status

    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


@app.get("/api/debug/redis-health")
async def redis_health_check():
    """
    Redis 健康检查端点 - 用于诊断 Redis 性能问题

    执行完整的 CRUD 操作并返回延迟时间
    """
    import time

    start = time.time()

    try:
        test_id = f"test-health-{int(time.time())}"

        # 测试 Create
        create_start = time.time()
        await session_manager.create(test_id, {"test": "data", "timestamp": datetime.now().isoformat()})
        create_time = (time.time() - create_start) * 1000

        # 测试 Read
        read_start = time.time()
        data = await session_manager.get(test_id)
        read_time = (time.time() - read_start) * 1000

        # 测试 Update
        update_start = time.time()
        await session_manager.update(test_id, {"test": "updated"})
        update_time = (time.time() - update_start) * 1000

        # 测试 Delete
        delete_start = time.time()
        await session_manager.delete(test_id)
        delete_time = (time.time() - delete_start) * 1000

        total_time = (time.time() - start) * 1000

        return {
            "status": "healthy",
            "total_latency_ms": int(total_time),
            "operations": {
                "create_ms": int(create_time),
                "read_ms": int(read_time),
                "update_ms": int(update_time),
                "delete_ms": int(delete_time),
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f"❌ Redis健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "elapsed_ms": int(elapsed),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/readiness")
async def readiness_check():
    """
    就绪检查端点 - 检查服务是否准备好接收流量

    检查项：
    1. Redis连接状态
    2. 腾讯云API可达性
    3. 动态规则加载器状态
    4. 会话管理器状态
    """
    checks = {}
    is_ready = True

    # 1. 检查Redis连接
    try:
        if session_manager:
            # 尝试ping Redis
            await session_manager.list_all_sessions()
            checks["redis"] = {"status": "ok", "message": "Redis连接正常"}
        else:
            checks["redis"] = {"status": "warning", "message": "会话管理器未初始化"}
            is_ready = False
    except Exception as e:
        checks["redis"] = {"status": "error", "message": f"Redis连接失败: {str(e)}"}
        is_ready = False

    # 2. 检查腾讯云API可达性（如果启用）
    try:
        if os.getenv("ENABLE_TENCENT_CONTENT_SAFETY") == "true":
            from intelligent_project_analyzer.security.tencent_content_safety import get_tencent_content_safety_client

            client = get_tencent_content_safety_client()
            if client:
                checks["tencent_api"] = {"status": "ok", "message": "腾讯云API已配置"}
            else:
                checks["tencent_api"] = {"status": "warning", "message": "腾讯云API未启用"}
        else:
            checks["tencent_api"] = {"status": "disabled", "message": "腾讯云API未启用"}
    except Exception as e:
        checks["tencent_api"] = {"status": "error", "message": f"腾讯云API检查失败: {str(e)}"}
        # 腾讯云API失败不影响就绪状态（可以降级到本地检测）

    # 3. 检查动态规则加载器状态
    try:
        from intelligent_project_analyzer.security.dynamic_rule_loader import get_rule_loader

        loader = get_rule_loader()
        if loader:
            stats = loader.get_stats()
            checks["dynamic_rules"] = {
                "status": "ok",
                "message": "动态规则加载器正常",
                "version": stats.get("version", "unknown"),
                "categories": stats["keywords"]["total_categories"],
            }
        else:
            checks["dynamic_rules"] = {"status": "warning", "message": "动态规则加载器未初始化"}
    except Exception as e:
        checks["dynamic_rules"] = {"status": "error", "message": f"动态规则检查失败: {str(e)}"}
        # 动态规则失败不影响就绪状态（可以回退到静态规则）

    # 4. 检查会话管理器状态
    try:
        if session_manager:
            checks["session_manager"] = {"status": "ok", "message": "会话管理器正常"}
        else:
            checks["session_manager"] = {"status": "error", "message": "会话管理器未初始化"}
            is_ready = False
    except Exception as e:
        checks["session_manager"] = {"status": "error", "message": f"会话管理器检查失败: {str(e)}"}
        is_ready = False

    # 5. 检查文件处理器（可选）
    try:
        if file_processor:
            checks["file_processor"] = {"status": "ok", "message": "文件处理器正常"}
        else:
            checks["file_processor"] = {"status": "warning", "message": "文件处理器未初始化"}
    except Exception as e:
        checks["file_processor"] = {"status": "warning", "message": f"文件处理器检查失败: {str(e)}"}

    # 构建响应
    response = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }

    # 如果不就绪，返回503状态码
    if not is_ready:
        return Response(
            content=json.dumps(response, ensure_ascii=False, indent=2), status_code=503, media_type="application/json"
        )

    return response


# ==================== 用户隔离 API ====================


@app.get("/api/user/{user_id}/sessions")
async def get_user_sessions(user_id: str, limit: int = 10):
    """
    获取用户的所有会话

    v3.9新增：用户会话隔离
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        sessions = await manager.get_user_sessions(user_id, limit)
        return {"user_id": user_id, "sessions": sessions, "count": len(sessions)}
    except Exception as e:
        return {"error": str(e), "sessions": []}


@app.get("/api/user/{user_id}/progress")
async def get_user_all_progress(user_id: str):
    """
    获取用户所有会话的进度

    v3.9新增：用户独立进度
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        progress_list = await manager.get_all_user_progress(user_id)
        return {"user_id": user_id, "progress": progress_list}
    except Exception as e:
        return {"error": str(e), "progress": []}


@app.get("/api/user/{user_id}/quota")
async def get_user_quota(user_id: str):
    """
    获取用户配额信息

    v3.9新增：用户配额管理
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        quota = await manager.check_user_quota(user_id)
        usage = await manager.get_user_usage(user_id)
        return {**quota, **usage}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/user/{user_id}/active")
async def get_user_active_session(user_id: str):
    """
    获取用户当前活跃会话

    v3.9新增：快速获取用户正在进行的分析
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        active_session_id = await manager.get_user_active_session(user_id)

        if active_session_id:
            progress = await manager.get_progress(user_id, active_session_id)
            return {
                "user_id": user_id,
                "active_session_id": active_session_id,
                "progress": progress.to_dict() if progress else None,
            }

        return {"user_id": user_id, "active_session_id": None, "message": "没有活跃会话"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/sessions")
async def debug_sessions():
    """调试：列出所有活跃会话"""
    all_sessions = await session_manager.get_all_sessions()
    return {
        "active_sessions": [s["session_id"] for s in all_sessions],
        "session_details": {
            s["session_id"]: {
                "status": s.get("status"),
                "current_node": s.get("current_node"),
                "has_interrupt": s.get("interrupt_data") is not None,
            }
            for s in all_sessions
        },
    }


@app.get("/api/debug/redis")
async def check_redis_status():
    """
    调试：检查Redis连接状态和配置

    v3.6新增：用于诊断会话历史不稳定问题
    """
    try:
        if session_manager._memory_mode:
            return {
                "mode": "memory",
                "status": "fallback",
                "warning": "Redis不可用，使用内存模式（数据不持久化）",
                "sessions_in_memory": len(session_manager._memory_sessions),
                "redis_url": session_manager.redis_url,
                "ttl": session_manager.SESSION_TTL,
            }

        # 测试Redis连接
        await session_manager.redis_client.ping()
        session_keys = await session_manager.list_all_sessions()

        # 获取Redis配置
        redis_info = await session_manager.redis_client.info("persistence")

        return {
            "mode": "redis",
            "status": "connected",
            "redis_url": session_manager.redis_url,
            "session_count": len(session_keys),
            "session_ttl": f"{session_manager.SESSION_TTL}秒 ({session_manager.SESSION_TTL // 3600}小时)",
            "persistence": {
                "rdb_enabled": redis_info.get("rdb_bgsave_in_progress", "unknown"),
                "aof_enabled": redis_info.get("aof_enabled", "unknown"),
                "last_save_time": redis_info.get("rdb_last_save_time", "unknown"),
            },
            "recommendation": "✅ Redis已连接，会话数据持久化存储"
            if redis_info.get("aof_enabled") == "1"
            else "⚠️ 建议启用AOF持久化以防止数据丢失",
        }
    except Exception as e:
        return {"mode": "error", "status": "failed", "error": str(e), "recommendation": "❌ Redis连接失败，请检查Redis服务是否运行"}


@app.post("/api/analysis/start", response_model=SessionResponse)
async def start_analysis(
    request: Request,  # 🌍 用于IP采集
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(optional_auth),  # 🆕 可选JWT认证
):
    """
    开始分析（仅 Dynamic Mode）

    创建新的分析会话并在后台执行工作流

    🆕 v7.39: 支持 analysis_mode 参数
    - normal: 普通模式，集中生成2-3张概念图
    - deep_thinking: 深度思考模式，每个专家都生成对应的概念图

    🆕 v7.130: 支持JWT认证获取真实WordPress用户信息
    """
    print(f"\n📥 收到分析请求")
    print(f"用户输入: {analysis_request.user_input[:100]}...")
    print(f"分析模式: {analysis_request.analysis_mode}")  # 🆕 v7.39

    # 🆕 v7.131: 完全依赖JWT认证，忽略前端传入的user_id
    # 这样可以防止前端伪造用户身份，确保会话管理显示正确的用户
    actual_user_id = "guest"  # 默认未认证用户
    username = None
    display_name = None

    # 🌍 采集IP地址和地理位置
    geoip_service = get_geoip_service()
    client_ip = geoip_service.get_client_ip(request)
    location_info = geoip_service.get_location(client_ip)

    logger.info(f"🌍 客户端IP: {client_ip} -> {location_info.get('country')}/{location_info.get('city')}")

    if current_user:
        # 用户已通过JWT认证，使用JWT中的用户信息（优先 sub 作为用户名）
        resolved_username = current_user.get("sub") or current_user.get("username")
        actual_user_id = resolved_username or str(current_user.get("user_id", "guest"))
        username = resolved_username
        display_name = current_user.get("name") or current_user.get("display_name") or username
        logger.info(f"✅ JWT认证用户: {username} ({display_name})")
    else:
        # 未认证用户，使用guest标识
        logger.info(f"ℹ️ 未认证访客用户，使用ID: guest")

    # 📊 v7.110: 添加模式使用统计日志
    logger.info(f"📊 [模式统计] 用户 {actual_user_id} " f"选择 {analysis_request.analysis_mode} 模式")

    print(f"运行模式: Dynamic Mode")

    # 输入守卫：空字符串直接拒绝（避免创建无意义会话）
    if not analysis_request.user_input or not analysis_request.user_input.strip():
        raise HTTPException(status_code=400, detail="requirement/user_input 不能为空")

    sm = await _get_session_manager()

    # 生成会话 ID（使用真实用户标识）
    session_id = f"{actual_user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    print(f"生成 Session ID: {session_id}")

    # ✅ 使用 Redis 创建会话
    session_data = {
        "session_id": session_id,
        "user_id": actual_user_id,  # 🆕 v7.130: 真实用户ID
        "user_input": analysis_request.user_input,
        "mode": "dynamic",
        "analysis_mode": analysis_request.analysis_mode,  # 🆕 v7.39: 分析模式
        "status": "initializing",
        "progress": 0.0,
        "events": [],
        "interrupt_data": None,
        "current_node": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "metadata": {  # 🌍 添加元数据
            "client_ip": client_ip,
            "location": location_info.get("city", "未知"),
            "geo_info": location_info,
            "user_agent": request.headers.get("User-Agent", ""),
        },
    }

    # 🆕 v7.130: 添加用户详细信息（如果有JWT认证）
    if username:
        session_data["username"] = username
    if display_name:
        session_data["display_name"] = display_name

    await sm.create(session_id, session_data)

    # 🔥 v7.120 P1: 使缓存失效
    sessions_cache.invalidate(f"sessions:{actual_user_id}")

    print(f"✅ 会话状态已初始化（Redis）")

    # 在后台执行工作流
    print(f"📤 添加后台任务...")
    background_tasks.add_task(run_workflow_async, session_id, analysis_request.user_input)

    print(f"✅ 后台任务已添加，返回响应\n")

    return SessionResponse(session_id=session_id, status="pending", message="分析已开始，请使用 session_id 查询状态")


@app.post("/api/analysis/start-with-files", response_model=SessionResponse)
async def start_analysis_with_files(
    background_tasks: BackgroundTasks,  # 🔥 修复：移到前面，移除默认值
    user_input: str = Form(default=""),
    requirement: str = Form(default=""),  # 兼容旧前端字段名
    user_id: str = Form(default="web_user"),
    analysis_mode: str = Form(default="normal"),  # 🆕 v7.39: 分析模式
    files: List[UploadFile] = File(default=[]),
    current_user: Optional[dict] = Depends(optional_auth),  # 🆕 v7.130: 可选JWT认证
):
    """
    🆕 v3.7: 支持多模态输入的分析接口

    接受文本 + 多个文件（PDF, TXT, 图片）

    🆕 v7.39: 支持 analysis_mode 参数
    - normal: 普通模式，集中生成2-3张概念图
    - deep_thinking: 深度思考模式，每个专家都生成对应的概念图

    Args:
        user_input: 用户输入的文本描述
        user_id: 用户ID
        analysis_mode: 分析模式 (normal/deep_thinking)
        files: 上传的文件列表
        background_tasks: 后台任务管理器

    Returns:
        会话响应
    """
    logger.info(f"\n📥 收到多模态分析请求")
    logger.info(f"用户输入: {user_input[:100] if user_input else '(无文本)'}...")
    logger.info(f"分析模式: {analysis_mode}")  # 🆕 v7.39
    logger.info(f"文件数量: {len(files)}")

    # 🆕 v7.131: 完全依赖JWT认证，忽略前端传入的user_id
    actual_user_id = "guest"  # 默认未认证用户
    username = None
    display_name = None

    if current_user:
        resolved_username = current_user.get("sub") or current_user.get("username")
        actual_user_id = resolved_username or str(current_user.get("user_id", "guest"))
        username = resolved_username
        display_name = current_user.get("name") or current_user.get("display_name") or username
        logger.info(f"✅ JWT认证用户: {username} ({display_name})")
    else:
        logger.info(f"ℹ️ 未认证访客用户，使用ID: guest")

    # 1. 验证输入
    if not user_input.strip() and not files:
        raise HTTPException(status_code=400, detail="请提供文本输入或上传文件")

    # 2. 生成会话 ID（使用真实用户标识）
    session_id = f"{actual_user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    logger.info(f"生成 Session ID: {session_id}")

    # 3. 保存并处理文件
    file_contents = []
    attachment_metadata = []

    for file in files:
        try:
            # 验证文件大小 (10MB限制)
            content = await file.read()
            file_size = len(content)

            if file_size > 10 * 1024 * 1024:
                logger.warning(f"⚠️ 文件过大，跳过: {file.filename} ({file_size} bytes)")
                continue

            # 保存文件
            file_path = await file_processor.save_file(
                file_content=content, filename=file.filename, session_id=session_id
            )

            # 提取内容
            extracted_content = await file_processor.extract_content(
                file_path=file_path, content_type=file.content_type
            )
            file_contents.append(extracted_content)

            # 保存元数据
            attachment_metadata.append(
                {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": file_size,
                    "path": str(file_path),
                    "extracted_summary": extracted_content.get("summary", ""),
                    "extraction_error": extracted_content.get("error", None),
                }
            )

            logger.info(f"✅ 文件处理完成: {file.filename} - {extracted_content.get('summary', '')}")

        except Exception as e:
            logger.error(f"❌ 文件处理失败: {file.filename} - {str(e)}")
            attachment_metadata.append({"filename": file.filename, "content_type": file.content_type, "error": str(e)})

    # 4. 合并用户输入和文件内容
    # 兼容：如果前端传的是 requirement 字段，则映射到 user_input
    effective_user_input = user_input or requirement
    if not effective_user_input and not files:
        raise HTTPException(status_code=400, detail="user_input/requirement 或 files 至少提供一个")

    combined_input = build_combined_input(effective_user_input, file_contents)

    logger.info(f"✅ 内容合并完成: 最终输入长度 {len(combined_input)} 字符")

    # 5. 创建会话（增强状态）
    sm = await _get_session_manager()
    session_data = {
        "session_id": session_id,
        "user_id": actual_user_id,  # 🆕 v7.130: 真实用户ID
        "user_input": effective_user_input,  # 原始文本
        "combined_input": combined_input,  # 🔥 合并后的输入
        "attachments": attachment_metadata,  # 🔥 附件元数据
        "mode": "dynamic",
        "analysis_mode": analysis_mode,  # 🆕 v7.39: 分析模式
        "status": "initializing",
        "progress": 0.0,
        "events": [],
        "interrupt_data": None,
        "current_node": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }

    # 🆕 v7.130: 添加用户详细信息（如果有JWT认证）
    if username:
        session_data["username"] = username
    if display_name:
        session_data["display_name"] = display_name

    await sm.create(session_id, session_data)

    logger.info(f"✅ 会话状态已初始化（Redis + 文件）")

    # 6. 启动工作流（传入 combined_input）
    background_tasks.add_task(run_workflow_async, session_id, combined_input)  # 🔥 使用增强后的输入

    logger.info(f"✅ 后台任务已添加\n")

    return SessionResponse(session_id=session_id, status="pending", message=f"分析已开始，已接收 {len(files)} 个文件")


@app.get("/api/analysis/status/{session_id}", response_model=AnalysisStatus)
async def get_analysis_status(
    session_id: str,
    extend_ttl: bool = False,
    include_history: bool = Query(False, description="是否包含完整history（影响性能）"),  # 🔥 v7.120 P1
):
    """
    获取分析状态

    查询指定会话的当前状态和进度

    Args:
        session_id: 会话ID
        extend_ttl: 是否延长TTL（默认False，避免频繁轮询时过度续期）
        include_history: 是否包含完整history（默认False，减少序列化开销）🔥 v7.120 P1优化

    🔥 v7.120 P1优化: 默认不返回history字段，预期性能提升: 2.03s→0.5s
    """
    # ✅ 使用 Redis 读取会话
    sm = await _get_session_manager()
    session = await sm.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # ✅ Fix 2.5: 仅在明确请求时才续期TTL（减少95% Redis负载）
    if extend_ttl:
        await sm.extend_ttl(session_id)

    # 🆕 v7.119: 检查 waiting_for_input 状态的超时
    if session["status"] == "waiting_for_input":
        import time

        interrupt_timestamp = session.get("interrupt_timestamp")
        if interrupt_timestamp:
            elapsed_minutes = (time.time() - interrupt_timestamp) / 60

            # 超过15分钟发送WebSocket提醒
            if elapsed_minutes > 15 and not session.get("timeout_reminder_sent"):
                logger.warning(f"⏰ Session {session_id} 等待用户输入已超过15分钟")
                await broadcast_to_websockets(
                    session_id,
                    {
                        "type": "status_update",
                        "status": "waiting_for_input",
                        "message": "⚠️ 系统已等待您的确认超过15分钟，请及时响应",
                        "detail": "超时提醒",
                    },
                )
                await sm.update(session_id, {"timeout_reminder_sent": True})

            # 超过30分钟自动标记为timeout
            if elapsed_minutes > 30:
                logger.error(f"❌ Session {session_id} 等待用户输入超时（30分钟）")
                await sm.update(session_id, {"status": "timeout", "error": "用户未在30分钟内响应，会话已超时", "detail": "会话超时"})
                session["status"] = "timeout"
                session["error"] = "用户未在30分钟内响应，会话已超时"

    return AnalysisStatus(
        session_id=session_id,
        status=session["status"],
        current_stage=session.get("current_node"),
        detail=session.get("detail"),  # 🔥 新增：返回详细信息
        progress=session["progress"],
        history=session.get("history", []) if include_history else [],  # 🔥 v7.120 P1: 按需返回
        interrupt_data=session.get("interrupt_data"),
        error=session.get("error"),
        traceback=session.get("traceback"),  # 返回traceback用于调试
        rejection_message=session.get("rejection_message"),  # 🆕 返回拒绝提示
        user_input=session.get("user_input"),  # 🔥 v7.37.7: 返回用户原始输入
    )


@app.post("/api/analysis/resume", response_model=SessionResponse)
async def resume_analysis(request: ResumeRequest, background_tasks: BackgroundTasks):
    """
    恢复分析

    在 interrupt 后提供用户输入并继续执行
    """
    session_id = request.session_id

    sm = await _get_session_manager()

    # ✅ 获取活跃会话列表
    active_sessions = await sm.list_all_sessions()

    logger.info(f"📨 收到 resume 请求: session_id={session_id}")
    logger.info(f"   resume_value: {request.resume_value}")
    logger.info(f"   当前活跃会话: {active_sessions}")

    # ✅ 检查会话是否存在
    session = await sm.get(session_id)
    if not session:
        logger.error(f"❌ 会话不存在: {session_id}")
        logger.error(f"   可用会话: {active_sessions}")
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    # 兼容：历史数据/旧实现可能使用 interrupted 表示等待用户输入
    if session.get("status") not in {"waiting_for_input", "interrupted"}:
        raise HTTPException(status_code=400, detail=f"会话状态不正确: {session.get('status')}")

    # 获取工作流
    workflow = workflows.get(session_id)
    if not workflow:
        logger.error(f"❌ 工作流实例不存在: {session_id}")
        logger.error(f"   这通常发生在服务器重启后，工作流无法继续")
        logger.error(f"   建议：使用持久化的检查点存储（如SqliteSaver）而非MemorySaver")

        # 🔧 DEV_MODE：测试/本地调试时，不用 410 直接阻塞（单测只关注 API 是否可用）
        if DEV_MODE:
            # DEV_MODE 下尽量不依赖 Redis 分布式锁更新（测试环境 mock redis_client 不一定支持 Lock）
            try:
                await sm.update(session_id, {"status": "running", "interrupt_data": None})
            except Exception:
                pass
            return SessionResponse(
                session_id=session_id, status="processing", message="恢复请求已接收（DEV_MODE 下跳过 workflow 实例校验）"
            )

        raise HTTPException(
            status_code=410, detail="工作流已失效，请重新开始分析。如果问题持续出现，请联系管理员。"  # 410 Gone - resource no longer available
        )

    # 更新状态
    logger.debug(f"[DEBUG] Resume request for session {session_id}")
    logger.debug(f"[DEBUG] resume_value type: {type(request.resume_value)}")
    logger.debug(f"[DEBUG] resume_value content: {request.resume_value}")

    # 🔥 v7.119: 立即更新 Redis 状态为 running，清除超时相关字段
    await sm.update(
        session_id,
        {
            "status": "running",
            "interrupt_data": None,
            "interrupt_timestamp": None,  # 清除超时时间戳
            "timeout_reminder_sent": None,  # 清除提醒标记
        },
    )

    # 更新本地 session 对象（虽然 continue_workflow 使用的是闭包中的 session，但为了保险起见）
    session["status"] = "running"
    session["interrupt_data"] = None

    # 继续执行工作流
    async def continue_workflow():
        # 🆕 导入GraphRecursionError
        from langgraph.errors import GraphRecursionError

        try:
            config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}  # 增加递归限制，默认是25

            logger.info(f"[DEBUG] Resuming workflow with Command(resume={request.resume_value})")

            # 使用 Command(resume) 继续执行
            # 不指定 stream_mode，使用默认模式以正确接收 __interrupt__
            async for chunk in workflow.graph.astream(Command(resume=request.resume_value), config):
                logger.debug(f"[DEBUG] Resume stream chunk keys: {chunk.keys()}")

                # 🔥 更新当前节点和详细信息
                for node_name, node_output in chunk.items():
                    if node_name != "__interrupt__":
                        session["current_node"] = node_name
                        detail = ""
                        if isinstance(node_output, dict):
                            if "current_stage" in node_output:
                                detail = node_output["current_stage"]
                            elif "status" in node_output:
                                detail = node_output["status"]
                        session["detail"] = detail
                        logger.debug(f"[PROGRESS] 节点: {node_name}, 详情: {detail}")

                session["events"].append(chunk)
                # 🎯 v7.21: 节点映射与 main_workflow.py 对齐
                current_node = session.get("current_node", "")
                node_progress_map = {
                    "unified_input_validator_initial": 0.05,
                    "unified_input_validator_secondary": 0.10,
                    "requirements_analyst": 0.15,
                    "feasibility_analyst": 0.20,
                    "calibration_questionnaire": 0.25,
                    "requirements_confirmation": 0.35,
                    "project_director": 0.40,
                    "role_task_unified_review": 0.45,
                    "quality_preflight": 0.50,
                    "batch_executor": 0.55,
                    "agent_executor": 0.70,
                    "batch_aggregator": 0.75,
                    "batch_router": 0.76,
                    "batch_strategy_review": 0.78,
                    "detect_challenges": 0.80,
                    "analysis_review": 0.85,
                    "result_aggregator": 0.90,
                    "report_guard": 0.95,
                    "pdf_generator": 0.98,
                }
                session["progress"] = node_progress_map.get(current_node, min(0.9, len(session["events"]) * 0.1))

                # 🔄 确保 Redis 和 WebSocket 原子性同步
                # 1. 先更新 Redis
                await session_manager.update(
                    session_id,
                    {
                        "status": session["status"],
                        "progress": session["progress"],
                        "current_node": current_node,
                        "detail": session.get("detail"),
                        "events": session["events"],
                    },
                )

                # 2. 基于最新 Redis 数据广播 WebSocket
                updated_session = await session_manager.get(session_id)
                if updated_session:
                    await broadcast_to_websockets(
                        request.session_id,
                        {
                            "type": "status_update",
                            "status": updated_session["status"],
                            "progress": updated_session["progress"],
                            "current_node": updated_session.get("current_node"),
                            "detail": updated_session.get("detail"),
                        },
                    )

                # 检查是否又有 interrupt - interrupt 作为独立的 chunk 返回
                if "__interrupt__" in chunk:
                    # 提取 interrupt 数据
                    interrupt_tuple = chunk["__interrupt__"]
                    # interrupt_tuple 是一个元组，第一个元素是 Interrupt 对象
                    if interrupt_tuple:
                        interrupt_obj = interrupt_tuple[0] if isinstance(interrupt_tuple, tuple) else interrupt_tuple

                        # 提取 interrupt 的 value
                        interrupt_value = None
                        if hasattr(interrupt_obj, "value"):
                            interrupt_value = interrupt_obj.value
                        else:
                            interrupt_value = interrupt_obj

                        session["status"] = "waiting_for_input"
                        session["interrupt_data"] = interrupt_value
                        session["current_node"] = "interrupt"

                        # 🔥 广播 interrupt 到 WebSocket
                        await broadcast_to_websockets(
                            request.session_id,
                            {"type": "interrupt", "status": "waiting_for_input", "interrupt_data": interrupt_value},
                        )

                        # 🔥 更新 Redis 中的 interrupt 状态
                        await session_manager.update(
                            session_id,
                            {
                                "status": "waiting_for_input",
                                "interrupt_data": interrupt_value,
                                "current_node": "interrupt",
                            },
                        )

                        logger.info(
                            f"📡 已广播第二个 interrupt 到 WebSocket: {interrupt_value.get('interaction_type', 'unknown') if isinstance(interrupt_value, dict) else type(interrupt_value)}"
                        )
                        return

            # 检查是否有节点错误
            has_error = False
            error_message = None
            for event in session["events"]:
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if node_output.get("error") or node_output.get("status") == "error":
                            has_error = True
                            error_message = node_output.get("error", f"节点 {node_name} 执行失败")
                            break
                if has_error:
                    break

            # 根据是否有错误设置状态
            if has_error:
                session["status"] = "failed"
                session["error"] = error_message
                logger.error(f"工作流失败: {error_message}")

                # 🔥 广播失败状态到 WebSocket
                await broadcast_to_websockets(
                    request.session_id, {"type": "status", "status": "failed", "message": error_message}
                )

                # 🔥 更新 Redis 失败状态
                await session_manager.update(session_id, {"status": "failed", "error": error_message})
            else:
                session["status"] = "completed"
                session["progress"] = 1.0

                # 提取最终报告
                final_report = None
                for event in session["events"]:
                    for node_name, node_output in event.items():
                        if isinstance(node_output, dict) and "final_report" in node_output:
                            final_report = node_output["final_report"]
                            break

                session["final_report"] = final_report or "分析完成"

                # 🔥 广播完成状态到 WebSocket
                await broadcast_to_websockets(
                    request.session_id,
                    {
                        "type": "status",
                        "status": "completed",
                        "progress": 1.0,
                        "message": "分析完成",
                        "final_report": session.get("final_report"),
                    },
                )

                # 🔥 更新 Redis 完成状态
                await session_manager.update(
                    session_id, {"status": "completed", "progress": 1.0, "final_report": session.get("final_report")}
                )

                # 🆕 v3.6新增: 自动归档完成的会话（永久保存）
                if archive_manager:
                    try:
                        # 获取完整会话数据
                        final_session = await session_manager.get(session_id)
                        if final_session:
                            await archive_manager.archive_session(
                                session_id=session_id, session_data=final_session, force=False
                            )
                            logger.info(f"📦 会话已自动归档（永久保存）: {session_id}")
                    except Exception as archive_error:
                        logger.warning(f"⚠️ 自动归档失败（不影响主流程）: {archive_error}")

                logger.info(f"📡 已广播完成状态到 WebSocket: {request.session_id}")

        # 🆕 处理递归限制错误
        except GraphRecursionError as e:
            logger.warning(f"⚠️ Resume时达到递归限制！会话: {session_id}")
            logger.info("📦 尝试获取最佳结果...")

            try:
                current_state = workflow.graph.get_state(config)
                state_values = current_state.values

                best_result = state_values.get("best_result")
                if best_result:
                    logger.info(f"✅ 找到最佳结果（评分{state_values.get('best_score', 0):.1f}）")
                    state_values["agent_results"] = best_result
                else:
                    logger.warning("⚠️ 未找到最佳结果，使用当前结果")

                session["status"] = "completed"
                session["progress"] = 1.0
                session["final_report"] = "分析已完成（达到递归限制）"

                # 🔥 广播完成状态到 WebSocket
                await broadcast_to_websockets(
                    session_id, {"type": "status", "status": "completed", "progress": 1.0, "message": "分析已完成（达到递归限制）"}
                )
                logger.info(f"📡 已广播完成状态到 WebSocket (递归限制): {session_id}")
                session["metadata"] = {"forced_completion": True, "best_score": state_values.get("best_score", 0)}

            except Exception as state_error:
                logger.error(f"❌ 获取状态失败: {state_error}")
                session["status"] = "failed"
                session["error"] = f"达到递归限制: {str(e)}"

        except Exception as e:
            session["status"] = "failed"
            session["error"] = str(e)
            import traceback

            session["traceback"] = traceback.format_exc()
            logger.error(f"[ERROR] Resume workflow failed: {e}")
            logger.error(f"[ERROR] Traceback:\n{traceback.format_exc()}")

    background_tasks.add_task(continue_workflow)

    return SessionResponse(session_id=session_id, status="resumed", message="分析已恢复")


@app.post("/api/analysis/followup", response_model=SessionResponse)
async def submit_followup_question(
    session_id: str = Form(...),
    question: str = Form(...),
    requires_analysis: bool = Form(True),
    image: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    提交追问（支持持续对话 + 图片上传）

    🔥 v3.11 重大改造：
    - 不再创建新会话，在原会话上追加对话历史
    - 支持无限轮次的连续追问
    - 支持"记忆全部"模式（智能上下文管理）
    - 对话历史持久化到Redis

    🔥 v7.108 新增：
    - 支持图片上传（multipart/form-data）
    - 图片永久保存到 data/followup_images/{session_id}/
    - 自动生成缩略图（400px）
    - 集成 Vision API 分析图片内容

    与 /api/analysis/resume 的区别:
    - resume: 用于 waiting_for_input 状态的中断恢复
    - followup: 用于 completed 状态的后续追问
    """
    logger.info(f"📨 收到追问请求: session_id={session_id}")
    logger.info(f"   问题: {question}")
    logger.info(f"   需要分析: {requires_analysis}")
    logger.info(f"   包含图片: {image is not None}")

    # 检查会话是否存在
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    # 允许 completed 状态的会话进行追问
    if session["status"] not in ["completed", "waiting_for_input"]:
        raise HTTPException(status_code=400, detail=f"无法追问，会话状态: {session['status']}（只能对已完成或等待输入的会话追问）")

    # 🔥 关键改变：不创建新会话，直接在原会话上追问
    logger.info(f"🔥 在原会话上追问（不创建新会话）")

    # 🔥 使用后台任务处理追问
    async def handle_followup():
        try:
            # 更新会话状态
            await session_manager.update(session_id, {"status": "processing_followup", "detail": "正在思考回答..."})

            # 🔥 获取追问历史
            history_data = await followup_history_manager.get_history(session_id, limit=None)  # 获取全部
            next_turn_id = len(history_data) + 1
            logger.info(f"📚 当前对话历史: {len(history_data)} 轮")

            # 🔥 v7.108: 处理图片上传（如果有）
            image_metadata = None
            enhanced_question = question

            if image is not None:
                try:
                    from pathlib import Path

                    from intelligent_project_analyzer.services.file_processor import FileProcessor
                    from intelligent_project_analyzer.services.followup_image_storage_manager import (
                        FollowupImageStorageManager,
                    )

                    logger.info(f"📷 开始处理图片: {image.filename}")

                    # 保存图片（原图 + 缩略图）
                    image_metadata = await FollowupImageStorageManager.save_image(
                        image_file=image, session_id=session_id, turn_id=next_turn_id
                    )
                    logger.info(f"✅ 图片已保存: {image_metadata['stored_filename']}")

                    # Vision API 分析（使用 FileProcessor）
                    try:
                        file_processor = FileProcessor(enable_vision_api=True)
                        image_path = Path(f"data/followup_images/{session_id}/{image_metadata['stored_filename']}")

                        vision_result = await file_processor._extract_image(image_path)
                        vision_analysis = (
                            vision_result.get("text", "").split("## AI视觉分析")[-1].strip()
                            if "## AI视觉分析" in vision_result.get("text", "")
                            else ""
                        )

                        image_metadata["vision_analysis"] = vision_analysis
                        logger.info(f"✅ Vision API 分析完成: {len(vision_analysis)} 字符")

                    except Exception as e:
                        logger.warning(f"⚠️ Vision API 分析失败: {e}")
                        image_metadata["vision_analysis"] = ""

                    # 增强问题文本（拼接 Vision 分析）
                    if image_metadata.get("vision_analysis"):
                        enhanced_question = f"""{question}

[图片: {image_metadata['original_filename']}]
AI分析: {image_metadata['vision_analysis']}
"""

                except Exception as e:
                    logger.error(f"❌ 图片处理失败: {e}")
                    import traceback

                    traceback.print_exc()
                    # 不阻塞追问，继续处理

            # 🔥 v7.15: 使用 FollowupAgent (LangGraph)
            agent = FollowupAgent()

            # 构建上下文
            parent_session = await session_manager.get(session_id)
            aggregated_results = parent_session.get("aggregated_results", {})
            agent_results = parent_session.get("agent_results", {})
            structured_requirements = parent_session.get("structured_requirements", {})
            original_input = parent_session.get("user_input", "")

            # 如果没有结构化数据，尝试从 final_report 解析
            final_report = parent_session.get("final_report")
            if isinstance(final_report, dict) and not aggregated_results:
                aggregated_results = final_report

            # 🔥 v7.15: 构建 report_context (新格式)
            report_context = {
                "final_report": aggregated_results if isinstance(aggregated_results, dict) else {},
                "agent_results": agent_results if isinstance(agent_results, dict) else {},
                "requirements": structured_requirements if isinstance(structured_requirements, dict) else {},
                "user_input": original_input,
            }

            # 🔥 v7.15: 调用 FollowupAgent（使用增强后的问题）
            logger.info(f"🤖 调用 FollowupAgent (LangGraph)（历史轮次: {len(history_data)}）")
            result = await agent.answer_question_async(
                question=enhanced_question, report_context=report_context, conversation_history=history_data
            )

            answer = result.get("answer", "抱歉，我无法回答这个问题。")

            # 🔥 v7.60.5: 累加追问Token到会话metadata
            from intelligent_project_analyzer.utils.token_utils import extract_tokens_from_result, update_session_tokens

            token_data = extract_tokens_from_result(result)
            if token_data:
                success = await update_session_tokens(session_manager, session_id, token_data, agent_name="followup_qa")
                if success:
                    logger.info(f"✅ [追问Token] 已累加到会话 {session_id}")

            # 🔥 保存到追问历史（包含附件）
            attachments = []
            if image_metadata:
                attachments.append({"type": "image", **image_metadata})

            await followup_history_manager.add_turn(
                session_id=session_id,
                question=question,
                answer=answer,
                intent=result.get("intent", "general"),
                referenced_sections=result.get("references", []),
                attachments=attachments,
            )

            # 更新会话状态（保持completed状态）
            await session_manager.update(
                session_id, {"status": "completed", "detail": "追问回答完成", "last_followup_at": datetime.now().isoformat()}
            )

            # 🔥 通过WebSocket广播更新（前端实时显示）
            await broadcast_to_websockets(
                session_id,
                {
                    "type": "followup_answer",
                    "turn_id": next_turn_id,
                    "question": question,
                    "answer": answer,
                    "intent": result.get("intent", "general"),
                    "referenced_sections": result.get("references", []),
                    "attachments": attachments,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f"✅ 追问完成: {session_id}, 轮次={next_turn_id}")

        except Exception as e:
            logger.error(f"❌ 追问处理失败: {e}")
            import traceback

            traceback.print_exc()
            await session_manager.update(
                session_id, {"status": "completed", "detail": f"追问失败: {str(e)}"}  # 回到completed状态
            )

            # 广播错误
            await broadcast_to_websockets(session_id, {"type": "followup_error", "error": str(e)})

    # 添加后台任务
    background_tasks.add_task(handle_followup)

    return SessionResponse(session_id=session_id, status="processing", message="追问已提交，正在生成回答...")  # 🔥 返回原会话ID，不是新会话


@app.get("/api/analysis/result/{session_id}", response_model=AnalysisResult)
async def get_analysis_result(session_id: str):
    """
    获取分析结果

    获取已完成分析的完整结果
    """
    # ✅ 使用 Redis 获取会话
    sm = await _get_session_manager()
    session = await sm.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 兼容：不同版本的会话结构字段名可能不同
    results = session.get("results")
    agent_results = session.get("agent_results")
    final_report = session.get("final_report")
    final_result = session.get("final_result")

    return AnalysisResult(
        session_id=session_id,
        status=session["status"],
        results=results if results is not None else agent_results,
        final_report=final_report if final_report is not None else final_result,
        final_result=final_result,
        agent_results=agent_results,
    )


@app.get("/api/analysis/report/{session_id}", response_model=ReportResponse)
async def get_analysis_report(session_id: str):
    """
    获取分析报告（专门为前端设计的端点）

    返回格式化的报告内容，适配前端 AnalysisReport 类型
    """
    # ✅ 使用 Redis 获取会话
    sm = await _get_session_manager()
    session = await sm.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取报告文本路径
    pdf_path = session.get("pdf_path")
    report_text = ""

    # 如果有 PDF 路径，尝试读取对应的 txt 文件
    if pdf_path and os.path.exists(pdf_path):
        try:
            with open(pdf_path, "r", encoding="utf-8") as f:
                report_text = f.read()
        except Exception as e:
            logger.warning(f"⚠️ 无法读取报告文件: {e}")
            # 🔥 v7.52.5: 降级方案 - 不使用json.dumps，让FastAPI自动序列化
            # report_text 仅用于简短提示，实际数据在 structured_report 中
            report_text = "报告文件读取失败，请查看结构化数据"
    else:
        # 🔥 v7.52.5: 没有文件路径时，返回简短提示
        # structured_report 字段会包含完整数据，不需要json.dumps
        report_text = "请查看结构化报告内容"

    # ✅ 解析结构化报告数据
    structured_report = None
    final_report = session.get("final_report", {})

    if isinstance(final_report, dict) and final_report:
        try:
            # 🔥 Phase 1.4+ P4 & v7.0: 解析 core_answer（支持新旧两种格式）
            core_answer_data = None
            ca_raw = final_report.get("core_answer")
            if ca_raw and isinstance(ca_raw, dict):
                # 检测是否是 v7.0 格式（有 deliverable_answers 字段）
                if "deliverable_answers" in ca_raw:
                    # 🆕 v7.0 格式：直接传递整个结构
                    core_answer_data = ca_raw
                    deliverable_count = len(ca_raw.get("deliverable_answers", []))
                    logger.info(f"🎯 [v7.0] 解析到多交付物核心答案: {deliverable_count} 个交付物")
                else:
                    # 旧格式：转换为字典（保持向后兼容）
                    core_answer_data = {
                        "question": ca_raw.get("question", ""),
                        "answer": ca_raw.get("answer", ""),
                        "deliverables": ca_raw.get("deliverables", []),
                        "timeline": ca_raw.get("timeline", ""),
                        "budget_range": ca_raw.get("budget_range", ""),
                        # v7.0 向后兼容字段（为空）
                        "deliverable_answers": [],
                        "expert_support_chain": [],
                    }
                    logger.info(f"🎯 解析到核心答案（旧格式）: {ca_raw.get('answer', '')[:50]}...")

            # 解析 executive_summary
            exec_summary_data = final_report.get("executive_summary", {})
            exec_summary = ExecutiveSummaryResponse(
                project_overview=exec_summary_data.get("project_overview", ""),
                key_findings=exec_summary_data.get("key_findings", []),
                key_recommendations=exec_summary_data.get("key_recommendations", []),
                success_factors=exec_summary_data.get("success_factors", []),
            )

            # 解析 sections（支持数组和字典两种格式）
            sections_data = final_report.get("sections", {})
            sections = []

            # 🔥 修复：sections可能是dict（key=section_id）或list格式
            if isinstance(sections_data, dict):
                # 字典格式：{"requirements_analysis": {...}, "design_research": {...}}
                for section_id, section_content in sections_data.items():
                    if isinstance(section_content, dict):
                        # 🔥 v7.52.5: content可能是dict或string
                        # 如果是字典，提取主要文本内容，不使用json.dumps
                        content_val = section_content.get("content", "")
                        if isinstance(content_val, dict):
                            # 尝试提取主要文本字段，而不是JSON字符串
                            if "text" in content_val:
                                content_val = content_val["text"]
                            elif "content" in content_val:
                                content_val = content_val["content"]
                            else:
                                # 如果实在需要展示结构化内容，用简短描述
                                content_val = f"[结构化内容: {len(content_val)} 个字段]"

                        raw_confidence = section_content.get("confidence", 0.0)
                        try:
                            confidence_value = float(raw_confidence)
                        except (TypeError, ValueError):
                            confidence_value = 0.0

                        sections.append(
                            ReportSectionResponse(
                                section_id=section_id,
                                title=section_content.get("title", section_id),
                                content=str(content_val) if content_val else "",
                                confidence=confidence_value,
                            )
                        )
            elif isinstance(sections_data, list):
                # 数组格式：[{section_id, title, content, confidence}, ...]
                for s in sections_data:
                    if isinstance(s, dict):
                        # 🔥 v7.52.5: content可能是dict或string
                        # 如果是字典，提取主要文本内容，不使用json.dumps
                        content_val = s.get("content", "")
                        if isinstance(content_val, dict):
                            # 尝试提取主要文本字段，而不是JSON字符串
                            if "text" in content_val:
                                content_val = content_val["text"]
                            elif "content" in content_val:
                                content_val = content_val["content"]
                            else:
                                # 如果实在需要展示结构化内容，用简短描述
                                content_val = f"[结构化内容: {len(content_val)} 个字段]"

                        raw_confidence = s.get("confidence", 0.0)
                        try:
                            confidence_value = float(raw_confidence)
                        except (TypeError, ValueError):
                            confidence_value = 0.0

                        sections.append(
                            ReportSectionResponse(
                                section_id=s.get("section_id", ""),
                                title=s.get("title", ""),
                                content=str(content_val) if content_val else "",
                                confidence=confidence_value,
                            )
                        )

            # 使用智能体原始输出补全章节
            sections = _enrich_sections_with_agent_results(sections, session)

            # 解析 comprehensive_analysis（兼容字段名差异）
            comp_data = final_report.get("comprehensive_analysis", {})
            comp_analysis = ComprehensiveAnalysisResponse(
                cross_domain_insights=comp_data.get("cross_domain_insights", []),
                integrated_recommendations=comp_data.get("integrated_recommendations")
                or comp_data.get("integration_recommendations", []),
                risk_assessment=comp_data.get("risk_assessment", []),
                implementation_roadmap=comp_data.get("implementation_roadmap", []),
            )

            # 解析 conclusions（兼容 summary 和 project_analysis_summary）
            concl_data = final_report.get("conclusions", {})
            conclusions = ConclusionsResponse(
                project_analysis_summary=concl_data.get("project_analysis_summary") or concl_data.get("summary", ""),
                next_steps=concl_data.get("next_steps", []),
                success_metrics=concl_data.get("success_metrics", []),
            )

            # 解析 review_feedback
            review_feedback = None
            rf_data = final_report.get("review_feedback")
            if rf_data and isinstance(rf_data, dict):

                def parse_feedback_items(items_data):
                    items = []
                    for item in items_data or []:
                        if isinstance(item, dict):
                            items.append(
                                ReviewFeedbackItemResponse(
                                    issue_id=item.get("issue_id", ""),
                                    reviewer=item.get("reviewer", ""),
                                    issue_type=item.get("issue_type", ""),
                                    description=item.get("description", ""),
                                    response=item.get("response", ""),
                                    status=item.get("status", ""),
                                    priority=str(item.get("priority", "medium")),
                                )
                            )
                    return items

                review_feedback = ReviewFeedbackResponse(
                    red_team_challenges=parse_feedback_items(rf_data.get("red_team_challenges")),
                    blue_team_validations=parse_feedback_items(rf_data.get("blue_team_validations")),
                    judge_rulings=parse_feedback_items(rf_data.get("judge_rulings")),
                    client_decisions=parse_feedback_items(rf_data.get("client_decisions")),
                    iteration_summary=rf_data.get("iteration_summary", ""),
                )

            # 解析 review_visualization
            review_viz = None
            rv_data = final_report.get("review_visualization")
            if rv_data and isinstance(rv_data, dict):
                rounds = []
                for rd in rv_data.get("rounds", []):
                    if isinstance(rd, dict):
                        rounds.append(
                            ReviewRoundDataResponse(
                                round_number=rd.get("round_number", 0),
                                red_score=rd.get("red_score", 0),
                                blue_score=rd.get("blue_score", 0),
                                judge_score=rd.get("judge_score", 0),
                                issues_found=rd.get("issues_found", 0),
                                issues_resolved=rd.get("issues_resolved", 0),
                                timestamp=rd.get("timestamp", ""),
                            )
                        )
                review_viz = ReviewVisualizationResponse(
                    rounds=rounds,
                    final_decision=rv_data.get("final_decision", ""),
                    total_rounds=rv_data.get("total_rounds", 0),
                    improvement_rate=float(rv_data.get("improvement_rate", 0.0)),
                )

            # 🆕 解析 challenge_detection（从 session state 中获取）
            challenge_detection = None
            cd_data = session.get("challenge_detection")
            if cd_data and isinstance(cd_data, dict):
                challenges_list = []
                raw_challenges = cd_data.get("challenges", [])
                must_fix_count = 0
                should_fix_count = 0

                for ch in raw_challenges:
                    if isinstance(ch, dict):
                        severity = ch.get("severity", "should-fix")
                        if severity == "must-fix":
                            must_fix_count += 1
                        else:
                            should_fix_count += 1

                        challenges_list.append(
                            ChallengeItemResponse(
                                expert_id=ch.get("expert_id", ""),
                                expert_name=ch.get("expert_name", ch.get("expert_id", "")),
                                challenged_item=ch.get("challenged_item", ""),
                                challenge_type=ch.get("challenge_type", ""),
                                severity=severity,
                                rationale=ch.get("rationale", ""),
                                proposed_alternative=ch.get("proposed_alternative", ""),
                                design_impact=ch.get("design_impact", ""),
                                decision=ch.get("decision", ""),
                            )
                        )

                # 获取处理摘要
                handling_data = session.get("challenge_handling", {})
                handling_summary = handling_data.get("summary", "") if isinstance(handling_data, dict) else ""

                challenge_detection = ChallengeDetectionResponse(
                    has_challenges=cd_data.get("has_challenges", False),
                    total_count=len(challenges_list),
                    must_fix_count=must_fix_count,
                    should_fix_count=should_fix_count,
                    challenges=challenges_list,
                    handling_summary=handling_summary,
                )

                if challenges_list:
                    logger.info(f"🔍 挑战检测: {must_fix_count} must-fix, {should_fix_count} should-fix")

            # 🔥 修复：从 session.agent_results 提取 expert_reports（如果 final_report 里没有）
            expert_reports_data = final_report.get("expert_reports", {})
            if not expert_reports_data:
                # 从 agent_results 提取专家报告
                agent_results = session.get("agent_results", {})
                active_agents = session.get("active_agents", [])
                expert_reports_data = {}

                for role_id in active_agents:
                    # 跳过需求分析师和项目总监
                    if role_id in ["requirements_analyst", "project_director"]:
                        continue
                    # 只提取 V2-V6 专家的报告
                    if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_"]):
                        continue

                    agent_result = agent_results.get(role_id, {})
                    if agent_result:
                        structured_raw = agent_result.get("structured_data", {})
                        structured_data, validation_warnings = _sanitize_structured_data(structured_raw)
                        content = agent_result.get("content", "")

                        if structured_data and content:
                            payload = OrderedDict()
                            payload["structured_data"] = structured_data
                            payload["narrative_summary"] = content
                            if validation_warnings:
                                payload["validation_warnings"] = validation_warnings
                            expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                        elif structured_data:
                            if validation_warnings:
                                payload = OrderedDict()
                                payload["structured_data"] = structured_data
                                payload["validation_warnings"] = validation_warnings
                                expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                            else:
                                expert_reports_data[role_id] = json.dumps(structured_data, ensure_ascii=False, indent=2)
                        elif content:
                            if validation_warnings:
                                payload = OrderedDict()
                                payload["narrative_summary"] = content
                                payload["validation_warnings"] = validation_warnings
                                expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                            else:
                                expert_reports_data[role_id] = content
                        elif validation_warnings:
                            payload = OrderedDict()
                            payload["validation_warnings"] = validation_warnings
                            expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)

                if expert_reports_data:
                    logger.info(f"📊 从agent_results提取了 {len(expert_reports_data)} 个专家报告")

            # 🔥 修复：如果sections仍为空，从agent_results动态填充
            if not sections:
                agent_results = session.get("agent_results") or {}
                if agent_results:
                    active_agents = session.get("active_agents") or list(agent_results.keys())

                    section_contributions: Dict[str, OrderedDict] = {}
                    section_titles: Dict[str, str] = {}
                    section_confidences: Dict[str, List[float]] = defaultdict(list)
                    section_sequence: List[str] = []

                    for role_id in active_agents:
                        if role_id in ["requirements_analyst", "project_director"]:
                            continue

                        agent_result = agent_results.get(role_id) or {}
                        payload = _format_agent_payload(agent_result)
                        if not payload:
                            continue

                        section_id, section_title = _derive_section_identity(role_id, agent_result)
                        source_name = agent_result.get("display_name") or agent_result.get("role_name") or role_id

                        section_contributions.setdefault(section_id, OrderedDict())
                        section_contributions[section_id][source_name] = payload

                        if section_title:
                            section_titles.setdefault(section_id, section_title)

                        if section_id not in section_sequence:
                            section_sequence.append(section_id)

                        raw_confidence = agent_result.get("confidence")
                        try:
                            if raw_confidence is not None:
                                section_confidences[section_id].append(float(raw_confidence))
                        except (TypeError, ValueError):
                            logger.debug(f"⚠️ 无法解析 {role_id} 的置信度: {raw_confidence}")

                    for section_id in section_sequence:
                        payload = section_contributions.get(section_id)
                        if not payload:
                            continue

                        confidence_values = section_confidences.get(section_id, [])
                        if confidence_values:
                            confidence = max(confidence_values)
                        else:
                            confidence = 0.8

                        section_content = json.dumps(payload, ensure_ascii=False, indent=2)
                        sections.append(
                            ReportSectionResponse(
                                section_id=section_id,
                                title=section_titles.get(section_id, section_id),
                                content=section_content,
                                confidence=confidence,
                            )
                        )

                    if sections:
                        logger.info(f"📊 从agent_results动态填充了 {len(sections)} 个章节")

            # 🔥 Phase 1.4+ P3: 解析问卷回答数据
            questionnaire_data = None
            qr_raw = final_report.get("questionnaire_responses")
            if qr_raw and isinstance(qr_raw, dict):
                responses_list = []
                for resp_item in qr_raw.get("responses", []):
                    if isinstance(resp_item, dict):
                        responses_list.append(
                            QuestionnaireResponseItem(
                                question_id=resp_item.get("question_id", ""),
                                question=resp_item.get("question", ""),
                                answer=resp_item.get("answer", ""),
                                context=resp_item.get("context", ""),
                            )
                        )

                if responses_list:
                    questionnaire_data = QuestionnaireResponseData(
                        responses=responses_list,
                        timestamp=qr_raw.get("timestamp", ""),
                        analysis_insights=qr_raw.get("analysis_insights", ""),
                    )
                    logger.info(f"📝 解析到 {len(responses_list)} 条问卷回答")

            # 🔥 Phase 1.4+ v4.1: 解析洞察区块 - 已废弃（改用需求分析师的原始输出）
            insights_data = None
            # insights_raw = final_report.get("insights")
            # if insights_raw:
            #     # 支持 Pydantic 对象和 dict 两种格式
            #     if hasattr(insights_raw, 'model_dump'):
            #         insights_dict = insights_raw.model_dump()
            #     elif isinstance(insights_raw, dict):
            #         insights_dict = insights_raw
            #     else:
            #         insights_dict = {}
            #
            #     if insights_dict:
            #         insights_data = InsightsSectionResponse(
            #             key_insights=insights_dict.get("key_insights", []),
            #             cross_domain_connections=insights_dict.get("cross_domain_connections", []),
            #             user_needs_interpretation=insights_dict.get("user_needs_interpretation", "")
            #         )
            #         logger.info(f"💡 解析到洞察区块: {len(insights_data.key_insights)} 条关键洞察")

            # 🔥 Phase 1.4+ v4.1: 解析推敲过程
            deliberation_data = None
            deliberation_raw = final_report.get("deliberation_process")
            if deliberation_raw:
                if hasattr(deliberation_raw, "model_dump"):
                    deliberation_dict = deliberation_raw.model_dump()
                elif isinstance(deliberation_raw, dict):
                    deliberation_dict = deliberation_raw
                else:
                    deliberation_dict = {}

                if deliberation_dict:
                    deliberation_data = DeliberationProcessResponse(
                        inquiry_architecture=deliberation_dict.get("inquiry_architecture", ""),
                        reasoning=deliberation_dict.get("reasoning", ""),
                        role_selection=deliberation_dict.get("role_selection", []),
                        strategic_approach=deliberation_dict.get("strategic_approach", ""),
                    )
                    logger.info(f"🧠 解析到推敲过程: 架构={deliberation_data.inquiry_architecture}")

            # 🔥 Phase 1.4+ v4.1: 解析建议区块
            recommendations_data = None
            recommendations_raw = final_report.get("recommendations")
            if recommendations_raw:
                if hasattr(recommendations_raw, "model_dump"):
                    recommendations_dict = recommendations_raw.model_dump()
                elif isinstance(recommendations_raw, dict):
                    recommendations_dict = recommendations_raw
                else:
                    recommendations_dict = {}

                if recommendations_dict:
                    recommendations_data = RecommendationsSectionResponse(
                        immediate_actions=recommendations_dict.get("immediate_actions", []),
                        short_term_priorities=recommendations_dict.get("short_term_priorities", []),
                        long_term_strategy=recommendations_dict.get("long_term_strategy", []),
                        risk_mitigation=recommendations_dict.get("risk_mitigation", []),
                    )
                    logger.info(f"📋 解析到建议区块: {len(recommendations_data.immediate_actions)} 条立即行动")

            # 🆕 解析需求分析结果（需求分析师原始输出）
            # 🔥 修复：应从 final_report 读取，而不是从 session.structured_requirements
            requirements_analysis_data = None
            requirements_analysis_raw = final_report.get("requirements_analysis")

            # 尝试从 final_report 顶层获取
            if requirements_analysis_raw and isinstance(requirements_analysis_raw, dict):
                requirements_analysis_data = RequirementsAnalysisResponse(
                    project_overview=requirements_analysis_raw.get("project_overview", ""),
                    core_objectives=requirements_analysis_raw.get("core_objectives", []),
                    project_tasks=requirements_analysis_raw.get("project_tasks", []),
                    narrative_characters=requirements_analysis_raw.get("narrative_characters", []),
                    physical_contexts=requirements_analysis_raw.get("physical_contexts", []),
                    constraints_opportunities=requirements_analysis_raw.get("constraints_opportunities", {}),
                    # 🆕 传递用户修改标识
                    has_user_modifications=session.get("has_user_modifications", False),
                    user_modification_summary=session.get("user_modification_summary"),
                )
                logger.info(f"📊 解析到需求分析结果（从 final_report）: {len(requirements_analysis_data.core_objectives)} 个核心目标")
            else:
                # 🔥 备用方案1：从 sections 数组中查找（针对已有会话）
                sections_data = final_report.get("sections", [])
                logger.debug(
                    f"🔍 [DEBUG] sections_data type: {type(sections_data)}, length: {len(sections_data) if isinstance(sections_data, list) else 'N/A'}"
                )

                if isinstance(sections_data, list):
                    for section in sections_data:
                        if isinstance(section, dict):
                            section_id = section.get("section_id", "")
                            logger.debug(f"🔍 [DEBUG] Checking section: {section_id}")

                            if section_id == "requirements_analysis":
                                content_str = section.get("content", "")
                                logger.info(
                                    f"🎯 Found requirements_analysis in sections, content length: {len(content_str)}"
                                )

                                if content_str:
                                    try:
                                        # 解析 JSON 字符串
                                        req_data = (
                                            json.loads(content_str) if isinstance(content_str, str) else content_str
                                        )

                                        # 🔥 修复：正确映射 requirements_analyst 的实际输出字段
                                        # requirements_analyst 输出的是完整的结构化数据，包含多个字段
                                        logger.debug(f"🔍 [FIELD MAPPING] req_data keys: {list(req_data.keys())}")
                                        logger.debug(
                                            f"🔍 [FIELD MAPPING] project_task: '{req_data.get('project_task', '')}' (len={len(req_data.get('project_task', ''))})"
                                        )
                                        logger.debug(
                                            f"🔍 [FIELD MAPPING] character_narrative: (len={len(req_data.get('character_narrative', ''))})"
                                        )
                                        logger.debug(
                                            f"🔍 [FIELD MAPPING] physical_context: (len={len(req_data.get('physical_context', ''))})"
                                        )

                                        requirements_analysis_data = RequirementsAnalysisResponse(
                                            project_overview=req_data.get("project_overview")
                                            or req_data.get("project_task", ""),
                                            core_objectives=req_data.get("core_objectives", []),
                                            project_tasks=[req_data.get("project_task", "")]
                                            if req_data.get("project_task")
                                            else [],
                                            narrative_characters=[req_data.get("character_narrative", "")]
                                            if req_data.get("character_narrative")
                                            else [],
                                            physical_contexts=[req_data.get("physical_context", "")]
                                            if req_data.get("physical_context")
                                            else [],
                                            constraints_opportunities={
                                                "resource_constraints": req_data.get("resource_constraints", ""),
                                                "regulatory_requirements": req_data.get("regulatory_requirements", ""),
                                                "space_constraints": req_data.get("space_constraints", ""),
                                                "core_tension": req_data.get("core_tension", ""),
                                                "design_challenge": req_data.get("design_challenge", ""),
                                            },
                                            # 🆕 传递用户修改标识
                                            has_user_modifications=session.get("has_user_modifications", False),
                                            user_modification_summary=session.get("user_modification_summary"),
                                        )
                                        logger.info(
                                            f"📊 解析到需求分析结果（从 sections）: {len(requirements_analysis_data.core_objectives)} 个核心目标"
                                        )
                                        logger.debug(
                                            f"🔍 [FIELD MAPPING] project_tasks after mapping: {len(requirements_analysis_data.project_tasks)} items"
                                        )
                                        logger.debug(
                                            f"🔍 [FIELD MAPPING] narrative_characters after mapping: {len(requirements_analysis_data.narrative_characters)} items"
                                        )
                                        logger.debug(
                                            f"🔍 [FIELD MAPPING] physical_contexts after mapping: {len(requirements_analysis_data.physical_contexts)} items"
                                        )
                                        break
                                    except (json.JSONDecodeError, TypeError) as e:
                                        logger.warning(f"⚠️ 解析 sections 中的 requirements_analysis 失败: {e}")
                else:
                    logger.debug(f"🔍 [DEBUG] sections_data is not a list, type: {type(sections_data)}")

                # 🔥 备用方案2：如果以上都失败，尝试从 session.structured_requirements 读取（向后兼容）
                if not requirements_analysis_data:
                    structured_req = session.get("structured_requirements")
                    if structured_req and isinstance(structured_req, dict):
                        requirements_analysis_data = RequirementsAnalysisResponse(
                            project_overview=structured_req.get("project_overview", ""),
                            core_objectives=structured_req.get("core_objectives", []),
                            project_tasks=structured_req.get("project_tasks", []),
                            narrative_characters=structured_req.get("narrative_characters", []),
                            physical_contexts=structured_req.get("physical_contexts", []),
                            constraints_opportunities=structured_req.get("constraints_opportunities", {}),
                            # 🆕 传递用户修改标识
                            has_user_modifications=session.get("has_user_modifications", False),
                            user_modification_summary=session.get("user_modification_summary"),
                        )
                        logger.info(
                            f"📊 解析到需求分析结果（从 session.structured_requirements 备用）: {len(requirements_analysis_data.core_objectives)} 个核心目标"
                        )

            structured_report = StructuredReportResponse(
                inquiry_architecture=final_report.get("inquiry_architecture", ""),
                core_answer=core_answer_data,  # 🔥 添加核心答案
                insights=None,  # 🔥 已废弃：不再使用LLM综合洞察
                requirements_analysis=requirements_analysis_data,  # 🆕 添加需求分析结果（需求分析师原始输出）
                deliberation_process=deliberation_data,  # 🔥 Phase 1.4+ v4.1: 添加推敲过程
                recommendations=recommendations_data,  # 🔥 Phase 1.4+ v4.1: 添加建议
                executive_summary=exec_summary,
                sections=sections,
                comprehensive_analysis=comp_analysis,
                conclusions=conclusions,
                expert_reports=expert_reports_data,
                review_feedback=review_feedback,
                questionnaire_responses=questionnaire_data,  # 🔥 添加问卷数据
                review_visualization=review_viz,
                challenge_detection=challenge_detection,
                # 🆕 v7.4: 添加执行元数据汇总
                execution_metadata=final_report.get("metadata"),
                # 🆕 v3.0.26: 添加思维导图内容结构
                mindmap_content=final_report.get("mindmap_content"),
                # 普通模式概念图（集中生成）
                generated_images=final_report.get("generated_images"),
                image_prompts=final_report.get("image_prompts"),
                image_top_constraints=final_report.get("image_top_constraints"),
                # 🆕 v7.39: 添加专家概念图（深度思考模式）
                generated_images_by_expert=final_report.get("generated_images_by_expert"),
            )

            logger.info(f"✅ 成功解析结构化报告，包含 {len(sections)} 个章节")

        except Exception as e:
            logger.warning(f"⚠️ 解析结构化报告失败: {e}，将返回 None")
            structured_report = None

    # 获取用户原始输入
    user_input = session.get("user_input", "")

    return ReportResponse(
        session_id=session_id,
        report_text=report_text,
        report_pdf_path=pdf_path,
        created_at=session.get("created_at", datetime.now().isoformat()),
        user_input=user_input,
        structured_report=structured_report,
    )


# ========== PDF 下载端点 ==========


class PDFGenerator(FPDF):
    """支持中文的 PDF 生成器"""

    def __init__(self):
        super().__init__()
        self.chinese_font_loaded = False
        # 设置页面边距（左、上、右）- 先设置边距
        self.set_margins(left=25, top=25, right=25)
        self.set_auto_page_break(auto=True, margin=30)
        # 尝试加载中文字体
        self._load_chinese_font()

    def _load_chinese_font(self):
        """加载中文字体"""
        # 尝试多个常见的中文字体路径
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
            "/System/Library/Fonts/PingFang.ttc",  # macOS
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.add_font("Chinese", "", font_path, uni=True)
                    self.add_font("Chinese", "B", font_path, uni=True)
                    self.chinese_font_loaded = True
                    logger.info(f"✅ 成功加载中文字体: {font_path}")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ 加载字体失败 {font_path}: {e}")
                    continue

        logger.warning("⚠️ 未找到中文字体，使用内置字体")

    def _set_font_safe(self, style: str = "", size: int = 10):
        """安全设置字体"""
        if self.chinese_font_loaded:
            self.set_font("Chinese", style, size)
        else:
            self.set_font("Arial", style, size)

    def header(self):
        """页眉（留空）"""
        pass

    def footer(self):
        """页脚（已移除）"""
        pass

    def add_cover_page(self, title: str = "项目分析报告"):
        """添加封面页

        🔥 v7.26 整改:
        - 中英文靠近（不要空行）
        - 生成时间前加"极致概念"
        - 不要生成时间和冒号
        - 不要版本
        """
        self.add_page()

        # 封面标题 - 居中显示在页面中部偏上
        self.set_y(80)
        self._set_font_safe("B", 28)
        self.set_text_color(26, 26, 26)
        self.cell(0, 20, title, ln=True, align="C")

        # 副标题 - 🔥 v7.26: 中英文靠近（ln(10) → ln(3)）
        self.ln(3)
        self._set_font_safe("", 14)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "Intelligent Project Analyzer", ln=True, align="C")

        # 🔥 v7.26: "极致概念" + 日期（无冒号，无版本）
        self.ln(40)
        self._set_font_safe("", 11)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, f"极致概念 {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="C")

    def add_table_of_contents(self, chapters: list):
        """添加目录页

        Args:
            chapters: 章节列表，每项为 {"title": str, "page": int}
        """
        self.add_page()

        # 目录标题
        self._set_font_safe("B", 18)
        self.set_text_color(26, 26, 26)
        self.cell(0, 15, "目 录", ln=True, align="C")
        self.ln(15)

        # 目录项
        self._set_font_safe("", 12)
        self.set_text_color(51, 51, 51)

        for i, chapter in enumerate(chapters, 1):
            title = chapter.get("title", "")
            page = chapter.get("page", "")

            # 章节编号和标题
            chapter_text = f"第{i}章  {title}"

            # 计算点线填充
            self.set_x(self.l_margin)
            title_width = self.get_string_width(chapter_text)
            page_width = self.get_string_width(str(page))
            available_width = self.w - self.l_margin - self.r_margin - title_width - page_width - 10
            dots = "." * int(available_width / self.get_string_width("."))

            # 输出目录行
            self.cell(title_width + 5, 10, chapter_text, ln=False)
            self.set_text_color(180, 180, 180)
            self.cell(available_width, 10, dots, ln=False)
            self.set_text_color(51, 51, 51)
            self.cell(page_width + 5, 10, str(page), ln=True, align="R")
            self.ln(2)

    def chapter_title(self, title: str, level: int = 1):
        """添加标题 - 智能处理换行"""
        if not title:
            return
        sizes = {1: 16, 2: 13, 3: 11, 4: 10}
        size = sizes.get(level, 10)
        self._set_font_safe("B", size)
        self.set_text_color(26, 26, 26)
        self.ln(4 if level > 1 else 0)
        # 重置 X 到左边距
        self.set_x(self.l_margin)
        # 使用 wrapmode=WrapMode.CHAR 避免英文单词被拆分换行
        from fpdf.enums import WrapMode

        self.multi_cell(w=0, h=7, text=str(title), wrapmode=WrapMode.CHAR)
        self.set_x(self.l_margin)  # multi_cell 后重置
        self.ln(2)

    def body_text(self, text: str):
        """添加正文 - 智能处理换行和Markdown格式

        🔥 v7.26.3: 支持Markdown格式解析
        - ### 标题 → 小节标题
        - **加粗** → 去除星号显示
        - - 列表项 → bullet列表
        """
        if not text:
            return

        # 清理文本，确保字符串格式
        clean_text = str(text).strip()
        if not clean_text:
            return

        import re

        from fpdf.enums import WrapMode

        # 🔥 v7.26.3: 按行处理，识别Markdown格式
        lines = clean_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. 处理 Markdown 标题 (### 或 ## 或 #)
            header_match = re.match(r"^(#{1,4})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1)) + 2  # # -> level 3, ## -> level 4
                title_text = header_match.group(2).strip()
                # 清理标题中的Markdown格式
                title_text = re.sub(r"\*\*(.+?)\*\*", r"\1", title_text)
                title_text = re.sub(r"\*(.+?)\*", r"\1", title_text)
                self.chapter_title(title_text, min(level, 4))
                continue

            # 2. 处理 Markdown 无序列表 (- 或 *)
            list_match = re.match(r"^[-*]\s+(.+)$", line)
            if list_match:
                item_text = list_match.group(1).strip()
                # 清理列表项中的Markdown格式
                item_text = re.sub(r"\*\*(.+?)\*\*", r"\1", item_text)
                item_text = re.sub(r"\*(.+?)\*", r"\1", item_text)
                self.list_item(item_text)
                continue

            # 3. 普通文本：清理Markdown格式后输出
            # 去除 **加粗** 和 *斜体* 标记
            clean_line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            clean_line = re.sub(r"\*(.+?)\*", r"\1", clean_line)

            # 设置字体和颜色
            self._set_font_safe("", 10)
            self.set_text_color(51, 51, 51)
            self.set_x(self.l_margin)

            # 检查是否包含编号列表
            if any(f"{i}." in clean_line or f"{i}、" in clean_line for i in range(1, 10)):
                formatted_text = _format_numbered_list(clean_line)
                sub_lines = formatted_text.split("\n")
                for sub_line in sub_lines:
                    sub_line = sub_line.strip()
                    if sub_line:
                        self.multi_cell(w=0, h=5, text=sub_line, wrapmode=WrapMode.CHAR)
                        self.set_x(self.l_margin)
            else:
                self.multi_cell(w=0, h=5, text=clean_line, wrapmode=WrapMode.CHAR)
                self.set_x(self.l_margin)

        self.ln(2)

    def list_item(self, text: str, numbered: bool = False, index: int = 0):
        """添加列表项 - 智能处理换行"""
        if not text:
            return
        self._set_font_safe("", 10)
        self.set_text_color(51, 51, 51)
        prefix = f"{index + 1}. " if numbered else "• "
        clean_text = str(text).strip()
        if clean_text:
            self.set_x(self.l_margin)  # 重置 X 到左边距
            # 使用 wrapmode=WrapMode.CHAR 避免英文单词被拆分换行
            from fpdf.enums import WrapMode

            self.multi_cell(w=0, h=5, text=prefix + clean_text, wrapmode=WrapMode.CHAR)
            self.set_x(self.l_margin)  # multi_cell 后重置

    def add_divider(self):
        """添加分隔线"""
        self.ln(3)
        self.set_draw_color(229, 231, 235)
        # 使用页面宽度计算
        page_width = self.w - self.l_margin - self.r_margin
        self.line(self.l_margin, self.get_y(), self.l_margin + page_width, self.get_y())
        self.ln(4)

    def highlighted_box(self, text: str):
        """添加高亮框（用户输入）"""
        if not text:
            return

        clean_text = str(text).strip()
        if not clean_text:
            return

        self.set_fill_color(248, 249, 250)
        self.set_draw_color(59, 130, 246)
        self._set_font_safe("", 10)
        self.set_text_color(51, 51, 51)

        # 计算可用宽度
        available_width = self.w - self.l_margin - self.r_margin
        box_width = available_width - 10  # 留一点边距

        # 先绘制左侧蓝色边线
        x = self.l_margin + 5
        y = self.get_y()

        # 存储当前位置
        start_y = y

        # 绘制背景和文本 - 使用字符级换行
        self.set_x(x + 5)
        from fpdf.enums import WrapMode

        self.multi_cell(w=box_width - 10, h=5, text=clean_text, fill=True, wrapmode=WrapMode.CHAR)

        # 绘制左侧蓝色边线
        end_y = self.get_y()
        self.set_line_width(0.8)
        self.set_draw_color(59, 130, 246)
        self.line(x, start_y, x, end_y)

        # 重置 X 位置
        self.set_x(self.l_margin)
        self.ln(4)


def generate_report_pdf(report_data: dict, user_input: str = "") -> bytes:
    """
    🔥 v7.24 合并优化：生成完整报告 PDF（含专家报告）

    PDF 结构对齐前端显示，包含 6 个核心章节：
    1. 用户原始需求
    2. 校准问卷回顾（过滤"未回答"）
    3. 需求洞察
    4. 核心答案（支持 v7.0 多交付物格式）
    5. 专家报告附录（🆕 v7.24: 合并原独立下载）
    6. 执行元数据
    """
    pdf = PDFGenerator()

    # ========== 封面页 ==========
    pdf.add_cover_page("项目分析报告")

    # ========== 目录页（简化版，无页码） ==========
    # 🔥 v7.26: 添加"报告（极致概念）"条目
    chapters = [
        {"title": "报告（极致概念）", "page": ""},
        {"title": "用户原始需求", "page": ""},
        {"title": "校准问卷回顾", "page": ""},
        {"title": "需求洞察", "page": ""},
        {"title": "核心答案", "page": ""},
        {"title": "专家报告附录", "page": ""},
        {"title": "执行元数据", "page": ""},
    ]
    pdf.add_table_of_contents(chapters)

    # ========== 第一章：报告（极致概念） ==========
    # 🔥 v7.26: 新增章节 - 报告概述
    pdf.add_page()  # 目录后的第一章需要新页
    pdf.chapter_title("第一章  报告（极致概念）", 1)
    pdf.body_text("本报告由极致概念智能分析系统生成，基于多智能体协作框架，为您的项目需求提供全方位的专业分析与建议。")
    pdf.ln(5)

    # 报告概述信息
    expert_reports = report_data.get("expert_reports", {})
    expert_count = len(expert_reports) if isinstance(expert_reports, dict) else 0
    if expert_count > 0:
        pdf.chapter_title("分析概述", 2)
        pdf.body_text(f"• 参与专家数量：{expert_count} 位")
        pdf.body_text(f"• 生成日期：{datetime.now().strftime('%Y-%m-%d')}")

    pdf.add_divider()

    # ========== 第二章：用户原始需求 ==========
    # 🔥 v7.26: 空两行连续输出，不要每个章节分页
    pdf.ln(15)
    pdf.chapter_title("第二章  用户原始需求", 1)
    if user_input:
        pdf.highlighted_box(user_input)
    else:
        pdf.body_text("（无用户输入）")
    pdf.add_divider()

    # ========== 第三章：校准问卷回顾 ==========
    # 🔥 v7.26: 空两行连续输出
    pdf.ln(15)
    pdf.chapter_title("第三章  校准问卷回顾", 1)

    questionnaire = report_data.get("questionnaire_responses", {})
    if questionnaire and isinstance(questionnaire, dict):
        responses = questionnaire.get("responses", [])
        # 🔥 过滤：只显示有效回答（排除"未回答"和空答案）
        valid_responses = [
            r for r in responses if isinstance(r, dict) and r.get("answer") and r.get("answer") not in ["未回答", ""]
        ]

        if valid_responses:
            pdf.body_text(f"共收集 {len(valid_responses)} 条有效回答：")
            pdf.ln(3)

            for idx, resp in enumerate(valid_responses, 1):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                context = resp.get("context", "")

                # 问题标题
                pdf.chapter_title(f"Q{idx}. {question}", 3)

                # 回答内容
                pdf._set_font_safe("", 10)
                pdf.set_text_color(51, 51, 51)
                pdf.body_text(f"回答：{answer}")

                # 问题背景（如果有）
                if context:
                    pdf._set_font_safe("", 9)
                    pdf.set_text_color(128, 128, 128)
                    pdf.body_text(f"背景：{context}")

                pdf.ln(2)

            # 分析洞察（如果有）
            analysis_insights = questionnaire.get("analysis_insights", "")
            if analysis_insights:
                pdf.add_divider()
                pdf.chapter_title("需求分析", 3)
                pdf.body_text(analysis_insights)
        else:
            pdf.body_text("用户跳过了校准问卷，或所有问题均未回答。")
    else:
        pdf.body_text("用户跳过了校准问卷。")

    pdf.add_divider()

    # ========== 第四章：需求洞察 ==========
    # 🔥 v7.26: 空两行连续输出
    pdf.ln(15)
    pdf.chapter_title("第四章  需求洞察", 1)

    insights = report_data.get("insights", {})

    # 🔥 v7.26.2: 兜底逻辑 - 如果 insights 为空，从 requirements_analysis 提取
    if not insights or not isinstance(insights, dict):
        requirements_analysis = report_data.get("requirements_analysis", {})
        if requirements_analysis and isinstance(requirements_analysis, dict):
            logger.info("🔧 [PDF] insights 为空，从 requirements_analysis 提取兜底数据")
            insights = {
                "key_insights": [
                    requirements_analysis.get("project_overview", ""),
                    requirements_analysis.get("project_task", ""),
                ],
                "cross_domain_connections": requirements_analysis.get("core_objectives", []),
                "user_needs_interpretation": requirements_analysis.get("character_narrative", ""),
            }
            # 过滤空值
            insights["key_insights"] = [i for i in insights["key_insights"] if i]
            if not insights["key_insights"]:
                insights = {}

    if insights and isinstance(insights, dict):
        # 核心洞察
        key_insights = insights.get("key_insights", [])
        if key_insights:
            pdf.chapter_title("核心洞察", 2)
            for idx, insight in enumerate(key_insights, 1):
                pdf.list_item(f"{insight}", numbered=True, index=idx - 1)
            pdf.ln(3)

        # 跨领域关联
        cross_domain = insights.get("cross_domain_connections", [])
        if cross_domain:
            pdf.chapter_title("跨领域关联", 2)
            for item in cross_domain:
                pdf.list_item(item)
            pdf.ln(3)

        # 用户需求深层解读
        interpretation = insights.get("user_needs_interpretation", "")
        if interpretation:
            pdf.chapter_title("用户需求深层解读", 2)
            pdf.body_text(interpretation)
    else:
        pdf.body_text("（暂无需求洞察数据）")

    pdf.add_divider()

    # ========== 第五章：核心答案 ==========
    # 🔥 v7.26: 空两行连续输出
    pdf.ln(15)
    pdf.chapter_title("第五章  核心答案", 1)

    core_answer = report_data.get("core_answer", {})

    # 🔥 v7.26.2: 兜底逻辑 - 如果 core_answer 为空，从 expert_reports 提取交付物信息
    if not core_answer or not isinstance(core_answer, dict):
        logger.info("🔧 [PDF] core_answer 为空，从 expert_reports 提取兜底数据")
        # 从专家报告中提取交付物名称
        deliverable_names = []
        expert_reports_raw = report_data.get("expert_reports", {})
        if isinstance(expert_reports_raw, dict):
            for expert_name, content in expert_reports_raw.items():
                if isinstance(content, str):
                    try:
                        content_dict = json.loads(content) if content.strip().startswith("{") else {}
                        ter = content_dict.get("task_execution_report", content_dict)
                        if isinstance(ter, dict):
                            outputs = ter.get("deliverable_outputs", [])
                            for output in outputs:
                                if isinstance(output, dict):
                                    name = output.get("deliverable_name", output.get("name", ""))
                                    if name and name not in deliverable_names:
                                        deliverable_names.append(name)
                    except (json.JSONDecodeError, AttributeError):
                        pass

        if deliverable_names:
            requirements = report_data.get("requirements_analysis", {})
            core_answer = {
                "question": user_input[:100] + "..." if len(user_input) > 100 else user_input,
                "answer": requirements.get("project_overview", "请查看各专家的详细分析报告"),
                "deliverables": deliverable_names[:5],
                "timeline": "请参考工程师专家的实施规划",
                "budget_range": "请参考工程师专家的成本估算",
            }

    if core_answer and isinstance(core_answer, dict):
        # 检测是否是 v7.0 多交付物格式
        deliverable_answers = core_answer.get("deliverable_answers", [])

        if deliverable_answers:
            # 🆕 v7.0 多交付物格式
            pdf.body_text(f"本项目包含 {len(deliverable_answers)} 个核心交付物：")
            pdf.ln(5)

            for da in deliverable_answers:
                if not isinstance(da, dict):
                    continue

                deliverable_id = da.get("deliverable_id", "")
                deliverable_name = da.get("deliverable_name", "")
                owner_role = da.get("owner_role", "")
                answer_summary = da.get("answer_summary", "")
                owner_answer = da.get("owner_answer", "")
                supporters = da.get("supporters", [])
                quality_score = da.get("quality_score")

                # 交付物标题
                pdf.chapter_title(f"【{deliverable_id}】{deliverable_name}", 2)

                # 责任者信息
                pdf._set_font_safe("", 10)
                pdf.set_text_color(100, 100, 100)
                role_display = _get_role_display_name(owner_role)
                pdf.body_text(f"责任专家: {role_display}")

                if quality_score:
                    pdf.body_text(f"完成度: {int(quality_score)}%")

                # 答案摘要
                if answer_summary:
                    pdf.chapter_title("答案摘要", 3)
                    pdf.body_text(answer_summary)

                # 完整输出
                if owner_answer:
                    pdf.chapter_title("责任者输出", 3)
                    pdf.body_text(owner_answer)

                # 支撑专家
                if supporters:
                    pdf.chapter_title("支撑专家", 3)
                    supporter_names = [_get_role_display_name(s) for s in supporters]
                    pdf.body_text("、".join(supporter_names))

                pdf.ln(5)
        else:
            # 旧格式（单一答案）
            question = core_answer.get("question", "")
            answer = core_answer.get("answer", "")
            deliverables = core_answer.get("deliverables", [])
            timeline = core_answer.get("timeline", "")
            budget_range = core_answer.get("budget_range", "")

            if question:
                pdf.chapter_title("核心问题", 2)
                pdf.body_text(question)

            if answer:
                pdf.chapter_title("综合答案", 2)
                pdf.body_text(answer)

            if deliverables:
                pdf.chapter_title("交付物清单", 2)
                for idx, d in enumerate(deliverables, 1):
                    pdf.list_item(d, numbered=True, index=idx - 1)
                pdf.ln(3)

            if timeline:
                pdf.chapter_title("时间规划", 2)
                pdf.body_text(timeline)

            if budget_range:
                pdf.chapter_title("预算范围", 2)
                pdf.body_text(budget_range)
    else:
        pdf.body_text("（暂无核心答案数据）")

    pdf.add_divider()

    # ========== 第六章：专家报告附录 🆕 v7.24 ==========
    expert_reports = report_data.get("expert_reports", {})
    if expert_reports and isinstance(expert_reports, dict) and len(expert_reports) > 0:
        # 🔥 v7.26: 空两行连续输出，不要分页
        pdf.ln(15)
        pdf.chapter_title("第六章  专家报告附录", 1)
        pdf.body_text(f"本章包含 {len(expert_reports)} 位专家的详细分析报告。")
        pdf.ln(5)

        # 专家目录
        pdf.chapter_title("专家列表", 2)
        for i, expert_name in enumerate(expert_reports.keys(), 1):
            pdf.list_item(f"{i}. {expert_name}", numbered=False)
        pdf.ln(5)

        # 逐个专家报告 - 🔥 v7.26: 不分页，空行分隔
        for expert_name, content in expert_reports.items():
            pdf.ln(10)
            pdf.chapter_title(expert_name, 2)
            format_expert_content_for_pdf(pdf, content)

    pdf.add_divider()

    # ========== 第七章：执行元数据 ==========
    # 🔥 v7.26: 空两行连续输出，不要分页
    pdf.ln(15)
    pdf.chapter_title("第七章  执行元数据", 1)

    # 从 report_data 中收集元数据
    inquiry_architecture = report_data.get("inquiry_architecture", "")
    expert_reports = report_data.get("expert_reports", {})
    expert_count = len(expert_reports) if isinstance(expert_reports, dict) else 0

    # 专家数量
    pdf.chapter_title("专家数量", 2)
    pdf.body_text(f"{expert_count} 位专家参与分析")

    # 探询架构
    if inquiry_architecture:
        pdf.chapter_title("探询架构", 2)
        pdf.body_text(inquiry_architecture)

    # 生成时间
    pdf.chapter_title("报告生成时间", 2)
    pdf.body_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return bytes(pdf.output())


def _get_role_display_name(role_id: str) -> str:
    """提取角色显示名称"""
    role_map = {
        "V2_设计总监": "设计总监",
        "V3_叙事与体验专家": "叙事与体验专家",
        "V3_人物及叙事专家": "人物及叙事专家",
        "V4_设计研究专员": "设计研究专员",
        "V4_设计研究员": "设计研究员",
        "V5_场景策划师": "场景策划师",
        "V5_场景与用户生态专家": "场景与用户生态专家",
        "V6_专业总工程师": "专业总工程师",
        "V6_工程师": "工程师",
    }

    for prefix, name in role_map.items():
        if role_id.startswith(prefix):
            return name
    return role_id


# 字段中文标签映射（与前端保持一致）
FIELD_LABELS = {
    # 通用字段
    "executive_summary": "执行摘要",
    "project_overview": "项目概述",
    "key_findings": "关键发现",
    "key_recommendations": "核心建议",
    "success_factors": "成功要素",
    "core_analysis": "核心分析",
    "professional_opinion": "专业意见",
    "design_recommendations": "设计建议",
    "implementation_guidance": "实施指导",
    "analysis": "分析",
    "recommendations": "建议",
    "conclusion": "结论",
    "summary": "总结",
    "overview": "概述",
    "details": "详情",
    "description": "描述",
    "assessment": "评估",
    "evaluation": "评价",
    "findings": "发现",
    "insights": "洞察",
    "observations": "观察",
    "considerations": "考虑因素",
    "factors": "因素",
    "challenges": "挑战",
    "opportunities": "机遇",
    "risks": "风险",
    "benefits": "优势",
    "limitations": "局限",
    "requirements": "需求",
    "objectives": "目标",
    "goals": "目标",
    "strategy": "策略",
    "approach": "方法",
    "methodology": "方法论",
    "framework": "框架",
    "principles": "原则",
    "guidelines": "指导方针",
    "standards": "标准",
    "criteria": "标准",
    "metrics": "指标",
    "indicators": "指标",
    "performance": "性能",
    "quality": "质量",
    "efficiency": "效率",
    "effectiveness": "有效性",
    "impact": "影响",
    "outcome": "结果",
    "output": "产出",
    "input": "输入",
    "process": "流程",
    "procedure": "程序",
    "steps": "步骤",
    "phases": "阶段",
    "stages": "阶段",
    "timeline": "时间线",
    "schedule": "计划",
    "budget": "预算",
    "cost": "成本",
    "resources": "资源",
    "materials": "材料",
    "equipment": "设备",
    "tools": "工具",
    "technologies": "技术",
    "methods": "方法",
    "techniques": "技术",
    "solutions": "解决方案",
    "alternatives": "替代方案",
    "options": "选项",
    "choices": "选择",
    "preferences": "偏好",
    "priorities": "优先级",
    "concerns": "关注点",
    "issues": "问题",
    "problems": "问题",
    "actions": "行动",
    "tasks": "任务",
    "activities": "活动",
    "deliverables": "交付物",
    "milestones": "里程碑",
    "achievements": "成就",
    "results": "结果",
    "confidence": "置信度",
    "custom_analysis": "定制分析",
    "expert_handoff_response": "专家交接响应",
    "critical_questions_responses": "关键问题响应",
    "missing_inputs_warning": "缺失输入警告",
    # 设计相关字段
    "project_vision_summary": "项目愿景概述",
    "decision_rationale": "决策依据",
    "spatial_concept": "空间概念",
    "customer_journey_design": "客户旅程设计",
    "visual_merchandising_strategy": "视觉营销策略",
    "brand_identity_integration": "品牌识别整合",
    "space_planning": "空间规划",
    "material_selection": "材料选择",
    "lighting_design": "照明设计",
    "color_scheme": "配色方案",
    "furniture_layout": "家具布局",
    "user_experience": "用户体验",
    "functional_requirements": "功能需求",
    "aesthetic_considerations": "美学考量",
    "sustainability": "可持续性",
    "accessibility": "无障碍设计",
    "safety": "安全性",
    "maintenance": "维护",
    "durability": "耐久性",
    # 案例研究相关
    "case_studies_deep_dive": "深度案例研究",
    "competitive_analysis": "竞品分析",
    "reusable_design_patterns": "可复用设计模式",
    "key_success_factors": "关键成功因素",
    "application_guidelines_for_team": "团队应用指南",
    "key_takeaways": "关键要点",
    "name": "名称",
    "brand": "品牌",
    "strengths": "优势",
    "weaknesses": "劣势",
    "pattern_name": "模式名称",
    "pattern name": "模式名称",
    # 运营相关
    "business_goal_analysis": "商业目标分析",
    "operational_blueprint": "运营蓝图",
    "key_performance_indicators": "关键绩效指标",
    "design_challenges_for_v2": "给设计总监的挑战",
    "journey_maps": "旅程地图",
    "healing_environment_kpis": "疗愈环境KPI",
    "technical_requirements_for_v6": "给技术专家的需求",
    "metric": "指标",
    "target": "目标值",
    "spatial_strategy": "空间策略",
    # 用户研究相关
    "pain_points": "痛点",
    "Pain Points": "痛点",
    "persona": "用户画像",
    "Persona": "用户画像",
    "user_needs": "用户需求",
    "user_goals": "用户目标",
    "user_journey": "用户旅程",
    "touchpoints": "触点",
    "empathy_map": "共情地图",
    # 技术相关
    "mep_overall_strategy": "机电整体策略",
    "system_solutions": "系统解决方案",
    "smart_building_scenarios": "智能建筑场景",
    "coordination_and_clash_points": "协调与冲突点",
    "sustainability_and_energy_saving": "可持续与节能",
    # 材料与工艺
    "craftsmanship_strategy": "工艺策略",
    "key_material_specifications": "关键材料规格",
    "critical_node_details": "关键节点详图",
    "quality_control_and_mockup": "质量控制与样板",
    "risk_analysis": "风险分析",
    "design_rationale": "设计依据",
    # 挑战相关
    "challenge": "挑战",
    "context": "背景",
    "constraints": "约束条件",
    "challenge_flags": "挑战标记",
    # 签名方法/应用相关
    "signature_methods": "标志性方法",
    "application_to_project": "项目应用",
    "initial_key_scenario": "初始关键场景",
    # 设计立场相关
    "pole_a_resolve": "立场A解决方案",
    "pole_b_resolve": "立场B解决方案",
    "chosen_design_stance": "选定的设计立场",
    # 大师案例研究相关
    "master_work_deconstruction_nendo": "大师作品解构：Nendo",
    "master_work_deconstruction": "大师作品解构",
    "master": "大师",
    "philosophy": "设计哲学",
    "missing_inspiration_warning": "缺失灵感警告",
    "desc": "说明",
    # 其他常见字段
    "q1": "问题1",
    "q2": "问题2",
    "q3": "问题3",
    # ============ 任务导向模型字段 (task_oriented_models.py) ============
    # DeliverableOutput 交付物输出
    "deliverable_name": "交付物名称",
    "deliverable_outputs": "交付物输出",
    "content": "内容",
    "completion_status": "完成状态",
    "completion_rate": "完成度",
    "notes": "备注",
    "quality_self_assessment": "质量自评",
    # TaskExecutionReport 任务执行报告
    "task_execution_report": "任务执行报告",
    "task_completion_summary": "任务完成总结",
    "additional_insights": "额外洞察",
    "execution_challenges": "执行挑战",
    # ProtocolExecutionReport 协议执行报告
    "protocol_execution": "协议执行报告",
    "protocol_status": "协议状态",
    "compliance_confirmation": "合规确认",
    "challenge_details": "挑战详情",
    "reinterpretation": "重新诠释",
    # ChallengeFlag 挑战标记
    "challenged_item": "被挑战内容",
    "challenge_reason": "挑战理由",
    "alternative_proposal": "替代方案",
    # ReinterpretationDetail 重新诠释详情
    "original_interpretation": "原始诠释",
    "new_interpretation": "新诠释",
    "reinterpretation_rationale": "诠释依据",
    "impact_on_approach": "方法论影响",
    # ExecutionMetadata 执行元数据
    "execution_metadata": "执行元数据",
    "execution_time_estimate": "执行时间估算",
    "execution_notes": "执行备注",
    "dependencies_satisfied": "依赖满足",
    # TaskInstruction 任务指令
    "objective": "核心目标",
    "success_criteria": "成功标准",
    "context_requirements": "上下文需求",
    # DeliverableSpec 交付物规格
    "format": "格式",
    "priority": "优先级",
    # 协议状态枚举值
    "complied": "已遵照",
    "challenged": "已挑战",
    "reinterpreted": "已重新诠释",
    # 完成状态枚举值
    "completed": "已完成",
    "partial": "部分完成",
    "unable": "无法完成",
    # ============ V2-V6 FlexibleOutput 专家模型字段 ============
    # 通用字段
    "output_mode": "输出模式",
    "user_question_focus": "问题聚焦",
    "design_rationale": "设计依据",
    "decision_rationale": "决策依据",
    "targeted_analysis": "针对性分析",
    "supplementary_insights": "补充洞察",
    # V6-1 结构与幕墙工程师
    "feasibility_assessment": "可行性评估",
    "structural_system_options": "结构体系选项",
    "facade_system_options": "幕墙体系选项",
    "key_technical_nodes": "关键技术节点",
    "risk_analysis_and_recommendations": "风险分析与建议",
    "option_name": "方案名称",
    "advantages": "优势",
    "disadvantages": "劣势",
    "estimated_cost_level": "预估造价等级",
    "node_name": "节点名称",
    "proposed_solution": "建议方案",
    # V6-2 机电与智能化工程师
    "mep_overall_strategy": "机电整体策略",
    "system_solutions": "系统解决方案",
    "smart_building_scenarios": "智能建筑场景",
    "coordination_and_clash_points": "协调与冲突点",
    "sustainability_and_energy_saving": "可持续与节能",
    "system_name": "系统名称",
    "recommended_solution": "推荐方案",
    "reasoning": "理由",
    "impact_on_architecture": "对建筑的影响",
    "scenario_name": "场景名称",
    "triggered_systems": "联动系统",
    # V6-3 室内工艺与材料专家
    "craftsmanship_strategy": "工艺策略",
    "key_material_specifications": "关键材料规格",
    "critical_node_details": "关键节点详图",
    "quality_control_and_mockup": "质量控制与样板",
    "material_name": "材料名称",
    "application_area": "应用区域",
    "key_specifications": "关键规格",
    # V6-4 成本与价值工程师
    "cost_estimation_summary": "成本估算摘要",
    "cost_breakdown_analysis": "成本构成分析",
    "value_engineering_options": "价值工程选项",
    "budget_control_strategy": "预算控制策略",
    "cost_overrun_risk_analysis": "成本超支风险分析",
    "category": "类别",
    "percentage": "百分比",
    "cost_drivers": "成本驱动因素",
    "original_scheme": "原方案",
    "proposed_option": "优化方案",
    "impact_analysis": "影响分析",
    # V5-1 居住场景与生活方式专家
    "family_profile_and_needs": "家庭成员画像与需求",
    "operational_blueprint": "运营蓝图",
    "design_challenges_for_v2": "给设计总监的挑战",
    "member": "成员",
    "daily_routine": "日常作息",
    "spatial_needs": "空间需求",
    "storage_needs": "收纳需求",
    # V5-2 商业零售运营专家
    "business_goal_analysis": "商业目标分析",
    "spatial_strategy": "空间策略",
    # V5-3 企业办公策略专家
    "organizational_analysis": "组织分析",
    "collaboration_model": "协作模式",
    "workspace_strategy": "工作空间策略",
    # V5-4 酒店餐饮运营专家
    "service_process_analysis": "服务流程分析",
    "operational_efficiency": "运营效率",
    "guest_experience_blueprint": "宾客体验蓝图",
    # V5-5 文化教育场景专家
    "visitor_journey_analysis": "访客旅程分析",
    "educational_model": "教育模式",
    "public_service_strategy": "公共服务策略",
    # V5-6 医疗康养场景专家
    "healthcare_process_analysis": "医疗流程分析",
    "patient_experience_blueprint": "患者体验蓝图",
    "wellness_strategy": "康养策略",
    # V2系列 设计总监
    "project_vision_summary": "项目愿景概述",
    "spatial_concept": "空间概念",
    "customer_journey_design": "客户旅程设计",
    "visual_merchandising_strategy": "视觉营销策略",
    "brand_identity_integration": "品牌识别整合",
    "implementation_guidance": "实施指导",
    "architectural_concept": "建筑概念",
    "facade_and_envelope": "立面与围护",
    "landscape_integration": "景观整合",
    "indoor_outdoor_relationship": "室内外关系",
    "public_vision": "公共愿景",
    "spatial_accessibility": "空间可达性",
    "community_engagement": "社区参与",
    "cultural_expression": "文化表达",
    # V3系列 叙事与体验专家
    "narrative_framework": "叙事框架",
    "emotional_journey": "情感旅程",
    "touchpoint_design": "触点设计",
    # V4系列 设计研究专员
    "case_studies_deep_dive": "深度案例研究",
    "reusable_design_patterns": "可复用设计模式",
    "key_success_factors": "关键成功因素",
    "application_guidelines_for_team": "团队应用指南",
    "trend_analysis": "趋势分析",
    "future_scenarios": "未来场景",
    "opportunity_identification": "机会识别",
    "design_implications": "设计启示",
}


def format_expert_content_for_pdf(pdf: "PDFGenerator", content: str, depth: int = 0):
    """
    格式化专家报告内容并写入 PDF

    支持解析 JSON 结构化数据，递归处理嵌套对象和数组
    """
    import json

    if not content:
        pdf.body_text("（无内容）")
        return

    # 尝试解析 JSON
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            _format_dict_to_pdf(pdf, parsed, depth)
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    _format_dict_to_pdf(pdf, item, depth)
                else:
                    pdf.list_item(str(item))
        else:
            pdf.body_text(str(parsed))
    except (json.JSONDecodeError, TypeError):
        # 不是 JSON，直接输出原始文本
        pdf.body_text(content)


def _get_field_label(key: str) -> str:
    """获取字段的中文标签"""
    import re

    lower_key = key.lower().strip()

    # 精确匹配（包括带空格的key）
    if lower_key in FIELD_LABELS:
        return FIELD_LABELS[lower_key]

    # 尝试替换空格为下划线后匹配
    normalized_key = lower_key.replace(" ", "_").replace("-", "_")
    if normalized_key in FIELD_LABELS:
        return FIELD_LABELS[normalized_key]

    # 处理特殊格式：如 "Q1 空间要强化..." 这种问题+内容混合格式
    # 只翻译 Q1/Q2/Q3 部分
    import re as regex

    q_match = regex.match(r"^(q\d+)\s*(.*)$", lower_key, regex.IGNORECASE)
    if q_match:
        q_num = q_match.group(1).upper()
        rest = q_match.group(2).strip()
        q_label = {"Q1": "问题1", "Q2": "问题2", "Q3": "问题3", "Q4": "问题4", "Q5": "问题5"}.get(q_num, q_num)
        if rest:
            return f"{q_label} {rest}"
        return q_label

    # 常见英文词汇到中文的映射
    common_words = {
        # 功能词
        "for": "",
        "the": "",
        "of": "",
        "and": "与",
        "to": "到",
        "in": "在",
        "on": "上",
        "a": "",
        "an": "",
        "is": "",
        "are": "",
        "be": "",
        # 角色
        "v2": "设计总监",
        "v3": "专家",
        "v4": "研究员",
        "v5": "创新专家",
        "v6": "技术专家",
        # 常见术语
        "kpi": "KPI",
        "kpis": "KPI指标",
        "deep": "深度",
        "dive": "研究",
        "how": "如何",
        "might": "可能",
        "we": "我们",
        "pattern": "模式",
        "name": "名称",
        "signature": "标志性",
        "methods": "方法",
        "application": "应用",
        "project": "项目",
        "initial": "初始",
        "key": "关键",
        "scenario": "场景",
        "pole": "立场",
        "resolve": "解决方案",
        "chosen": "选定的",
        "design": "设计",
        "stance": "立场",
        "q1": "问题1",
        "q2": "问题2",
        "q3": "问题3",
        "brand": "品牌",
        "identity": "识别",
        "integration": "整合",
        "space": "空间",
        "spatial": "空间",
        "concept": "概念",
        "customer": "客户",
        "journey": "旅程",
        "visual": "视觉",
        "merchandising": "营销",
        "strategy": "策略",
        "summary": "概述",
        "vision": "愿景",
        "rationale": "依据",
        "decision": "决策",
        "guidance": "指导",
        "implementation": "实施",
        "custom": "定制",
        "analysis": "分析",
        "confidence": "置信度",
        "expert": "专家",
        "handoff": "交接",
        "response": "响应",
        "critical": "关键",
        "questions": "问题",
        "responses": "响应",
        "missing": "缺失",
        "inputs": "输入",
        "warning": "警告",
        "challenges": "挑战",
        "flags": "标记",
        # 大师/案例相关
        "master": "大师",
        "work": "作品",
        "deconstruction": "解构",
        "nendo": "Nendo",
        "philosophy": "设计哲学",
        "inspiration": "灵感",
        "desc": "说明",
    }

    # 尝试部分匹配（将 snake_case 分解后翻译）
    parts = normalized_key.split("_")
    translated_parts = []
    has_untranslated = False

    for part in parts:
        if not part:
            continue
        if part in FIELD_LABELS:
            translated_parts.append(FIELD_LABELS[part])
        elif part in common_words:
            if common_words[part]:
                translated_parts.append(common_words[part])
        elif part.isdigit():
            translated_parts.append(part)
        else:
            has_untranslated = True
            translated_parts.append(part)

    # 如果有未翻译的部分，返回格式化的原始标签
    if has_untranslated:
        label = key.replace("_", " ").replace("-", " ")
        label = regex.sub(r"([a-z])([A-Z])", r"\1 \2", label)
        return label.title()

    return "".join(translated_parts) if translated_parts else key


# 需要跳过的重复/内部字段
# 🔥 v7.9.2: 扩展黑名单,过滤元数据字段(与前端ExpertReportAccordion.tsx保持一致)
# 🔥 v7.26.1: 移除 content 字段，交给递归函数特殊处理（允许嵌套对象的 content）
SKIP_FIELDS = {
    # 原有字段 - 🔥 v7.26.1: 移除 'content'，交给递归函数处理
    "raw_content",
    "raw_response",
    "original_content",
    # 🔥 v7.9.2: 任务导向输出元数据(避免显示技术字段)
    "task_execution_report",  # 已被提取,不再需要显示
    "protocol_execution",
    "protocol执行",
    "protocol_status",
    "protocol状态",
    "execution_metadata",
    "executionmetadata",
    "compliance_confirmation",
    "complianceconfirmation",
    # 技术字段
    "confidence",
    "置信度",
    "completion_status",
    "completion记录",
    "completion_ratio",
    "completion_rate",
    "quality_self_assessment",
    "dependencies_satisfied",
    "notes",  # 通常是技术备注
    # 🔥 v7.10.1: 过滤无意义的图片占位符字段
    "image",
    "images",
    "图片",
    "illustration",
    "illustrations",
    "image_1_url",
    "image_2_url",
    "image_3_url",
    "image_4_url",
    "image_5_url",
    "image_6_url",
    "image_url",
    "image_urls",
    "图片链接",
}

# 🔥 v7.26.1: 顶层专用黑名单（只在 depth=0 时跳过）
TOP_LEVEL_SKIP_FIELDS = {
    "content",  # 顶层 content 可能与 structured_data 重复
}

# ============ 内容翻译函数（处理 LLM 输出中的英文短语） ============
CONTENT_TRANSLATIONS = {
    # 设计思维框架短语
    "How might we": "我们如何能够",
    "How Might We": "我们如何能够",
    "HMW": "如何",
    # Pain Points 各种变体
    "Pain Points": "痛点",
    "Pain points": "痛点",
    "pain points": "痛点",
    "Pain Point": "痛点",
    "pain point": "痛点",
    # Persona 各种变体（保留冒号后的空格）
    "Persona: ": "用户画像: ",
    "Persona:": "用户画像:",
    "persona: ": "用户画像: ",
    "persona:": "用户画像:",
    # 值翻译（LLM 可能输出的英文值）
    "pole_a_resolve": "立场A解决方案",
    "pole_b_resolve": "立场B解决方案",
    "pole_a": "立场A",
    "pole_b": "立场B",
    "Pole A": "立场A",
    "Pole B": "立场B",
    # 旅程地图相关
    "Journey Map": "旅程地图",
    "journey map": "旅程地图",
    "User Journey": "用户旅程",
    "Customer Journey": "客户旅程",
    "Touchpoint": "触点",
    "touchpoint": "触点",
    # 常见设计术语
    "Key Takeaways": "关键要点",
    "Key takeaways": "关键要点",
    "Best Practices": "最佳实践",
    "best practices": "最佳实践",
    "Case Study": "案例研究",
    "case study": "案例研究",
    "Deep Dive": "深度研究",
    "deep dive": "深度研究",
    "Next Steps": "下一步",
    "next steps": "下一步",
    "Action Items": "行动项",
    "action items": "行动项",
    "Trade-offs": "权衡",
    "trade-offs": "权衡",
    "Pros and Cons": "优缺点",
    "pros and cons": "优缺点",
}


def _translate_content(text: str) -> str:
    """翻译内容中的英文短语为中文"""
    if not text or not isinstance(text, str):
        return text

    result = text
    for eng, chn in CONTENT_TRANSLATIONS.items():
        result = result.replace(eng, chn)

    return result


def _clean_markdown_inline(text: str) -> str:
    """🔥 v7.26.3: 清理行内Markdown格式（用于短文本）

    去除 **加粗** 和 *斜体* 标记，保留文本内容
    """
    if not text or not isinstance(text, str):
        return text

    import re

    # 去除 **加粗**
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # 去除 *斜体*
    result = re.sub(r"\*(.+?)\*", r"\1", result)
    return result


def _format_numbered_list(text: str) -> str:
    """将连续的编号列表拆分成独立行

    例如: "1. xxx 2. yyy 3. zzz" -> "1. xxx\n2. yyy\n3. zzz"
    """
    if not text or not isinstance(text, str):
        return text

    import re

    # 匹配 "数字. " 或 "数字、" 或 "数字）" 前面有内容的情况
    # 在编号前插入换行（但不是开头的编号）
    result = re.sub(r"([。；，、\.\)）])\s*(\d+[\.\、\)）]\s*)", r"\1\n\2", text)

    return result


def _format_dict_to_pdf(pdf: "PDFGenerator", data: dict, depth: int = 0):
    """递归格式化字典数据到 PDF

    增强版：
    - depth=0 (顶级) 时添加分隔线
    - 改进列表和嵌套结构的间距
    - 🔥 v7.26.1: 顶层跳过 content，嵌套层允许
    """
    is_top_level = depth == 0
    item_count = 0

    for key, value in data.items():
        # 跳过重复内容字段
        if key.lower() in SKIP_FIELDS:
            continue

        # 🔥 v7.26.1: 顶层时额外跳过 content（可能与 structured_data 重复）
        if is_top_level and key.lower() in TOP_LEVEL_SKIP_FIELDS:
            continue

        label = _get_field_label(key)

        if value is None or (isinstance(value, str) and not value.strip()):
            continue

        # 顶级字段之间添加分隔线（除了第一个）
        if is_top_level and item_count > 0:
            pdf.add_divider()
        item_count += 1

        if isinstance(value, list):
            if not value:
                continue
            # 列表标题
            level = min(depth + 2, 4) if is_top_level else min(depth + 3, 4)
            pdf.chapter_title(label, level)

            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    # 交付物列表项之间添加小间距
                    if idx > 0:
                        pdf.ln(3)
                    _format_dict_to_pdf(pdf, item, depth + 1)
                else:
                    # 🔥 v7.26.3: 清理列表项中的Markdown格式
                    item_str = _translate_content(str(item).strip())
                    item_str = _clean_markdown_inline(item_str)
                    if item_str:
                        pdf.list_item(item_str)
            pdf.ln(3)

        elif isinstance(value, dict):
            if not value:
                continue
            level = min(depth + 2, 4) if is_top_level else min(depth + 3, 4)
            pdf.chapter_title(label, level)
            _format_dict_to_pdf(pdf, value, depth + 1)

        else:
            # 🔥 v7.26.3: 先翻译，再清理Markdown格式
            value_str = _translate_content(str(value).strip())
            value_str = _clean_markdown_inline(value_str)
            if not value_str:
                continue

            # 计算标签和值的实际显示宽度
            pdf._set_font_safe("B", 10)
            label_text = f"{label}: "
            label_width = pdf.get_string_width(label_text) + 2

            pdf._set_font_safe("", 10)
            value_width = pdf.get_string_width(value_str)

            # 页面可用宽度
            page_width = pdf.w - pdf.l_margin - pdf.r_margin

            # 决定显示方式：
            # 1. 如果标签+值能在一行显示 → 同行
            # 2. 如果值本身超过页面宽度的80% → 作为段落（标签单独一行作为标题）
            # 3. 否则 → 标签: 换行显示值

            if label_width + value_width <= page_width - 5:
                # 情况1: 能在一行显示
                pdf.set_text_color(51, 51, 51)
                pdf.set_x(pdf.l_margin)
                pdf._set_font_safe("B", 10)
                pdf.cell(label_width, 6, label_text, ln=False)
                pdf._set_font_safe("", 10)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 6, value_str, ln=True)
                pdf.set_x(pdf.l_margin)
                pdf.ln(2)
            elif value_width > page_width * 0.8:
                # 情况2: 长文本，作为段落显示
                level = min(depth + 2, 4) if is_top_level else min(depth + 3, 4)
                pdf.chapter_title(label, level)
                pdf.body_text(value_str)
            else:
                # 情况3: 中等长度，标签后换行显示值
                pdf.set_text_color(51, 51, 51)
                pdf.set_x(pdf.l_margin)
                pdf._set_font_safe("B", 10)
                pdf.cell(0, 6, label_text, ln=True)
                pdf._set_font_safe("", 10)
                pdf.set_text_color(0, 0, 0)
                pdf.set_x(pdf.l_margin)
                from fpdf.enums import WrapMode

                pdf.multi_cell(w=0, h=5, text=value_str, wrapmode=WrapMode.CHAR)
                pdf.set_x(pdf.l_margin)
                pdf.ln(2)


@app.get("/api/analysis/report/{session_id}/download-pdf")
async def download_report_pdf(session_id: str):
    """
    下载分析报告 PDF（v7.0 重构版）

    生成可编辑的 PDF 文件（文本可选中复制）

    包含 5 个核心章节：
    1. 用户原始需求
    2. 校准问卷回顾（过滤"未回答"）
    3. 需求洞察
    4. 核心答案（支持 v7.0 多交付物格式）
    5. 执行元数据

    不包含专家报告（专家报告有独立下载入口）
    """
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取报告数据
    final_report = session.get("final_report", {})
    user_input = session.get("user_input", "")

    if not isinstance(final_report, dict) or not final_report:
        raise HTTPException(status_code=400, detail="报告数据不可用")

    try:
        pdf_bytes = generate_report_pdf(final_report, user_input)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=project_report_{session_id}.pdf"},
        )
    except Exception as e:
        logger.error(f"❌ 生成 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")


async def generate_all_experts_pdf_async(expert_reports: Dict[str, str], user_input: str = "") -> bytes:
    """异步生成所有专家报告的合并 PDF（使用 HTML + Playwright 方案）

    v7.1.2 性能优化：使用异步版本，充分利用浏览器池
    """
    import json

    # 转换专家数据格式
    experts = []
    for expert_name, expert_content in expert_reports.items():
        # 解析内容
        content = expert_content
        if isinstance(expert_content, str):
            try:
                content = json.loads(expert_content)
            except json.JSONDecodeError:
                content = {"分析内容": expert_content}

        experts.append({"expert_name": expert_name, "content": content})

    # 使用异步 HTML PDF 生成器
    generator = HTMLPDFGenerator()
    pdf_bytes = await generator.generate_pdf_async(
        experts=experts,
        title="专家报告合集",
        subtitle=user_input[:100] + "..." if len(user_input) > 100 else user_input if user_input else None,
        session_id=None,
    )

    return pdf_bytes


def generate_all_experts_pdf(expert_reports: Dict[str, str], user_input: str = "") -> bytes:
    """生成所有专家报告的合并 PDF（使用 HTML + Playwright 方案）

    注意：此为同步版本，在 FastAPI 异步上下文中推荐使用 generate_all_experts_pdf_async
    """
    import json

    # 转换专家数据格式
    experts = []
    for expert_name, expert_content in expert_reports.items():
        # 解析内容
        content = expert_content
        if isinstance(expert_content, str):
            try:
                content = json.loads(expert_content)
            except json.JSONDecodeError:
                content = {"分析内容": expert_content}

        experts.append({"expert_name": expert_name, "content": content})

    # 使用新的 HTML PDF 生成器
    pdf_bytes = generate_html_pdf(
        experts=experts,
        title="专家报告合集",
        subtitle=user_input[:100] + "..." if len(user_input) > 100 else user_input if user_input else None,
        session_id=None,
    )

    return pdf_bytes


def generate_all_experts_pdf_fast(expert_reports: Dict[str, str], user_input: str = "") -> bytes:
    """
    🔥 v7.1.3: 快速生成所有专家报告 PDF (使用 FPDF)

    替代 Playwright 方案，提供极速生成体验。
    """
    pdf = PDFGenerator()

    # 封面
    pdf.add_cover_page("专家报告汇总")

    # 目录
    pdf.add_page()
    pdf._set_font_safe("B", 18)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(0, 15, "专家列表", ln=True, align="C")
    pdf.ln(10)
    pdf._set_font_safe("", 12)
    pdf.set_text_color(51, 51, 51)

    # 收集专家列表用于目录
    expert_names = list(expert_reports.keys())
    for i, name in enumerate(expert_names, 1):
        pdf.cell(0, 10, f"{i}. {name}", ln=True)

    # 用户输入
    if user_input:
        pdf.add_page()
        pdf.chapter_title("用户原始需求", level=1)
        pdf.body_text(user_input)

    # 专家内容
    for expert_name, content in expert_reports.items():
        pdf.add_page()
        pdf.chapter_title(expert_name, level=1)
        format_expert_content_for_pdf(pdf, content)

    return bytes(pdf.output())


@app.get("/api/analysis/report/{session_id}/download-all-experts-pdf")
async def download_all_experts_pdf(session_id: str):
    """
    下载所有专家报告的合并 PDF

    v7.1.3 升级：
    - 切换为 FPDF 原生生成引擎 (generate_all_experts_pdf_fast)
    - 速度提升 10x (10s -> <1s)
    - 移除 Playwright 依赖，更稳定
    """
    # 🚀 缓存检查 - 缓存命中直接返回
    cache_key = f"all_experts_pdf_fast_{session_id}"
    if cache_key in pdf_cache:
        logger.info(f"📦 PDF 缓存命中: {session_id}")
        pdf_bytes = pdf_cache[cache_key]
        from urllib.parse import quote

        safe_filename = quote(f"all_expert_reports_{session_id}.pdf", safe="")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
        )

    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取专家报告
    final_report = session.get("final_report", {})
    expert_reports = final_report.get("expert_reports", {}) if isinstance(final_report, dict) else {}

    if not expert_reports:
        raise HTTPException(status_code=400, detail="无专家报告数据")

    user_input = session.get("user_input", "")

    try:
        logger.info(f"⚡ 快速生成 PDF (FPDF): {session_id}")
        # 使用新的快速生成函数
        pdf_bytes = generate_all_experts_pdf_fast(expert_reports, user_input)

        # 🚀 缓存 PDF
        pdf_cache[cache_key] = pdf_bytes
        logger.info(f"💾 PDF 已缓存: {session_id} ({len(pdf_bytes)} bytes)")

        # 使用 URL 编码处理中文文件名
        from urllib.parse import quote

        safe_filename = quote(f"all_expert_reports_{session_id}.pdf", safe="")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
        )
    except Exception as e:
        logger.error(f"❌ 生成所有专家报告 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")


# 🆕 v7.40.1: 图像重新生成 API
# 🔥 v7.41: 扩展支持多图、参数控制、保存副本
class RegenerateImageRequest(BaseModel):
    expert_name: str
    new_prompt: str
    # 🔥 v7.41: 新增字段
    save_as_copy: bool = False  # 是否保存为副本（默认覆盖）
    image_id: Optional[str] = None  # 要替换的图像ID（多图模式）
    aspect_ratio: Optional[str] = "16:9"  # 宽高比
    style_type: Optional[str] = None  # 风格类型


class AddImageRequest(BaseModel):
    """🔥 v7.41: 新增概念图请求"""

    expert_name: str
    prompt: str
    aspect_ratio: Optional[str] = "16:9"
    style_type: Optional[str] = None


class DeleteImageRequest(BaseModel):
    """🔥 v7.41: 删除概念图请求"""

    expert_name: str
    image_id: Optional[str] = None  # 如果为空，删除该专家的所有图像


@app.post("/api/analysis/regenerate-image/{session_id}")
async def regenerate_expert_image(session_id: str, request: RegenerateImageRequest):
    """
    重新生成专家概念图像

    🔥 v7.40.1: 允许用户编辑提示词后重新生成图像
    🔥 v7.41: 支持保存为副本、参数控制
    """
    try:
        # 获取会话
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"🔄 开始重新生成图像: session={session_id}, expert={request.expert_name}")
        logger.info(f"📝 新提示词: {request.new_prompt[:100]}...")
        logger.info(
            f"⚙️ 参数: aspect_ratio={request.aspect_ratio}, style_type={request.style_type}, save_as_copy={request.save_as_copy}"
        )

        # 检查图像生成是否启用
        if not settings.image_generation.enabled:
            raise HTTPException(status_code=400, detail="图像生成功能未启用")

        # 导入图像生成服务
        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

        image_service = ImageGeneratorService()

        # 🔥 v7.60.4: 修复参数名称和类型（style_type→style, string→enum）
        result = await image_service.generate_image(
            prompt=request.new_prompt, aspect_ratio=_parse_aspect_ratio(request.aspect_ratio), style=request.style_type
        )

        if not result.success:
            logger.error(f"❌ 图像生成失败: {result.error}")
            return {"success": False, "error": result.error or "图像生成失败"}

        # 🔥 v7.60.5: 累加图像生成Token到会话metadata
        if result.total_tokens > 0:
            from intelligent_project_analyzer.utils.token_utils import update_session_tokens

            token_data = {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            }
            success = await update_session_tokens(
                session_manager, session_id, token_data, agent_name="image_generation"
            )
            if success:
                logger.info(f"✅ [图像Token] 已累加 {result.total_tokens} tokens 到会话 {session_id}")

        logger.info(f"✅ 图像重新生成成功: expert={request.expert_name}")

        # 🔥 v7.41: 生成唯一ID
        import uuid

        new_image_id = str(uuid.uuid4())[:8]

        new_image_data = {
            "expert_name": request.expert_name,
            "image_url": result.image_url,
            "prompt": request.new_prompt,
            "id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
            "created_at": datetime.now().isoformat(),
        }

        # 更新会话中的图像数据
        final_report = session.get("final_report", {})
        if isinstance(final_report, dict):
            generated_images_by_expert = final_report.get("generated_images_by_expert", {})

            # 🔥 v7.41: 多图支持
            if request.expert_name in generated_images_by_expert:
                existing = generated_images_by_expert[request.expert_name]

                # 兼容旧格式（单图对象 -> 数组）
                if isinstance(existing, dict) and "images" not in existing:
                    existing = {"expert_name": request.expert_name, "images": [existing]}
                elif isinstance(existing, dict) and "images" in existing:
                    pass  # 已经是新格式
                else:
                    existing = {"expert_name": request.expert_name, "images": []}

                images = existing.get("images", [])

                if request.save_as_copy:
                    # 保存为副本（最多3张）
                    if len(images) >= 3:
                        logger.warning(f"⚠️ 专家 {request.expert_name} 已有3张图像，无法添加更多")
                        return {"success": False, "error": "已达到最大图像数量（3张）"}
                    images.append(new_image_data)
                else:
                    # 覆盖：替换指定图像或第一张
                    if request.image_id:
                        for i, img in enumerate(images):
                            if img.get("id") == request.image_id:
                                images[i] = new_image_data
                                break
                        else:
                            # 未找到指定ID，追加
                            if len(images) < 3:
                                images.append(new_image_data)
                    elif images:
                        images[0] = new_image_data
                    else:
                        images.append(new_image_data)

                existing["images"] = images
                generated_images_by_expert[request.expert_name] = existing
            else:
                # 新专家，创建新条目
                generated_images_by_expert[request.expert_name] = {
                    "expert_name": request.expert_name,
                    "images": [new_image_data],
                }

            final_report["generated_images_by_expert"] = generated_images_by_expert
            session["final_report"] = final_report
            await session_manager.update(session_id, session)
            logger.info(f"💾 已更新会话中的图像数据")

        return {
            "success": True,
            "image_url": result.image_url,
            "prompt": request.new_prompt,
            "expert_name": request.expert_name,
            "image_id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 重新生成图像失败: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


# 🔥 v7.41: 新增概念图 API
@app.post("/api/analysis/add-image/{session_id}")
async def add_expert_image(session_id: str, request: AddImageRequest):
    """
    为专家新增概念图（最多3张）
    """
    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"➕ 新增概念图: session={session_id}, expert={request.expert_name}")

        if not settings.image_generation.enabled:
            raise HTTPException(status_code=400, detail="图像生成功能未启用")

        # 检查是否已达到上限
        final_report = session.get("final_report", {})
        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

        if request.expert_name in generated_images_by_expert:
            existing = generated_images_by_expert[request.expert_name]
            # 兼容旧格式
            if isinstance(existing, dict) and "images" not in existing:
                images = [existing]
            elif isinstance(existing, dict) and "images" in existing:
                images = existing.get("images", [])
            else:
                images = []

            if len(images) >= 3:
                return {"success": False, "error": "已达到最大图像数量（3张）"}

        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

        image_service = ImageGeneratorService()
        # 🔥 v7.60.4: 修复参数名称和类型（style_type→style, string→enum）
        result = await image_service.generate_image(
            prompt=request.prompt, aspect_ratio=_parse_aspect_ratio(request.aspect_ratio), style=request.style_type
        )

        if not result.success:
            return {"success": False, "error": result.error or "图像生成失败"}

        # 🔥 v7.60.5: 累加图像生成Token到会话metadata
        if result.total_tokens > 0:
            from intelligent_project_analyzer.utils.token_utils import update_session_tokens

            token_data = {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            }
            success = await update_session_tokens(
                session_manager, session_id, token_data, agent_name="image_generation"
            )
            if success:
                logger.info(f"✅ [图像Token] 已累加 {result.total_tokens} tokens 到会话 {session_id}")

        import uuid

        new_image_id = str(uuid.uuid4())[:8]

        new_image_data = {
            "expert_name": request.expert_name,
            "image_url": result.image_url,
            "prompt": request.prompt,
            "id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
            "created_at": datetime.now().isoformat(),
        }

        # 更新会话
        if request.expert_name in generated_images_by_expert:
            existing = generated_images_by_expert[request.expert_name]
            if isinstance(existing, dict) and "images" not in existing:
                existing = {"expert_name": request.expert_name, "images": [existing]}
            existing["images"].append(new_image_data)
            generated_images_by_expert[request.expert_name] = existing
        else:
            generated_images_by_expert[request.expert_name] = {
                "expert_name": request.expert_name,
                "images": [new_image_data],
            }

        final_report["generated_images_by_expert"] = generated_images_by_expert
        session["final_report"] = final_report
        await session_manager.update(session_id, session)

        logger.info(f"✅ 新增概念图成功: id={new_image_id}")

        return {"success": True, "image": new_image_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 新增概念图失败: {e}")
        return {"success": False, "error": str(e)}


# 🔥 v7.41: 删除概念图 API
@app.delete("/api/analysis/delete-image/{session_id}")
async def delete_expert_image(session_id: str, request: DeleteImageRequest):
    """
    删除专家概念图
    """
    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"🗑️ 删除概念图: session={session_id}, expert={request.expert_name}, image_id={request.image_id}")

        final_report = session.get("final_report", {})
        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

        if request.expert_name not in generated_images_by_expert:
            return {"success": False, "error": "未找到该专家的概念图"}

        existing = generated_images_by_expert[request.expert_name]

        if request.image_id:
            # 删除指定图像
            if isinstance(existing, dict) and "images" in existing:
                images = existing.get("images", [])
                images = [img for img in images if img.get("id") != request.image_id]
                if images:
                    existing["images"] = images
                    generated_images_by_expert[request.expert_name] = existing
                else:
                    del generated_images_by_expert[request.expert_name]
            else:
                # 旧格式单图，直接删除
                del generated_images_by_expert[request.expert_name]
        else:
            # 删除该专家的所有图像
            del generated_images_by_expert[request.expert_name]

        final_report["generated_images_by_expert"] = generated_images_by_expert
        session["final_report"] = final_report
        await session_manager.update(session_id, session)

        logger.info(f"✅ 删除概念图成功")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除概念图失败: {e}")
        return {"success": False, "error": str(e)}


# 🔥 v7.41: 智能推荐提示词 API
@app.get("/api/analysis/suggest-prompts/{session_id}/{expert_name}")
async def suggest_image_prompts(session_id: str, expert_name: str):
    """
    基于专家报告关键词生成3个推荐提示词

    策略：从专家报告中提取关键概念，组合成可视化提示词
    """
    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"💡 生成推荐提示词: session={session_id}, expert={expert_name}")

        final_report = session.get("final_report", {})
        expert_reports = final_report.get("expert_reports", {})

        # 查找专家报告
        expert_content = None
        expert_dynamic_name = expert_name

        for key, value in expert_reports.items():
            # 匹配专家名称（支持多种格式）
            if expert_name in key or key in expert_name:
                expert_content = value
                expert_dynamic_name = key
                break

        if not expert_content:
            # 尝试从 agent_results 获取
            agent_results = session.get("agent_results", {})
            for key, value in agent_results.items():
                if expert_name in key or key in expert_name:
                    if isinstance(value, dict):
                        expert_content = value.get("content", "")
                    else:
                        expert_content = str(value)
                    break

        if not expert_content:
            logger.warning(f"⚠️ 未找到专家报告: {expert_name}")
            # 返回默认推荐
            return {
                "success": True,
                "suggestions": [
                    {
                        "label": "现代室内设计",
                        "prompt": f"A modern interior design concept for {expert_name}, featuring clean lines and warm lighting",
                        "keywords": ["modern", "interior", "design"],
                        "confidence": 0.6,
                    },
                    {
                        "label": "空间材质可视化",
                        "prompt": f"An architectural visualization showing spatial arrangement and material textures",
                        "keywords": ["architecture", "spatial", "materials"],
                        "confidence": 0.5,
                    },
                    {
                        "label": "概念风格展板",
                        "prompt": f"A conceptual design mood board with color palette and style references",
                        "keywords": ["concept", "mood board", "style"],
                        "confidence": 0.5,
                    },
                ],
            }

        # 从专家报告中提取关键词
        import re

        import jieba

        # 清理内容
        if isinstance(expert_content, dict):
            content_text = json.dumps(expert_content, ensure_ascii=False)
        else:
            content_text = str(expert_content)

        # 提取中文关键词
        words = list(jieba.cut(content_text))

        # 过滤常见词和短词
        stop_words = {
            "的",
            "是",
            "在",
            "和",
            "与",
            "了",
            "将",
            "对",
            "为",
            "等",
            "中",
            "以",
            "及",
            "到",
            "从",
            "有",
            "这",
            "个",
            "人",
            "我",
            "们",
            "你",
            "他",
            "她",
            "它",
        }
        keywords = [w for w in words if len(w) >= 2 and w not in stop_words]

        # 统计词频
        from collections import Counter

        word_freq = Counter(keywords)
        top_keywords = [word for word, _ in word_freq.most_common(30)]

        # 提取设计相关关键词
        design_keywords = []
        design_patterns = [
            r"(空间|布局|风格|材质|色彩|灯光|家具|装饰|功能区|动线)",
            r"(现代|简约|奢华|自然|工业|北欧|日式|中式|美式)",
            r"(客厅|卧室|厨房|书房|阳台|玄关|餐厅|卫生间)",
            r"(木质|石材|金属|玻璃|皮革|织物|大理石)",
            r"(温馨|舒适|明亮|开放|私密|层次|对比)",
        ]

        for pattern in design_patterns:
            matches = re.findall(pattern, content_text)
            design_keywords.extend(matches)

        # 合并关键词
        all_keywords = list(set(design_keywords + top_keywords[:15]))[:20]

        # 生成推荐提示词
        suggestions = []

        # 提示词模板（包含中文标签）
        templates = [
            {
                "label": "空间氛围渲染",
                "template": "A {style} interior design concept featuring {material} elements, {lighting} lighting, and {mood} atmosphere, professional architectural visualization, 8K",
                "defaults": {
                    "style": "modern minimalist",
                    "material": "natural wood and marble",
                    "lighting": "warm ambient",
                    "mood": "serene and inviting",
                },
            },
            {
                "label": "功能区规划",
                "template": "Spatial visualization of {space} with {feature} design, {color} color palette, {style} aesthetic, photorealistic rendering",
                "defaults": {
                    "space": "open living area",
                    "feature": "flowing",
                    "color": "neutral earth tone",
                    "style": "contemporary",
                },
            },
            {
                "label": "设计概念图",
                "template": "Conceptual design for {function} space, emphasizing {quality} and {element}, {style} style, architectural photography",
                "defaults": {
                    "function": "multi-functional",
                    "quality": "natural light flow",
                    "element": "spatial hierarchy",
                    "style": "Scandinavian",
                },
            },
        ]

        # 根据关键词填充模板
        for i, template_info in enumerate(templates):
            template = template_info["template"]
            defaults = template_info["defaults"]

            # 尝试用提取的关键词替换默认值
            filled = template
            used_keywords = []

            for key, default_value in defaults.items():
                # 查找相关关键词
                relevant = [kw for kw in all_keywords if kw not in used_keywords]
                if relevant and i < len(all_keywords):
                    # 选择一个关键词
                    keyword = relevant[i % len(relevant)]
                    used_keywords.append(keyword)
                    filled = filled.replace(
                        f"{{{key}}}",
                        f"{keyword} {default_value.split()[0]}" if len(default_value.split()) > 1 else keyword,
                    )
                else:
                    filled = filled.replace(f"{{{key}}}", default_value)

            suggestions.append(
                {
                    "label": template_info["label"],
                    "prompt": filled,
                    "keywords": used_keywords[:5] if used_keywords else list(defaults.values())[:3],
                    "confidence": 0.8 - (i * 0.1),
                }
            )

        logger.info(f"✅ 生成了 {len(suggestions)} 个推荐提示词")

        return {"success": True, "suggestions": suggestions, "extracted_keywords": all_keywords[:10]}

    except Exception as e:
        logger.error(f"❌ 生成推荐提示词失败: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e), "suggestions": []}


# ============================================================================
# 🔥 v7.48: 图像对话历史 API（Google AI Studio 风格）
# ============================================================================


class ImageChatTurnModel(BaseModel):
    """单轮对话模型"""

    turn_id: str
    type: str  # 'user' | 'assistant'
    timestamp: str
    prompt: Optional[str] = None
    aspect_ratio: Optional[str] = None
    style_type: Optional[str] = None
    reference_image_url: Optional[str] = None
    image: Optional[Dict[str, Any]] = None  # ExpertGeneratedImage
    error: Optional[str] = None


class ImageChatHistoryRequest(BaseModel):
    """保存对话历史请求"""

    turns: List[ImageChatTurnModel]


class RegenerateImageWithContextRequest(BaseModel):
    """带上下文的图像生成请求"""

    expert_name: str
    prompt: str
    aspect_ratio: Optional[str] = "16:9"
    style_type: Optional[str] = None
    reference_image: Optional[str] = None
    context: Optional[str] = None  # 多轮对话上下文
    # 🔥 v7.61: Vision 分析参数
    use_vision_analysis: Optional[bool] = True
    vision_focus: Optional[str] = "comprehensive"
    # 🔥 v7.62: Inpainting 图像编辑参数
    mask_image: Optional[str] = None  # Mask 图像 Base64（黑色=保留，透明=编辑）
    edit_mode: Optional[bool] = False  # 是否为编辑模式（有mask时自动为True）


@app.get("/api/analysis/image-chat-history/{session_id}/{expert_name}")
async def get_image_chat_history(session_id: str, expert_name: str):
    """
    获取专家的图像对话历史

    🔥 v7.48: 支持 Google AI Studio 风格的图像生成对话
    """
    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"📖 获取图像对话历史: session={session_id}, expert={expert_name}")

        # 从 session 中获取对话历史
        image_chat_histories = session.get("image_chat_histories", {})
        expert_history = image_chat_histories.get(expert_name, {})

        if not expert_history:
            # 返回空历史
            return {
                "success": True,
                "history": {
                    "expert_name": expert_name,
                    "session_id": session_id,
                    "turns": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            }

        return {"success": True, "history": expert_history}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取图像对话历史失败: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/analysis/image-chat-history/{session_id}/{expert_name}")
async def save_image_chat_history(session_id: str, expert_name: str, request: ImageChatHistoryRequest):
    """
    保存专家的图像对话历史

    🔥 v7.48: 对话历史持久化，支持删除整条对话记录
    """
    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"💾 保存图像对话历史: session={session_id}, expert={expert_name}, turns={len(request.turns)}")

        # 获取或初始化对话历史存储
        if "image_chat_histories" not in session:
            session["image_chat_histories"] = {}

        # 转换 turns 为字典格式存储
        turns_data = [turn.dict() for turn in request.turns]

        # 保存对话历史
        session["image_chat_histories"][expert_name] = {
            "expert_name": expert_name,
            "session_id": session_id,
            "turns": turns_data,
            "created_at": session["image_chat_histories"]
            .get(expert_name, {})
            .get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
        }

        await session_manager.update(session_id, session)

        logger.info(f"✅ 图像对话历史已保存")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 保存图像对话历史失败: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/analysis/regenerate-image-with-context/{session_id}")
async def regenerate_image_with_context(session_id: str, request: RegenerateImageWithContextRequest):
    """
    带多轮对话上下文的图像生成

    🔥 v7.48: 支持多轮对话上下文传递给 LLM，实现更连贯的图像生成

    上下文格式：将之前的 prompts 拼接为字符串，帮助 LLM 理解用户意图演变
    """
    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"🎨 带上下文生成图像: session={session_id}, expert={request.expert_name}")
        logger.info(f"   提示词: {request.prompt[:100]}...")
        if request.context:
            logger.info(f"   上下文: {request.context[:200]}...")

        if not settings.image_generation.enabled:
            raise HTTPException(status_code=400, detail="图像生成功能未启用")

        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

        image_service = ImageGeneratorService()

        def _build_top_constraints(session_data: Dict[str, Any]) -> str:
            """自动从项目类型与需求分析提取顶层约束，用于统一图像风格。"""
            final_report = session_data.get("final_report", {}) if isinstance(session_data, dict) else {}
            req = {}
            if isinstance(final_report, dict):
                req = final_report.get("requirements_analysis", {}) or final_report.get("structured_data", {}) or {}

            def _pick_str(*vals: Any) -> str:
                for v in vals:
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                return ""

            def _pick_list(val: Any) -> str:
                if isinstance(val, list):
                    cleaned = [str(x).strip() for x in val if str(x).strip()]
                    if cleaned:
                        return "；".join(cleaned[:4])
                return ""

            project_type = _pick_str(
                session_data.get("project_type") if isinstance(session_data, dict) else "",
                req.get("project_type") if isinstance(req, dict) else "",
                final_report.get("project_type") if isinstance(final_report, dict) else "",
            )
            overview = _pick_str(
                req.get("project_overview") if isinstance(req, dict) else "",
                req.get("project_task") if isinstance(req, dict) else "",
                req.get("project_tasks") if isinstance(req, dict) else "",
            )
            objectives = _pick_list(req.get("core_objectives") if isinstance(req, dict) else [])
            constraints = _pick_str(req.get("constraints_opportunities") if isinstance(req, dict) else "")
            user_input = _pick_str(
                session_data.get("user_input") if isinstance(session_data, dict) else "",
                final_report.get("user_input") if isinstance(final_report, dict) else "",
            )

            pieces: List[str] = []
            if project_type:
                pieces.append(f"Project type: {project_type}")
            if overview:
                pieces.append(f"Overview: {overview}")
            if objectives:
                pieces.append(f"Objectives: {objectives}")
            if constraints:
                pieces.append(f"Constraints: {constraints}")
            if user_input and len(pieces) < 3:
                pieces.append(f"User intent: {user_input[:200]}")

            text = "\n".join(pieces)
            if len(text) > 600:
                text = text[:600]
            return text

        def _get_expert_context(session_data: Dict[str, Any], expert_name: str) -> str:
            """🆕 v7.50: 获取专家报告上下文用于 LLM 增强"""
            final_report = session_data.get("final_report", {}) if isinstance(session_data, dict) else {}
            expert_reports = final_report.get("expert_reports", {}) if isinstance(final_report, dict) else {}

            expert_content = expert_reports.get(expert_name, "")
            if isinstance(expert_content, dict):
                # 提取关键字段
                parts = []
                for key in ["structured_data", "content", "narrative_summary"]:
                    if key in expert_content:
                        val = expert_content[key]
                        if isinstance(val, str):
                            parts.append(val[:400])
                        elif isinstance(val, dict):
                            parts.append(json.dumps(val, ensure_ascii=False)[:400])
                return " ".join(parts)[:1000]
            elif isinstance(expert_content, str):
                return expert_content[:1000]
            return ""

        # 🆕 v7.50: 使用 LLM 增强用户输入的提示词
        constraint_text = _build_top_constraints(session)
        expert_context = _get_expert_context(session, request.expert_name)

        # 🔥 v7.61: Vision 分析集成 (如果有参考图且启用 Vision)
        vision_analysis_text = None
        if request.reference_image and request.use_vision_analysis:
            try:
                from intelligent_project_analyzer.services.vision_service import get_vision_service

                logger.info(f"🔍 [v7.61] 开始 Vision 分析参考图...")
                vision_service = get_vision_service()

                vision_result = await vision_service.analyze_design_image(
                    image_data=request.reference_image, analysis_type=request.vision_focus or "comprehensive"
                )

                if vision_result.success:
                    logger.info(f"✅ Vision 分析成功: {len(vision_result.features or {})} 个特征")
                    vision_analysis_text = vision_result.analysis

                    # 添加结构化特征
                    features = vision_result.features or {}
                    if features.get("colors"):
                        vision_analysis_text += f"\n主色调: {', '.join(features['colors'][:3])}"
                    if features.get("styles"):
                        vision_analysis_text += f"\n风格: {', '.join(features['styles'][:3])}"
                    if features.get("materials"):
                        vision_analysis_text += f"\n材质: {', '.join(features['materials'][:3])}"
                else:
                    logger.warning(f"⚠️ Vision 分析失败: {vision_result.error}")

            except Exception as e:
                logger.error(f"❌ Vision 分析异常: {e}")
                # 优雅降级：继续使用纯文本模式

        # 🔥 v7.62: Inpainting 编辑模式路由（双模式架构）
        if request.mask_image:
            logger.info("🎯 [v7.62 Dual-Mode] 检测到 Mask，路由到编辑模式")

            try:
                from intelligent_project_analyzer.services.inpainting_service import get_inpainting_service

                # 获取 Inpainting 服务（需要 OPENAI_API_KEY）
                openai_key = os.getenv("OPENAI_API_KEY")
                inpainting_service = get_inpainting_service(api_key=openai_key)

                if not inpainting_service.is_available():
                    logger.warning("⚠️ Inpainting 服务不可用（缺少 OPENAI_API_KEY），回退到生成模式")
                else:
                    # 调用双模式方法（会自动使用 Inpainting 或回退）
                    result = await image_service.edit_image_with_mask(
                        original_image=request.reference_image,
                        mask_image=request.mask_image,
                        prompt=request.prompt,
                        aspect_ratio=_parse_aspect_ratio(request.aspect_ratio),
                        style=request.style_type,
                        inpainting_service=inpainting_service,
                    )

                    # 如果成功，直接返回结果（跳过后续 LLM 增强）
                    if result.success:
                        import uuid

                        new_image_id = str(uuid.uuid4())[:8]

                        new_image_data = {
                            "expert_name": request.expert_name,
                            "image_url": result.image_url,
                            "prompt": request.prompt,
                            "prompt_used": result.revised_prompt or request.prompt,
                            "id": new_image_id,
                            "aspect_ratio": request.aspect_ratio,
                            "style_type": request.style_type,
                            "created_at": datetime.now().isoformat(),
                            "edit_mode": True,  # 🆕 v7.62: 标记为编辑模式
                            "model_used": result.model_used,
                        }

                        # 更新 session
                        final_report = session.get("final_report", {})
                        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

                        if request.expert_name in generated_images_by_expert:
                            existing = generated_images_by_expert[request.expert_name]
                            if isinstance(existing, dict) and "images" not in existing:
                                existing = {"expert_name": request.expert_name, "images": [existing]}
                            if "images" not in existing:
                                existing["images"] = []
                            existing["images"].append(new_image_data)
                            generated_images_by_expert[request.expert_name] = existing
                        else:
                            generated_images_by_expert[request.expert_name] = {
                                "expert_name": request.expert_name,
                                "images": [new_image_data],
                            }

                        final_report["generated_images_by_expert"] = generated_images_by_expert
                        session["final_report"] = final_report
                        await session_manager.update(session_id, session)

                        logger.info(f"✅ [Inpainting Mode] 图像编辑成功: id={new_image_id}")

                        return {
                            "success": True,
                            "image_url": result.image_url,
                            "image_id": new_image_id,
                            "image_data": new_image_data,
                            "mode": "inpainting",  # 🆕 标记模式
                        }

            except ImportError:
                logger.warning("⚠️ InpaintingService 未安装，回退到生成模式")
            except Exception as e:
                logger.error(f"❌ Inpainting 模式异常: {e}")
                logger.warning("🔄 回退到生成模式")

        # 如果没有 Mask 或 Inpainting 失败，继续使用生成模式（原有逻辑）

        # 调用 LLM 增强方法（包含 Vision 特征）
        enhanced_prompt = await image_service._enhance_prompt_with_user_input(
            user_prompt=request.prompt,
            expert_context=expert_context,
            conversation_history=request.context or "",
            project_constraints=constraint_text,
            vision_analysis=vision_analysis_text,
        )

        logger.info(f"🧠 [v7.50] 提示词增强: {len(request.prompt)} → {len(enhanced_prompt)} 字符")
        logger.debug(f"📝 增强后提示词: {enhanced_prompt[:200]}...")

        # 🔥 v7.60.4: 修复参数名称和类型（style_type→style, string→enum）
        result = await image_service.generate_image(
            prompt=enhanced_prompt, aspect_ratio=_parse_aspect_ratio(request.aspect_ratio), style=request.style_type
        )

        if not result.success:
            return {"success": False, "error": result.error or "图像生成失败"}

        # 🔥 v7.60.5: 累加图像生成Token到会话metadata（后置Token追踪）
        if result.total_tokens > 0:
            from intelligent_project_analyzer.utils.token_utils import update_session_tokens

            token_data = {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            }
            success = await update_session_tokens(
                session_manager, session_id, token_data, agent_name="image_generation"
            )
            if success:
                logger.info(f"✅ [图像Token-带上下文] 已累加 {result.total_tokens} tokens 到会话 {session_id}")

        import uuid

        new_image_id = str(uuid.uuid4())[:8]

        new_image_data = {
            "expert_name": request.expert_name,
            "image_url": result.image_url,
            "prompt": request.prompt,  # 用户原始输入
            "prompt_used": enhanced_prompt,  # 🆕 v7.50: 实际使用的增强后提示词
            "id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
            "created_at": datetime.now().isoformat(),
            "has_context": bool(request.context),  # 标记是否使用了上下文
            "llm_enhanced": len(enhanced_prompt) > len(request.prompt),  # 🆕 v7.50: 标记是否经过 LLM 增强
        }

        # 同时更新到 generated_images_by_expert（保持兼容性）
        final_report = session.get("final_report", {})
        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

        if request.expert_name in generated_images_by_expert:
            existing = generated_images_by_expert[request.expert_name]
            if isinstance(existing, dict) and "images" not in existing:
                existing = {"expert_name": request.expert_name, "images": [existing]}
            if "images" not in existing:
                existing["images"] = []
            existing["images"].append(new_image_data)
            generated_images_by_expert[request.expert_name] = existing
        else:
            generated_images_by_expert[request.expert_name] = {
                "expert_name": request.expert_name,
                "images": [new_image_data],
            }

        final_report["generated_images_by_expert"] = generated_images_by_expert
        session["final_report"] = final_report
        await session_manager.update(session_id, session)

        logger.info(f"✅ 带上下文图像生成成功: id={new_image_id}")

        return {"success": True, "image_url": result.image_url, "image_id": new_image_id, "image_data": new_image_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 带上下文图像生成失败: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.post("/api/analysis/report/{session_id}/suggest-questions")
async def generate_followup_questions(session_id: str):
    """
    基于分析报告生成智能推荐问题

    🔥 新功能 (2025-11-29): 使用LLM根据报告内容生成启发性追问
    """
    # 获取会话和报告
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 读取报告文本
    pdf_path = session.get("pdf_path")
    report_text = ""

    if pdf_path and os.path.exists(pdf_path):
        try:
            with open(pdf_path, "r", encoding="utf-8") as f:
                report_text = f.read()
        except Exception as e:
            logger.warning(f"⚠️ 无法读取报告文件: {e}")
            final_report = session.get("final_report", {})
            if isinstance(final_report, dict):
                import json

                report_text = json.dumps(final_report, ensure_ascii=False, indent=2)
            else:
                report_text = str(final_report)
    else:
        final_report = session.get("final_report", {})
        if isinstance(final_report, dict):
            import json

            report_text = json.dumps(final_report, ensure_ascii=False, indent=2)
        else:
            report_text = str(final_report) if final_report else ""

    default_questions = ["能否进一步分析关键技术的实现难点？", "请详细说明资源配置的优先级？", "有哪些潜在风险需要特别关注？", "能否提供更具体的实施时间表？"]

    def build_fallback_response(reason: str):
        logger.info(f"💡 使用通用追问，原因: {reason}")
        return {"questions": default_questions, "source": "fallback", "message": reason}

    if not report_text or len(report_text) < 100:
        return build_fallback_response("报告内容不足 100 字，使用系统默认问题")

    # 使用LLM生成智能推荐问题
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        logger.info(f"🔍 开始生成智能推荐问题: session_id={session_id}, 报告长度={len(report_text)}")

        llm = LLMFactory.create_llm(temperature=0.7, timeout=30)

        # 截取报告前3000字符用于分析
        report_summary = report_text[:3000] if len(report_text) > 3000 else report_text

        prompt = f"""作为项目分析专家，基于以下分析报告，生成4个启发性的追问。

要求：
1. 每个问题都要针对报告中的具体内容，不要问泛泛的通用问题
2. 问题要能引发更深入的讨论和分析
3. 聚焦于：实现难点、潜在风险、资源优化、创新机会等方面
4. 问题要简洁清晰，15-25字为宜
5. 直接输出4个问题，每行一个，不要编号

分析报告摘要：
{report_summary}

请生成4个追问："""

        messages = [SystemMessage(content="你是一位资深项目分析专家，擅长从分析报告中发现深层次问题。"), HumanMessage(content=prompt)]

        # 🔥 新增：重试机制
        max_retries = 2
        response = None
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"📡 调用LLM生成推荐问题 (尝试 {attempt + 1}/{max_retries + 1})...")
                response = await asyncio.wait_for(asyncio.to_thread(llm.invoke, messages), timeout=30)
                logger.info(f"✅ LLM调用成功")
                break
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"⏱️ LLM调用超时，重试 {attempt + 1}/{max_retries}")
                    await asyncio.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    logger.error(f"❌ LLM调用超时，已达最大重试次数")
                    raise
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ LLM调用失败: {type(e).__name__}: {e}，重试 {attempt + 1}/{max_retries}")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise

        if response is None:
            raise Exception("LLM调用失败，未获取到响应")

        questions_text = response.content.strip()

        # 解析问题列表
        questions = [q.strip() for q in questions_text.split("\n") if q.strip() and len(q.strip()) > 5]

        # 确保有4个问题
        if len(questions) < 4:
            questions.extend(["能否进一步分析关键技术的实现难点？", "请详细说明资源配置的优先级？", "有哪些潜在风险需要特别关注？", "能否提供更具体的实施时间表？"])
        questions = questions[:4]

        logger.info(f"✅ 已为会话 {session_id} 生成 {len(questions)} 个智能推荐问题: {questions}")
        return {"questions": questions, "source": "llm"}

    except Exception as e:
        logger.error(f"❌ 生成推荐问题失败: {type(e).__name__}: {e}")
        logger.error(f"   模型配置: model={settings.llm.model}, base_url={settings.llm.api_base}")
        logger.error(f"   报告长度: {len(report_text)} 字符")
        return build_fallback_response("智能生成失败，已回退默认问题")


@app.get("/api/analysis/{session_id}/followup-history")
async def get_followup_history(session_id: str):
    """
    获取追问历史

    🔥 v3.11 新增：支持查询完整对话历史

    Returns:
        {
            "session_id": str,
            "total_turns": int,
            "history": List[Dict]  # 按时间顺序排列的对话历史
        }
    """
    try:
        # 检查会话是否存在
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

        # 获取完整追问历史
        history = await followup_history_manager.get_history(session_id, limit=None)

        logger.info(f"📚 查询追问历史: {session_id}, 共{len(history)}轮")

        return {"session_id": session_id, "total_turns": len(history), "history": history}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取追问历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取追问历史失败: {str(e)}")


@app.get("/api/sessions")
async def list_sessions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user),
):
    """
    列出当前用户的会话（需要认证）

    返回当前登录用户的活跃会话列表（从Redis获取）

    🔒 安全：需要JWT认证，只返回当前用户的会话
    🔧 v7.35: 开发模式返回所有会话
    🔥 v7.105: 支持分页（优化首屏加载性能）
    🔥 v7.120 P1: 添加5秒TTL缓存（4.09s→0.05s）
    """
    try:
        username = current_user.get("username")

        # 🔥 P1优化: 尝试从缓存获取
        cache_key = f"sessions:{username}"
        cached_result = sessions_cache.get(cache_key)

        if cached_result:
            logger.debug(f"⚡ 使用会话列表缓存: {username}")
            all_sessions = cached_result
        else:
            # 从Redis获取所有会话
            start_time = time.time()
            all_sessions = await session_manager.get_all_sessions()
            elapsed = time.time() - start_time

            # 缓存结果（仅缓存原始数据，避免缓存分页结果）
            sessions_cache.set(cache_key, all_sessions)
            logger.info(f"🔄 刷新会话列表缓存: {username} ({elapsed:.2f}s)")

        # 🆕 v7.106.1: 过滤null/None会话（数据完整性保护）
        all_sessions = [s for s in all_sessions if s is not None and isinstance(s, dict)]

        # 🔧 v7.35: 开发模式返回所有会话
        if DEV_MODE and username == "dev_user":
            logger.info(f"🔧 [DEV_MODE] 返回所有会话: {len(all_sessions)} 个")
            user_sessions = all_sessions
        else:
            # 🔒 过滤：只返回当前用户的会话
            user_sessions = [
                session
                for session in all_sessions
                if session.get("user_id") == username or session.get("user_id") == "web_user"  # 兼容旧数据
            ]

        # 按创建时间倒序排序
        user_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 🆕 v7.106.1: 后台清理无效会话索引（不阻塞响应）
        asyncio.create_task(session_manager.cleanup_invalid_user_sessions(current_user.get("username")))

        # 🔥 v7.105: 分页处理
        total = len(user_sessions)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_sessions = user_sessions[start:end]

        # 🔥 v7.109: 修复 has_next 边界问题 + 诊断日志
        has_next = (page * page_size) < total
        logger.info(
            f"📊 会话分页诊断 | 用户: {current_user.get('username', 'unknown')} | "
            f"页码: {page}/{math.ceil(total/page_size) if page_size > 0 else 0} | "
            f"范围: [{start}:{end}] | "
            f"返回: {len(paginated_sessions)}条 | "
            f"总计: {total}条 | "
            f"has_next: {has_next}"
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
            "sessions": [
                {
                    "session_id": session.get("session_id"),
                    "status": session.get("status"),
                    "mode": session.get("mode", "api"),
                    "created_at": session.get("created_at"),
                    "user_input": session.get("user_input", ""),
                    "pinned": session.get("pinned", False),  # 🔥 v7.60.6: 返回置顶状态
                    # 🔥 v7.107: 新增字段 - 深度思考模式和进度信息
                    "analysis_mode": session.get("analysis_mode", "normal"),
                    "progress": session.get("progress", 0.0),
                    "current_stage": session.get("current_stage"),
                }
                for session in paginated_sessions
            ],
        }
    except HTTPException:
        # 认证失败，返回空列表
        return {"total": 0, "sessions": []}
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return {"total": 0, "sessions": []}


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, updates: Dict[str, Any]):
    """更新会话信息（重命名、置顶等）"""
    try:
        sm = await _get_session_manager()
        # 验证会话是否存在
        session = await sm.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 更新会话
        success = await sm.update(session_id, updates)
        if not success:
            raise HTTPException(status_code=500, detail="更新会话失败")

        logger.info(f"✅ 会话已更新: {session_id}, 更新内容: {updates}")
        return {"success": True, "message": "会话更新成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):  # 🆕 v7.106: 添加用户认证
    """
    删除会话（含权限校验和级联删除）

    🆕 v7.106: 添加权限校验、级联删除文件、同步删除归档副本
    🆕 v7.107: 支持删除归档会话（当Redis中找不到时检查归档数据库）
    🔥 v7.120 P1: 删除后使缓存失效
    """
    try:
        # 🔥 v7.120 P1: 使所有用户缓存失效（因为不知道会话属于谁）
        sessions_cache.invalidate()
        sm = await _get_session_manager()
        # 1. 验证会话是否存在（优先检查Redis）
        session = await sm.get(session_id)
        is_archived = False

        # 🆕 v7.107: 如果Redis中找不到，检查归档数据库
        if not session:
            try:
                if archive_manager:
                    session = await archive_manager.get_archived_session(session_id)
                    if session:
                        is_archived = True
                        logger.info(f"🗄️ 会话存在于归档数据库: {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ 查询归档数据库失败: {e}")

        if not session:
            # 🔧 DEV_MODE 兜底：部分测试只模拟了 redis.delete(1) 而没有提供 redis.get 数据。
            # 在这种场景下，允许直接根据 delete 返回值判断是否删除成功。
            if DEV_MODE and getattr(sm, "redis_client", None) is not None:
                try:
                    deleted = await sm.redis_client.delete(sm._get_session_key(session_id))
                    if deleted:
                        return {"success": True, "message": "会话删除成功"}
                except Exception:
                    # 忽略兜底失败，回落到标准 404
                    pass
            raise HTTPException(status_code=404, detail="会话不存在")

        # 🆕 2. 权限校验：只能删除自己的会话
        # 🔧 v7.114: 修复权限校验逻辑，支持多种user_id格式
        session_user_id = session.get("user_id", "")
        current_username = current_user.get("username", "")

        # 兼容以下情况：
        # 1. 正常情况：session.user_id == current_user.username
        # 2. 未登录用户会话：user_id == "web_user" (允许任何登录用户删除)
        # 3. 开发模式：dev_user 可以删除所有会话
        is_owner = (
            session_user_id == current_username
            or session_user_id == "web_user"
            or (DEV_MODE and current_username == "dev_user")
        )

        if not is_owner:
            logger.warning(f"⚠️ 权限拒绝 | 用户: {current_username} | " f"尝试删除会话: {session_id} | 会话所有者: {session_user_id}")
            raise HTTPException(status_code=403, detail="无权删除此会话")

        logger.info(f"✅ 权限验证通过 | 用户: {current_username} | " f"删除会话: {session_id}")

        # 3. 删除会话（根据来源选择删除方式）
        if is_archived:
            # 🆕 v7.107: 删除归档会话
            try:
                if archive_manager:
                    success = await archive_manager.delete_archived_session(session_id)
                    if not success:
                        raise HTTPException(status_code=500, detail="删除归档会话失败")
                    logger.info(f"✅ 归档会话已删除: {session_id}")
                else:
                    raise HTTPException(status_code=500, detail="归档管理器未初始化")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ 删除归档会话失败: {e}")
                raise HTTPException(status_code=500, detail=f"删除归档会话失败: {str(e)}")
        else:
            # 删除Redis中的活跃会话（含用户索引、进度数据等）
            success = await sm.delete(session_id)
            if not success:
                raise HTTPException(status_code=500, detail="删除会话失败")

        # 4. 清理内存中的workflow实例（仅活跃会话需要）
        if not is_archived and session_id in workflows:
            del workflows[session_id]
            logger.info(f"🗑️ 清理工作流实例: {session_id}")

        # 🆕 5. 删除会话相关文件
        import shutil
        from pathlib import Path

        try:
            # 删除概念图
            image_dir = Path("data/generated_images") / session_id
            if image_dir.exists():
                shutil.rmtree(image_dir)
                logger.info(f"🗑️ 删除概念图目录: {image_dir}")

            # 删除追问图片
            followup_dir = Path("data/followup_images") / session_id
            if followup_dir.exists():
                shutil.rmtree(followup_dir)
                logger.info(f"🗑️ 删除追问图片目录: {followup_dir}")

            # 删除上传文件
            upload_dir = Path("data/uploads") / session_id
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
                logger.info(f"🗑️ 删除上传文件目录: {upload_dir}")
        except Exception as e:
            logger.warning(f"⚠️ 删除文件失败（不影响主流程）: {e}")

        # 🆕 6. 同步删除归档副本（如果删除的是活跃会话，同时删除归档副本）
        if not is_archived and archive_manager:
            try:
                archived = await archive_manager.get_archived_session(session_id)
                if archived:
                    await archive_manager.delete_archived_session(session_id)
                    logger.info(f"🗑️ 同时删除归档副本: {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ 删除归档副本失败（不影响主流程）: {e}")

        # 🆕 v7.107: 根据来源返回不同的成功消息
        message = "归档会话删除成功" if is_archived else "会话删除成功"
        logger.info(f"✅ 会话已完整删除: {session_id} ({'归档' if is_archived else '活跃'}), 用户: {current_user.get('username')}")
        return {"success": True, "message": message}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 对话模式 API ====================


@app.post("/api/conversation/ask", response_model=ConversationResponse)
async def ask_question(request: ConversationRequest):
    """
    对话模式提问

    完成分析后，用户可以针对报告内容继续提问
    """
    session_id = request.session_id
    question = request.question

    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析未完成，无法进入对话模式。当前状态: {session['status']}")

    logger.info(f"💬 Conversation question from {session_id}: {question[:50]}...")

    try:
        # 🔥 v7.15: 使用 FollowupAgent (LangGraph)

        # 从会话中提取上下文
        final_state = session.get("final_state", {})

        # 构建 report_context
        report_context = {
            "final_report": session.get("final_report", {}),
            "agent_results": final_state.get("agent_results", {}),
            "requirements": final_state.get("requirements_analysis", {}),
            "user_input": session.get("user_input", ""),
        }

        # 获取对话历史
        history_data = session.get("conversation_history", [])

        # 🔥 调用 FollowupAgent
        agent = FollowupAgent()
        result = agent.answer_question(
            question=question, report_context=report_context, conversation_history=history_data
        )

        # 保存到会话
        conversation_history = session.get("conversation_history", [])

        turn_data = {
            "question": question,
            "answer": result["answer"],
            "intent": result["intent"],
            "referenced_sections": result["references"],
            "timestamp": datetime.now().isoformat(),
        }

        conversation_history.append(turn_data)

        # 更新 Redis
        await session_manager.update(session_id, {"conversation_history": conversation_history})

        conversation_id = len(conversation_history)

        logger.info(f"✅ Conversation turn {conversation_id} completed")

        return ConversationResponse(
            answer=result["answer"],
            intent=result["intent"],
            references=result["references"],
            suggestions=result["suggestions"],
            conversation_id=conversation_id,
        )

    except Exception as e:
        logger.error(f"❌ Conversation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")


@app.get("/api/conversation/history/{session_id}")
async def get_conversation_history(session_id: str):
    """获取对话历史"""
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    history = session.get("conversation_history", [])
    return {"session_id": session_id, "history": history, "total": len(history)}


@app.post("/api/conversation/end")
async def end_conversation(session_id: str):
    """结束对话模式"""
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    await session_manager.update(session_id, {"conversation_mode": False})

    logger.info(f"💬 Conversation ended for session {session_id}")

    return {"session_id": session_id, "message": "对话已结束", "total_turns": len(session.get("conversation_history", []))}


# ==================== 会话归档 API (v3.6新增) ====================


@app.post("/api/sessions/{session_id}/archive")
async def archive_session(session_id: str, force: bool = False):
    """
    归档会话到数据库（永久保存）

    Args:
        session_id: 会话ID
        force: 是否强制归档（即使状态不是completed）

    Returns:
        归档状态
    """
    if not archive_manager:
        # 测试/轻量部署：未启用归档功能时按“资源不存在”处理
        raise HTTPException(status_code=404, detail="会话归档功能未启用")

    # 获取会话数据
    sm = await _get_session_manager()
    session = await sm.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 归档会话
    try:
        success = await archive_manager.archive_session(session_id=session_id, session_data=session, force=force)

        if success:
            logger.info(f"📦 会话已归档: {session_id}")
            return {"success": True, "session_id": session_id, "message": "会话已成功归档到数据库（永久保存）"}
        else:
            raise HTTPException(status_code=400, detail="会话归档失败（可能已归档或状态不允许）")
    except Exception as e:
        logger.error(f"❌ 归档会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"归档失败: {str(e)}")


@app.get("/api/sessions/archived")
async def list_archived_sessions(
    limit: int = 50, offset: int = 0, status: Optional[str] = None, pinned_only: bool = False
):
    """
    列出归档会话（支持分页、过滤）

    Args:
        limit: 每页数量（默认50）
        offset: 偏移量（默认0）
        status: 过滤状态（可选: completed, failed, rejected）
        pinned_only: 是否只显示置顶会话

    Returns:
        归档会话列表
    """
    if not archive_manager:
        # 未启用归档功能：返回空列表（保持 200，便于前端/测试兼容）
        return {"total": 0, "limit": limit, "offset": offset, "sessions": []}

    try:
        sessions = await archive_manager.list_archived_sessions(
            limit=limit, offset=offset, status=status, pinned_only=pinned_only
        )

        total = await archive_manager.count_archived_sessions(status=status, pinned_only=pinned_only)

        return {"total": total, "limit": limit, "offset": offset, "sessions": sessions}
    except Exception as e:
        logger.error(f"❌ 获取归档会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.get("/api/sessions/archived/stats")
async def get_archive_stats():
    """获取归档会话统计信息。

    注意：必须在 `/api/sessions/archived/{session_id}` 之前注册，否则会被动态路由抢先匹配。
    """
    if not archive_manager:
        # 未启用归档功能：返回空统计（保持 200，便于前端/测试兼容）
        return {
            "total": 0,
            "by_status": {"completed": 0, "failed": 0, "rejected": 0},
            "pinned": 0,
            "updated_at": datetime.now().isoformat(),
        }

    try:
        total = await archive_manager.count_archived_sessions()
        completed = await archive_manager.count_archived_sessions(status="completed")
        failed = await archive_manager.count_archived_sessions(status="failed")
        rejected = await archive_manager.count_archived_sessions(status="rejected")
        pinned = await archive_manager.count_archived_sessions(pinned_only=True)

        return {
            "total": total,
            "by_status": {
                "completed": completed,
                "failed": failed,
                "rejected": rejected,
            },
            "pinned": pinned,
            "updated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ 获取归档统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.get("/api/sessions/archived/{session_id}")
async def get_archived_session(session_id: str):
    """
    获取归档会话详情

    Args:
        session_id: 会话ID

    Returns:
        归档会话完整数据
    """
    if not archive_manager:
        raise HTTPException(status_code=404, detail="会话归档功能未启用")

    try:
        session = await archive_manager.get_archived_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="归档会话不存在")

        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取归档会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


class ArchivedSessionUpdateRequest(BaseModel):
    """归档会话元数据更新请求。

    兼容：历史/测试使用 `title` 字段表示显示名称。
    """

    title: Optional[str] = None
    display_name: Optional[str] = None
    pinned: Optional[bool] = None
    tags: Optional[List[str]] = None


@app.patch("/api/sessions/archived/{session_id}")
async def update_archived_session_metadata(
    session_id: str, payload: Optional[ArchivedSessionUpdateRequest] = Body(default=None)
):
    """
    更新归档会话元数据（重命名、置顶、标签）

    Args:
        session_id: 会话ID
        display_name: 自定义显示名称
        pinned: 是否置顶
        tags: 标签列表

    Returns:
        更新状态
    """
    if not archive_manager:
        raise HTTPException(status_code=404, detail="会话归档功能未启用")

    payload = payload or ArchivedSessionUpdateRequest()
    display_name = payload.display_name or payload.title

    try:
        success = await archive_manager.update_metadata(
            session_id=session_id,
            display_name=display_name,
            pinned=payload.pinned,
            tags=payload.tags,
        )

        if success:
            logger.info(f"✏️ 归档会话元数据已更新: {session_id}")
            return {"success": True, "session_id": session_id, "message": "元数据更新成功"}
        else:
            raise HTTPException(status_code=404, detail="归档会话不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新归档会话元数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@app.delete("/api/sessions/archived/{session_id}")
async def delete_archived_session(session_id: str, current_user: dict = Depends(get_current_user)):  # 🆕 v7.114: 添加JWT认证
    """
    删除归档会话（含权限校验）

    🔒 v7.114: 添加权限校验，修复安全漏洞

    Args:
        session_id: 会话ID
        current_user: 当前登录用户（从JWT获取）

    Returns:
        删除状态
    """
    if not archive_manager:
        raise HTTPException(status_code=404, detail="会话归档功能未启用")

    try:
        # 🔒 1. 获取归档会话并验证所有权
        session = await archive_manager.get_archived_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="归档会话不存在")

        # 🔒 2. 权限校验（与活跃会话相同逻辑）
        session_user_id = session.get("user_id", "")
        current_username = current_user.get("username", "")

        is_owner = (
            session_user_id == current_username
            or session_user_id == "web_user"
            or (DEV_MODE and current_username == "dev_user")
        )

        if not is_owner:
            logger.warning(f"⚠️ 权限拒绝 | 用户: {current_username} | " f"尝试删除归档会话: {session_id} | 会话所有者: {session_user_id}")
            raise HTTPException(status_code=403, detail="无权删除此归档会话")

        # 3. 执行删除
        success = await archive_manager.delete_archived_session(session_id)

        if not success:
            raise HTTPException(status_code=500, detail="归档会话删除失败")

        logger.info(f"✅ 归档会话已删除: {session_id} | 用户: {current_username}")

        return {"success": True, "session_id": session_id, "message": "归档会话删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除归档会话失败: {session_id} | 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@app.get("/api/sessions/{session_id}")
async def get_session_by_id(session_id: str):
    """获取单个会话详情（用于测试/调试与前端详情页）。

    注意：必须在 /api/sessions/archived* 路由之后注册，避免与 archived 子路由冲突。
    """
    sm = await _get_session_manager()
    session = await sm.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


# ============================================================================
# 🆕 v7.108: 概念图管理API端点
# ============================================================================


@app.post("/api/images/regenerate")
async def regenerate_concept_image(
    session_id: str = Query(..., description="会话ID"),
    deliverable_id: str = Query(..., description="交付物ID"),
    aspect_ratio: str = Query(default="16:9", description="宽高比（16:9, 9:16, 1:1）"),
):
    """
    重新生成指定交付物的概念图

    Args:
        session_id: 会话ID
        deliverable_id: 交付物ID
        aspect_ratio: 宽高比（16:9, 9:16, 1:1）

    Returns:
        新生成的图片元数据
    """
    try:
        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService
        from intelligent_project_analyzer.services.image_storage_manager import ImageStorageManager
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        # 获取会话状态
        session_manager = RedisSessionManager()
        state = session_manager.get_state(session_id)

        if not state:
            raise HTTPException(status_code=404, detail="会话不存在")

        deliverable_metadata = state.get("deliverable_metadata", {}).get(deliverable_id)
        if not deliverable_metadata:
            raise HTTPException(status_code=404, detail="交付物不存在")

        # 获取专家分析（从agent_results中）
        owner_role = deliverable_metadata.get("owner_role")
        agent_results = state.get("agent_results", {})
        expert_result = agent_results.get(owner_role, {})
        expert_analysis = expert_result.get("analysis", "")[:500]

        # 删除旧图片
        await ImageStorageManager.delete_image(session_id, deliverable_id)

        # 重新生成
        image_generator = ImageGeneratorService()
        new_image = await image_generator.generate_deliverable_image(
            deliverable_metadata=deliverable_metadata,
            expert_analysis=expert_analysis,
            session_id=session_id,
            project_type=state.get("project_type", "interior"),
            aspect_ratio=aspect_ratio,
        )

        return {"status": "success", "image": new_image.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 重新生成概念图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/images/{session_id}/{deliverable_id}")
async def delete_concept_image(session_id: str, deliverable_id: str):
    """删除指定交付物的概念图"""
    try:
        from intelligent_project_analyzer.services.image_storage_manager import ImageStorageManager

        success = await ImageStorageManager.delete_image(session_id, deliverable_id)

        if not success:
            raise HTTPException(status_code=404, detail="图片不存在")

        return {"status": "success", "message": "图片已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除概念图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/images/{session_id}")
async def list_session_images(session_id: str):
    """获取会话的所有概念图列表"""
    try:
        from intelligent_project_analyzer.services.image_storage_manager import ImageStorageManager

        images = await ImageStorageManager.get_session_images(session_id)

        return {"session_id": session_id, "total": len(images), "images": images}

    except Exception as e:
        logger.error(f"❌ 获取图片列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _wait_for_connected(websocket: WebSocket, timeout: float = 2.0) -> bool:
    """
    ✅ Fix 1.1 + v7.118: Wait for WebSocket to reach CONNECTED state

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
            logger.error(f"❌ WebSocket 连接超时 (state: {websocket.client_state.name}, elapsed: {elapsed:.2f}s)")
            return False
        await asyncio.sleep(0.05)

    logger.debug(f"✅ WebSocket已连接 (耗时: {(asyncio.get_event_loop().time() - start):.2f}s)")
    return True


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket 端点 - 实时推送工作流状态更新

    客户端连接后，会实时接收：
    - 节点更新 (node_update)
    - 状态更新 (status_update)
    - 中断通知 (interrupt)
    """
    # 接受连接
    await websocket.accept()
    logger.info(f"🔌 WebSocket 握手完成: {session_id}")

    try:
        # ✅ P0修复: 先等待达到CONNECTED状态，再加入连接池
        is_connected = await _wait_for_connected(websocket, timeout=3.0)
        if not is_connected:
            logger.error(f"❌ WebSocket 连接超时，关闭连接: {session_id}")
            await websocket.close(code=1008, reason="Connection timeout")
            return  # 不加入连接池，直接返回

        # ✅ P0修复: 仅在确认连接后才加入连接池
        if session_id not in websocket_connections:
            websocket_connections[session_id] = []
        websocket_connections[session_id].append(websocket)
        logger.info(f"✅ WebSocket 已加入连接池: {session_id}")

        # 发送初始状态（简化重试逻辑）
        if session_manager:
            session = await session_manager.get(session_id)
            if session:
                # ✅ P0修复: 连接已确认，直接发送初始状态（无需重试）
                await websocket.send_json(
                    {
                        "type": "initial_status",
                        "status": session.get("status", "pending"),
                        "progress": session.get("progress", 0),
                        "current_node": session.get("current_node"),
                        "detail": session.get("detail"),
                    }
                )
                logger.debug(f"✅ WebSocket 初始状态已发送: {session_id}")

        # 保持连接并接收客户端心跳
        while True:
            try:
                # 接收客户端消息（主要用于心跳检测）
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # 可选：处理客户端发送的消息
                if data == "ping":
                    # ✅ P0修复: 发送pong前检查连接状态
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # 60秒无心跳，发送 ping 检查连接
                # ✅ P0修复: 发送ping前检查连接状态
                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket 断开: {session_id}")
    except Exception as e:
        # ✅ v7.118: 改进错误处理，忽略常见的连接关闭错误
        error_str = str(e)
        if any(keyword in error_str for keyword in ["Cannot call", "send", "close message", "not connected"]):
            logger.debug(f"🔌 WebSocket 连接已关闭: {session_id} ({type(e).__name__})")
        else:
            logger.error(f"❌ WebSocket 错误: {session_id}, {type(e).__name__}: {e}", exc_info=True)
    finally:
        # 从连接池移除
        if session_id in websocket_connections:
            if websocket in websocket_connections[session_id]:
                websocket_connections[session_id].remove(websocket)
            # 如果没有连接了，清理字典
            if not websocket_connections[session_id]:
                del websocket_connections[session_id]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")
