import type { TokenResponse, User } from '../types'
import { api, setAccessToken } from './api'

export async function register(email: string, password: string): Promise<User> {
  const res = await api.post<User>('/auth/register', { email, password })
  return res.data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/login', { email, password })
  setAccessToken(res.data.access_token)
  return res.data
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } finally {
    setAccessToken(null) // forget the token even if the server is unreachable
  }
}

export async function getMe(): Promise<User> {
  const res = await api.get<User>('/auth/me')
  return res.data
}
