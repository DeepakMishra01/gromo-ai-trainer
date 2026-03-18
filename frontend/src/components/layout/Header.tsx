import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/products': 'Products Manager',
  '/avatars': 'Avatar Manager',
  '/voices': 'Voice Manager',
  '/video-studio': 'Video Studio',
  '/video-queue': 'Video Queue',
  '/training': 'Training Player',
  '/roleplay': 'Roleplay Practice',
  '/settings': 'Settings',
}

export default function Header() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'GroMo AI Trainer'
  const [language, setLanguage] = useState('Hinglish')
  const { toggleTheme, isDark } = useTheme()

  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then((data) => {
        if (data.default_language) {
          setLanguage(data.default_language.charAt(0).toUpperCase() + data.default_language.slice(1))
        }
      })
      .catch(() => {})
  }, [])

  return (
    <header className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-500 dark:text-gray-400">Language: {language}</span>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className={`relative w-14 h-7 rounded-full transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
            isDark ? 'bg-primary-600' : 'bg-gray-300'
          }`}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          <div
            className={`absolute top-0.5 w-6 h-6 rounded-full bg-white shadow-md transform transition-transform duration-300 flex items-center justify-center ${
              isDark ? 'translate-x-7' : 'translate-x-0.5'
            }`}
          >
            {isDark ? (
              <Moon className="w-3.5 h-3.5 text-primary-600" />
            ) : (
              <Sun className="w-3.5 h-3.5 text-amber-500" />
            )}
          </div>
        </button>

        <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center">
          <span className="text-sm font-medium text-primary-700 dark:text-primary-400">G</span>
        </div>
      </div>
    </header>
  )
}
