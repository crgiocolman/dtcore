import { create } from 'zustand'

export interface AuthUser {
  id: string
  username: string
  full_name: string
  email: string | null
  role: 'admin' | 'operator'
  is_active: boolean
}

interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  initFromStorage: () => void
}

const TOKEN_KEY = 'dtcore_token'
const USER_KEY = 'dtcore_user'

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,

  initFromStorage: () => {
    const token = localStorage.getItem(TOKEN_KEY)
    const userRaw = localStorage.getItem(USER_KEY)
    if (token && userRaw) {
      try {
        const user: AuthUser = JSON.parse(userRaw)
        set({ token, user, isAuthenticated: true })
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
      }
    }
  },

  login: async (username: string, password: string) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error((data as { detail?: string }).detail ?? 'Error al iniciar sesión')
    }

    const data: TokenResponse = await res.json()
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    set({ token: data.access_token, user: data.user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    set({ token: null, user: null, isAuthenticated: false })
  },
}))
