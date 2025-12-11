# -*- coding: utf-8 -*-
"""
用户认证系统

提供：
1. 用户注册/登录
2. JWT Token 认证
3. 密码加密
4. 会话管理
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from loguru import logger

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
REFRESH_TOKEN_EXPIRE_DAYS = 30


# ==================== 数据模型 ====================

class UserCreate(BaseModel):
    """用户注册"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None


class UserLogin(BaseModel):
    """用户登录"""
    email: str
    password: str


class UserInDB(BaseModel):
    """数据库用户模型"""
    id: str
    username: str
    email: str
    hashed_password: str
    phone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    
    # 会员信息
    membership_level: str = "free"  # free, basic, pro, enterprise
    membership_expires: Optional[datetime] = None
    
    # 使用统计
    total_analyses: int = 0
    tokens_used: int = 0


class UserResponse(BaseModel):
    """用户响应（不含密码）"""
    id: str
    username: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    membership_level: str
    membership_expires: Optional[datetime]
    created_at: datetime


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Token 载荷"""
    sub: str  # user_id
    exp: datetime
    type: str  # access or refresh


# ==================== 工具函数 ====================

def hash_password(password: str) -> str:
    """加密密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """创建刷新令牌"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[TokenPayload]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(
            sub=payload.get("sub"),
            exp=datetime.fromtimestamp(payload.get("exp")),
            type=payload.get("type", "access")
        )
    except JWTError as e:
        logger.warning(f"Token 解码失败: {e}")
        return None


def create_tokens(user_id: str) -> Token:
    """创建完整的令牌对"""
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
