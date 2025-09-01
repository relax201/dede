"""
نقطة نهاية فحص صحة النظام
Health Check Endpoint
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.config import settings
import datetime

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """فحص صحة النظام والاتصال بقاعدة البيانات"""
    try:
        # اختبار الاتصال بقاعدة البيانات
        db.execute(text("SELECT 1"))
        db_status = "متصل"
    except Exception as e:
        db_status = f"خطأ في الاتصال: {str(e)}"
    
    return {
        "status": "يعمل",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "timezone": settings.TIMEZONE,
        "database": db_status,
        "api_provider": settings.API_PROVIDER
    }

