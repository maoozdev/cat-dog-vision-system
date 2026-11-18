import type { Prediction } from '../types'
import { formatDate, LABEL_INFO, percent } from '../utils/format'
import AuthImage from './AuthImage'

/** One history entry: thumbnail, label, confidence, date. */
export default function PredictionCard({ p }: { p: Prediction }) {
  const info = LABEL_INFO[p.predicted_label]
  return (
    <article className="history-card">
      <AuthImage src={p.image_url} alt={`Image classified as ${info.name}`} className="thumb" />
      <div className="history-body">
        <span className={`badge ${info.className}`}>{info.name}</span>
        <p className="history-conf">{percent(p.confidence)} confidence</p>
        <p className="muted small">{formatDate(p.created_at)}</p>
      </div>
    </article>
  )
}
