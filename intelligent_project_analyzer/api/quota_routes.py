"""
知识库配额管理 API 路由 - v7.141.3

功能:
- 用户配额查询
- 配额检查
- 会员等级管理
- 过期清理触发
"""


from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from ..services.expiry_cleanup_service import ExpiryCleanupService
from ..services.quota_manager import QuotaManager

router = APIRouter(prefix="/api/admin/knowledge-quota", tags=["admin", "knowledge-quota"])


# ============================================================================
# Pydantic 模型
# ============================================================================


class QuotaCheckRequest(BaseModel):
    """配额检查请求"""

    user_id: str
    user_tier: str = "free"


class FileSizeCheckRequest(BaseModel):
    """文件大小检查请求"""

    file_size_bytes: int
    user_tier: str = "free"


class CleanupRequest(BaseModel):
    """清理请求"""

    force: bool = False  # 是否强制清理（跳过确认）


# ============================================================================
# API 端点
# ============================================================================


@router.get("/quota/{user_id}")
async def get_user_quota(user_id: str, user_tier: str = "free"):
    """
    获取用户配额和使用情况

    Args:
        user_id: 用户ID
        user_tier: 会员等级

    Returns:
        {
            "user_id": "user_123",
            "user_tier": "free",
            "quota": {...},
            "usage": {...},
            "remaining": {...},
            "warnings": [...]
        }
    """
    try:
        # 初始化配额管理器
        quota_manager = QuotaManager()

        # 获取配额限制
        quota = quota_manager.quota_config.get_tier_quota(user_tier)

        # 获取使用量
        usage = quota_manager.get_user_usage(user_id)

        # 计算剩余配额
        max_documents = quota.get("max_documents", 10)
        max_storage_mb = quota.get("max_storage_mb", 50)

        remaining = {
            "documents": max_documents - usage["document_count"] if max_documents != -1 else -1,
            "storage_mb": max_storage_mb - usage["storage_mb"] if max_storage_mb != -1 else -1,
        }

        # 执行配额检查
        check_result = quota_manager.check_quota(user_id, user_tier)

        return JSONResponse(
            {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "user_tier": user_tier,
                    "quota": quota,
                    "usage": usage,
                    "remaining": remaining,
                    "warnings": check_result.get("warnings", []),
                    "quota_exceeded": not check_result.get("allowed", True),
                },
            }
        )

    except Exception as e:
        logger.error(f"获取用户配额失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quota/check")
async def check_quota(request: QuotaCheckRequest):
    """
    检查用户是否可以上传新文档

    Args:
        request: 配额检查请求

    Returns:
        {
            "allowed": True/False,
            "quota": {...},
            "usage": {...},
            "warnings": [...],
            "errors": [...]
        }
    """
    try:
        quota_manager = QuotaManager()

        result = quota_manager.check_quota(user_id=request.user_id, user_tier=request.user_tier)

        return JSONResponse({"success": True, "data": result})

    except Exception as e:
        logger.error(f"配额检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file-size/check")
async def check_file_size(request: FileSizeCheckRequest):
    """
    检查文件大小是否符合配额限制

    Args:
        request: 文件大小检查请求

    Returns:
        {
            "allowed": True/False,
            "file_size_mb": 5.5,
            "max_file_size_mb": 10,
            "error": "..."
        }
    """
    try:
        quota_manager = QuotaManager()

        result = quota_manager.check_file_size(file_size_bytes=request.file_size_bytes, user_tier=request.user_tier)

        return JSONResponse({"success": True, "data": result})

    except Exception as e:
        logger.error(f"文件大小检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiers")
async def get_membership_tiers():
    """
    获取所有会员等级配置

    Returns:
        {
            "tiers": {
                "free": {...},
                "basic": {...},
                "professional": {...},
                "enterprise": {...}
            },
            "default_tier": "free"
        }
    """
    try:
        quota_manager = QuotaManager()

        return JSONResponse(
            {
                "success": True,
                "data": {
                    "tiers": quota_manager.quota_config.tiers,
                    "default_tier": quota_manager.quota_config.default_tier,
                },
            }
        )

    except Exception as e:
        logger.error(f"获取会员等级失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/expired")
async def cleanup_expired_documents(request: CleanupRequest):
    """
    手动触发过期文档清理

    Args:
        request: 清理请求

    Returns:
        {
            "success": True/False,
            "total_found": 100,
            "total_deleted": 95,
            "errors": [...]
        }
    """
    try:
        cleanup_service = ExpiryCleanupService()

        result = cleanup_service.cleanup_expired_documents()

        return JSONResponse({"success": True, "data": result})

    except Exception as e:
        logger.error(f"清理过期文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cleanup/preview")
async def preview_expired_documents():
    """
    预览将要清理的过期文档

    Returns:
        {
            "total_expired": 100,
            "documents": [...]
        }
    """
    try:
        cleanup_service = ExpiryCleanupService()

        expired_docs = cleanup_service.find_expired_documents()

        return JSONResponse(
            {"success": True, "data": {"total_expired": len(expired_docs), "documents": expired_docs[:50]}}  # 只返回前 50 个
        )

    except Exception as e:
        logger.error(f"预览过期文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/{user_tier}")
async def get_tier_features(user_tier: str):
    """
    获取指定会员等级的功能权限

    Args:
        user_tier: 会员等级

    Returns:
        {
            "tier": "free",
            "features": {
                "allow_sharing": False,
                "allow_team_kb": False,
                "allowed_document_types": [...]
            }
        }
    """
    try:
        quota_manager = QuotaManager()

        quota = quota_manager.quota_config.get_tier_quota(user_tier)

        if not quota:
            raise HTTPException(status_code=404, detail=f"会员等级 '{user_tier}' 不存在")

        features = {
            "allow_sharing": quota_manager.check_sharing_allowed(user_tier),
            "allow_team_kb": quota_manager.check_team_kb_allowed(user_tier),
            "allowed_document_types": quota_manager.get_allowed_document_types(user_tier),
        }

        return JSONResponse({"success": True, "data": {"tier": user_tier, "features": features}})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取等级功能失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
