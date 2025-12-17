# intelligent_project_analyzer/api/auth_routes.py
"""
FastAPI 认证路由
处理 WordPress JWT 认证的登录、验证、刷新等端点
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from ..services.wordpress_jwt_service import get_jwt_service
from ..services.device_session_manager import get_device_manager

router = APIRouter(prefix="/api/auth", tags=["authentication"])
jwt_service = get_jwt_service()
device_manager = get_device_manager()


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
async def logout(request: Request):
    """
    用户登出端点
    
    🆕 v3.0.24: 登出时清除设备记录
    """
    # 尝试获取用户信息以清除设备记录
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = jwt_service.verify_jwt_token(token)
        if payload:
            user_id = payload.get('user_id')
            if user_id:
                await device_manager.logout_device(int(user_id))
                logger.info(f"👋 用户 {user_id} 登出，设备记录已清除")
    
    logger.info("👋 用户登出")
    return {
        "status": "success",
        "message": "已成功登出"
    }


@router.post("/check-device")
async def check_device(request: Request):
    """
    🆕 v3.0.24: 检查当前设备是否被踢出
    
    前端定期调用此接口，检测是否有其他设备登录
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 Token")
    
    token = auth_header[7:]
    
    # 获取设备 ID（从请求体或 header）
    device_id = None
    try:
        body = await request.json()
        device_id = body.get('device_id')
    except:
        pass
    
    if not device_id:
        device_id = request.headers.get("X-Device-ID")
    
    if not device_id:
        # 无设备 ID，跳过检查（兼容旧版本）
        return {"status": "success", "valid": True, "reason": "no_device_id"}
    
    # 验证 Token
    payload = jwt_service.verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效")
    
    user_id = payload.get('user_id')
    if not user_id:
        return {"status": "success", "valid": True, "reason": "no_user_id"}
    
    # 检查设备是否有效
    result = await device_manager.verify_device(int(user_id), device_id)
    
    if not result.get('valid'):
        logger.warning(f"⚠️ 用户 {user_id} 设备已被踢出: {device_id[:8]}...")
        return {
            "status": "kicked",
            "valid": False,
            "reason": result.get('reason'),
            "message": result.get('message', '您的账号已在其他设备登录')
        }
    
    return {
        "status": "success",
        "valid": True,
        "reason": result.get('reason')
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
    
    🆕 v3.0.24: 支持设备绑定，限制多设备同时登录
    - 请求体可包含 device_id 和 device_info
    - 新设备登录时会踢出旧设备
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 Token")

    token = auth_header[7:]
    
    # 🆕 v3.0.24: 获取设备信息（从请求体或 header）
    device_id = None
    device_info = None
    try:
        body = await request.json()
        device_id = body.get('device_id')
        device_info = body.get('device_info')
    except:
        # 请求体可能为空或非 JSON
        pass
    
    # 也支持从 header 获取设备 ID
    if not device_id:
        device_id = request.headers.get("X-Device-ID")
    
    # 🔍 DEBUG: 记录 Token 前缀（脱敏）
    logger.debug(f"🔐 开始验证 Token (前20字符): {token[:20]}...")
    if device_id:
        logger.debug(f"📱 设备ID: {device_id[:8]}...")

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
            user_id = user_data.get('id')
            logger.info(f"✅ SSO Token 验证成功 (WordPress SSO 格式): {user_data.get('username')}")
            logger.debug(f"📋 用户数据: ID={user_data.get('id')}, Email={user_data.get('email')}, Roles={user_data.get('roles')}")
        else:
            # Python 后端生成的扁平格式
            user_data = payload
            user_id = user_data.get('user_id')
            logger.info(f"✅ SSO Token 验证成功 (Python 格式): {user_data.get('username')}")
            logger.debug(f"📋 用户数据: ID={user_data.get('user_id')}, Email={user_data.get('email')}")

        # 🆕 v3.0.24: 设备验证和注册
        kicked_device = None
        if device_id and user_id:
            # 注册新设备（如果有旧设备会被踢出）
            register_result = await device_manager.register_device(
                user_id=int(user_id),
                device_id=device_id,
                device_info=device_info
            )
            kicked_device = register_result.get('kicked_device')
            if kicked_device:
                logger.warning(f"⚠️ 用户 {user_id} 新设备登录，旧设备已被踢出")

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
            },
            # 🆕 v3.0.24: 返回设备绑定信息
            "device_registered": bool(device_id),
            "kicked_other_device": bool(kicked_device)
        }
    except Exception as e:
        logger.error(f"❌ Token 验证失败: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token 验证失败: {str(e)}")
