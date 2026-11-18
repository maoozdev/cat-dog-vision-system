/**
 * <img> for protected images. A normal <img src> can't send our Authorization
 * header, so we download the image with Axios and show it from a local blob URL.
 */
import { useEffect, useState } from 'react'
import { getImageObjectUrl } from '../services/predictionService'

export default function AuthImage({ src, alt, className }: { src: string; alt: string; className?: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    getImageObjectUrl(src)
      .then((u) => {
        objectUrl = u
        if (cancelled) URL.revokeObjectURL(u)
        else setUrl(u)
      })
      .catch(() => !cancelled && setFailed(true))
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl) // free memory
    }
  }, [src])

  if (failed) return <div className={`img-placeholder ${className ?? ''}`}>Image unavailable</div>
  if (!url) return <div className={`img-placeholder shimmer ${className ?? ''}`} aria-label="Loading image" />
  return <img src={url} alt={alt} className={className} loading="lazy" />
}
