import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Spinner from '../components/Spinner'
import { useAuth } from '../hooks/useAuth'

/** Visiting /logout revokes the session on the server, then goes to the login page. */
export default function LogoutPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const started = useRef(false) // React dev mode runs effects twice; log out only once

  useEffect(() => {
    if (started.current) return
    started.current = true
    logout().finally(() => navigate('/login', { replace: true }))
  }, [logout, navigate])

  return <Spinner label="Logging out…" />
}
