import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Sun, Moon, LogOut, ChevronDown, Menu } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import { useAuthStore } from '../../store/authStore'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/products': 'Products Manager',
  '/avatars': 'Avatar Manager',
  '/voices': 'Voice Manager',
  '/video-studio': 'Video Studio',
  '/video-queue': 'Video Queue',
  '/training': 'Training Player',
  '/roleplay': 'Roleplay Practice',
  '/agent': 'Sahayak',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
}

interface HeaderProps {
  onMenuToggle: () => void
}

export default function Header({ onMenuToggle }: HeaderProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const title = pageTitles[location.pathname] || 'GroMo AI Trainer'
  const { toggleTheme, isDark } = useTheme()
  const { user, logout, isAdmin } = useAuthStore()
  const [showMenu, setShowMenu] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.charAt(0).toUpperCase() || 'U'

  return (
    <header className="h-14 md:h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-3 md:px-6">
      <div className="flex items-center gap-2">
        <button
          onClick={onMenuToggle}
          className="md:hidden p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h2 className="text-base md:text-lg font-semibold text-gray-900 dark:text-white truncate">{title}</h2>
      </div>
      <div className="flex items-center gap-2 md:gap-3">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className={`relative w-12 h-6 md:w-14 md:h-7 rounded-full transition-colors duration-300 focus:outline-none ${
            isDark ? 'bg-primary-600' : 'bg-gray-300'
          }`}
          title={isDark ? 'Light mode' : 'Dark mode'}
        >
          <div className={`absolute top-0.5 w-5 h-5 md:w-6 md:h-6 rounded-full bg-white shadow-md transform transition-transform duration-300 flex items-center justify-center ${isDark ? 'translate-x-6 md:translate-x-7' : 'translate-x-0.5'}`}>
            {isDark ? <Moon className="w-3 h-3 md:w-3.5 md:h-3.5 text-primary-600" /> : <Sun className="w-3 h-3 md:w-3.5 md:h-3.5 text-amber-500" />}
          </div>
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="flex items-center gap-1.5 md:gap-2 px-1.5 md:px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <div className={`w-7 h-7 md:w-8 md:h-8 rounded-full flex items-center justify-center text-xs md:text-sm font-medium ${
              isAdmin
                ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-400'
                : 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-400'
            }`}>
              {initials}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-sm font-medium text-gray-900 dark:text-white leading-tight">
                {user?.name || user?.email?.split('@')[0] || 'User'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{user?.role || 'user'}</p>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-400 hidden sm:block" />
          </button>

          {showMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 top-12 z-50 w-56 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 py-2">
                <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.name || 'User'}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{user?.email}</p>
                  <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                    isAdmin
                      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                      : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  }`}>
                    {user?.role}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
