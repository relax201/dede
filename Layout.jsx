import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  BarChart3, 
  TrendingUp, 
  Star, 
  Search, 
  Menu, 
  X,
  Sun,
  Moon,
  Bell
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(false)
  const location = useLocation()

  const navigation = [
    { name: 'لوحة التحكم', href: '/', icon: BarChart3 },
    { name: 'التوصيات', href: '/recommendations', icon: TrendingUp },
    { name: 'قائمة المراقبة', href: '/watchlist', icon: Star },
  ]

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
    document.documentElement.classList.toggle('dark')
  }

  return (
    <div className={`min-h-screen bg-background ${darkMode ? 'dark' : ''}`}>
      {/* الشريط العلوي */}
      <header className="bg-card border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* الشعار والعنوان */}
            <div className="flex items-center">
              <Button
                variant="ghost"
                size="sm"
                className="md:hidden ml-2"
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
              <Link to="/" className="flex items-center space-x-2 space-x-reverse">
                <div className="w-8 h-8 bg-tasi-blue rounded-lg flex items-center justify-center">
                  <BarChart3 className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">تاسي</h1>
                  <p className="text-xs text-muted-foreground">منصة تحليل الأسهم</p>
                </div>
              </Link>
            </div>

            {/* شريط البحث */}
            <div className="flex-1 max-w-lg mx-8 hidden md:block">
              <div className="relative">
                <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  type="text"
                  placeholder="ابحث عن سهم..."
                  className="pr-10 bg-background"
                />
              </div>
            </div>

            {/* أزرار التحكم */}
            <div className="flex items-center space-x-2 space-x-reverse">
              <Button variant="ghost" size="sm">
                <Bell className="h-5 w-5" />
              </Button>
              <Button variant="ghost" size="sm" onClick={toggleDarkMode}>
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* الشريط الجانبي */}
        <aside className={`
          fixed inset-y-0 right-0 z-40 w-64 bg-card border-l border-border transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : 'translate-x-full'}
          md:translate-x-0 md:static md:inset-0
        `}>
          <div className="flex flex-col h-full pt-16 md:pt-0">
            {/* التنقل الرئيسي */}
            <nav className="flex-1 px-4 py-6 space-y-2">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`
                      flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors
                      ${isActive 
                        ? 'bg-primary text-primary-foreground' 
                        : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                      }
                    `}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon className="ml-3 h-5 w-5" />
                    {item.name}
                  </Link>
                )
              })}
            </nav>

            {/* معلومات السوق السريعة */}
            <div className="p-4 border-t border-border">
              <Card className="p-4">
                <h3 className="text-sm font-medium text-foreground mb-2">مؤشر تاسي</h3>
                <div className="space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-bold currency">12,345.67</span>
                    <span className="text-sm text-tasi-green">+1.25%</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    آخر تحديث: 15:30
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </aside>

        {/* المحتوى الرئيسي */}
        <main className="flex-1 md:mr-64">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {children}
          </div>
        </main>
      </div>

      {/* خلفية الشريط الجانبي للموبايل */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}

export default Layout

