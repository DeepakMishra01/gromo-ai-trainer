import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Phone, ArrowRight, Shield } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { auth, RecaptchaVerifier, signInWithPhoneNumber } from '../config/firebase'

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
    recaptchaVerifier?: any
  }
}

export default function Login() {
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [step, setStep] = useState<'phone' | 'otp'>('phone')
  const [confirmationResult, setConfirmationResult] = useState<any>(null)
  const [otpLoading, setOtpLoading] = useState(false)
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const { error, clearError } = useAuthStore()
  const navigate = useNavigate()
  const googleBtnRef = useRef<HTMLDivElement>(null)
  const recaptchaContainerRef = useRef<HTMLDivElement>(null)

  const navigateByRole = (role: string) => {
    navigate(role === 'admin' ? '/' : '/training')
  }

  // Google Sign-In
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

  // Initialize Google Sign-In
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
        width: '100%',
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

  // Countdown timer for resend OTP
  useEffect(() => {
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  // Send OTP
  const sendOtp = async () => {
    const cleanPhone = phone.replace(/\D/g, '')
    if (cleanPhone.length !== 10) {
      useAuthStore.setState({ error: 'Please enter a valid 10-digit phone number' })
      return
    }

    setOtpLoading(true)
    clearError()

    try {
      // Setup invisible reCAPTCHA
      if (!window.recaptchaVerifier && recaptchaContainerRef.current) {
        window.recaptchaVerifier = new RecaptchaVerifier(auth, recaptchaContainerRef.current, {
          size: 'invisible',
        })
      }

      const fullPhone = `+91${cleanPhone}`
      const result = await signInWithPhoneNumber(auth, fullPhone, window.recaptchaVerifier)
      setConfirmationResult(result)
      setStep('otp')
      setCountdown(30)
    } catch (err: any) {
      console.error('OTP send error:', err)
      let msg = 'OTP bhejne mein error aaya. Please try again.'
      if (err.code === 'auth/too-many-requests') {
        msg = 'Too many attempts. Please try after some time.'
      } else if (err.code === 'auth/invalid-phone-number') {
        msg = 'Invalid phone number. Please check and try again.'
      }
      useAuthStore.setState({ error: msg })
      // Reset reCAPTCHA on error
      window.recaptchaVerifier = null
    } finally {
      setOtpLoading(false)
    }
  }

  // Verify OTP
  const verifyOtp = async () => {
    if (otp.length !== 6) {
      useAuthStore.setState({ error: 'Please enter the 6-digit OTP' })
      return
    }

    setVerifyLoading(true)
    clearError()

    try {
      const result = await confirmationResult.confirm(otp)
      const idToken = await result.user.getIdToken()

      // Send Firebase token to our backend
      const res = await fetch('/api/auth/firebase', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Phone login failed')
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
      console.error('OTP verify error:', err)
      let msg = 'OTP verification failed. Please try again.'
      if (err.code === 'auth/invalid-verification-code') {
        msg = 'Wrong OTP. Please check and try again.'
      } else if (err.code === 'auth/code-expired') {
        msg = 'OTP expired. Please request a new one.'
      }
      useAuthStore.setState({ error: msg })
    } finally {
      setVerifyLoading(false)
    }
  }

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
          {/* Google Sign In */}
          <div className="flex justify-center mb-4">
            <div ref={googleBtnRef} />
          </div>
          {googleLoading && (
            <p className="text-center text-sm text-gray-500 dark:text-gray-400 mb-4">Signing in with Google...</p>
          )}

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200 dark:border-gray-700" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white dark:bg-gray-800 px-3 text-gray-400 dark:text-gray-500">or sign in with phone</span>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-400 mb-4">
              {error}
              <button type="button" onClick={clearError} className="float-right font-bold">&times;</button>
            </div>
          )}

          {step === 'phone' ? (
            /* Phone Input */
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Phone Number
                </label>
                <div className="flex">
                  <span className="inline-flex items-center px-3 rounded-l-xl border border-r-0 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-sm">
                    +91
                  </span>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    placeholder="Enter 10-digit number"
                    maxLength={10}
                    className="flex-1 px-4 py-2.5 rounded-r-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                    autoFocus
                  />
                </div>
              </div>
              <button
                onClick={sendOtp}
                disabled={phone.length !== 10 || otpLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 transition-colors text-sm font-medium"
              >
                <Phone className="w-4 h-4" />
                {otpLoading ? 'Sending OTP...' : 'Send OTP'}
              </button>
            </div>
          ) : (
            /* OTP Input */
            <div className="space-y-4">
              <div className="text-center mb-2">
                <Shield className="w-10 h-10 text-primary-500 mx-auto mb-2" />
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  OTP sent to <span className="font-semibold">+91 {phone}</span>
                </p>
                <button
                  onClick={() => { setStep('phone'); setOtp(''); clearError() }}
                  className="text-xs text-primary-600 dark:text-primary-400 hover:underline mt-1"
                >
                  Change number
                </button>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Enter OTP
                </label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="Enter 6-digit OTP"
                  maxLength={6}
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent text-center text-lg tracking-[0.5em] font-mono"
                  autoFocus
                />
              </div>

              <button
                onClick={verifyOtp}
                disabled={otp.length !== 6 || verifyLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:opacity-50 transition-colors text-sm font-medium"
              >
                <ArrowRight className="w-4 h-4" />
                {verifyLoading ? 'Verifying...' : 'Verify & Sign In'}
              </button>

              {/* Resend OTP */}
              <div className="text-center">
                {countdown > 0 ? (
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Resend OTP in {countdown}s
                  </p>
                ) : (
                  <button
                    onClick={() => { setOtp(''); sendOtp() }}
                    className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                  >
                    Resend OTP
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Invisible reCAPTCHA container */}
        <div ref={recaptchaContainerRef} id="recaptcha-container" />
      </div>
    </div>
  )
}
