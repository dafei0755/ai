# intelligent_project_analyzer/api/auth_middleware.py
"""
FastAPI 认证中间件
集成 WordPress JWT 验证
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request
from loguru import logger

from ..services.wordpress_jwt_service import get_jwt_service


class AuthMiddleware:
    """FastAPI 认证中间件"""

    def __init__(self):
        self.jwt_service = get_jwt_service()

    def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        从请求中提取 JWT Token

        支持两种方式：
        1. Authorization header: Bearer <token>
        2. Cookie: jwt_token
        """
        # 方式1：Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        # 方式2：Cookie
        return request.cookies.get("jwt_token")

    async def get_current_user(self, request: Request) -> dict:
        """
        依赖注入：获取当前认证用户

        用法：
        @app.get("/protected")
        async def protected_endpoint(current_user: dict = Depends(auth_middleware.get_current_user)):
            return {"user": current_user}
        """
        token = self.get_token_from_request(request)

        if not token:
            logger.warning("❌ 请求缺少 JWT Token")
            raise HTTPException(status_code=401, detail="未提供认证 Token", headers={"WWW-Authenticate": "Bearer"})

        payload = self.jwt_service.verify_jwt_token(token)

        if not payload:
            logger.warning("❌ JWT Token 验证失败")
            raise HTTPException(status_code=401, detail="无效的认证 Token", headers={"WWW-Authenticate": "Bearer"})

        logger.info(f"✅ 用户认证成功: {payload.get('username')}")
        return payload

    async def optional_auth(self, request: Request) -> Optional[dict]:
        """
        可选认证（Token 存在则验证，不存在也允许访问）
        """
        token = self.get_token_from_request(request)

        if not token:
            return None

        return self.jwt_service.verify_jwt_token(token)


# 全局中间件实例
auth_middleware = AuthMiddleware()


# 使用示例
async def require_auth(request: Request):
    """强制认证的依赖注入"""
    return await auth_middleware.get_current_user(request)


async def optional_auth(request: Request):
    """可选认证的依赖注入"""
    return await auth_middleware.optional_auth(request)


async def require_admin(request: Request) -> dict:
    """
    管理员权限认证的依赖注入

    验证用户是否具有管理员权限
    用法：
    @router.get("/api/admin/config")
    async def admin_config(admin: dict = Depends(require_admin)):
        return {"status": "ok"}
    """
    current_user = await auth_middleware.get_current_user(request)

    # 检查用户角色
    roles = current_user.get("roles", [])
    if "administrator" not in roles:
        logger.warning(f"❌ 用户 {current_user.get('username')} 尝试访问管理员功能，但权限不足")
        raise HTTPException(status_code=403, detail="需要管理员权限才能访问此资源")

    logger.info(f"✅ 管理员访问: {current_user.get('username')}")
    return current_user
