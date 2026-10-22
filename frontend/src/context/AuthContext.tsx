import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authService, type User } from '../services/api'

type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (payload: { name: string; email: string; password: string; role: string }) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!localStorage.getItem('skillbridge-token')) {
      setLoading(false)
      return
    }
    authService.me().then(setUser).catch(() => {
      localStorage.removeItem('skillbridge-token')
      setUser(null)
    }).finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    async login(email, password) {
      const result = await authService.login(email, password)
      localStorage.setItem('skillbridge-token', result.token)
      setUser(result.user)
      return result.user
    },
    async register(payload) {
      const result = await authService.register(payload)
      localStorage.setItem('skillbridge-token', result.token)
      setUser(result.user)
      return result.user
    },
    logout() {
      localStorage.removeItem('skillbridge-token')
      setUser(null)
    },
  }), [user, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
