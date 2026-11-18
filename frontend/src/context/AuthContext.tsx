/**
 * AuthContext = the "who is logged in?" state, shared by every component.
 *
 * On page load we try a silent refresh: if the browser still has a valid
 * refresh cookie, the user stays logged in after a reload without typing anything.
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { refreshSession, setSessionExpiredHandler } from '../services/api'
import * as authService from '../services/authService'
import type { User } from '../types'
import { AuthContext } from './authContextValue'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))
    refreshSession()
      .then((data) => setUser(data.user))
      .catch(() => setUser(null)) // no valid cookie -> just not logged in
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const data = await authService.login(email, password)
    setUser(data.user)
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    await authService.register(email, password)
    const data = await authService.login(email, password) // log in right away
    setUser(data.user)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } finally {
      setUser(null)
    }
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
