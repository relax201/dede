"""Register / login against PostgreSQL users table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Role, create_access_token, hash_password, verify_password
from app.infrastructure.db.models import User
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, payload: RegisterRequest) -> TokenResponse:
        email = payload.email.strip().lower()
        existing = self.db.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise LookupError("البريد مسجّل مسبقاً")
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role=Role.USER.value,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._token(user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        email = payload.email.strip().lower()
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(payload.password, user.password_hash):
            raise PermissionError("بيانات الدخول غير صحيحة")
        if not user.is_active:
            raise PermissionError("الحساب غير نشط")
        return self._token(user)

    def me(self, user_id: str) -> MeResponse:
        from uuid import UUID

        user = self.db.get(User, UUID(user_id))
        if user is None:
            raise LookupError("المستخدم غير موجود")
        return MeResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        )

    @staticmethod
    def _token(user: User) -> TokenResponse:
        role = Role(user.role) if user.role in {r.value for r in Role} else Role.USER
        return TokenResponse(
            access_token=create_access_token(str(user.id), role),
            role=role.value,
            email=user.email,
        )
