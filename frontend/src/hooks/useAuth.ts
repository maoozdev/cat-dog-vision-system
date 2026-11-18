import { useContext } from 'react'
import { AuthContext, type AuthContextValue } from '../context/authContextValue'

/** Use in any component: const { user, login, logout } = useAuth() */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
