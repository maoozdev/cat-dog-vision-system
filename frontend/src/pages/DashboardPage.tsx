import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PredictionCard from '../components/PredictionCard'
import Predictor from '../components/Predictor'
import Spinner from '../components/Spinner'
import { useAuth } from '../hooks/useAuth'
import { getPredictions } from '../services/predictionService'
import type { PredictionPage } from '../types'
import { errorMessage } from '../utils/format'

export default function DashboardPage() {
  const { user } = useAuth()
  const [recent, setRecent] = useState<PredictionPage | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadRecent = useCallback(() => {
    getPredictions(1, 4)
      .then((data) => {
        setRecent(data)
        setError(null)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(loadRecent, [loadRecent])

  return (
    <>
      <section className="page-header">
        <div>
          <h1>Hello, {user?.email.split('@')[0]}</h1>
          <p className="muted">Upload a photo or use your camera. The AI tells you: cat, dog, or neither.</p>
        </div>
        <div className="stat">
          <span className="stat-value">{recent?.total ?? '–'}</span>
          <span className="muted small">predictions so far</span>
        </div>
      </section>

      <div className="dashboard-grid">
        <Predictor onPredicted={loadRecent} />

        <aside className="card">
          <div className="card-title-row">
            <h2>Recent predictions</h2>
            <Link to="/history" className="small">View all</Link>
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          {!recent && !error && <Spinner />}
          {recent && recent.items.length === 0 && (
            <p className="muted">No predictions yet. Try your first image!</p>
          )}
          <div className="recent-list">
            {recent?.items.map((p) => <PredictionCard key={p.id} p={p} />)}
          </div>
        </aside>
      </div>
    </>
  )
}
