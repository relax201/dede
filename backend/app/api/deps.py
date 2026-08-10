"""FastAPI dependencies — auth, rate limit, DB"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import Role, decode_token, has_min_role
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.session import get_db

bearer = HTTPBearer(auto_error=False)


async def rate_limit(
    request: Request,
    x_user_id: Annotated[str | None, Header()] = None,
) -> None:
    """100 requests / minute for normal users."""
    identity = x_user_id or (request.client.host if request.client else "anonymous")
    key = f"rl:user:{identity}"
    try:
        count = redis_client.incr_with_expire(key, ttl_seconds=60)
    except Exception:  # noqa: BLE001 — fail open if Redis down, log elsewhere
        return
    if count > settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تم تجاوز حد الطلبات (100/دقيقة). حاول لاحقاً.",
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="مطلوب تسجيل الدخول")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return payload


def require_role(min_role: Role):
    async def _checker(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        role = Role(user.get("role", "user"))
        if not has_min_role(role, min_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="صلاحيات غير كافية")
        return user

    return _checker


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
