/**
 * The main feature: pick an image (upload or camera) -> preview -> Predict -> result.
 * Used on both the Dashboard and the Predict page.
 */
import { useEffect, useRef, useState } from 'react'
import { predictImage } from '../services/predictionService'
import type { PredictResponse } from '../types'
import { errorMessage, validateImageFile } from '../utils/format'
import { formatBytes, prepareImage } from '../utils/image'
import CameraCapture from './CameraCapture'
import ImageUploader from './ImageUploader'
import PredictionResult from './PredictionResult'
import Spinner from './Spinner'

type Mode = 'upload' | 'camera'

export default function Predictor({ onPredicted }: { onPredicted?: (r: PredictResponse) => void }) {
  const [mode, setMode] = useState<Mode>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null) // e.g. "photo was resized"
  const [preparing, setPreparing] = useState(false) // true while a big photo is resized

  // A preview needs a temporary "blob:" URL for the file. We free the old one
  // whenever it is replaced, and the last one when the component disappears.
  const urlRef = useRef<string | null>(null)
  const changeFile = (f: File | null) => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    urlRef.current = f ? URL.createObjectURL(f) : null
    setFile(f)
    setPreviewUrl(urlRef.current)
  }
  useEffect(() => () => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
  }, [])

  const selectFile = async (f: File) => {
    setResult(null)
    setNotice(null)
    const problem = validateImageFile(f)
    if (problem) {
      setError(problem)
      changeFile(null)
      return
    }
    setError(null)
    try {
      setPreparing(true)
      const prepared = await prepareImage(f) // shrinks photos larger than 5 MB
      changeFile(prepared.file)
      if (prepared.resized) {
        setNotice(
          `Large photo (${formatBytes(prepared.originalSize)}) was resized to ` +
            `${formatBytes(prepared.file.size)} before uploading.`,
        )
      }
    } catch (err) {
      setError(errorMessage(err))
      changeFile(null)
    } finally {
      setPreparing(false)
    }
  }

  const predict = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const r = await predictImage(file)
      setResult(r)
      onPredicted?.(r)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    changeFile(null)
    setResult(null)
    setError(null)
    setNotice(null)
  }

  return (
    <div className="predictor">
      <div className="card">
        <div className="tabs" role="tablist">
          {(['upload', 'camera'] as Mode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              className={`tab ${mode === m ? 'active' : ''}`}
              onClick={() => setMode(m)}
              disabled={loading}
            >
              {m === 'upload' ? 'Upload image' : 'Live camera'}
            </button>
          ))}
        </div>

        {!file &&
          !preparing &&
          (mode === 'upload' ? (
            <ImageUploader onFile={selectFile} disabled={loading} />
          ) : (
            <CameraCapture onCapture={selectFile} disabled={loading} />
          ))}
        {preparing && <Spinner label="Resizing large photo…" />}

        {previewUrl && (
          <div className="preview">
            <img src={previewUrl} alt="Selected image preview" />
            <p className="muted small">
              {file?.name} · {((file?.size ?? 0) / 1024).toFixed(0)} KB
            </p>
          </div>
        )}

        {notice && <div className="alert alert-info">{notice}</div>}

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        {file && (
          <div className="actions">
            <button className="btn btn-primary" onClick={predict} disabled={loading || !!result}>
              {loading ? 'Predicting…' : 'Predict'}
            </button>
            <button className="btn btn-ghost" onClick={reset} disabled={loading}>
              {result ? 'Try another image' : 'Choose a different image'}
            </button>
          </div>
        )}
        {loading && <Spinner label="Analysing image…" />}
      </div>

      {result && <PredictionResult result={result} />}
    </div>
  )
}
