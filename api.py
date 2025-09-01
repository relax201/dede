"""
تجميع نقاط نهاية API الإصدار الأول
API v1 Router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import health, symbols, market, websocket, notifications

api_router = APIRouter()

# تضمين نقاط النهاية
api_router.include_router(health.router, tags=["صحة النظام"])
api_router.include_router(symbols.router, tags=["رموز الأسهم"])
api_router.include_router(market.router, tags=["بيانات السوق"])
api_router.include_router(websocket.router, tags=["الاتصال المباشر"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["الإشعارات"])

