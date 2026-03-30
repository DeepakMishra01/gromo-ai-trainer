import { useState, useEffect, useCallback } from 'react'

type Theme = 'light' | 'dark'

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light'
  const stored = localStorage.getItem('gromo-theme') as Theme | null
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
      document.body.classList.remove('bg-gray-50')
      document.body.classList.add('bg-gray-900')
    } else {
      root.classList.remove('dark')
      document.body.classList.remove('bg-gray-900')
      document.body.classList.add('bg-gray-50')
    }
    localStorage.setItem('gromo-theme', theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setThemeState(prev => prev === 'light' ? 'dark' : 'light')
  }, [])

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t)
  }, [])

  return { theme, toggleTheme, setTheme, isDark: theme === 'dark' }
}
