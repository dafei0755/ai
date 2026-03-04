"""
FastAPI 后端服务器

提供 RESTful API 接口，支持前后端分离架构
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

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

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

#  v7.120: 初始化生产级日志系统（环境感知配置）
from intelligent_project_analyzer.config.logging_config import setup_logging

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


# MT-1 迁移：_parse_aspect_ratio / sync_checkpoint_to_redis / get_current_user /
# get_user_identifier / optional_auth / _serialize_for_json / DEV_MODE / sessions_cache
# 已迁移至 api/deps.py — 此处重新导出以保持 _server 代理兼容性
from .deps import (  # noqa: E402
    DEV_MODE,
    _parse_aspect_ratio,
    _serialize_for_json,
    get_current_user,
    get_current_user_optional,
    get_user_identifier,
    optional_auth,
    sessions_cache,
    sync_checkpoint_to_redis,
)

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langgraph.checkpoint.base import BaseCheckpointSaver

#  v3.11新增: 追问历史管理器
from intelligent_project_analyzer.services.followup_history_manager import FollowupHistoryManager

#  Redis 会话管理器
from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

#  v3.6新增: 会话归档管理器
from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager

#  使用新的统一配置 - 不再需要load_dotenv()
from intelligent_project_analyzer.settings import settings
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

# � v7.145: Checkpoint 到 Redis 数据同步函数
# MT-1 迁移：sync_checkpoint_to_redis 已迁移至 api/deps.py


# � v7.120 P1优化: TTL缓存工具类（用于会话列表缓存 4.09s→0.05s）
# MT-1 迁移：TTLCache / sessions_cache / DEV_MODE 已迁移至 api/deps.py


# MT-1 迁移：get_current_user 已迁移至 api/deps.py


# MT-1 迁移：get_user_identifier 已迁移至 api/deps.py


#  v7.130: 可选认证依赖函数（Token存在则验证，不存在也允许访问）
# MT-1 迁移：optional_auth / get_current_user_optional 已迁移至 api/deps.py


# 全局变量存储工作流实例
workflows: Dict[str, MainWorkflow] = {}

# LangGraph 检查点存储（异步版，全局复用）
async_checkpointer: BaseCheckpointSaver[str] | None = None
async_checkpointer_lock: asyncio.Lock | None = None

#  Redis 会话管理器实例（替代内存字典）
session_manager: RedisSessionManager | None = None


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
archive_manager: SessionArchiveManager | None = None

#  v3.11新增: 追问历史管理器实例
followup_history_manager: FollowupHistoryManager | None = None

# WebSocket 连接管理
websocket_connections: Dict[str, List[WebSocket]] = {}  # session_id -> [websocket1, websocket2, ...]

# Redis Pub/Sub 支持
import redis.asyncio as aioredis

redis_pubsub_client: aioredis.Redis | None = None
redis_pubsub_task: asyncio.Task | None = None

#  v7.1.2新增: PDF 缓存（性能优化）
from cachetools import TTLCache

pdf_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)  # 100项，1小时过期


# MT-1 迁移：_serialize_for_json 已迁移至 api/deps.py


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
# ⚠️ 深度搜索功能暂停开放 — 由 feature_flags.DEEP_SEARCH_ENABLED 控制，恢复时设置环境变量 DEEP_SEARCH_ENABLED=true
try:
    from intelligent_project_analyzer.config.feature_flags import (
        DEEP_SEARCH_ENABLED as _DEEP_SEARCH_ENABLED,
    )

    if _DEEP_SEARCH_ENABLED:
        from intelligent_project_analyzer.api.search_routes import router as search_router

        app.include_router(search_router)
        logger.info(" 搜索模式路由已注册")
    else:
        logger.info("⏸️ 搜索模式路由已暂停（DEEP_SEARCH_ENABLED=false）")
except Exception as e:
    logger.warning(f"️ 搜索模式路由加载失败: {e}")

#  v7.216: 搜索质量监控路由
try:
    from intelligent_project_analyzer.api.search_quality_routes import (
        router as search_quality_router,
    )

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
    from intelligent_project_analyzer.api.routes.admin_dashboard_routes import (
        router as admin_dashboard_router,
    )

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


# ── MT-1: 数据模型及报告辅助函数已迁移至 api/models.py 和 api/helpers.py ──────


from intelligent_project_analyzer.api._broadcast_registry import (
    register_broadcast as _register_broadcast,  # noqa: E402
)

# MT-1 迁移：broadcast_to_websockets 已迁移至 api/workflow_runner.py（含 EventStore 增强）
# MT-1 迁移：subscribe_to_redis_pubsub 已迁移至 api/workflow_runner.py
from .workflow_runner import (
    broadcast_to_websockets,  # noqa: E402  (registry + workflow 直接调用)
    subscribe_to_redis_pubsub,  # noqa: E402  (lifespan 依赖)
)

# MT-1 迁移：_ensure_aiosqlite_is_alive / get_or_create_async_checkpointer / create_workflow 已迁移至 api/workflow_runner.py


_register_broadcast(broadcast_to_websockets)


# MT-1 迁移：run_workflow_async 已迁移至 api/workflow_runner.py


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")
