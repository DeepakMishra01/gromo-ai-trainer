import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void
          renderButton: (element: HTMLElement, config: any) => void
        }
      }
    }
  }
}

export default function Login() {
  const [googleLoading, setGoogleLoading] = useState(false)
  const { error, clearError } = useAuthStore()
  const navigate = useNavigate()
  const googleBtnRef = useRef<HTMLDivElement>(null)

  const navigateByRole = (role: string) => {
    navigate(role === 'admin' ? '/' : '/training')
  }

  const handleGoogleCallback = async (response: any) => {
    setGoogleLoading(true)
    clearError()
    try {
      const res = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Google login failed')
      }
      const data = await res.json()
      localStorage.setItem('gromo-token', data.access_token)
      localStorage.setItem('gromo-user', JSON.stringify(data.user))
      useAuthStore.setState({
        user: data.user,
        token: data.access_token,
        isAuthenticated: true,
        isAdmin: data.user.role === 'admin',
      })
      navigateByRole(data.user.role)
    } catch (err: any) {
      useAuthStore.setState({ error: err.message || 'Google login failed' })
    } finally {
      setGoogleLoading(false)
    }
  }

  useEffect(() => {
    const initGoogle = (clientId: string) => {
      if (!window.google || !googleBtnRef.current) return
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCallback,
      })
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'outline',
        size: 'large',
        width: 320,
        text: 'signin_with',
        shape: 'pill',
      })
    }

    fetch('/api/auth/google-client-id')
      .then(r => r.json())
      .then(data => {
        if (!data.client_id) return
        if (window.google) {
          initGoogle(data.client_id)
          return
        }
        let attempts = 0
        const interval = setInterval(() => {
          attempts++
          if (window.google) {
            clearInterval(interval)
            initGoogle(data.client_id)
          } else if (attempts > 50) {
            clearInterval(interval)
          }
        }, 200)
      })
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 dark:from-gray-900 dark:to-gray-800 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl font-bold text-white">G</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">GroMo AI Trainer</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Sign in to start training</p>
        </div>

        {/* Login Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
          {/* Error */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-400 mb-4">
              {error}
              <button type="button" onClick={clearError} className="float-right font-bold">&times;</button>
            </div>
          )}

          {/* Google Sign In */}
          <div className="flex flex-col items-center gap-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">Sign in with your Google account</p>
            <div ref={googleBtnRef} />
            {googleLoading && (
              <p className="text-sm text-gray-500 dark:text-gray-400">Signing in with Google...</p>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-6">
          By signing in, you agree to the terms of use.
        </p>
      </div>
    </div>
  )
}
