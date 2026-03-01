"""
开发环境简单认证
生产环境需替换为JWT/OAuth2
"""
import logging

logger = logging.getLogger(__name__)


async def require_admin():
    """
    开发环境简单认证 - 自动通过
    生产环境需替换为JWT/OAuth2
    """
    logger.debug(" 开发模式认证：自动通过")

    return {"user_id": "dev_admin", "username": "开发管理员", "role": "admin", "permissions": ["read", "write", "delete"]}


async def get_current_user():
    """
    获取当前用户（开发模式）
    """
    return {"user_id": "dev_user", "username": "开发用户", "role": "user"}
