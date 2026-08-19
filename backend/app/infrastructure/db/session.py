"""SQLAlchemy session factory"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    pass


def ensure_schema() -> None:
    """Create ORM tables if missing (Railway first boot / no Alembic yet)."""
    # Import models so metadata is populated
    from app.infrastructure.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("PostgreSQL schema ensured (%s tables)", len(Base.metadata.tables))


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
