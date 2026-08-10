"""
خدمة جلب بيانات السوق السعودي
"""
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models.symbol import Symbol
from app.models.price import Price
from app.db.database import get_db

class MarketDataService:
    """خدمة جلب وتحديث بيانات السوق"""
    
    def __init__(self):
        self.base_url = "https://www.tadawul.com.sa"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_tasi_symbols(self) -> List[Dict]:
        """جلب قائمة رموز الأسهم من تداول"""
        try:
            # محاكاة بيانات حقيقية لرموز تاسي الرئيسية
            symbols = [
                {
                    "symbol": "2010",
                    "symbol_name": "SABIC",
                    "company_name_ar": "الشركة السعودية للصناعات الأساسية",
                    "company_name_en": "Saudi Basic Industries Corporation",
                    "sector_ar": "البتروكيماويات",
                    "sector_en": "Petrochemicals",
                    "market_cap": 375200000000,
                    "shares_outstanding": 3000000000
                },
                {
                    "symbol": "7010",
                    "symbol_name": "STC",
                    "company_name_ar": "شركة الاتصالات السعودية",
                    "company_name_en": "Saudi Telecom Company",
                    "sector_ar": "الاتصالات",
                    "sector_en": "Telecommunications",
                    "market_cap": 91600000000,
                    "shares_outstanding": 2000000000
                },
                {
                    "symbol": "1120",
                    "symbol_name": "RAJHI",
                    "company_name_ar": "مصرف الراجحي",
                    "company_name_en": "Al Rajhi Bank",
                    "sector_ar": "البنوك",
                    "sector_en": "Banks",
                    "market_cap": 267300000000,
                    "shares_outstanding": 3000000000
                },
                {
                    "symbol": "2222",
                    "symbol_name": "ARAMCO",
                    "company_name_ar": "أرامكو السعودية",
                    "company_name_en": "Saudi Aramco",
                    "sector_ar": "الطاقة",
                    "sector_en": "Energy",
                    "market_cap": 1600000000000,
                    "shares_outstanding": 50000000000
                },
                {
                    "symbol": "2280",
                    "symbol_name": "ALMARAI",
                    "company_name_ar": "شركة المراعي",
                    "company_name_en": "Almarai Company",
                    "sector_ar": "الأغذية",
                    "sector_en": "Food & Beverages",
                    "market_cap": 62400000000,
                    "shares_outstanding": 1200000000
                },
                {
                    "symbol": "1180",
                    "symbol_name": "NCB",
                    "company_name_ar": "البنك الأهلي السعودي",
                    "company_name_en": "National Commercial Bank",
                    "sector_ar": "البنوك",
                    "sector_en": "Banks",
                    "market_cap": 116700000000,
                    "shares_outstanding": 3000000000
                },
                {
                    "symbol": "1010",
                    "symbol_name": "RIYAD",
                    "company_name_ar": "بنك الرياض",
                    "company_name_en": "Riyad Bank",
                    "sector_ar": "البنوك",
                    "sector_en": "Banks",
                    "market_cap": 85350000000,
                    "shares_outstanding": 3000000000
                },
                {
                    "symbol": "1050",
                    "symbol_name": "SAMBA",
                    "company_name_ar": "مجموعة سامبا المالية",
                    "company_name_en": "Samba Financial Group",
                    "sector_ar": "البنوك",
                    "sector_en": "Banks",
                    "market_cap": 123600000000,
                    "shares_outstanding": 3000000000
                }
            ]
            return symbols
        except Exception as e:
            print(f"خطأ في جلب رموز الأسهم: {e}")
            return []
    
    async def get_real_time_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """جلب الأسعار اللحظية للرموز المحددة"""
        try:
            # محاكاة أسعار حقيقية مع تقلبات طبيعية
            prices = {}
            base_prices = {
                "SABIC": 125.50,
                "STC": 45.80,
                "RAJHI": 89.20,
                "ARAMCO": 32.15,
                "ALMARAI": 52.30,
                "NCB": 38.90,
                "RIYAD": 28.45,
                "SAMBA": 41.20
            }
            
            for symbol in symbols:
                if symbol in base_prices:
                    base_price = base_prices[symbol]
                    # إضافة تقلب عشوائي ±3%
                    variation = np.random.uniform(-0.03, 0.03)
                    current_price = base_price * (1 + variation)
                    
                    change = current_price - base_price
                    change_percent = (change / base_price) * 100
                    
                    # محاكاة حجم التداول
                    volume = np.random.randint(1000000, 5000000)
                    
                    prices[symbol] = {
                        "symbol": symbol,
                        "price": round(current_price, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2),
                        "volume": volume,
                        "high": round(current_price * 1.02, 2),
                        "low": round(current_price * 0.98, 2),
                        "open": round(base_price * 0.995, 2),
                        "previous_close": base_price,
                        "timestamp": datetime.now().isoformat(),
                        "market_status": "open" if 9 <= datetime.now().hour <= 15 else "closed"
                    }
            
            return prices
        except Exception as e:
            print(f"خطأ في جلب الأسعار اللحظية: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """جلب البيانات التاريخية للسهم"""
        try:
            # محاكاة بيانات تاريخية
            end_date = datetime.now()
            if period == "1d":
                start_date = end_date - timedelta(days=1)
                freq = "1H"
            elif period == "1w":
                start_date = end_date - timedelta(weeks=1)
                freq = "1D"
            elif period == "1m":
                start_date = end_date - timedelta(days=30)
                freq = "1D"
            elif period == "3m":
                start_date = end_date - timedelta(days=90)
                freq = "1D"
            elif period == "6m":
                start_date = end_date - timedelta(days=180)
                freq = "1D"
            else:  # 1y
                start_date = end_date - timedelta(days=365)
                freq = "1D"
            
            # إنشاء فهرس زمني
            date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
            
            # محاكاة أسعار تاريخية مع اتجاه عام
            base_price = 100.0
            prices = []
            
            for i, date in enumerate(date_range):
                # إضافة اتجاه عام صاعد مع تقلبات
                trend = i * 0.1
                noise = np.random.normal(0, 2)
                price = base_price + trend + noise
                
                # ضمان أن السعر موجب
                price = max(price, 10.0)
                
                # حساب OHLC
                open_price = price + np.random.uniform(-1, 1)
                high_price = max(open_price, price) + np.random.uniform(0, 2)
                low_price = min(open_price, price) - np.random.uniform(0, 2)
                close_price = price
                volume = np.random.randint(500000, 3000000)
                
                prices.append({
                    "date": date,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": volume
                })
            
            df = pd.DataFrame(prices)
            df.set_index("date", inplace=True)
            return df
            
        except Exception as e:
            print(f"خطأ في جلب البيانات التاريخية: {e}")
            return pd.DataFrame()
    
    async def get_tasi_index(self) -> Dict:
        """جلب بيانات مؤشر تاسي"""
        try:
            # محاكاة بيانات مؤشر تاسي
            base_index = 12000
            variation = np.random.uniform(-0.02, 0.02)
            current_index = base_index * (1 + variation)
            
            change = current_index - base_index
            change_percent = (change / base_index) * 100
            
            return {
                "index": round(current_index, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": np.random.randint(2000000000, 3000000000),
                "trades": np.random.randint(100000, 150000),
                "timestamp": datetime.now().isoformat(),
                "market_status": "open" if 9 <= datetime.now().hour <= 15 else "closed"
            }
        except Exception as e:
            print(f"خطأ في جلب بيانات المؤشر: {e}")
            return {}
    
    def save_symbols_to_db(self, symbols: List[Dict], db: Session):
        """حفظ رموز الأسهم في قاعدة البيانات"""
        try:
            for symbol_data in symbols:
                # التحقق من وجود الرمز
                existing_symbol = db.query(Symbol).filter(
                    Symbol.symbol == symbol_data["symbol_name"]
                ).first()
                
                if not existing_symbol:
                    new_symbol = Symbol(
                        symbol=symbol_data["symbol_name"],
                        company_name_ar=symbol_data["company_name_ar"],
                        company_name_en=symbol_data["company_name_en"],
                        sector_ar=symbol_data["sector_ar"],
                        sector_en=symbol_data["sector_en"],
                        market_cap=symbol_data.get("market_cap"),
                        shares_outstanding=symbol_data.get("shares_outstanding"),
                        is_active=True
                    )
                    db.add(new_symbol)
            
            db.commit()
            print(f"تم حفظ {len(symbols)} رمز في قاعدة البيانات")
        except Exception as e:
            db.rollback()
            print(f"خطأ في حفظ الرموز: {e}")
    
    def save_prices_to_db(self, prices: Dict[str, Dict], db: Session):
        """حفظ الأسعار في قاعدة البيانات"""
        try:
            for symbol, price_data in prices.items():
                # البحث عن الرمز
                symbol_obj = db.query(Symbol).filter(Symbol.symbol == symbol).first()
                if symbol_obj:
                    new_price = Price(
                        symbol_id=symbol_obj.id,
                        price=price_data["price"],
                        change=price_data["change"],
                        change_percent=price_data["change_percent"],
                        volume=price_data["volume"],
                        high=price_data["high"],
                        low=price_data["low"],
                        open=price_data["open"],
                        previous_close=price_data["previous_close"],
                        timestamp=datetime.fromisoformat(price_data["timestamp"].replace('Z', '+00:00'))
                    )
                    db.add(new_price)
            
            db.commit()
            print(f"تم حفظ {len(prices)} سعر في قاعدة البيانات")
        except Exception as e:
            db.rollback()
            print(f"خطأ في حفظ الأسعار: {e}")

# إنشاء مثيل عام للخدمة
market_data_service = MarketDataService()

