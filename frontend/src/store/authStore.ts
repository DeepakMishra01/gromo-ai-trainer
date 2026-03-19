import { create } from 'zustand'

export interface User {
  id: string
  email: string
  name: string | null
  role: 'admin' | 'user'
  created_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isAdmin: boolean
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name?: string) => Promise<void>
  logout: () => void
  loadFromStorage: () => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isAdmin: false,
  loading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Login failed')
      }
      const data = await res.json()
      localStorage.setItem('gromo-token', data.access_token)
      localStorage.setItem('gromo-user', JSON.stringify(data.user))
      set({
        user: data.user,
        token: data.access_token,
        isAuthenticated: true,
        isAdmin: data.user.role === 'admin',
        loading: false,
      })
    } catch (err: any) {
      set({ loading: false, error: err.message || 'Login failed' })
      throw err
    }
  },

  register: async (email: string, password: string, name?: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name: name || '' }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Registration failed')
      }
      const data = await res.json()
      localStorage.setItem('gromo-token', data.access_token)
      localStorage.setItem('gromo-user', JSON.stringify(data.user))
      set({
        user: data.user,
        token: data.access_token,
        isAuthenticated: true,
        isAdmin: data.user.role === 'admin',
        loading: false,
      })
    } catch (err: any) {
      set({ loading: false, error: err.message || 'Registration failed' })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('gromo-token')
    localStorage.removeItem('gromo-user')
    set({ user: null, token: null, isAuthenticated: false, isAdmin: false })
  },

  loadFromStorage: () => {
    const token = localStorage.getItem('gromo-token')
    const userStr = localStorage.getItem('gromo-user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr) as User
        set({ user, token, isAuthenticated: true, isAdmin: user.role === 'admin' })
      } catch {
        localStorage.removeItem('gromo-token')
        localStorage.removeItem('gromo-user')
      }
    }
  },

  clearError: () => set({ error: null }),
}))
