"""POST /api/auth/register | POST /api/auth/login | GET /api/auth/me"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, rate_limit
from app.domain.services.auth_service import AuthService
from app.infrastructure.db.session import SessionLocal, ensure_schema, ping_db
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse

router = APIRouter(tags=["auth"])


def _db_session():
    if not ping_db():
        ensure_schema()
    return SessionLocal()


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء حساب",
)
async def register(
    payload: RegisterRequest,
    _: None = Depends(rate_limit),
) -> TokenResponse:
    try:
        ensure_schema()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"قاعدة البيانات غير جاهزة: {exc}",
        ) from exc
    db = SessionLocal()
    try:
        return AuthService(db).register(payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"تعذر التسجيل: {exc}",
        ) from exc
    finally:
        db.close()


@router.post("/auth/login", response_model=TokenResponse, summary="تسجيل الدخول")
async def login(
    payload: LoginRequest,
    _: None = Depends(rate_limit),
) -> TokenResponse:
    try:
        ensure_schema()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"قاعدة البيانات غير جاهزة: {exc}",
        ) from exc
    db = SessionLocal()
    try:
        return AuthService(db).login(payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"تعذر تسجيل الدخول: {exc}",
        ) from exc
    finally:
        db.close()


@router.get("/auth/me", response_model=MeResponse, summary="الملف الحالي")
async def me(user: CurrentUser, _: None = Depends(rate_limit)) -> MeResponse:
    db = SessionLocal()
    try:
        return AuthService(db).me(str(user["sub"]))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    finally:
        db.close()
