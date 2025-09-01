"""
نموذج إشارات التداول والتوصيات
Trading Signals and Recommendations Model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class SignalType(enum.Enum):
    """أنواع الإشارات"""
    BUY = "شراء"
    SELL = "بيع"
    HOLD = "انتظار"


class SignalStatus(enum.Enum):
    """حالة الإشارة"""
    ACTIVE = "نشطة"
    HIT_TP = "تحقق الهدف"
    HIT_SL = "ضرب وقف الخسارة"
    EXPIRED = "منتهية الصلاحية"
    CANCELLED = "ملغية"


class Signal(Base):
    """نموذج إشارات التداول"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, comment="وقت الإشارة")
    timeframe = Column(String(10), nullable=False, comment="الإطار الزمني")
    
    # نوع وحالة الإشارة
    signal_type = Column(Enum(SignalType), nullable=False, comment="نوع الإشارة")
    status = Column(Enum(SignalStatus), default=SignalStatus.ACTIVE, comment="حالة الإشارة")
    confidence = Column(Float, nullable=False, comment="مستوى الثقة (0-100)")
    
    # أسعار الدخول والأهداف
    entry_price = Column(Float, nullable=False, comment="سعر الدخول")
    stop_loss = Column(Float, nullable=True, comment="وقف الخسارة")
    take_profit_1 = Column(Float, nullable=True, comment="الهدف الأول")
    take_profit_2 = Column(Float, nullable=True, comment="الهدف الثاني")
    
    # تفاصيل الإشارة
    reason = Column(Text, nullable=True, comment="سبب الإشارة")
    indicators_used = Column(Text, nullable=True, comment="المؤشرات المستخدمة")
    
    # نتائج الإشارة
    exit_price = Column(Float, nullable=True, comment="سعر الخروج")
    profit_loss = Column(Float, nullable=True, comment="الربح/الخسارة")
    risk_reward_ratio = Column(Float, nullable=True, comment="نسبة المخاطرة للعائد")
    
    # العلاقات
    symbol = relationship("Symbol", back_populates="signals")
    
    # تواريخ الإنشاء والتحديث
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Signal(symbol_id={self.symbol_id}, type={self.signal_type.value}, confidence={self.confidence})>"


# إضافة العلاقة العكسية في نموذج Symbol
from app.models.symbol import Symbol
Symbol.signals = relationship("Signal", back_populates="symbol")

