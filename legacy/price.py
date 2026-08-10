"""
نموذج أسعار الأسهم
Stock Prices Model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Price(Base):
    """نموذج أسعار الأسهم التاريخية واللحظية"""
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, comment="وقت السعر")
    timeframe = Column(String(10), nullable=False, comment="الإطار الزمني (1m, 5m, 15m, 1h, 1d)")
    
    # بيانات الشمعة
    open_price = Column(Float, nullable=False, comment="سعر الافتتاح")
    high_price = Column(Float, nullable=False, comment="أعلى سعر")
    low_price = Column(Float, nullable=False, comment="أدنى سعر")
    close_price = Column(Float, nullable=False, comment="سعر الإغلاق")
    volume = Column(Integer, default=0, comment="حجم التداول")
    
    # بيانات إضافية
    change_amount = Column(Float, nullable=True, comment="مقدار التغيير")
    change_percent = Column(Float, nullable=True, comment="نسبة التغيير")
    
    # العلاقات
    symbol = relationship("Symbol", back_populates="prices")
    
    # تاريخ الإنشاء
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # فهارس للأداء
    __table_args__ = (
        Index('idx_symbol_timeframe_timestamp', 'symbol_id', 'timeframe', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Price(symbol_id={self.symbol_id}, close={self.close_price}, timestamp='{self.timestamp}')>"


# إضافة العلاقة العكسية في نموذج Symbol
from app.models.symbol import Symbol
Symbol.prices = relationship("Price", back_populates="symbol")

