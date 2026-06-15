"""FastAPI dependencies for the standalone application auth boundary."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

from ..services.internal_auth_service import get_internal_auth_service


async def require_admin(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Require an application-owned admin token."""

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing application auth token")

    token = authorization.split(" ", 1)[1].strip()
    user = get_internal_auth_service().verify_jwt_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid application auth token")

    roles = set(user.get("roles") or [])
    if "administrator" not in roles and "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin permission required")

    return user
