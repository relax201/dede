"""
Notifications endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from app.services.notification_service import notification_service
from app.services.market_data import market_data_service
from app.services.technical_analysis import technical_analysis_service

router = APIRouter()

class TelegramSubscription(BaseModel):
    chat_id: str

class EmailSubscription(BaseModel):
    email: EmailStr

class NotificationSettings(BaseModel):
    market_summary_enabled: Optional[bool] = None
    trading_signals_enabled: Optional[bool] = None
    price_alerts_enabled: Optional[bool] = None

class PriceAlert(BaseModel):
    user_id: str
    symbol: str
    target_price: float
    alert_type: str  # "above" or "below"
    notification_type: str = "telegram"  # "telegram", "email", "websocket"

@router.post("/subscribe/telegram")
async def subscribe_telegram(subscription: TelegramSubscription):
    """الاشتراك في إشعارات تليجرام"""
    try:
        success = notification_service.add_telegram_subscriber(subscription.chat_id)
        if success:
            return {
                "success": True,
                "message": "تم الاشتراك في إشعارات تليجرام بنجاح",
                "chat_id": subscription.chat_id
            }
        else:
            raise HTTPException(status_code=400, detail="فشل في الاشتراك")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في الاشتراك: {str(e)}")

@router.delete("/subscribe/telegram/{chat_id}")
async def unsubscribe_telegram(chat_id: str):
    """إلغاء الاشتراك في إشعارات تليجرام"""
    try:
        success = notification_service.remove_telegram_subscriber(chat_id)
        if success:
            return {
                "success": True,
                "message": "تم إلغاء الاشتراك بنجاح",
                "chat_id": chat_id
            }
        else:
            raise HTTPException(status_code=400, detail="فشل في إلغاء الاشتراك")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إلغاء الاشتراك: {str(e)}")

@router.post("/subscribe/email")
async def subscribe_email(subscription: EmailSubscription):
    """الاشتراك في إشعارات البريد الإلكتروني"""
    try:
        success = notification_service.add_email_subscriber(subscription.email)
        if success:
            return {
                "success": True,
                "message": "تم الاشتراك في إشعارات البريد الإلكتروني بنجاح",
                "email": subscription.email
            }
        else:
            raise HTTPException(status_code=400, detail="فشل في الاشتراك")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في الاشتراك: {str(e)}")

@router.delete("/subscribe/email/{email}")
async def unsubscribe_email(email: str):
    """إلغاء الاشتراك في إشعارات البريد الإلكتروني"""
    try:
        success = notification_service.remove_email_subscriber(email)
        if success:
            return {
                "success": True,
                "message": "تم إلغاء الاشتراك بنجاح",
                "email": email
            }
        else:
            raise HTTPException(status_code=400, detail="فشل في إلغاء الاشتراك")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إلغاء الاشتراك: {str(e)}")

@router.post("/send/market-summary")
async def send_market_summary(background_tasks: BackgroundTasks):
    """إرسال ملخص السوق لجميع المشتركين"""
    try:
        # جلب بيانات السوق
        async with market_data_service as service:
            tasi_data = await service.get_tasi_index()
            symbols = ["SABIC", "STC", "RAJHI", "ARAMCO"]
            prices = await service.get_real_time_prices(symbols)
            
            # تحضير بيانات ملخص السوق
            gainers = []
            losers = []
            
            for symbol, price_data in prices.items():
                if price_data["change_percent"] > 0:
                    gainers.append({
                        "symbol": symbol,
                        "change_percent": price_data["change_percent"],
                        "price": price_data["price"]
                    })
                else:
                    losers.append({
                        "symbol": symbol,
                        "change_percent": price_data["change_percent"],
                        "price": price_data["price"]
                    })
            
            gainers.sort(key=lambda x: x["change_percent"], reverse=True)
            losers.sort(key=lambda x: x["change_percent"])
            
            market_data = {
                "tasi_index": tasi_data,
                "top_gainers": gainers,
                "top_losers": losers,
                "advancing": len(gainers),
                "declining": len(losers)
            }
        
        # إرسال الإشعارات في الخلفية
        background_tasks.add_task(notification_service.send_market_summary, market_data)
        
        return {
            "success": True,
            "message": "تم بدء إرسال ملخص السوق",
            "subscribers": notification_service.get_subscription_stats()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إرسال ملخص السوق: {str(e)}")

@router.post("/send/trading-signal/{symbol}")
async def send_trading_signal(symbol: str, background_tasks: BackgroundTasks):
    """إرسال إشارة تداول لرمز محدد"""
    try:
        # جلب البيانات وتوليد الإشارة
        async with market_data_service as service:
            historical_data = await service.get_historical_data(symbol.upper(), "3m")
            
            if historical_data.empty:
                raise HTTPException(status_code=404, detail="لا توجد بيانات كافية للتحليل")
            
            # توليد الإشارات
            signals = technical_analysis_service.generate_signals(symbol.upper(), historical_data)
            
            if not signals:
                return {
                    "success": False,
                    "message": "لا توجد إشارات قوية للرمز حالياً",
                    "symbol": symbol.upper()
                }
            
            # أخذ أقوى إشارة
            best_signal = max(signals, key=lambda s: s.confidence)
            
            signal_data = {
                "symbol": best_signal.symbol,
                "signal_type": best_signal.signal_type,
                "confidence": best_signal.confidence,
                "entry_price": best_signal.entry_price,
                "stop_loss": best_signal.stop_loss,
                "target1": best_signal.target1,
                "target2": best_signal.target2,
                "timeframe": best_signal.timeframe,
                "reason": best_signal.reason,
                "indicators": best_signal.indicators,
                "timestamp": best_signal.timestamp.isoformat()
            }
        
        # إرسال الإشعارات في الخلفية
        background_tasks.add_task(notification_service.send_trading_signal, signal_data)
        
        return {
            "success": True,
            "message": "تم بدء إرسال إشارة التداول",
            "signal": signal_data,
            "subscribers": notification_service.get_subscription_stats()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إرسال إشارة التداول: {str(e)}")

@router.post("/send/price-alert")
async def send_price_alert(alert: PriceAlert):
    """إرسال تنبيه سعر"""
    try:
        # جلب السعر الحالي
        async with market_data_service as service:
            prices = await service.get_real_time_prices([alert.symbol.upper()])
            
            if alert.symbol.upper() not in prices:
                raise HTTPException(status_code=404, detail="الرمز غير موجود")
            
            current_price = prices[alert.symbol.upper()]["price"]
        
        # التحقق من شرط التنبيه
        should_alert = False
        if alert.alert_type == "above" and current_price >= alert.target_price:
            should_alert = True
        elif alert.alert_type == "below" and current_price <= alert.target_price:
            should_alert = True
        
        if should_alert:
            success = await notification_service.send_price_alert(
                alert.user_id, alert.symbol.upper(), current_price, 
                alert.target_price, alert.alert_type, alert.notification_type
            )
            
            return {
                "success": success,
                "message": "تم إرسال تنبيه السعر" if success else "فشل في إرسال التنبيه",
                "alert_triggered": True,
                "current_price": current_price,
                "target_price": alert.target_price
            }
        else:
            return {
                "success": True,
                "message": "لم يتم تفعيل التنبيه بعد",
                "alert_triggered": False,
                "current_price": current_price,
                "target_price": alert.target_price
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في تنبيه السعر: {str(e)}")

@router.get("/stats")
async def get_notification_stats():
    """إحصائيات الإشعارات والاشتراكات"""
    try:
        stats = notification_service.get_subscription_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب الإحصائيات: {str(e)}")

@router.put("/settings")
async def update_notification_settings(settings: NotificationSettings):
    """تحديث إعدادات الإشعارات"""
    try:
        settings_dict = settings.dict(exclude_unset=True)
        success = notification_service.update_settings(settings_dict)
        
        if success:
            return {
                "success": True,
                "message": "تم تحديث الإعدادات بنجاح",
                "settings": notification_service.get_subscription_stats()["settings"]
            }
        else:
            raise HTTPException(status_code=400, detail="فشل في تحديث الإعدادات")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في تحديث الإعدادات: {str(e)}")

@router.post("/test/telegram/{chat_id}")
async def test_telegram_notification(chat_id: str):
    """اختبار إشعار تليجرام"""
    try:
        from app.services.telegram_service import telegram_service
        
        test_message = """
