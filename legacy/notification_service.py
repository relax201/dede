"""
خدمة إدارة الإشعارات والاشتراكات
"""
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.telegram_service import telegram_service
from app.services.email_service import email_service
from app.services.websocket_manager import websocket_manager
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """خدمة إدارة الإشعارات والاشتراكات"""
    
    def __init__(self):
        # قوائم المشتركين
        self.telegram_subscribers: Set[str] = set()
        self.email_subscribers: Set[str] = set()
        self.websocket_subscribers: Set[str] = set()
        
        # إعدادات الإشعارات
        self.market_summary_enabled = True
        self.trading_signals_enabled = True
        self.price_alerts_enabled = True
        
        # آخر إرسال للتقارير
        self.last_market_summary = None
        self.last_signals_check = None
        
    def add_telegram_subscriber(self, chat_id: str) -> bool:
        """إضافة مشترك تليجرام"""
        try:
            self.telegram_subscribers.add(chat_id)
            logger.info(f"تم إضافة مشترك تليجرام: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"خطأ في إضافة مشترك تليجرام: {e}")
            return False
    
    def remove_telegram_subscriber(self, chat_id: str) -> bool:
        """إزالة مشترك تليجرام"""
        try:
            self.telegram_subscribers.discard(chat_id)
            logger.info(f"تم إزالة مشترك تليجرام: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"خطأ في إزالة مشترك تليجرام: {e}")
            return False
    
    def add_email_subscriber(self, email: str) -> bool:
        """إضافة مشترك بريد إلكتروني"""
        try:
            self.email_subscribers.add(email)
            logger.info(f"تم إضافة مشترك بريد إلكتروني: {email}")
            return True
        except Exception as e:
            logger.error(f"خطأ في إضافة مشترك بريد إلكتروني: {e}")
            return False
    
    def remove_email_subscriber(self, email: str) -> bool:
        """إزالة مشترك بريد إلكتروني"""
        try:
            self.email_subscribers.discard(email)
            logger.info(f"تم إزالة مشترك بريد إلكتروني: {email}")
            return True
        except Exception as e:
            logger.error(f"خطأ في إزالة مشترك بريد إلكتروني: {e}")
            return False
    
    async def send_market_summary(self, market_data: Dict) -> Dict[str, int]:
        """إرسال ملخص السوق لجميع المشتركين"""
        results = {
            "telegram_sent": 0,
            "email_sent": 0,
            "websocket_sent": 0,
            "total_subscribers": len(self.telegram_subscribers) + len(self.email_subscribers)
        }
        
        try:
            # إرسال عبر تليجرام
            if self.telegram_subscribers and self.market_summary_enabled:
                async with telegram_service as tg:
                    results["telegram_sent"] = await tg.send_market_summary(
                        list(self.telegram_subscribers), market_data
                    )
            
            # إرسال عبر البريد الإلكتروني
            if self.email_subscribers and self.market_summary_enabled:
                results["email_sent"] = 1 if await email_service.send_market_summary_email(
                    list(self.email_subscribers), market_data
                ) else 0
            
            # إرسال عبر WebSocket
            await websocket_manager.broadcast_market_data(market_data)
            results["websocket_sent"] = len(websocket_manager.connection_manager.active_connections)
            
            self.last_market_summary = datetime.now()
            logger.info(f"تم إرسال ملخص السوق: {results}")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال ملخص السوق: {e}")
        
        return results
    
    async def send_trading_signal(self, signal: Dict) -> Dict[str, int]:
        """إرسال إشارة تداول لجميع المشتركين"""
        results = {
            "telegram_sent": 0,
            "email_sent": 0,
            "websocket_sent": 0,
            "total_subscribers": len(self.telegram_subscribers) + len(self.email_subscribers)
        }
        
        try:
            # إرسال عبر تليجرام
            if self.telegram_subscribers and self.trading_signals_enabled:
                async with telegram_service as tg:
                    results["telegram_sent"] = await tg.send_trading_signal(
                        list(self.telegram_subscribers), signal
                    )
            
            # إرسال عبر البريد الإلكتروني
            if self.email_subscribers and self.trading_signals_enabled:
                results["email_sent"] = 1 if await email_service.send_trading_signal_email(
                    list(self.email_subscribers), signal
                ) else 0
            
            # إرسال عبر WebSocket
            await websocket_manager.broadcast_signal(signal)
            results["websocket_sent"] = len(websocket_manager.connection_manager.active_connections)
            
            logger.info(f"تم إرسال إشارة تداول: {results}")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال إشارة التداول: {e}")
        
        return results
    
    async def send_price_alert(self, user_id: str, symbol: str, current_price: float, 
                              target_price: float, alert_type: str, 
                              notification_type: str = "telegram") -> bool:
        """إرسال تنبيه سعر لمستخدم محدد"""
        try:
            if notification_type == "telegram" and user_id in self.telegram_subscribers:
                async with telegram_service as tg:
                    return await tg.send_price_alert(user_id, symbol, current_price, target_price, alert_type)
            
            elif notification_type == "email" and user_id in self.email_subscribers:
                # يمكن تطوير تنبيه البريد الإلكتروني هنا
                return True
            
            elif notification_type == "websocket":
                alert_data = {
                    "symbol": symbol,
                    "current_price": current_price,
                    "target_price": target_price,
                    "alert_type": alert_type
                }
                await websocket_manager.send_notification(user_id, alert_data)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في إرسال تنبيه السعر: {e}")
            return False
    
    async def send_daily_report(self, market_data: Dict, signals: List[Dict]) -> Dict[str, int]:
        """إرسال التقرير اليومي"""
        results = {
            "telegram_sent": 0,
            "email_sent": 0,
            "total_subscribers": len(self.telegram_subscribers) + len(self.email_subscribers)
        }
        
        try:
            # إعداد محتوى التقرير
            report_data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "market_summary": market_data,
                "signals": signals,
                "total_signals": len(signals)
            }
            
            # إرسال عبر تليجرام
            if self.telegram_subscribers:
                message = self._format_daily_report_telegram(report_data)
                async with telegram_service as tg:
                    for chat_id in self.telegram_subscribers:
                        if await tg.send_message(chat_id, message):
                            results["telegram_sent"] += 1
                        await asyncio.sleep(0.1)
            
            # إرسال عبر البريد الإلكتروني
            if self.email_subscribers:
                subject = f"التقرير اليومي - {report_data['date']}"
                html_content = self._format_daily_report_html(report_data)
                
                if await email_service.send_email(
                    list(self.email_subscribers), subject, html_content
                ):
                    results["email_sent"] = len(self.email_subscribers)
            
            logger.info(f"تم إرسال التقرير اليومي: {results}")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال التقرير اليومي: {e}")
        
        return results
    
    def _format_daily_report_telegram(self, report_data: Dict) -> str:
        """تنسيق التقرير اليومي لتليجرام"""
        market_data = report_data["market_summary"]
        tasi_data = market_data.get("tasi_index", {})
        signals = report_data["signals"]
        
        trend_icon = "📈" if tasi_data.get("change", 0) >= 0 else "📉"
        
        message = f"""
📊 <b>التقرير اليومي - {report_data['date']}</b>

🏛️ <b>مؤشر تاسي:</b>
{trend_icon} {tasi_data.get('index', 0):,.2f} ({tasi_data.get('change_percent', 0):+.2f}%)

📈 <b>إحصائيات اليوم:</b>
• إجمالي الإشارات: {len(signals)}
• الأسهم الرابحة: {market_data.get('advancing', 0)}
• الأسهم الخاسرة: {market_data.get('declining', 0)}

🎯 <b>أهم الإشارات:</b>
"""
        
        # إضافة أهم 3 إشارات
        for i, signal in enumerate(signals[:3], 1):
            confidence_emoji = "🟢" if signal.get("confidence", 0) >= 70 else "🟡"
            message += f"{i}. {confidence_emoji} {signal.get('symbol', '')}: {signal.get('signal_type', '')} ({signal.get('confidence', 0):.0f}%)\n"
        
        message += f"\n⏰ <b>وقت التقرير:</b> {datetime.now().strftime('%H:%M:%S')}"
        message += "\n\n📱 منصة تحليل الأسهم السعودية"
        
        return message
    
    def _format_daily_report_html(self, report_data: Dict) -> str:
        """تنسيق التقرير اليومي للبريد الإلكتروني"""
        # يمكن تطوير قالب HTML مفصل هنا
        return f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>التقرير اليومي - {report_data['date']}</title>
</head>
<body style="font-family: Arial, sans-serif; direction: rtl;">
    <h1>التقرير اليومي - {report_data['date']}</h1>
    <p>تم إنشاء التقرير في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>إجمالي الإشارات: {len(report_data['signals'])}</p>
</body>
</html>
"""
    
    def get_subscription_stats(self) -> Dict:
        """إحصائيات الاشتراكات"""
        return {
            "telegram_subscribers": len(self.telegram_subscribers),
            "email_subscribers": len(self.email_subscribers),
            "total_subscribers": len(self.telegram_subscribers) + len(self.email_subscribers),
            "websocket_connections": len(websocket_manager.connection_manager.active_connections),
            "settings": {
                "market_summary_enabled": self.market_summary_enabled,
                "trading_signals_enabled": self.trading_signals_enabled,
                "price_alerts_enabled": self.price_alerts_enabled
            },
            "last_activities": {
                "last_market_summary": self.last_market_summary.isoformat() if self.last_market_summary else None,
                "last_signals_check": self.last_signals_check.isoformat() if self.last_signals_check else None
            }
        }
    
    def update_settings(self, settings: Dict) -> bool:
        """تحديث إعدادات الإشعارات"""
        try:
            if "market_summary_enabled" in settings:
                self.market_summary_enabled = settings["market_summary_enabled"]
            
            if "trading_signals_enabled" in settings:
                self.trading_signals_enabled = settings["trading_signals_enabled"]
            
            if "price_alerts_enabled" in settings:
                self.price_alerts_enabled = settings["price_alerts_enabled"]
            
            logger.info("تم تحديث إعدادات الإشعارات")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الإعدادات: {e}")
            return False

# إنشاء مثيل عام للخدمة
notification_service = NotificationService()

