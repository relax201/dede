"""
خدمة إرسال الإشعارات عبر تليجرام
"""
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class TelegramService:
    """خدمة إرسال الإشعارات عبر تليجرام"""
    
    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self.session = None
        
    async def __aenter__(self):
        if self.bot_token:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_message(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """إرسال رسالة نصية"""
        if not self.bot_token or not self.session:
            logger.warning("تليجرام غير مُعد بشكل صحيح")
            return False
            
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.info(f"تم إرسال الرسالة بنجاح إلى {chat_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"فشل إرسال الرسالة: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة تليجرام: {e}")
            return False
    
    async def send_photo(self, chat_id: str, photo_url: str, caption: str = "") -> bool:
        """إرسال صورة مع تعليق"""
        if not self.bot_token or not self.session:
            return False
            
        try:
            url = f"{self.base_url}/sendPhoto"
            data = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "HTML"
            }
            
            async with self.session.post(url, json=data) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"خطأ في إرسال صورة تليجرام: {e}")
            return False
    
    def format_market_summary(self, market_data: Dict) -> str:
        """تنسيق ملخص السوق"""
        tasi_data = market_data.get("tasi_index", {})
        gainers = market_data.get("top_gainers", [])
        losers = market_data.get("top_losers", [])
        
        # رمز الاتجاه
        trend_icon = "📈" if tasi_data.get("change", 0) >= 0 else "📉"
        
        message = f"""
🏛️ <b>ملخص السوق السعودي - تاسي</b>

{trend_icon} <b>المؤشر العام:</b> {tasi_data.get('index', 0):,.2f}
📊 <b>التغيير:</b> {tasi_data.get('change', 0):+.2f} ({tasi_data.get('change_percent', 0):+.2f}%)
💰 <b>حجم التداول:</b> {tasi_data.get('volume', 0):,}

🟢 <b>الأسهم الرابحة:</b>
"""
        
        for i, gainer in enumerate(gainers[:3], 1):
            message += f"{i}. {gainer['symbol']}: {gainer['change_percent']:+.2f}%\n"
        
        message += "\n🔴 <b>الأسهم الخاسرة:</b>\n"
        
        for i, loser in enumerate(losers[:3], 1):
            message += f"{i}. {loser['symbol']}: {loser['change_percent']:+.2f}%\n"
        
        message += f"\n⏰ <b>وقت التحديث:</b> {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def format_trading_signal(self, signal: Dict) -> str:
        """تنسيق إشارة التداول"""
        symbol = signal.get("symbol", "")
        signal_type = signal.get("signal_type", "")
        confidence = signal.get("confidence", 0)
        entry_price = signal.get("entry_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        target1 = signal.get("target1", 0)
        reason = signal.get("reason", "")
        
        # تحديد الرمز واللون حسب نوع الإشارة
        if signal_type == "شراء":
            icon = "🟢"
            action = "شراء"
        elif signal_type == "بيع":
            icon = "🔴"
            action = "بيع"
        else:
            icon = "🟡"
            action = "انتظار"
        
        # تحديد مستوى الثقة
        if confidence >= 80:
            confidence_level = "عالية جداً"
        elif confidence >= 70:
            confidence_level = "عالية"
        elif confidence >= 60:
            confidence_level = "متوسطة"
        else:
            confidence_level = "منخفضة"
        
        message = f"""
{icon} <b>إشارة تداول جديدة</b>

📊 <b>الرمز:</b> {symbol}
🎯 <b>التوصية:</b> {action}
⭐ <b>مستوى الثقة:</b> {confidence:.0f}% ({confidence_level})

💰 <b>سعر الدخول:</b> {entry_price:.2f} ريال
🛑 <b>وقف الخسارة:</b> {stop_loss:.2f} ريال
🎯 <b>الهدف الأول:</b> {target1:.2f} ريال

📝 <b>السبب:</b> {reason}

⏰ <b>وقت الإشارة:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return message
    
    def format_price_alert(self, symbol: str, current_price: float, target_price: float, alert_type: str) -> str:
        """تنسيق تنبيه السعر"""
        if alert_type == "above":
            icon = "📈"
            message_type = "تجاوز السعر المستهدف"
        else:
            icon = "📉"
            message_type = "انخفض دون السعر المستهدف"
        
        message = f"""
{icon} <b>تنبيه سعر</b>

📊 <b>الرمز:</b> {symbol}
🚨 <b>التنبيه:</b> {message_type}

💰 <b>السعر الحالي:</b> {current_price:.2f} ريال
🎯 <b>السعر المستهدف:</b> {target_price:.2f} ريال

⏰ <b>وقت التنبيه:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return message
    
    async def send_market_summary(self, chat_ids: List[str], market_data: Dict) -> int:
        """إرسال ملخص السوق لقائمة من المستخدمين"""
        if not chat_ids:
            return 0
            
        message = self.format_market_summary(market_data)
        success_count = 0
        
        for chat_id in chat_ids:
            if await self.send_message(chat_id, message):
                success_count += 1
                # تأخير قصير لتجنب حدود API
                await asyncio.sleep(0.1)
        
        return success_count
    
    async def send_trading_signal(self, chat_ids: List[str], signal: Dict) -> int:
        """إرسال إشارة تداول لقائمة من المستخدمين"""
        if not chat_ids:
            return 0
            
        message = self.format_trading_signal(signal)
        success_count = 0
        
        for chat_id in chat_ids:
            if await self.send_message(chat_id, message):
                success_count += 1
                await asyncio.sleep(0.1)
        
        return success_count
    
    async def send_price_alert(self, chat_id: str, symbol: str, current_price: float, target_price: float, alert_type: str) -> bool:
        """إرسال تنبيه سعر لمستخدم محدد"""
        message = self.format_price_alert(symbol, current_price, target_price, alert_type)
        return await self.send_message(chat_id, message)
    
    async def get_bot_info(self) -> Optional[Dict]:
        """الحصول على معلومات البوت"""
        if not self.bot_token or not self.session:
            return None
            
        try:
            url = f"{self.base_url}/getMe"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result")
                return None
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات البوت: {e}")
            return None
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """إعداد webhook للبوت"""
        if not self.bot_token or not self.session:
            return False
            
        try:
            url = f"{self.base_url}/setWebhook"
            data = {"url": webhook_url}
            
            async with self.session.post(url, json=data) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"خطأ في إعداد webhook: {e}")
            return False

# إنشاء مثيل عام للخدمة
telegram_service = TelegramService()

