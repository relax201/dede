"""
خدمة التحليل الفني وحساب المؤشرات
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
from dataclasses import dataclass

@dataclass
class TechnicalSignal:
    """إشارة فنية"""
    symbol: str
    signal_type: str  # "buy", "sell", "hold"
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    target1: float
    target2: Optional[float]
    timeframe: str
    reason: str
    indicators: List[str]
    timestamp: datetime

class TechnicalAnalysisService:
    """خدمة التحليل الفني"""
    
    def __init__(self):
        self.min_periods = 50  # الحد الأدنى للفترات المطلوبة للتحليل
    
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """حساب المتوسط المتحرك البسيط"""
        return data.rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """حساب المتوسط المتحرك الأسي"""
        return data.ewm(span=period).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """حساب مؤشر القوة النسبية"""
        if TALIB_AVAILABLE:
            try:
                return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)
            except:
                pass
        
        # حساب RSI يدوياً
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """حساب مؤشر MACD"""
        if TALIB_AVAILABLE:
            try:
                macd, macd_signal, macd_hist = talib.MACD(data.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
                return {
                    'macd': pd.Series(macd, index=data.index),
                    'signal': pd.Series(macd_signal, index=data.index),
                    'histogram': pd.Series(macd_hist, index=data.index)
                }
            except:
                pass
        
        # حساب MACD يدوياً
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)
        macd = ema_fast - ema_slow
        macd_signal = self.calculate_ema(macd, signal)
        macd_hist = macd - macd_signal
        
        return {
            'macd': macd,
            'signal': macd_signal,
            'histogram': macd_hist
        }
    
    def calculate_bollinger_bands(self, data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """حساب نطاقات بولينجر"""
        sma = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """حساب مؤشر الستوكاستيك"""
        if TALIB_AVAILABLE:
            try:
                slowk, slowd = talib.STOCH(high.values, low.values, close.values, 
                                         fastk_period=k_period, slowk_period=3, slowd_period=d_period)
                return {
                    'k': pd.Series(slowk, index=close.index),
                    'd': pd.Series(slowd, index=close.index)
                }
            except:
                pass
        
        # حساب الستوكاستيك يدوياً
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }
    
    def detect_support_resistance(self, data: pd.DataFrame, window: int = 20) -> Dict[str, List[float]]:
        """كشف مستويات الدعم والمقاومة"""
        highs = data['high'].rolling(window=window, center=True).max()
        lows = data['low'].rolling(window=window, center=True).min()
        
        # مستويات المقاومة (القمم)
        resistance_levels = []
        for i in range(window, len(data) - window):
            if data['high'].iloc[i] == highs.iloc[i]:
                resistance_levels.append(data['high'].iloc[i])
        
        # مستويات الدعم (القيعان)
        support_levels = []
        for i in range(window, len(data) - window):
            if data['low'].iloc[i] == lows.iloc[i]:
                support_levels.append(data['low'].iloc[i])
        
        return {
            'resistance': sorted(set(resistance_levels), reverse=True)[:5],
            'support': sorted(set(support_levels))[:5]
        }
    
    def analyze_trend(self, data: pd.DataFrame) -> Dict[str, str]:
        """تحليل الاتجاه العام"""
        if len(data) < 50:
            return {'trend': 'غير محدد', 'strength': 'ضعيف'}
        
        # حساب المتوسطات المتحركة
        sma_20 = self.calculate_sma(data['close'], 20)
        sma_50 = self.calculate_sma(data['close'], 50)
        
        current_price = data['close'].iloc[-1]
        sma_20_current = sma_20.iloc[-1]
        sma_50_current = sma_50.iloc[-1]
        
        # تحديد الاتجاه
        if current_price > sma_20_current > sma_50_current:
            trend = 'صاعد'
            strength = 'قوي' if (current_price - sma_50_current) / sma_50_current > 0.05 else 'متوسط'
        elif current_price < sma_20_current < sma_50_current:
            trend = 'هابط'
            strength = 'قوي' if (sma_50_current - current_price) / sma_50_current > 0.05 else 'متوسط'
        else:
            trend = 'جانبي'
            strength = 'ضعيف'
        
        return {'trend': trend, 'strength': strength}
    
    def generate_signals(self, symbol: str, data: pd.DataFrame, timeframe: str = "1D") -> List[TechnicalSignal]:
        """توليد الإشارات الفنية"""
        signals = []
        
        if len(data) < self.min_periods:
            return signals
        
        try:
            # حساب المؤشرات
            rsi = self.calculate_rsi(data['close'])
            macd_data = self.calculate_macd(data['close'])
            bb_data = self.calculate_bollinger_bands(data['close'])
            stoch_data = self.calculate_stochastic(data['high'], data['low'], data['close'])
            
            # المتوسطات المتحركة
            ema_20 = self.calculate_ema(data['close'], 20)
            ema_50 = self.calculate_ema(data['close'], 50)
            
            # مستويات الدعم والمقاومة
            levels = self.detect_support_resistance(data)
            
            # تحليل الاتجاه
            trend_analysis = self.analyze_trend(data)
            
            # الحصول على القيم الحالية
            current_price = data['close'].iloc[-1]
            current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            current_macd = macd_data['macd'].iloc[-1] if not pd.isna(macd_data['macd'].iloc[-1]) else 0
            current_macd_signal = macd_data['signal'].iloc[-1] if not pd.isna(macd_data['signal'].iloc[-1]) else 0
            current_stoch_k = stoch_data['k'].iloc[-1] if not pd.isna(stoch_data['k'].iloc[-1]) else 50
            
            # قواعد توليد الإشارات
            confidence = 0
            signal_type = "hold"
            reason = ""
            indicators_used = []
            
            # إشارات الشراء
            buy_signals = 0
            sell_signals = 0
            
            # RSI
            if current_rsi < 30:
                buy_signals += 1
                indicators_used.append(f"RSI: {current_rsi:.1f}")
            elif current_rsi > 70:
                sell_signals += 1
                indicators_used.append(f"RSI: {current_rsi:.1f}")
            
            # MACD
            if current_macd > current_macd_signal and macd_data['macd'].iloc[-2] <= macd_data['signal'].iloc[-2]:
                buy_signals += 1
                indicators_used.append("MACD: إشارة ذهبية")
            elif current_macd < current_macd_signal and macd_data['macd'].iloc[-2] >= macd_data['signal'].iloc[-2]:
                sell_signals += 1
                indicators_used.append("MACD: إشارة موت")
            
            # المتوسطات المتحركة
            if ema_20.iloc[-1] > ema_50.iloc[-1] and ema_20.iloc[-2] <= ema_50.iloc[-2]:
                buy_signals += 1
                indicators_used.append("EMA: كسر صاعد")
            elif ema_20.iloc[-1] < ema_50.iloc[-1] and ema_20.iloc[-2] >= ema_50.iloc[-2]:
                sell_signals += 1
                indicators_used.append("EMA: كسر هابط")
            
            # الستوكاستيك
            if current_stoch_k < 20:
                buy_signals += 1
                indicators_used.append(f"Stoch: {current_stoch_k:.1f}")
            elif current_stoch_k > 80:
                sell_signals += 1
                indicators_used.append(f"Stoch: {current_stoch_k:.1f}")
            
            # نطاقات بولينجر
            if current_price <= bb_data['lower'].iloc[-1]:
                buy_signals += 1
                indicators_used.append("BB: لمس النطاق السفلي")
            elif current_price >= bb_data['upper'].iloc[-1]:
                sell_signals += 1
                indicators_used.append("BB: لمس النطاق العلوي")
            
            # تحديد نوع الإشارة والثقة
            if buy_signals > sell_signals:
                signal_type = "شراء"
                confidence = min(90, 40 + (buy_signals * 15))
                reason = f"إشارات شراء متعددة ({buy_signals} مؤشرات إيجابية)"
                
                # حساب مستويات الدخول والأهداف
                entry_price = current_price
                stop_loss = current_price * 0.95  # 5% وقف خسارة
                target1 = current_price * 1.08   # 8% هدف أول
                target2 = current_price * 1.15   # 15% هدف ثاني
                
            elif sell_signals > buy_signals:
                signal_type = "بيع"
                confidence = min(90, 40 + (sell_signals * 15))
                reason = f"إشارات بيع متعددة ({sell_signals} مؤشرات سلبية)"
                
                # حساب مستويات الدخول والأهداف
                entry_price = current_price
                stop_loss = current_price * 1.05  # 5% وقف خسارة
                target1 = current_price * 0.92   # 8% هدف أول
                target2 = current_price * 0.85   # 15% هدف ثاني
                
            else:
                signal_type = "انتظار"
                confidence = 30
                reason = "إشارات متضاربة، يُنصح بالانتظار"
                entry_price = current_price
                stop_loss = current_price * 0.95
                target1 = current_price * 1.05
                target2 = None
            
            # إنشاء الإشارة
            if signal_type != "انتظار" and confidence >= 60:
                signal = TechnicalSignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    entry_price=round(entry_price, 2),
                    stop_loss=round(stop_loss, 2),
                    target1=round(target1, 2),
                    target2=round(target2, 2) if target2 else None,
                    timeframe=timeframe,
                    reason=reason,
                    indicators=indicators_used,
                    timestamp=datetime.now()
                )
                signals.append(signal)
        
        except Exception as e:
            print(f"خطأ في توليد الإشارات للرمز {symbol}: {e}")
        
        return signals
    
    def calculate_all_indicators(self, data: pd.DataFrame) -> Dict:
        """حساب جميع المؤشرات الفنية"""
        if len(data) < self.min_periods:
            return {}
        
        try:
            indicators = {}
            
            # المتوسطات المتحركة
            indicators['sma_20'] = self.calculate_sma(data['close'], 20).iloc[-1]
            indicators['sma_50'] = self.calculate_sma(data['close'], 50).iloc[-1]
            indicators['ema_20'] = self.calculate_ema(data['close'], 20).iloc[-1]
            indicators['ema_50'] = self.calculate_ema(data['close'], 50).iloc[-1]
            
            # RSI
            rsi = self.calculate_rsi(data['close'])
            indicators['rsi'] = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
            
            # MACD
            macd_data = self.calculate_macd(data['close'])
            indicators['macd'] = macd_data['macd'].iloc[-1] if not pd.isna(macd_data['macd'].iloc[-1]) else None
            indicators['macd_signal'] = macd_data['signal'].iloc[-1] if not pd.isna(macd_data['signal'].iloc[-1]) else None
            indicators['macd_histogram'] = macd_data['histogram'].iloc[-1] if not pd.isna(macd_data['histogram'].iloc[-1]) else None
            
            # نطاقات بولينجر
            bb_data = self.calculate_bollinger_bands(data['close'])
            indicators['bb_upper'] = bb_data['upper'].iloc[-1]
            indicators['bb_middle'] = bb_data['middle'].iloc[-1]
            indicators['bb_lower'] = bb_data['lower'].iloc[-1]
            
            # الستوكاستيك
            stoch_data = self.calculate_stochastic(data['high'], data['low'], data['close'])
            indicators['stoch_k'] = stoch_data['k'].iloc[-1] if not pd.isna(stoch_data['k'].iloc[-1]) else None
            indicators['stoch_d'] = stoch_data['d'].iloc[-1] if not pd.isna(stoch_data['d'].iloc[-1]) else None
            
            # مستويات الدعم والمقاومة
            levels = self.detect_support_resistance(data)
            indicators['support_levels'] = levels['support']
            indicators['resistance_levels'] = levels['resistance']
            
            # تحليل الاتجاه
            trend_analysis = self.analyze_trend(data)
            indicators['trend'] = trend_analysis['trend']
            indicators['trend_strength'] = trend_analysis['strength']
            
            return indicators
            
        except Exception as e:
            print(f"خطأ في حساب المؤشرات: {e}")
            return {}

# إنشاء مثيل عام للخدمة
technical_analysis_service = TechnicalAnalysisService()

