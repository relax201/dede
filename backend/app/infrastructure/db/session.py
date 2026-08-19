"""SQLAlchemy session factory"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

_connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=_connect_args,
    **(
        {}
        if settings.DATABASE_URL.startswith("sqlite")
        else {"pool_size": 5, "max_overflow": 10, "pool_timeout": 5}
    ),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    pass


def ensure_schema() -> None:
    """Create ORM tables if missing (Railway first boot / no Alembic yet)."""
    from app.infrastructure.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info(
        "Schema ensured (%s tables) via %s",
        len(Base.metadata.tables),
        settings.DATABASE_URL.split("://", 1)[0],
    )


def ping_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database ping failed: %s", exc)
        return False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
