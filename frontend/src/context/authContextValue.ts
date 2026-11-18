import { createContext } from 'react'
import type { User } from '../types'

export interface AuthContextValue {
  user: User | null
  loading: boolean // true while we check the session on startup
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

/** The context object itself (kept separate so AuthContext.tsx only exports a component). */
export const AuthContext = createContext<AuthContextValue | null>(null)
