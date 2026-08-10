"""
WebSocket endpoints للبيانات اللحظية
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.websocket_manager import websocket_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = Query(None)):
    """نقطة نهاية WebSocket للبيانات اللحظية"""
    await websocket_manager.handle_websocket(websocket, user_id)

@router.websocket("/ws/{symbol}")
async def websocket_symbol_endpoint(websocket: WebSocket, symbol: str, user_id: str = Query(None)):
    """نقطة نهاية WebSocket لرمز محدد"""
    await websocket_manager.connection_manager.connect(websocket, user_id)
    
    # اشتراك تلقائي في الرمز
    websocket_manager.connection_manager.subscribe_to_symbol(websocket, symbol.upper())
    
    try:
        # إرسال رسالة ترحيب
        await websocket_manager.connection_manager.send_personal_message({
            "type": "welcome",
            "symbol": symbol.upper(),
            "message": f"مرحباً بك في تحديثات {symbol.upper()}"
        }, websocket)
        
        # الاستماع للرسائل
        while True:
            data = await websocket.receive_text()
            # يمكن معالجة رسائل إضافية هنا
            
    except WebSocketDisconnect:
        logger.info(f"تم قطع اتصال WebSocket للرمز {symbol}")
    except Exception as e:
        logger.error(f"خطأ في WebSocket للرمز {symbol}: {e}")
    finally:
        websocket_manager.connection_manager.disconnect(websocket, user_id)