🧪 <b>رسالة اختبار</b>

مرحباً! هذه رسالة اختبار من منصة تحليل الأسهم السعودية.

✅ إذا وصلتك هذه الرسالة، فإن الإشعارات تعمل بشكل صحيح.

📱 منصة تحليل الأسهم السعودية
"""
        
        async with telegram_service as tg:
            success = await tg.send_message(chat_id, test_message)
        
        return {
            "success": success,
            "message": "تم إرسال رسالة الاختبار" if success else "فشل في إرسال رسالة الاختبار",
            "chat_id": chat_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في اختبار تليجرام: {str(e)}")

@router.post("/test/email")
async def test_email_notification(subscription: EmailSubscription):
    """اختبار إشعار البريد الإلكتروني"""
    try:
        from app.services.email_service import email_service
        
        subject = "رسالة اختبار - منصة تحليل الأسهم السعودية"
        html_content = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>رسالة اختبار</title>
</head>
<body style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
    <h1>🧪 رسالة اختبار</h1>
    <p>مرحباً! هذه رسالة اختبار من منصة تحليل الأسهم السعودية.</p>
    <p>✅ إذا وصلك هذا البريد، فإن الإشعارات تعمل بشكل صحيح.</p>
    <hr>
    <p><strong>منصة تحليل الأسهم السعودية</strong></p>
    <p>تحليل احترافي للأسهم السعودية مع أسعار لحظية ونظام توصيات آلي</p>
</body>
</html>
"""
        
        success = await email_service.send_email([subscription.email], subject, html_content)
        
        return {
            "success": success,
            "message": "تم إرسال بريد الاختبار" if success else "فشل في إرسال بريد الاختبار",
            "email": subscription.email
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في اختبار البريد الإلكتروني: {str(e)}")

