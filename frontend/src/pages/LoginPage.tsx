import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { errorMessage } from '../utils/format'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault() // stop the browser's default full-page form submit
    setBusy(true)
    setError(null)
    try {
      await login(email.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <img src="/favicon.svg" alt="" width={48} height={48} className="auth-logo" />
        <h1>Welcome back</h1>
        <p className="muted">Log in to classify cats, dogs and everything else.</p>

        {error && <div className="alert alert-error" role="alert">{error}</div>}

        <label>
          Email
          <input type="email" autoComplete="email" required value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" autoComplete="current-password" required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </label>

        <button className="btn btn-primary btn-block" disabled={busy || !email || !password}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
        <p className="muted small center">
          No account yet? <Link to="/register">Create one</Link>
        </p>
      </form>
    </div>
  )
}
