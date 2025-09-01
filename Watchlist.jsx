import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Star, 
  Trash2, 
  Plus,
  Search,
  TrendingUp,
  TrendingDown,
  Bell,
  BellOff,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

const Watchlist = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [watchedStocks, setWatchedStocks] = useState([
    {
      id: 1,
      symbol: 'SABIC',
      nameAr: 'سابك',
      sector: 'البتروكيماويات',
      price: 125.50,
      change: 5.25,
      changePercent: 4.37,
      volume: 2500000,
      alertsEnabled: true,
      addedDate: '2024-01-10'
    },
    {
      id: 2,
      symbol: 'STC',
      nameAr: 'الاتصالات السعودية',
      sector: 'الاتصالات',
      price: 45.80,
      change: -1.90,
      changePercent: -3.98,
      volume: 1800000,
      alertsEnabled: true,
      addedDate: '2024-01-12'
    },
    {
      id: 3,
      symbol: 'RAJHI',
      nameAr: 'الراجحي',
      sector: 'البنوك',
      price: 89.20,
      change: 3.10,
      changePercent: 3.60,
      volume: 3200000,
      alertsEnabled: false,
      addedDate: '2024-01-08'
    },
    {
      id: 4,
      symbol: 'ARAMCO',
      nameAr: 'أرامكو',
      sector: 'الطاقة',
      price: 32.15,
      change: 0.95,
      changePercent: 3.05,
      volume: 5600000,
      alertsEnabled: true,
      addedDate: '2024-01-15'
    }
  ])

  const [availableStocks] = useState([
    { symbol: 'ALMARAI', nameAr: 'المراعي', sector: 'الأغذية' },
    { symbol: 'NCB', nameAr: 'الأهلي', sector: 'البنوك' },
    { symbol: 'RIYAD', nameAr: 'الرياض', sector: 'البنوك' },
    { symbol: 'SAMBA', nameAr: 'سامبا', sector: 'البنوك' },
    { symbol: 'MOBILY', nameAr: 'موبايلي', sector: 'الاتصالات' },
    { symbol: 'ZAIN', nameAr: 'زين', sector: 'الاتصالات' }
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

  const removeFromWatchlist = (stockId) => {
    setWatchedStocks(watchedStocks.filter(stock => stock.id !== stockId))
  }

  const toggleAlerts = (stockId) => {
    setWatchedStocks(watchedStocks.map(stock => 
      stock.id === stockId 
        ? { ...stock, alertsEnabled: !stock.alertsEnabled }
        : stock
    ))
  }

  const addToWatchlist = (stockSymbol) => {
    const stockToAdd = availableStocks.find(stock => stock.symbol === stockSymbol)
    if (stockToAdd && !watchedStocks.find(stock => stock.symbol === stockSymbol)) {
      const newStock = {
        id: Date.now(),
        ...stockToAdd,
        price: Math.random() * 100 + 20,
        change: (Math.random() - 0.5) * 10,
        changePercent: (Math.random() - 0.5) * 10,
        volume: Math.floor(Math.random() * 5000000) + 1000000,
        alertsEnabled: true,
        addedDate: new Date().toISOString().split('T')[0]
      }
      setWatchedStocks([...watchedStocks, newStock])
    }
  }

  const filteredAvailableStocks = availableStocks.filter(stock => 
    !watchedStocks.find(watched => watched.symbol === stock.symbol) &&
    (stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
     stock.nameAr.includes(searchTerm))
  )

  const totalValue = watchedStocks.reduce((sum, stock) => sum + stock.price, 0)
  const totalGainers = watchedStocks.filter(stock => stock.change > 0).length
  const totalLosers = watchedStocks.filter(stock => stock.change < 0).length

  return (
    <div className="space-y-6">
      {/* العنوان والإحصائيات */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">قائمة المراقبة</h1>
          <p className="text-muted-foreground mt-2">تتبع أسهمك المفضلة</p>
        </div>
        
        <Dialog>
          <DialogTrigger asChild>
            <Button className="mt-4 md:mt-0">
              <Plus className="h-4 w-4 ml-2" />
              إضافة سهم
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>إضافة سهم لقائمة المراقبة</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="relative">
                <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  type="text"
                  placeholder="ابحث عن سهم..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pr-10"
                />
              </div>
              <div className="max-h-60 overflow-y-auto space-y-2">
                {filteredAvailableStocks.map((stock) => (
                  <div 
                    key={stock.symbol}
                    className="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-accent cursor-pointer"
                    onClick={() => addToWatchlist(stock.symbol)}
                  >
                    <div>
                      <div className="font-medium">{stock.symbol}</div>
                      <div className="text-sm text-muted-foreground">{stock.nameAr}</div>
                    </div>
                    <Badge variant="outline">{stock.sector}</Badge>
                  </div>
                ))}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* إحصائيات سريعة */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">إجمالي الأسهم</p>
                <p className="text-2xl font-bold">{watchedStocks.length}</p>
              </div>
              <Star className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">القيمة الإجمالية</p>
                <p className="text-2xl font-bold currency">{formatCurrency(totalValue)}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">الأسهم الرابحة</p>
                <p className="text-2xl font-bold text-tasi-green">{totalGainers}</p>
              </div>
              <ArrowUpRight className="h-8 w-8 text-tasi-green" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">الأسهم الخاسرة</p>
                <p className="text-2xl font-bold text-tasi-red">{totalLosers}</p>
              </div>
              <ArrowDownRight className="h-8 w-8 text-tasi-red" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* قائمة الأسهم المراقبة */}
      {watchedStocks.length > 0 ? (
        <div className="space-y-4">
          {watchedStocks.map((stock) => (
            <Card key={stock.id} className="hover:shadow-md transition-shadow">
              <CardContent className="pt-6">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                  {/* معلومات السهم */}
                  <div className="lg:col-span-3">
                    <div className="flex items-center space-x-3 space-x-reverse">
                      <Star className="h-5 w-5 text-yellow-500 fill-current" />
                      <div>
                        <Link 
                          to={`/stock/${stock.symbol}`}
                          className="font-bold text-lg text-foreground hover:text-primary"
                        >
                          {stock.symbol}
                        </Link>
                        <p className="text-sm text-muted-foreground">{stock.nameAr}</p>
                        <Badge variant="outline" className="text-xs mt-1">{stock.sector}</Badge>
                      </div>
                    </div>
                  </div>

                  {/* السعر والتغيير */}
                  <div className="lg:col-span-3">
                    <div className="text-2xl font-bold currency">{formatCurrency(stock.price)}</div>
                    <div className="flex items-center mt-1">
                      {stock.change > 0 ? (
                        <>
                          <ArrowUpRight className="h-4 w-4 text-tasi-green ml-1" />
                          <span className="text-tasi-green font-medium">
                            +{formatCurrency(Math.abs(stock.change))} (+{Math.abs(stock.changePercent).toFixed(2)}%)
                          </span>
                        </>
                      ) : (
                        <>
                          <ArrowDownRight className="h-4 w-4 text-tasi-red ml-1" />
                          <span className="text-tasi-red font-medium">
                            -{formatCurrency(Math.abs(stock.change))} ({Math.abs(stock.changePercent).toFixed(2)}%)
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* حجم التداول */}
                  <div className="lg:col-span-2">
                    <p className="text-sm text-muted-foreground">حجم التداول</p>
                    <p className="font-medium">{formatNumber(stock.volume)}</p>
                  </div>

                  {/* تاريخ الإضافة */}
                  <div className="lg:col-span-2">
                    <p className="text-sm text-muted-foreground">تاريخ الإضافة</p>
                    <p className="font-medium">{stock.addedDate}</p>
                  </div>

                  {/* أزرار التحكم */}
                  <div className="lg:col-span-2">
                    <div className="flex items-center space-x-2 space-x-reverse">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleAlerts(stock.id)}
                        className={stock.alertsEnabled ? 'text-blue-500' : 'text-muted-foreground'}
                      >
                        {stock.alertsEnabled ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4" />}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFromWatchlist(stock.id)}
                        className="text-tasi-red hover:text-tasi-red"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <Star className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">قائمة المراقبة فارغة</h3>
              <p className="text-muted-foreground mb-6">ابدأ بإضافة أسهمك المفضلة لتتبع أدائها</p>
              <Dialog>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="h-4 w-4 ml-2" />
                    إضافة أول سهم
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>إضافة سهم لقائمة المراقبة</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="relative">
                      <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                      <Input
                        type="text"
                        placeholder="ابحث عن سهم..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pr-10"
                      />
                    </div>
                    <div className="max-h-60 overflow-y-auto space-y-2">
                      {filteredAvailableStocks.map((stock) => (
                        <div 
                          key={stock.symbol}
                          className="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-accent cursor-pointer"
                          onClick={() => addToWatchlist(stock.symbol)}
                        >
                          <div>
                            <div className="font-medium">{stock.symbol}</div>
                            <div className="text-sm text-muted-foreground">{stock.nameAr}</div>
                          </div>
                          <Badge variant="outline">{stock.sector}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default Watchlist

