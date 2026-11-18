import type { Label, PredictResponse } from '../types'
import { LABEL_INFO, percent } from '../utils/format'

const ORDER: Label[] = ['cat', 'dog', 'other']

export default function PredictionResult({ result }: { result: PredictResponse }) {
  const info = LABEL_INFO[result.predicted_label]

  return (
    <section className="result card" aria-live="polite">
      <p className="muted small">Prediction</p>
      <h2 className={`result-label ${info.className}`}>{info.name}</h2>
      <p className="result-confidence">
        Confidence <strong>{percent(result.confidence)}</strong>
      </p>

      {result.low_confidence && (
        <div className="alert alert-warning">
          The model was not confident enough (below {percent(result.threshold, 0)}), so the
          answer is <strong>Neither / Unknown</strong>.
        </div>
      )}

      <h3 className="small-heading">Class probabilities</h3>
      <ul className="prob-list">
        {ORDER.map((label) => {
          const value = result.probabilities[label] ?? 0
          return (
            <li key={label}>
              <div className="prob-row">
                <span>{LABEL_INFO[label].name}</span>
                <span>{percent(value)}</span>
              </div>
              <div
                className="prob-bar"
                role="progressbar"
                aria-label={LABEL_INFO[label].name}
                aria-valuenow={Math.round(value * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div className={`prob-fill ${LABEL_INFO[label].className}`} style={{ width: percent(value) }} />
              </div>
            </li>
          )
        })}
      </ul>
      <p className="muted small">Model v{result.model_version}</p>
    </section>
  )
}
