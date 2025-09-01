"""
إعدادات التطبيق الأساسية
Application Core Configuration
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """إعدادات التطبيق الأساسية"""
    
    # معلومات التطبيق الأساسية
    APP_NAME: str = "منصة تحليل الأسهم السعودية"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # إعدادات قاعدة البيانات
    DATABASE_URL: str
    
    # إعدادات الأمان
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # إعدادات API
    API_V1_STR: str = "/api/v1"
    
    # إعدادات مزود البيانات
    API_PROVIDER: str = "tiingo"
    DATA_API_KEY: str
    DATA_API_BASE_URL: str = "https://api.tiingo.com"
    
    # إعدادات Redis (اختيارية)
    REDIS_URL: Optional[str] = None
    
    # إعدادات تيليجرام
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # إعدادات البريد الإلكتروني
    SMTP_SERVER: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: Optional[int] = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = None
    FROM_NAME: str = "منصة تحليل الأسهم السعودية"
    
    # إعدادات المنطقة الزمنية
    TIMEZONE: str = "Asia/Riyadh"
    
    # إعدادات CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    @property
    def cors_origins(self) -> List[str]:
        """تحويل ALLOWED_ORIGINS إلى قائمة"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# إنشاء مثيل الإعدادات
settings = Settings()

