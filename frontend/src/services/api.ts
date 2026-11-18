/**
 * One configured Axios instance for the whole app.
 *
 * - The ACCESS token is kept only in memory (a variable), never in localStorage,
 *   so injected scripts can't steal it from storage.
 * - The REFRESH token is an HttpOnly cookie that JavaScript cannot read at all;
 *   the browser sends it automatically to /api/auth/refresh.
 * - If a request fails with 401 (access token expired), we refresh once and retry.
 */
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { TokenResponse } from '../types'

export const API_BASE = '/api'

let accessToken: string | null = null
let onSessionExpired: (() => void) | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

/** AuthContext registers a callback so it can log the user out in the UI. */
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler
}

export const api = axios.create({ baseURL: API_BASE, withCredentials: true })

// Attach "Authorization: Bearer <token>" to every request.
api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

// ---------------------------------------------------------------- refreshing
let refreshPromise: Promise<TokenResponse> | null = null

async function doRefresh(): Promise<TokenResponse> {
  const res = await axios.post<TokenResponse>(`${API_BASE}/auth/refresh`, null, {
    withCredentials: true,
  })
  setAccessToken(res.data.access_token)
  return res.data
}

/**
 * Get a new access token using the refresh cookie.
 * - Calls made at the same time share ONE request (refreshPromise).
 * - Web Locks make other browser tabs wait their turn, because each refresh
 *   rotates the cookie and reusing an old one would log the user out everywhere.
 */
export function refreshSession(): Promise<TokenResponse> {
  if (!refreshPromise) {
    const run = navigator.locks
      ? navigator.locks.request('catdog-refresh', doRefresh)
      : doRefresh()
    refreshPromise = run.finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

// Auth endpoints that must NOT trigger the "refresh and retry" logic.
const NO_RETRY = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout']

type RetryConfig = InternalAxiosRequestConfig & { _retried?: boolean }

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined
    const skip = !config || config._retried || NO_RETRY.some((p) => config.url?.startsWith(p))
    if (error.response?.status === 401 && !skip) {
      config._retried = true
      try {
        await refreshSession()
        return api(config) // retry the original request with the new token
      } catch {
        setAccessToken(null)
        onSessionExpired?.()
      }
    }
    return Promise.reject(error)
  },
)
