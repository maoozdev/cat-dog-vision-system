import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PredictionCard from '../components/PredictionCard'
import Spinner from '../components/Spinner'
import { getPredictions } from '../services/predictionService'
import type { PredictionPage } from '../types'
import { errorMessage } from '../utils/format'

const PAGE_SIZE = 12

export default function HistoryPage() {
  // Page number lives in the URL (?page=2) so reload/back button keep it.
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)

  const [data, setData] = useState<PredictionPage | null>(null)
  const [error, setError] = useState<{ page: number; message: string } | null>(null)
  // "Loading" is derived: we are loading if we have neither data nor an error for THIS page.
  const loading = data?.page !== page && error?.page !== page

  useEffect(() => {
    let cancelled = false // ignore late answers if the user already switched page
    getPredictions(page, PAGE_SIZE)
      .then((d) => {
        if (cancelled) return
        setData(d)
        setError(null)
      })
      .catch((err) => {
        if (!cancelled) setError({ page, message: errorMessage(err) })
      })
    return () => {
      cancelled = true
    }
  }, [page])

  const goTo = (p: number) => {
    setParams({ page: String(p) })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <>
      <section className="page-header">
        <div>
          <h1>Prediction history</h1>
          <p className="muted">
            {data ? `${data.total} prediction${data.total === 1 ? '' : 's'} in total` : ' '}
          </p>
        </div>
      </section>

      {error && <div className="alert alert-error">{error.message}</div>}
      {loading && !data && <Spinner />}

      {data && data.total === 0 && (
        <div className="card empty">
          <p>No predictions yet.</p>
          <Link to="/predict" className="btn btn-primary">Make your first prediction</Link>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className={`history-grid ${loading ? 'faded' : ''}`}>
            {data.items.map((p) => <PredictionCard key={p.id} p={p} />)}
          </div>
          <nav className="pagination" aria-label="History pages">
            <button className="btn btn-secondary" disabled={page <= 1 || loading} onClick={() => goTo(page - 1)}>
              ← Previous
            </button>
            <span className="muted">Page {data.page} of {Math.max(data.pages, 1)}</span>
            <button className="btn btn-secondary" disabled={page >= data.pages || loading} onClick={() => goTo(page + 1)}>
              Next →
            </button>
          </nav>
        </>
      )}
    </>
  )
}
