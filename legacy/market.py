"""
Market data endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.services.market_data import market_data_service
from app.services.technical_analysis import technical_analysis_service

router = APIRouter()

@router.get("/tasi-index")
async def get_tasi_index():
    """الحصول على بيانات مؤشر تاسي"""
    try:
        async with market_data_service as service:
            index_data = await service.get_tasi_index()
            return {"success": True, "data": index_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب بيانات المؤشر: {str(e)}")

@router.get("/symbols")
async def get_symbols(db: Session = Depends(get_db)):
    """الحصول على قائمة رموز الأسهم"""
    try:
        async with market_data_service as service:
            symbols = await service.get_tasi_symbols()
            
            # حفظ في قاعدة البيانات إذا لم تكن موجودة
            if symbols:
                service.save_symbols_to_db(symbols, db)
            
            return {"success": True, "data": symbols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب الرموز: {str(e)}")

@router.get("/prices")
async def get_real_time_prices(
    symbols: Optional[str] = Query(None, description="رموز الأسهم مفصولة بفاصلة"),
    db: Session = Depends(get_db)
):
    """الحصول على الأسعار اللحظية"""
    try:
        # تحديد الرموز
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
        else:
            symbol_list = ["SABIC", "STC", "RAJHI", "ARAMCO", "ALMARAI", "NCB", "RIYAD", "SAMBA"]
        
        async with market_data_service as service:
            prices = await service.get_real_time_prices(symbol_list)
            
            # حفظ في قاعدة البيانات
            if prices:
                service.save_prices_to_db(prices, db)
            
            return {"success": True, "data": prices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب الأسعار: {str(e)}")

@router.get("/prices/{symbol}")
async def get_symbol_price(symbol: str, db: Session = Depends(get_db)):
    """الحصول على سعر رمز محدد"""
    try:
        async with market_data_service as service:
            prices = await service.get_real_time_prices([symbol.upper()])
            
            if symbol.upper() not in prices:
                raise HTTPException(status_code=404, detail="الرمز غير موجود")
            
            price_data = prices[symbol.upper()]
            
            # حفظ في قاعدة البيانات
            service.save_prices_to_db({symbol.upper(): price_data}, db)
            
            return {"success": True, "data": price_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب سعر الرمز: {str(e)}")

@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = Query("1m", description="الفترة الزمنية (1d, 1w, 1m, 3m, 6m, 1y)"),
    interval: str = Query("1d", description="الفاصل الزمني (1m, 5m, 15m, 1h, 1d)")
):
    """الحصول على البيانات التاريخية"""
    try:
        async with market_data_service as service:
            historical_data = await service.get_historical_data(symbol.upper(), period)
            
            if historical_data.empty:
                raise HTTPException(status_code=404, detail="لا توجد بيانات تاريخية للرمز")
            
            # تحويل DataFrame إلى قاموس
            data = []
            for index, row in historical_data.iterrows():
                data.append({
                    "date": index.isoformat(),
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"]
                })
            
            return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب البيانات التاريخية: {str(e)}")

@router.get("/analysis/{symbol}")
async def get_technical_analysis(symbol: str):
    """الحصول على التحليل الفني لرمز"""
    try:
        async with market_data_service as service:
            # جلب البيانات التاريخية
            historical_data = await service.get_historical_data(symbol.upper(), "3m")
            
            if historical_data.empty:
                raise HTTPException(status_code=404, detail="لا توجد بيانات كافية للتحليل")
            
            # حساب المؤشرات الفنية
            indicators = technical_analysis_service.calculate_all_indicators(historical_data)
            
            # توليد الإشارات
            signals = technical_analysis_service.generate_signals(symbol.upper(), historical_data)
            
            # تحويل الإشارات إلى قاموس
            signals_data = []
            for signal in signals:
                signals_data.append({
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type,
                    "confidence": signal.confidence,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target1": signal.target1,
                    "target2": signal.target2,
                    "timeframe": signal.timeframe,
                    "reason": signal.reason,
                    "indicators": signal.indicators,
                    "timestamp": signal.timestamp.isoformat()
                })
            
            return {
                "success": True,
                "data": {
                    "indicators": indicators,
                    "signals": signals_data
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في التحليل الفني: {str(e)}")

@router.get("/signals")
async def get_all_signals():
    """الحصول على جميع الإشارات الحالية"""
    try:
        symbols = ["SABIC", "STC", "RAJHI", "ARAMCO", "ALMARAI", "NCB", "RIYAD", "SAMBA"]
        all_signals = []
        
        async with market_data_service as service:
            for symbol in symbols:
                try:
                    # جلب البيانات التاريخية
                    historical_data = await service.get_historical_data(symbol, "3m")
                    
                    if not historical_data.empty:
                        # توليد الإشارات
                        signals = technical_analysis_service.generate_signals(symbol, historical_data)
                        
                        # تحويل إلى قاموس
                        for signal in signals:
                            all_signals.append({
                                "symbol": signal.symbol,
                                "signal_type": signal.signal_type,
                                "confidence": signal.confidence,
                                "entry_price": signal.entry_price,
                                "stop_loss": signal.stop_loss,
                                "target1": signal.target1,
                                "target2": signal.target2,
                                "timeframe": signal.timeframe,
                                "reason": signal.reason,
                                "indicators": signal.indicators,
                                "timestamp": signal.timestamp.isoformat()
                            })
                except Exception as e:
                    print(f"خطأ في معالجة الرمز {symbol}: {e}")
                    continue
        
        return {"success": True, "data": all_signals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب الإشارات: {str(e)}")

@router.get("/market-summary")
async def get_market_summary():
    """الحصول على ملخص السوق"""
    try:
        async with market_data_service as service:
            # بيانات المؤشر
            tasi_data = await service.get_tasi_index()
            
            # أسعار الأسهم الرئيسية
            main_symbols = ["SABIC", "STC", "RAJHI", "ARAMCO"]
            prices = await service.get_real_time_prices(main_symbols)
            
            # حساب إحصائيات السوق
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
            
            # ترتيب حسب النسبة
            gainers.sort(key=lambda x: x["change_percent"], reverse=True)
            losers.sort(key=lambda x: x["change_percent"])
            
            return {
                "success": True,
                "data": {
                    "tasi_index": tasi_data,
                    "top_gainers": gainers[:5],
                    "top_losers": losers[:5],
                    "total_symbols": len(prices),
                    "advancing": len(gainers),
                    "declining": len(losers)
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب ملخص السوق: {str(e)}")

