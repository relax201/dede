"""
مدير WebSocket للبيانات اللحظية
"""
import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import weakref

logger = logging.getLogger(__name__)

class ConnectionManager:
    """مدير اتصالات WebSocket"""
    
    def __init__(self):
        # استخدام WeakSet لتجنب memory leaks
        self.active_connections: Set[WebSocket] = set()
        self.symbol_subscribers: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str = None):
        """قبول اتصال WebSocket جديد"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if user_id:
            self.user_connections[user_id] = websocket
            
        logger.info(f"اتصال WebSocket جديد. إجمالي الاتصالات: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, user_id: str = None):
        """قطع اتصال WebSocket"""
        self.active_connections.discard(websocket)
        
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        
        # إزالة الاشتراكات
        for symbol, subscribers in self.symbol_subscribers.items():
            subscribers.discard(websocket)
            
        logger.info(f"تم قطع اتصال WebSocket. إجمالي الاتصالات: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """إرسال رسالة شخصية لاتصال محدد"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة شخصية: {e}")
            self.active_connections.discard(websocket)
    
    async def send_to_user(self, message: dict, user_id: str):
        """إرسال رسالة لمستخدم محدد"""
        if user_id in self.user_connections:
            websocket = self.user_connections[user_id]
            await self.send_personal_message(message, websocket)
    
    async def broadcast(self, message: dict):
        """بث رسالة لجميع الاتصالات النشطة"""
        if not self.active_connections:
            return
            
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"خطأ في البث: {e}")
                disconnected.add(connection)
        
        # إزالة الاتصالات المنقطعة
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_symbol_subscribers(self, symbol: str, message: dict):
        """بث رسالة لمشتركي رمز معين"""
        if symbol not in self.symbol_subscribers:
            return
            
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for connection in self.symbol_subscribers[symbol].copy():
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"خطأ في البث للرمز {symbol}: {e}")
                disconnected.add(connection)
        
        # إزالة الاتصالات المنقطعة
        for connection in disconnected:
            self.symbol_subscribers[symbol].discard(connection)
    
    def subscribe_to_symbol(self, websocket: WebSocket, symbol: str):
        """اشتراك في تحديثات رمز معين"""
        if symbol not in self.symbol_subscribers:
            self.symbol_subscribers[symbol] = set()
        
        self.symbol_subscribers[symbol].add(websocket)
        logger.info(f"اشتراك جديد في الرمز {symbol}. إجمالي المشتركين: {len(self.symbol_subscribers[symbol])}")
    
    def unsubscribe_from_symbol(self, websocket: WebSocket, symbol: str):
        """إلغاء الاشتراك في تحديثات رمز معين"""
        if symbol in self.symbol_subscribers:
            self.symbol_subscribers[symbol].discard(websocket)
            
            # حذف القائمة إذا كانت فارغة
            if not self.symbol_subscribers[symbol]:
                del self.symbol_subscribers[symbol]
    
    def get_connection_stats(self) -> dict:
        """إحصائيات الاتصالات"""
        return {
            "total_connections": len(self.active_connections),
            "user_connections": len(self.user_connections),
            "symbol_subscriptions": {
                symbol: len(subscribers) 
                for symbol, subscribers in self.symbol_subscribers.items()
            }
        }

class WebSocketManager:
    """مدير WebSocket الرئيسي"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.is_broadcasting = False
        self.broadcast_task = None
        
    async def handle_websocket(self, websocket: WebSocket, user_id: str = None):
        """معالجة اتصال WebSocket"""
        await self.connection_manager.connect(websocket, user_id)
        
        try:
            while True:
                # استقبال الرسائل من العميل
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await self.handle_client_message(websocket, message, user_id)
                
        except WebSocketDisconnect:
            logger.info("تم قطع اتصال WebSocket بواسطة العميل")
        except Exception as e:
            logger.error(f"خطأ في معالجة WebSocket: {e}")
        finally:
            self.connection_manager.disconnect(websocket, user_id)
    
    async def handle_client_message(self, websocket: WebSocket, message: dict, user_id: str = None):
        """معالجة رسائل العميل"""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe":
                # اشتراك في رمز
                symbol = message.get("symbol")
                if symbol:
                    self.connection_manager.subscribe_to_symbol(websocket, symbol)
                    await self.connection_manager.send_personal_message({
                        "type": "subscription_confirmed",
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
            
            elif message_type == "unsubscribe":
                # إلغاء اشتراك
                symbol = message.get("symbol")
                if symbol:
                    self.connection_manager.unsubscribe_from_symbol(websocket, symbol)
                    await self.connection_manager.send_personal_message({
                        "type": "unsubscription_confirmed",
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
            
            elif message_type == "ping":
                # رد على ping
                await self.connection_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
            
            elif message_type == "get_stats":
                # إرسال إحصائيات الاتصال
                stats = self.connection_manager.get_connection_stats()
                await self.connection_manager.send_personal_message({
                    "type": "connection_stats",
                    "data": stats,
                    "timestamp": datetime.now().isoformat()
                }, websocket)
                
        except Exception as e:
            logger.error(f"خطأ في معالجة رسالة العميل: {e}")
    
    async def broadcast_market_data(self, market_data: dict):
        """بث بيانات السوق"""
        message = {
            "type": "market_data",
            "data": market_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.broadcast(message)
    
    async def broadcast_price_update(self, symbol: str, price_data: dict):
        """بث تحديث سعر لرمز معين"""
        message = {
            "type": "price_update",
            "symbol": symbol,
            "data": price_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # بث للمشتركين في الرمز
        await self.connection_manager.broadcast_to_symbol_subscribers(symbol, message)
    
    async def broadcast_signal(self, signal_data: dict):
        """بث إشارة تداول جديدة"""
        message = {
            "type": "trading_signal",
            "data": signal_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.broadcast(message)
    
    async def send_notification(self, user_id: str, notification: dict):
        """إرسال إشعار لمستخدم محدد"""
        message = {
            "type": "notification",
            "data": notification,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.send_to_user(message, user_id)
    
    async def start_broadcasting(self, interval: int = 5):
        """بدء البث الدوري للبيانات"""
        if self.is_broadcasting:
            return
            
        self.is_broadcasting = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop(interval))
        logger.info(f"تم بدء البث الدوري كل {interval} ثواني")
    
    async def stop_broadcasting(self):
        """إيقاف البث الدوري"""
        self.is_broadcasting = False
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("تم إيقاف البث الدوري")
    
    async def _broadcast_loop(self, interval: int):
        """حلقة البث الدوري"""
        from app.services.market_data import market_data_service
        
        while self.is_broadcasting:
            try:
                # جلب البيانات اللحظية
                symbols = ["SABIC", "STC", "RAJHI", "ARAMCO", "ALMARAI", "NCB", "RIYAD", "SAMBA"]
                
                async with market_data_service as service:
                    # بيانات المؤشر
                    tasi_data = await service.get_tasi_index()
                    if tasi_data:
                        await self.broadcast_market_data(tasi_data)
                    
                    # أسعار الأسهم
                    prices = await service.get_real_time_prices(symbols)
                    for symbol, price_data in prices.items():
                        await self.broadcast_price_update(symbol, price_data)
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"خطأ في حلقة البث: {e}")
                await asyncio.sleep(interval)

# إنشاء مثيل عام لمدير WebSocket
websocket_manager = WebSocketManager()

