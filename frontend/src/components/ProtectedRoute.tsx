/**
 * Route guards.
 * ProtectedRoute - only for logged-in users; others are sent to /login.
 * GuestRoute     - only for logged-OUT users (login/register pages).
 */
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import Spinner from './Spinner'

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export function GuestRoute() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner label="Checking your session…" />
  if (user) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
