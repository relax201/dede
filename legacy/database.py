"""
إعداد قاعدة البيانات
Database Configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# إنشاء محرك قاعدة البيانات
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# إنشاء جلسة قاعدة البيانات
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# إنشاء الفئة الأساسية للنماذج
Base = declarative_base()


def get_db():
    """الحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

