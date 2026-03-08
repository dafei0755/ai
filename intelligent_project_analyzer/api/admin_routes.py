"""
管理员后台 API 路由 (MT-7 重构)
提供系统监控、配置管理、会话管理、日志查询等功能

仅限管理员访问
原始 3056 行已按功能领域拆分为 8 个子模块 (routes/admin_*.py)
"""

from fastapi import APIRouter

from .routes.admin_config import router as config_router
from .routes.admin_database import router as database_router
from .routes.admin_domain import router as domain_router
from .routes.admin_health import router as health_router
from .routes.admin_metrics import router as metrics_router
from .routes.admin_ontology import router as ontology_router
from .routes.admin_sessions import router as sessions_router
from .routes.admin_showcase import router as showcase_router

router = APIRouter(prefix="/api/admin", tags=["admin"])

router.include_router(metrics_router)
router.include_router(config_router)
router.include_router(sessions_router)
router.include_router(health_router)
router.include_router(showcase_router)
router.include_router(domain_router)
router.include_router(database_router)
router.include_router(ontology_router)
