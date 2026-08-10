"""JWT + password hashing + RBAC helpers"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


class Role(str, Enum):
    USER = "user"
    ANALYST = "analyst"
    ADMIN = "admin"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.USER: 1,
    Role.ANALYST: 2,
    Role.ADMIN: 3,
}


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def hash_password(password: str) -> str:
    digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return digest.decode("utf-8")


def create_access_token(subject: str, role: Role, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": subject, "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def has_min_role(user_role: Role, required: Role) -> bool:
    return ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[required]
