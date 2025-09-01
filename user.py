"""
نموذج المستخدمين وقوائم المراقبة
Users and Watchlists Model
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

# جدول العلاقة بين المستخدمين والرموز (قائمة المراقبة)
user_watchlist = Table(
    'user_watchlist',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('symbol_id', Integer, ForeignKey('symbols.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)


class User(Base):
    """نموذج المستخدمين"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False, comment="البريد الإلكتروني")
    username = Column(String(50), unique=True, index=True, nullable=True, comment="اسم المستخدم")
    full_name = Column(String(255), nullable=True, comment="الاسم الكامل")
    hashed_password = Column(String(255), nullable=False, comment="كلمة المرور المشفرة")
    
    # معلومات إضافية
    phone = Column(String(20), nullable=True, comment="رقم الهاتف")
    telegram_chat_id = Column(String(50), nullable=True, comment="معرف تيليجرام")
    
    # حالة الحساب
    is_active = Column(Boolean, default=True, comment="حالة النشاط")
    is_verified = Column(Boolean, default=False, comment="حالة التحقق")
    is_premium = Column(Boolean, default=False, comment="عضوية مميزة")
    
    # إعدادات التنبيهات
    email_notifications = Column(Boolean, default=True, comment="تنبيهات البريد الإلكتروني")
    telegram_notifications = Column(Boolean, default=False, comment="تنبيهات تيليجرام")
    
    # العلاقات
    watchlist = relationship("Symbol", secondary=user_watchlist, back_populates="watchers")
    
    # تواريخ الإنشاء والتحديث
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(email='{self.email}', username='{self.username}')>"


# إضافة العلاقة العكسية في نموذج Symbol
from app.models.symbol import Symbol
Symbol.watchers = relationship("User", secondary=user_watchlist, back_populates="watchlist")

