"""
التطبيق الرئيسي لمنصة تحليل الأسهم السعودية
Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

# استيراد الإعدادات والمكونات
from app.core.config import settings
from app.core.logging_config import setup_logging, request_logger
from app.api.v1.api import api_router
from app.middleware.security import (
    SecurityMiddleware, 
    RequestLoggingMiddleware, 
    setup_rate_limiting
)

# إعداد التسجيل
setup_logging(
    log_level="INFO" if not settings.DEBUG else "DEBUG",
    app_name="tasi_platform",
    enable_json=True,
    enable_console=True
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    # بداية التشغيل
    logger.info("🚀 بدء تشغيل منصة تحليل الأسهم السعودية")
    logger.info(f"📊 الإصدار: {settings.APP_VERSION}")
    logger.info(f"🔧 وضع التطوير: {settings.DEBUG}")
    
    yield
    
    # إنهاء التشغيل
    logger.info("⏹️ إيقاف منصة تحليل الأسهم السعودية")

# إنشاء التطبيق
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="منصة احترافية لتحليل الأسهم السعودية مع أسعار لحظية ونظام توصيات آلي",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# إعداد Rate Limiting
limiter = setup_rate_limiting(app)

# إضافة Middleware بالترتيب الصحيح
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# إعداد الأمان للمضيفين الموثوقين
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # يجب تحديد المضيفين المسموحين في الإنتاج
    )

# تضمين المسارات
app.include_router(api_router, prefix=settings.API_V1_STR)

# معالج الأخطاء العام
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """معالج الأخطاء العام"""
    request_logger.log_error(
        exc,
        context={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "حدث خطأ داخلي في الخادم",
            "message": "يرجى المحاولة مرة أخرى لاحقاً" if not settings.DEBUG else str(exc)
        }
    )

# معالج 404
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """معالج الصفحات غير الموجودة"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "الصفحة غير موجودة",
            "message": f"المسار {request.url.path} غير متاح"
        }
    )

# الصفحة الرئيسية
@app.get("/")
async def root():
    """الصفحة الرئيسية للـ API"""
    return {
        "success": True,
        "message": "مرحباً بك في منصة تحليل الأسهم السعودية",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs" if settings.DEBUG else "غير متاح في الإنتاج",
        "api_v1": settings.API_V1_STR,
        "features": [
            "أسعار لحظية للأسهم السعودية",
            "تحليل فني متقدم",
            "نظام توصيات آلي",
            "إشعارات تليجرام والبريد الإلكتروني",
            "واجهة عربية متجاوبة"
        ],
        "endpoints": {
            "health": f"{settings.API_V1_STR}/health",
            "symbols": f"{settings.API_V1_STR}/symbols",
            "tasi_index": f"{settings.API_V1_STR}/tasi-index",
            "prices": f"{settings.API_V1_STR}/prices",
            "notifications": f"{settings.API_V1_STR}/notifications",
            "websocket": f"{settings.API_V1_STR}/ws"
        }
    }

# معلومات الصحة المتقدمة
@app.get("/health/detailed")
@limiter.limit("10/minute")
async def detailed_health_check(request: Request):
    """فحص صحة مفصل للنظام"""
    try:
        import psutil
        import sys
        from datetime import datetime
        
        # معلومات النظام
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "python_version": sys.version,
            "uptime": time.time() - psutil.boot_time()
        }
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "app_info": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "debug_mode": settings.DEBUG
            },
            "system_info": system_info,
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"خطأ في فحص الصحة المفصل: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": "خطأ في فحص صحة النظام",
                "status": "unhealthy"
            }
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 تشغيل الخادم مباشرة...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5002,
        reload=settings.DEBUG,
        log_level="info"
    )

