import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { 
  TrendingUp, 
  TrendingDown, 
  Star,
  StarOff,
  Target,
  Shield,
  Clock,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const StockDetails = () => {
  const { symbol } = useParams()
  const [isWatched, setIsWatched] = useState(false)
  
  // بيانات وهمية للسهم
  const [stockData] = useState({
    symbol: symbol || 'SABIC',
    nameAr: 'الشركة السعودية للصناعات الأساسية',
    nameEn: 'Saudi Basic Industries Corporation',
    sector: 'البتروكيماويات',
    price: 125.50,
    change: 5.25,
    changePercent: 4.37,
    volume: 2500000,
    high: 127.80,
    low: 120.30,
    open: 121.00,
    previousClose: 120.25,
    marketCap: '375.2B',
    pe: 18.5,
    eps: 6.78,
    dividend: 3.2
  })

  const [recommendation] = useState({
    signal: 'شراء',
    confidence: 85,
    entry: 125.50,
    stopLoss: 118.00,
    target1: 135.00,
    target2: 142.00,
    reason: 'كسر مقاومة قوية مع حجم تداول عالي وإشارات فنية إيجابية',
    indicators: ['RSI: 65', 'MACD: إيجابي', 'EMA50: فوق', 'Volume: عالي'],
    timeframe: '1ساعة',
    timestamp: '2024-01-15 14:30:00'
  })

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency: 'SAR',
      minimumFractionDigits: 2
    }).format(value)
  }

  const formatNumber = (value) => {
    return new Intl.NumberFormat('ar-SA').format(value)
  }

  const toggleWatchlist = () => {
    setIsWatched(!isWatched)
  }

  return (
    <div className="space-y-6">
      {/* رأس الصفحة */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center space-x-4 space-x-reverse">
            <h1 className="text-3xl font-bold text-foreground">{stockData.symbol}</h1>
            <Badge variant="outline">{stockData.sector}</Badge>
          </div>
          <h2 className="text-xl text-muted-foreground mt-1">{stockData.nameAr}</h2>
          <p className="text-sm text-muted-foreground">{stockData.nameEn}</p>
        </div>
        <Button 
          variant={isWatched ? "default" : "outline"}
          onClick={toggleWatchlist}
          className="mt-4 md:mt-0"
        >
          {isWatched ? <Star className="h-4 w-4 ml-2 fill-current" /> : <StarOff className="h-4 w-4 ml-2" />}
          {isWatched ? 'في المراقبة' : 'إضافة للمراقبة'}
        </Button>
      </div>

      {/* السعر الحالي */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-4xl font-bold currency">{formatCurrency(stockData.price)}</div>
              <div className="flex items-center mt-2">
                {stockData.change > 0 ? (
                  <>
                    <ArrowUpRight className="h-5 w-5 text-tasi-green ml-1" />
                    <span className="text-tasi-green font-medium">
                      +{formatCurrency(stockData.change)} (+{stockData.changePercent}%)
                    </span>
                  </>
                ) : (
                  <>
                    <ArrowDownRight className="h-5 w-5 text-tasi-red ml-1" />
                    <span className="text-tasi-red font-medium">
                      {formatCurrency(stockData.change)} ({stockData.changePercent}%)
                    </span>
                  </>
                )}
              </div>
            </div>
            <div className="text-left ltr space-y-2">
              <div className="text-sm text-muted-foreground">
                <span>الحجم: </span>
                <span className="font-medium">{formatNumber(stockData.volume)}</span>
              </div>
              <div className="text-sm text-muted-foreground">
                <span>آخر تحديث: </span>
                <span className="font-medium">15:30</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* التوصية الحالية */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Target className="h-5 w-5 ml-2" />
            التوصية الحالية
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">نوع الإشارة:</span>
                <Badge 
                  variant={recommendation.signal === 'شراء' ? 'default' : 'destructive'}
                  className={recommendation.signal === 'شراء' ? 'bg-tasi-green' : 'bg-tasi-red'}
                >
                  {recommendation.signal}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">مستوى الثقة:</span>
                <span className="font-medium">{recommendation.confidence}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">الإطار الزمني:</span>
                <span className="font-medium">{recommendation.timeframe}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">وقت الإشارة:</span>
                <span className="font-medium text-xs">{recommendation.timestamp}</span>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">نقطة الدخول:</span>
                <span className="font-medium currency">{formatCurrency(recommendation.entry)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">وقف الخسارة:</span>
                <span className="font-medium currency text-tasi-red">{formatCurrency(recommendation.stopLoss)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">الهدف الأول:</span>
                <span className="font-medium currency text-tasi-green">{formatCurrency(recommendation.target1)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">الهدف الثاني:</span>
                <span className="font-medium currency text-tasi-green">{formatCurrency(recommendation.target2)}</span>
              </div>
            </div>
          </div>
          
          <div className="mt-6">
            <h4 className="text-sm font-medium text-foreground mb-2">سبب التوصية:</h4>
            <p className="text-sm text-muted-foreground">{recommendation.reason}</p>
          </div>
          
          <div className="mt-4">
            <h4 className="text-sm font-medium text-foreground mb-2">المؤشرات المستخدمة:</h4>
            <div className="flex flex-wrap gap-2">
              {recommendation.indicators.map((indicator, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {indicator}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* التبويبات */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview">نظرة عامة</TabsTrigger>
          <TabsTrigger value="chart">الرسم البياني</TabsTrigger>
          <TabsTrigger value="analysis">التحليل الفني</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-6">
          {/* الإحصائيات الرئيسية */}
          <Card>
            <CardHeader>
              <CardTitle>الإحصائيات الرئيسية</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">الافتتاح</div>
                  <div className="font-medium currency">{formatCurrency(stockData.open)}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">أعلى سعر</div>
                  <div className="font-medium currency">{formatCurrency(stockData.high)}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">أدنى سعر</div>
                  <div className="font-medium currency">{formatCurrency(stockData.low)}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">الإغلاق السابق</div>
                  <div className="font-medium currency">{formatCurrency(stockData.previousClose)}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">القيمة السوقية</div>
                  <div className="font-medium">{stockData.marketCap}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">نسبة السعر للربح</div>
                  <div className="font-medium">{stockData.pe}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">ربحية السهم</div>
                  <div className="font-medium currency">{formatCurrency(stockData.eps)}</div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">العائد</div>
                  <div className="font-medium">{stockData.dividend}%</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="chart">
          <Card>
            <CardHeader>
              <CardTitle>الرسم البياني</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96 flex items-center justify-center bg-muted rounded-lg chart-container">
                <p className="text-muted-foreground">سيتم إضافة الرسم البياني التفاعلي هنا</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="analysis">
          <Card>
            <CardHeader>
              <CardTitle>التحليل الفني</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-muted-foreground">سيتم إضافة التحليل الفني التفصيلي هنا</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default StockDetails

