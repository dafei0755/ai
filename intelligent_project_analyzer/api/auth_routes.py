# intelligent_project_analyzer/api/auth_routes.py
"""
FastAPI 认证路由
处理 WordPress JWT 认证的登录、验证、刷新等端点
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from loguru import logger
from ..services.wordpress_jwt_service import get_jwt_service

router = APIRouter(prefix="/api/auth", tags=["authentication"])
jwt_service = get_jwt_service()


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应模型"""
    status: str
    token: str
    user: dict
    message: str = ""


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    用户登录端点
    
    验证 WordPress 用户凭证，生成 JWT Token
    """
    logger.info(f"🔐 用户登录请求: {request.username}")
    
    # 1. 使用 WordPress REST API 验证凭证
    user_data = await jwt_service.authenticate_with_wordpress(
        request.username,
        request.password
    )
    
    if not user_data:
        logger.warning(f"❌ 登录失败: {request.username}")
        raise HTTPException(
            status_code=401,
            detail="用户名或密码不正确"
        )
    
    # 2. 生成 JWT Token
    try:
        token = jwt_service.generate_jwt_token(user_data)
        logger.info(f"✅ 用户 {request.username} 登录成功，Token 已生成")
        
        return TokenResponse(
            status="success",
            token=token,
            user=user_data,
            message=f"欢迎 {user_data.get('name', request.username)}！"
        )
    except Exception as e:
        logger.error(f"❌ Token 生成失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Token 生成失败，请稍后重试"
        )


@router.post("/refresh")
async def refresh_token(request: Request):
    """
    Token 刷新端点
    
    使用有效的旧 Token 生成新 Token
    """
    # 提取 Authorization header 中的 token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 Token")
    
    old_token = auth_header[7:]
    
    logger.info("🔄 Token 刷新请求")
    
    # 验证旧 Token
    payload = jwt_service.verify_jwt_token(old_token)
    if not payload:
        logger.warning("❌ Token 验证失败，刷新被拒绝")
        raise HTTPException(
            status_code=401,
            detail="Token 无效或已过期"
        )
    
    # 生成新 Token
    try:
        new_token = jwt_service.refresh_jwt_token(old_token)
        if not new_token:
            raise HTTPException(status_code=401, detail="Token 刷新失败")
        
        logger.info(f"✅ Token 刷新成功: {payload.get('username')}")
        
        return {
            "status": "success",
            "token": new_token,
            "user": {
                "user_id": payload.get('user_id'),
                "username": payload.get('username'),
                "email": payload.get('email'),
                "name": payload.get('name'),
                "roles": payload.get('roles', [])
            }
        }
    except Exception as e:
        logger.error(f"❌ Token 刷新异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Token 刷新失败"
        )


@router.post("/logout")
async def logout():
    """
    用户登出端点
    
    注：JWT 是无状态的，登出仅清除客户端 Token
    """
    logger.info("👋 用户登出")
    return {
        "status": "success",
        "message": "已成功登出"
    }


@router.get("/me")
async def get_current_user(request: Request):
    """
    获取当前用户信息
    
    需要在请求头中提供有效的 JWT Token
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 Token")
    
    token = auth_header[7:]
    payload = jwt_service.verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效")
    
    return {
        "status": "success",
        "user": {
            "user_id": payload.get('user_id'),
            "username": payload.get('username'),
            "email": payload.get('email'),
            "name": payload.get('name'),
            "roles": payload.get('roles', [])
        }
    }


@router.post("/verify")
async def verify_token(request: Request):
    """
    🔥 SSO: 验证从 WordPress 返回的 JWT Token

    用于回调页面验证 Token 有效性并获取用户信息
    兼容两种 JWT 格式：
    1. Python 后端生成的（扁平结构）
    2. WordPress SSO 插件生成的（嵌套结构 data.user）
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 Token")

    token = auth_header[7:]
    
    # 🔍 DEBUG: 记录 Token 前缀（脱敏）
    logger.debug(f"🔐 开始验证 Token (前20字符): {token[:20]}...")

    try:
        # 使用 WordPress JWT Service 验证 Token
        payload = jwt_service.verify_jwt_token(token)
        
        # 🔍 DEBUG: 记录完整 payload 结构（调试用）
        logger.debug(f"📦 Token payload 结构: {list(payload.keys()) if payload else 'None'}")

        if not payload:
            logger.warning("⚠️ Token 验证返回空 payload")
            raise HTTPException(status_code=401, detail="Token 验证失败")

        # 🔧 兼容 WordPress SSO 插件的嵌套格式 (data.user)
        if 'data' in payload and 'user' in payload['data']:
            user_data = payload['data']['user']
            logger.info(f"✅ SSO Token 验证成功 (WordPress SSO 格式): {user_data.get('username')}")
            logger.debug(f"📋 用户数据: ID={user_data.get('id')}, Email={user_data.get('email')}, Roles={user_data.get('roles')}")
        else:
            # Python 后端生成的扁平格式
            user_data = payload
            logger.info(f"✅ SSO Token 验证成功 (Python 格式): {user_data.get('username')}")
            logger.debug(f"📋 用户数据: ID={user_data.get('user_id')}, Email={user_data.get('email')}")

        return {
            "status": "success",
            "user": {
                "user_id": user_data.get('id') or user_data.get('user_id'),
                "username": user_data.get('username'),
                "email": user_data.get('email'),
                "name": user_data.get('display_name') or user_data.get('name'),
                "display_name": user_data.get('display_name') or user_data.get('name'),
                "roles": user_data.get('roles', []),
                "avatar_url": user_data.get('avatar_url', '')
            }
        }
    except Exception as e:
        logger.error(f"❌ Token 验证失败: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token 验证失败: {str(e)}")
