import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { errorMessage } from '../utils/format'

/** Same rules as the backend, checked early for a nicer experience. */
function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return 'Password must be at least 8 characters.'
  if (!/[a-zA-Z]/.test(pw) || !/\d/.test(pw)) return 'Password must contain a letter and a number.'
  return null
}

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const problem = passwordProblem(password) ?? (password !== confirm ? 'Passwords do not match.' : null)
    if (problem) {
      setError(problem)
      return
    }
    setBusy(true)
    setError(null)
    try {
      await register(email.trim(), password)
      navigate('/dashboard', { replace: true })
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
        <h1>Create your account</h1>
        <p className="muted">It takes less than a minute.</p>

        {error && <div className="alert alert-error" role="alert">{error}</div>}

        <label>
          Email
          <input type="email" autoComplete="email" required value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" autoComplete="new-password" required value={password}
                 aria-describedby="password-hint"
                 onChange={(e) => setPassword(e.target.value)} />
        </label>
        <span id="password-hint" className="hint">At least 8 characters, with a letter and a number.</span>
        <label>
          Confirm password
          <input type="password" autoComplete="new-password" required value={confirm}
                 onChange={(e) => setConfirm(e.target.value)} />
        </label>

        <button className="btn btn-primary btn-block" disabled={busy || !email || !password || !confirm}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted small center">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
