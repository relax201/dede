"""SQLAlchemy session factory with SQLite fallback when Postgres is unreachable."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

SQLITE_URL = "sqlite:////tmp/tasi_vision.db"


def _make_engine(url: str):
    sqlite = url.startswith("sqlite")
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if sqlite else {"connect_timeout": 3},
        **({} if sqlite else {"pool_size": 3, "max_overflow": 5, "pool_timeout": 3}),
    )


engine = _make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
_active_url = settings.DATABASE_URL


class Base(DeclarativeBase):
    pass


def _switch_to_sqlite(reason: str) -> None:
    global engine, SessionLocal, _active_url
    if _active_url.startswith("sqlite"):
        return
    logger.warning("Switching DATABASE_URL to SQLite (%s)", reason)
    engine = _make_engine(SQLITE_URL)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    _active_url = SQLITE_URL


def ensure_schema() -> None:
    """Create ORM tables if missing; fall back to SQLite on Postgres failure."""
    global engine, SessionLocal, _active_url
    from app.infrastructure.db import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Primary DB schema failed: %s", exc)
        _switch_to_sqlite(str(exc))
        Base.metadata.create_all(bind=engine)

    logger.info("Schema ensured (%s tables) via %s", len(Base.metadata.tables), _active_url.split("://", 1)[0])


def ping_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database ping failed: %s", exc)
        try:
            _switch_to_sqlite(str(exc))
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
            return True
        except Exception:  # noqa: BLE001
            return False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_url_kind() -> str:
    return _active_url.split("://", 1)[0]
