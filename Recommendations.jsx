import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  TrendingUp, 
  TrendingDown, 
  Filter,
  Clock,
  Target,
  Shield,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const Recommendations = () => {
  const [filter, setFilter] = useState('all')
  const [sortBy, setSortBy] = useState('time')

  const [recommendations] = useState([
    {
      id: 1,
      symbol: 'SABIC',
      nameAr: 'سابك',
      signal: 'شراء',
      confidence: 85,
      entry: 125.50,
      currentPrice: 127.80,
      stopLoss: 118.00,
      target1: 135.00,
      target2: 142.00,
      status: 'نشطة',
      timeframe: '1ساعة',
      timestamp: '2024-01-15 14:30:00',
      reason: 'كسر مقاومة قوية مع حجم تداول عالي',
      profitLoss: 1.83,
      sector: 'البتروكيماويات'
    },
    {
      id: 2,
      symbol: 'STC',
      nameAr: 'الاتصالات السعودية',
      signal: 'بيع',
      confidence: 78,
      entry: 47.20,
      currentPrice: 45.80,
      stopLoss: 49.50,
      target1: 42.00,
      target2: 38.50,
      status: 'تحقق الهدف الأول',
      timeframe: '4ساعات',
      timestamp: '2024-01-15 10:15:00',
      reason: 'تشبع شرائي وإشارات بيع قوية',
      profitLoss: -2.97,
      sector: 'الاتصالات'
    },
    {
      id: 3,
      symbol: 'RAJHI',
      nameAr: 'الراجحي',
      signal: 'شراء',
      confidence: 92,
      entry: 86.10,
      currentPrice: 89.20,
      stopLoss: 82.00,
      target1: 94.00,
      target2: 98.50,
      status: 'نشطة',
      timeframe: 'يومي',
      timestamp: '2024-01-14 13:45:00',
      reason: 'إشارة ذهبية وكسر مستوى مقاومة',
      profitLoss: 3.60,
      sector: 'البنوك'
    },
    {
      id: 4,
      symbol: 'ARAMCO',
      nameAr: 'أرامكو',
      signal: 'شراء',
      confidence: 75,
      entry: 31.20,
      currentPrice: 32.15,
      stopLoss: 29.50,
      target1: 34.00,
      target2: 36.50,
      status: 'نشطة',
      timeframe: '1ساعة',
      timestamp: '2024-01-15 12:00:00',
      reason: 'ارتداد من دعم قوي',
      profitLoss: 3.05,
      sector: 'الطاقة'
    },
    {
      id: 5,
      symbol: 'ALMARAI',
      nameAr: 'المراعي',
      signal: 'بيع',
      confidence: 68,
      entry: 55.10,
      currentPrice: 52.30,
      stopLoss: 57.80,
      target1: 50.00,
      target2: 47.50,
      status: 'ضرب وقف الخسارة',
      timeframe: '4ساعات',
      timestamp: '2024-01-13 09:30:00',
      reason: 'كسر دعم مهم',
      profitLoss: -4.90,
      sector: 'الأغذية'
    }
  ])

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency: 'SAR',
      minimumFractionDigits: 2
    }).format(value)
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'نشطة':
        return 'bg-blue-500'
      case 'تحقق الهدف الأول':
      case 'تحقق الهدف الثاني':
        return 'bg-tasi-green'
      case 'ضرب وقف الخسارة':
        return 'bg-tasi-red'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'نشطة':
        return <AlertCircle className="h-4 w-4" />
      case 'تحقق الهدف الأول':
      case 'تحقق الهدف الثاني':
        return <CheckCircle className="h-4 w-4" />
      case 'ضرب وقف الخسارة':
        return <XCircle className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const filteredRecommendations = recommendations.filter(rec => {
    if (filter === 'all') return true
    if (filter === 'buy') return rec.signal === 'شراء'
    if (filter === 'sell') return rec.signal === 'بيع'
    if (filter === 'active') return rec.status === 'نشطة'
    return true
  })

  return (
    <div className="space-y-6">
      {/* العنوان والفلاتر */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">التوصيات الحية</h1>
          <p className="text-muted-foreground mt-2">إشارات التداول والتوصيات الآلية</p>
        </div>
        
        <div className="flex items-center space-x-4 space-x-reverse mt-4 md:mt-0">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="فلترة" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">جميع التوصيات</SelectItem>
              <SelectItem value="buy">إشارات الشراء</SelectItem>
              <SelectItem value="sell">إشارات البيع</SelectItem>
              <SelectItem value="active">النشطة فقط</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="ترتيب" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="time">الوقت</SelectItem>
              <SelectItem value="confidence">مستوى الثقة</SelectItem>
              <SelectItem value="profit">الربح/الخسارة</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* إحصائيات سريعة */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">إجمالي التوصيات</p>
                <p className="text-2xl font-bold">{recommendations.length}</p>
              </div>
              <Target className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">التوصيات النشطة</p>
                <p className="text-2xl font-bold text-blue-500">
                  {recommendations.filter(r => r.status === 'نشطة').length}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">تحقق الأهداف</p>
                <p className="text-2xl font-bold text-tasi-green">
                  {recommendations.filter(r => r.status.includes('تحقق')).length}
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-tasi-green" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">وقف الخسائر</p>
                <p className="text-2xl font-bold text-tasi-red">
                  {recommendations.filter(r => r.status.includes('ضرب')).length}
                </p>
              </div>
              <XCircle className="h-8 w-8 text-tasi-red" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* قائمة التوصيات */}
      <div className="space-y-4">
        {filteredRecommendations.map((rec) => (
          <Card key={rec.id} className="hover:shadow-md transition-shadow">
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                {/* معلومات السهم */}
                <div className="lg:col-span-3">
                  <div className="flex items-center space-x-3 space-x-reverse">
                    <div className={`w-3 h-3 rounded-full ${getStatusColor(rec.status)}`}></div>
                    <div>
                      <Link 
                        to={`/stock/${rec.symbol}`}
                        className="font-bold text-lg text-foreground hover:text-primary"
                      >
                        {rec.symbol}
                      </Link>
                      <p className="text-sm text-muted-foreground">{rec.nameAr}</p>
                      <Badge variant="outline" className="text-xs mt-1">{rec.sector}</Badge>
                    </div>
                  </div>
                </div>

                {/* نوع الإشارة والثقة */}
                <div className="lg:col-span-2">
                  <Badge 
                    variant={rec.signal === 'شراء' ? 'default' : 'destructive'}
                    className={`${rec.signal === 'شراء' ? 'bg-tasi-green' : 'bg-tasi-red'} mb-2`}
                  >
                    {rec.signal}
                  </Badge>
                  <p className="text-sm text-muted-foreground">ثقة {rec.confidence}%</p>
                  <p className="text-xs text-muted-foreground">{rec.timeframe}</p>
                </div>

                {/* الأسعار */}
                <div className="lg:col-span-3">
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-xs text-muted-foreground">الدخول:</span>
                      <span className="text-sm font-medium currency">{formatCurrency(rec.entry)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-muted-foreground">الحالي:</span>
                      <span className="text-sm font-medium currency">{formatCurrency(rec.currentPrice)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-muted-foreground">الهدف:</span>
                      <span className="text-sm font-medium currency text-tasi-green">{formatCurrency(rec.target1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-muted-foreground">وقف الخسارة:</span>
                      <span className="text-sm font-medium currency text-tasi-red">{formatCurrency(rec.stopLoss)}</span>
                    </div>
                  </div>
                </div>

                {/* الحالة والربح/الخسارة */}
                <div className="lg:col-span-2">
                  <div className="flex items-center space-x-2 space-x-reverse mb-2">
                    {getStatusIcon(rec.status)}
                    <span className="text-sm font-medium">{rec.status}</span>
                  </div>
                  <div className={`text-lg font-bold ${rec.profitLoss >= 0 ? 'text-tasi-green' : 'text-tasi-red'}`}>
                    {rec.profitLoss >= 0 ? '+' : ''}{rec.profitLoss}%
                  </div>
                </div>

                {/* الوقت والسبب */}
                <div className="lg:col-span-2">
                  <p className="text-xs text-muted-foreground mb-1">{rec.timestamp}</p>
                  <p className="text-sm text-muted-foreground">{rec.reason}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredRecommendations.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <Target className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">لا توجد توصيات تطابق الفلتر المحدد</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default Recommendations

