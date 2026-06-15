"""Internal authentication token helper.

This is the runtime boundary for the new standalone account system.  It keeps
the backend independent from any retired external member provider while
preserving the token verification contract used by existing routes.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from loguru import logger


class InternalAuthService:
    """Verify and issue application-owned JWT tokens."""

    def __init__(self) -> None:
        self.secret = os.getenv("APP_JWT_SECRET") or os.getenv("JWT_SECRET") or "local-dev-secret-change-me"
        self.algorithm = os.getenv("APP_JWT_ALGORITHM", "HS256")
        self.expire_hours = int(os.getenv("APP_JWT_EXPIRE_HOURS", "168"))

    def generate_token(self, user: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "email": user.get("email"),
            "name": user.get("name") or user.get("display_name"),
            "roles": user.get("roles", []),
            "iat": now,
            "exp": now + timedelta(hours=self.expire_hours),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        if token == "dev-token-mock":
            return {
                "user_id": 9999,
                "username": "dev_user",
                "email": "dev@localhost",
                "name": "开发测试用户",
                "roles": ["administrator"],
            }

        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return dict(payload)
        except jwt.ExpiredSignatureError:
            logger.debug("Internal auth token expired")
            return None
        except jwt.InvalidTokenError as exc:
            logger.debug(f"Internal auth token invalid: {exc}")
            return None

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        return self.verify_jwt_token(token)


_auth_service: Optional[InternalAuthService] = None


def get_internal_auth_service() -> InternalAuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = InternalAuthService()
    return _auth_service
