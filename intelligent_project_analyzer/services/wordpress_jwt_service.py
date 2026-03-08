# intelligent_project_analyzer/services/wordpress_jwt_service.py
"""
WordPress 原生 JWT 认证服务
直接与 WordPress REST API 集成，无需 miniOrange 插件
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict

import httpx
import jwt
from loguru import logger


class WordPressJWTService:
    """WordPress 原生 JWT 认证服务"""

    def __init__(self):
        #  安全优化：移除硬编码默认值，强制从环境变量读取
        self.wordpress_url = os.getenv("WORDPRESS_URL")
        if not self.wordpress_url:
            raise ValueError("WORDPRESS_URL 必须在 .env 中配置")

        self.wordpress_user = os.getenv("WORDPRESS_ADMIN_USERNAME")
        if not self.wordpress_user:
            raise ValueError("WORDPRESS_ADMIN_USERNAME 必须在 .env 中配置")

        self.jwt_secret = os.getenv("JWT_SECRET_KEY", self._generate_secret_key())
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiry = int(os.getenv("JWT_EXPIRY", "604800"))  # 7天

        logger.info(" WordPress JWT Service 初始化完成")
        logger.info(f"   WordPress URL: {self.wordpress_url}")
        logger.info(f"   认证算法: {self.jwt_algorithm}")

    @staticmethod
    def _generate_secret_key() -> str:
        """生成安全的 JWT Secret Key"""
        import secrets

        return secrets.token_urlsafe(32)

    async def authenticate_with_wordpress(self, username: str, password: str) -> Dict[str, Any] | None:
        """
        使用 WordPress REST API 验证用户凭证

        Args:
            username: WordPress 用户名
            password: WordPress 密码

        Returns:
            成功返回用户信息字典，失败返回 None
        """
        try:
            # 调用 WordPress REST API 验证用户
            url = f"{self.wordpress_url}/wp-json/wp/v2/users/me"

            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.get(url, auth=(username, password), follow_redirects=True)

            if response.status_code == 200:
                user_data = response.json()
                logger.info(f" 用户 {username} 认证成功")
                return {
                    "user_id": user_data.get("id"),
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "name": user_data.get("name"),
                    "roles": user_data.get("roles", []),
                }
            else:
                logger.warning(f" 用户 {username} 认证失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f" WordPress 认证异常: {str(e)}")
            return None

    def generate_jwt_token(self, user_data: Dict[str, Any], device_id: str | None = None) -> str:
        """
        生成 JWT Token

        Args:
            user_data: 用户信息字典（包含 user_id, username 等）
            device_id: 设备唯一标识（v3.0.24 新增，用于多设备登录限制）

        Returns:
            JWT Token 字符串
        """
        try:
            payload = {
                "user_id": user_data.get("user_id"),
                "username": user_data.get("username"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "roles": user_data.get("roles", []),
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=self.jwt_expiry),
            }

            #  v3.0.24: 添加设备标识（用于多设备登录限制）
            if device_id:
                payload["device_id"] = device_id

            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

            logger.info(
                f" JWT Token 生成成功: {user_data.get('username')}" + (f" (设备: {device_id[:8]}...)" if device_id else "")
            )
            return token

        except Exception as e:
            logger.error(f" JWT Token 生成失败: {str(e)}")
            raise

    def verify_jwt_token(self, token: str) -> Dict[str, Any] | None:
        """
        验证 JWT Token

        Args:
            token: JWT Token 字符串

        Returns:
            成功返回载荷数据，失败返回 None
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            #  兼容 WordPress 插件 v3.0.1 的嵌套结构
            # WordPress 格式: { "data": { "user": { "id": 1, "username": "...", ... } } }
            # Python 格式: { "user_id": 1, "username": "...", ... }
            if "data" in payload and "user" in payload["data"]:
                # WordPress 插件格式 - 提取并扁平化
                wp_user = payload["data"]["user"]
                normalized_payload = {
                    "user_id": wp_user.get("id"),  # WordPress 使用 "id"，Python 使用 "user_id"
                    "username": wp_user.get("username"),
                    "email": wp_user.get("email"),
                    "name": wp_user.get("display_name"),  # WordPress 的 display_name
                    "display_name": wp_user.get("display_name"),
                    "roles": wp_user.get("roles", []),
                    "iat": payload.get("iat"),
                    "exp": payload.get("exp"),
                }
                logger.info(f" JWT Token 验证成功 (WordPress 插件格式): {normalized_payload.get('username')}")
                return normalized_payload

            # Python 原生格式 - 直接返回
            logger.debug(f" JWT Token 验证成功 (Python 格式): {payload.get('username')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning(" Token 已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f" Token 无效: {str(e)}")
            return None
        except Exception as e:
            logger.error(f" Token 验证异常: {str(e)}")
            return None

    def refresh_jwt_token(self, old_token: str) -> str | None:
        """
        刷新 JWT Token

         v7.217: 允许在过期窗口内（7天）刷新已过期的 Token
        - 如果 Token 未过期，直接刷新
        - 如果 Token 已过期但在7天内，仍允许刷新（宽限期）
        - 如果 Token 已过期超过7天，拒绝刷新

        Args:
            old_token: 旧的 JWT Token

        Returns:
            新的 JWT Token，或 None（Token 无效或过期超过宽限期）
        """
        #  v7.217: 先尝试正常验证
        payload = self.verify_jwt_token(old_token)

        # 如果正常验证失败，尝试跳过过期检查解码
        if not payload:
            try:
                # 跳过过期检查，只验证签名
                payload = jwt.decode(
                    old_token,
                    self.jwt_secret,
                    algorithms=[self.jwt_algorithm],
                    options={"verify_exp": False},  #  关键：跳过过期验证
                )

                # 检查过期时间是否在宽限期内（7天）
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
                    grace_period = timedelta(days=7)

                    if datetime.utcnow() > exp_datetime + grace_period:
                        logger.warning(" Token 过期超过宽限期，无法刷新")
                        return None

                    logger.info(f" Token 已过期但在宽限期内，允许刷新: {payload.get('username')}")

                # 处理 WordPress 插件格式
                if "data" in payload and "user" in payload["data"]:
                    wp_user = payload["data"]["user"]
                    payload = {
                        "user_id": wp_user.get("id"),
                        "username": wp_user.get("username"),
                        "email": wp_user.get("email"),
                        "name": wp_user.get("display_name"),
                        "display_name": wp_user.get("display_name"),
                        "roles": wp_user.get("roles", []),
                    }

            except jwt.InvalidTokenError as e:
                logger.warning(f" Token 无效，无法刷新: {str(e)}")
                return None
            except Exception as e:
                logger.error(f" Token 解码异常: {str(e)}")
                return None

        # 移除 exp 和 iat，重新生成
        payload.pop("exp", None)
        payload.pop("iat", None)

        try:
            new_payload = {
                **payload,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=self.jwt_expiry),
            }

            new_token = jwt.encode(new_payload, self.jwt_secret, algorithm=self.jwt_algorithm)

            logger.info(f" JWT Token 刷新成功: {payload.get('username')}")
            return new_token

        except Exception as e:
            logger.error(f" Token 刷新失败: {str(e)}")
            return None


# 全局实例
_jwt_service: WordPressJWTService | None = None


def get_jwt_service() -> WordPressJWTService:
    """获取 JWT 服务单例"""
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = WordPressJWTService()
    return _jwt_service
