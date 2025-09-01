"""
خدمة إرسال البريد الإلكتروني
"""
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """خدمة إرسال البريد الإلكتروني"""
    
    def __init__(self):
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', None)
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        self.from_email = getattr(settings, 'FROM_EMAIL', self.smtp_username)
        self.from_name = getattr(settings, 'FROM_NAME', 'منصة تحليل الأسهم السعودية')
    
    async def send_email(self, to_emails: List[str], subject: str, html_content: str, 
                        text_content: str = None, attachments: List[str] = None) -> bool:
        """إرسال بريد إلكتروني"""
        if not self.smtp_username or not self.smtp_password:
            logger.warning("إعدادات البريد الإلكتروني غير مُعدة بشكل صحيح")
            return False
        
        try:
            # إنشاء الرسالة
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = ', '.join(to_emails)
            
            # إضافة المحتوى النصي
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(text_part)
            
            # إضافة المحتوى HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(html_part)
            
            # إضافة المرفقات
            if attachments:
                for file_path in attachments:
                    try:
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {file_path.split("/")[-1]}'
                            )
                            message.attach(part)
                    except Exception as e:
                        logger.error(f"خطأ في إضافة المرفق {file_path}: {e}")
            
            # إرسال البريد
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_username,
                password=self.smtp_password
            )
            
            logger.info(f"تم إرسال البريد الإلكتروني بنجاح إلى {len(to_emails)} مستلم")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إرسال البريد الإلكتروني: {e}")
            return False
    
    def generate_market_summary_html(self, market_data: Dict) -> str:
        """إنشاء تقرير HTML لملخص السوق"""
        tasi_data = market_data.get("tasi_index", {})
        gainers = market_data.get("top_gainers", [])
        losers = market_data.get("top_losers", [])
        
        # تحديد لون التغيير
        change_color = "#28a745" if tasi_data.get("change", 0) >= 0 else "#dc3545"
        change_icon = "📈" if tasi_data.get("change", 0) >= 0 else "📉"
        
        html = f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ملخص السوق السعودي</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            direction: rtl;
            text-align: right;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            padding: 30px;
        }}
        .index-card {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid {change_color};
        }}
        .index-value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }}
        .index-change {{
            font-size: 18px;
            color: {change_color};
            font-weight: bold;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h3 {{
            color: #333;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .stock-list {{
            list-style: none;
            padding: 0;
        }}
        .stock-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        .stock-symbol {{
            font-weight: bold;
            color: #333;
        }}
        .stock-change {{
            font-weight: bold;
        }}
        .positive {{
            color: #28a745;
        }}
        .negative {{
            color: #dc3545;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 14px;
            text-align: center;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ ملخص السوق السعودي - تاسي</h1>
        </div>
        
        <div class="content">
            <div class="index-card">
                <div class="index-value">
                    {change_icon} {tasi_data.get('index', 0):,.2f}
                </div>
                <div class="index-change">
                    التغيير: {tasi_data.get('change', 0):+.2f} ({tasi_data.get('change_percent', 0):+.2f}%)
                </div>
                <div style="margin-top: 10px; color: #6c757d;">
                    حجم التداول: {tasi_data.get('volume', 0):,}
                </div>
            </div>
            
            <div class="section">
                <h3>🟢 الأسهم الرابحة</h3>
                <ul class="stock-list">
"""
        
        for gainer in gainers[:5]:
            html += f"""
                    <li class="stock-item">
                        <span class="stock-symbol">{gainer['symbol']}</span>
                        <span class="stock-change positive">+{gainer['change_percent']:.2f}%</span>
                    </li>
"""
        
        html += """
                </ul>
            </div>
            
            <div class="section">
                <h3>🔴 الأسهم الخاسرة</h3>
                <ul class="stock-list">
"""
        
        for loser in losers[:5]:
            html += f"""
                    <li class="stock-item">
                        <span class="stock-symbol">{loser['symbol']}</span>
                        <span class="stock-change negative">{loser['change_percent']:.2f}%</span>
                    </li>
"""
        
        html += f"""
                </ul>
            </div>
            
            <div class="timestamp">
                ⏰ وقت التحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <div class="footer">
            <p>منصة تحليل الأسهم السعودية</p>
            <p>تحليل احترافي للأسهم السعودية مع أسعار لحظية ونظام توصيات آلي</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_trading_signal_html(self, signal: Dict) -> str:
        """إنشاء تقرير HTML لإشارة التداول"""
        symbol = signal.get("symbol", "")
        signal_type = signal.get("signal_type", "")
        confidence = signal.get("confidence", 0)
        entry_price = signal.get("entry_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        target1 = signal.get("target1", 0)
        reason = signal.get("reason", "")
        
        # تحديد الألوان والرموز
        if signal_type == "شراء":
            signal_color = "#28a745"
            signal_icon = "🟢"
        elif signal_type == "بيع":
            signal_color = "#dc3545"
            signal_icon = "🔴"
        else:
            signal_color = "#ffc107"
            signal_icon = "🟡"
        
        html = f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>إشارة تداول جديدة</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            direction: rtl;
            text-align: right;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 500px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, {signal_color} 0%, {signal_color}dd 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .content {{
            padding: 30px;
        }}
        .signal-card {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid {signal_color};
        }}
        .detail-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        .detail-label {{
            font-weight: bold;
            color: #333;
        }}
        .detail-value {{
            color: #6c757d;
        }}
        .reason-box {{
            background-color: #e9ecef;
            border-radius: 5px;
            padding: 15px;
            margin-top: 20px;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{signal_icon} إشارة تداول جديدة</h1>
            <h2>{symbol}</h2>
        </div>
        
        <div class="content">
            <div class="signal-card">
                <div class="detail-row">
                    <span class="detail-label">🎯 التوصية:</span>
                    <span class="detail-value" style="color: {signal_color}; font-weight: bold;">{signal_type}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">⭐ مستوى الثقة:</span>
                    <span class="detail-value">{confidence:.0f}%</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">💰 سعر الدخول:</span>
                    <span class="detail-value">{entry_price:.2f} ريال</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">🛑 وقف الخسارة:</span>
                    <span class="detail-value">{stop_loss:.2f} ريال</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">🎯 الهدف الأول:</span>
                    <span class="detail-value">{target1:.2f} ريال</span>
                </div>
            </div>
            
            <div class="reason-box">
                <strong>📝 السبب:</strong><br>
                {reason}
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #6c757d; font-size: 14px;">
                ⏰ وقت الإشارة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <div class="footer">
            <p>منصة تحليل الأسهم السعودية</p>
            <p><strong>تنبيه:</strong> هذه الإشارات للأغراض التعليمية فقط وليست نصائح استثمارية</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    async def send_market_summary_email(self, to_emails: List[str], market_data: Dict) -> bool:
        """إرسال ملخص السوق عبر البريد الإلكتروني"""
        subject = f"ملخص السوق السعودي - {datetime.now().strftime('%Y-%m-%d')}"
        html_content = self.generate_market_summary_html(market_data)
        
        # محتوى نصي بديل
        tasi_data = market_data.get("tasi_index", {})
        text_content = f"""
ملخص السوق السعودي - تاسي

المؤشر العام: {tasi_data.get('index', 0):,.2f}
التغيير: {tasi_data.get('change', 0):+.2f} ({tasi_data.get('change_percent', 0):+.2f}%)
حجم التداول: {tasi_data.get('volume', 0):,}

وقت التحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

منصة تحليل الأسهم السعودية
"""
        
        return await self.send_email(to_emails, subject, html_content, text_content)
    
    async def send_trading_signal_email(self, to_emails: List[str], signal: Dict) -> bool:
        """إرسال إشارة تداول عبر البريد الإلكتروني"""
        symbol = signal.get("symbol", "")
        signal_type = signal.get("signal_type", "")
        
        subject = f"إشارة تداول جديدة - {symbol} ({signal_type})"
        html_content = self.generate_trading_signal_html(signal)
        
        # محتوى نصي بديل
        text_content = f"""
إشارة تداول جديدة

الرمز: {symbol}
التوصية: {signal_type}
مستوى الثقة: {signal.get('confidence', 0):.0f}%
سعر الدخول: {signal.get('entry_price', 0):.2f} ريال
وقف الخسارة: {signal.get('stop_loss', 0):.2f} ريال
الهدف الأول: {signal.get('target1', 0):.2f} ريال

السبب: {signal.get('reason', '')}

وقت الإشارة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

منصة تحليل الأسهم السعودية
تنبيه: هذه الإشارات للأغراض التعليمية فقط وليست نصائح استثمارية
"""
        
        return await self.send_email(to_emails, subject, html_content, text_content)

# إنشاء مثيل عام للخدمة
email_service = EmailService()

