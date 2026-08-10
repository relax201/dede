"""
نموذج رموز الأسهم
Stock Symbols Model
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.db.database import Base


class Symbol(Base):
    """نموذج رموز الأسهم السعودية"""
    __tablename__ = "symbols"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True, nullable=False, comment="رمز السهم")
    name_ar = Column(String(255), nullable=False, comment="اسم الشركة بالعربية")
    name_en = Column(String(255), nullable=True, comment="اسم الشركة بالإنجليزية")
    sector = Column(String(100), nullable=True, comment="القطاع")
    market_cap = Column(String(50), nullable=True, comment="القيمة السوقية")
    currency = Column(String(3), default="SAR", comment="العملة")
    is_active = Column(Boolean, default=True, comment="حالة النشاط")
    description = Column(Text, nullable=True, comment="وصف الشركة")
    
    # تواريخ الإنشاء والتحديث
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Symbol(ticker='{self.ticker}', name_ar='{self.name_ar}')>"

