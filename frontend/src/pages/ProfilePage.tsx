import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMe } from '../services/authService'
import { getPredictions } from '../services/predictionService'
import type { User } from '../types'
import { errorMessage, formatDate } from '../utils/format'
import Spinner from '../components/Spinner'

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null)
  const [total, setTotal] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Fresh data from the server (GET /auth/me), not just the cached login response.
    Promise.all([getMe(), getPredictions(1, 1)])
      .then(([me, page]) => {
        setUser(me)
        setTotal(page.total)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  return (
    <>
      <section className="page-header">
        <div>
          <h1>Your profile</h1>
        </div>
      </section>
      <div className="card narrow">
        {error && <div className="alert alert-error">{error}</div>}
        {!user && !error && <Spinner />}
        {user && (
          <dl className="profile-list">
            <dt>Email</dt>
            <dd>{user.email}</dd>
            <dt>Member since</dt>
            <dd>{formatDate(user.created_at)}</dd>
            <dt>Total predictions</dt>
            <dd>{total ?? '–'}</dd>
            <dt>User ID</dt>
            <dd className="mono small">{user.id}</dd>
          </dl>
        )}
        <div className="actions">
          <Link to="/history" className="btn btn-secondary">View history</Link>
          <Link to="/logout" className="btn btn-danger">Log out</Link>
        </div>
      </div>
    </>
  )
}
