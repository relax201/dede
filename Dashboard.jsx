import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  TrendingUp, 
  TrendingDown, 
  Activity,
  DollarSign,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const Dashboard = () => {
  const [marketData, setMarketData] = useState({
    tasiIndex: 12345.67,
    tasiChange: 1.25,
    volume: 2500000000,
    trades: 125000
  })

  const [topGainers] = useState([
    { symbol: 'SABIC', name: 'سابك', price: 125.50, change: 5.25, changePercent: 4.37 },
    { symbol: 'STC', name: 'الاتصالات السعودية', price: 45.80, change: 1.90, changePercent: 4.33 },
    { symbol: 'RAJHI', name: 'الراجحي', price: 89.20, change: 3.10, changePercent: 3.60 },
    { symbol: 'ARAMCO', name: 'أرامكو', price: 32.15, change: 0.95, changePercent: 3.05 },
  ])

  const [topLosers] = useState([
    { symbol: 'ALMARAI', name: 'المراعي', price: 52.30, change: -2.80, changePercent: -5.08 },
    { symbol: 'NCB', name: 'الأهلي', price: 38.90, change: -1.60, changePercent: -3.95 },
    { symbol: 'RIYAD', name: 'الرياض', price: 28.45, change: -1.05, changePercent: -3.56 },
    { symbol: 'SAMBA', name: 'سامبا', price: 41.20, change: -1.30, changePercent: -3.06 },
  ])

  const [recentSignals] = useState([
    { symbol: 'SABIC', type: 'شراء', confidence: 85, time: '14:30', reason: 'كسر مقاومة قوية' },
    { symbol: 'STC', type: 'بيع', confidence: 78, time: '14:15', reason: 'تشبع شرائي' },
    { symbol: 'RAJHI', type: 'شراء', confidence: 92, time: '13:45', reason: 'إشارة ذهبية' },
  ])

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

  return (
    <div className="space-y-6">
      {/* العنوان الرئيسي */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">لوحة التحكم</h1>
        <p className="text-muted-foreground mt-2">نظرة عامة على السوق السعودي</p>
      </div>

      {/* بطاقات المؤشرات الرئيسية */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">مؤشر تاسي</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold currency">{formatNumber(marketData.tasiIndex)}</div>
            <div className="flex items-center text-sm">
              {marketData.tasiChange > 0 ? (
                <>
                  <ArrowUpRight className="h-4 w-4 text-tasi-green ml-1" />
                  <span className="text-tasi-green">+{marketData.tasiChange}%</span>
                </>
              ) : (
                <>
                  <ArrowDownRight className="h-4 w-4 text-tasi-red ml-1" />
                  <span className="text-tasi-red">{marketData.tasiChange}%</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">حجم التداول</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(marketData.volume / 1000000)}م</div>
            <p className="text-xs text-muted-foreground">ريال سعودي</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">عدد الصفقات</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(marketData.trades)}</div>
            <p className="text-xs text-muted-foreground">صفقة</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">التوصيات النشطة</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">توصية</p>
          </CardContent>
        </Card>
      </div>

      {/* الأسهم الرابحة والخاسرة */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* أكبر الرابحين */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <TrendingUp className="h-5 w-5 text-tasi-green ml-2" />
              أكبر الرابحين
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {topGainers.map((stock) => (
                <div key={stock.symbol} className="flex items-center justify-between">
                  <div className="flex-1">
                    <Link 
                      to={`/stock/${stock.symbol}`}
                      className="font-medium text-foreground hover:text-primary"
                    >
                      {stock.symbol}
                    </Link>
                    <p className="text-sm text-muted-foreground">{stock.name}</p>
                  </div>
                  <div className="text-left ltr">
                    <div className="font-medium currency">{formatCurrency(stock.price)}</div>
                    <div className="text-sm text-tasi-green">
                      +{stock.changePercent}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* أكبر الخاسرين */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <TrendingDown className="h-5 w-5 text-tasi-red ml-2" />
              أكبر الخاسرين
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {topLosers.map((stock) => (
                <div key={stock.symbol} className="flex items-center justify-between">
                  <div className="flex-1">
                    <Link 
                      to={`/stock/${stock.symbol}`}
                      className="font-medium text-foreground hover:text-primary"
                    >
                      {stock.symbol}
                    </Link>
                    <p className="text-sm text-muted-foreground">{stock.name}</p>
                  </div>
                  <div className="text-left ltr">
                    <div className="font-medium currency">{formatCurrency(stock.price)}</div>
                    <div className="text-sm text-tasi-red">
                      {stock.changePercent}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* التوصيات الأخيرة */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>أحدث التوصيات</CardTitle>
          <Button variant="outline" size="sm" asChild>
            <Link to="/recommendations">عرض الكل</Link>
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentSignals.map((signal, index) => (
              <div key={index} className="flex items-center justify-between p-4 border border-border rounded-lg">
                <div className="flex items-center space-x-4 space-x-reverse">
                  <Badge 
                    variant={signal.type === 'شراء' ? 'default' : 'destructive'}
                    className={signal.type === 'شراء' ? 'bg-tasi-green' : 'bg-tasi-red'}
                  >
                    {signal.type}
                  </Badge>
                  <div>
                    <Link 
                      to={`/stock/${signal.symbol}`}
                      className="font-medium text-foreground hover:text-primary"
                    >
                      {signal.symbol}
                    </Link>
                    <p className="text-sm text-muted-foreground">{signal.reason}</p>
                  </div>
                </div>
                <div className="text-left ltr">
                  <div className="text-sm font-medium">ثقة {signal.confidence}%</div>
                  <div className="text-xs text-muted-foreground">{signal.time}</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default Dashboard

