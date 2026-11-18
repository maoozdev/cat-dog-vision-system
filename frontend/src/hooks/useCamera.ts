/**
 * Live camera with getUserMedia.
 *
 * getUserMedia asks the browser for a video stream. Browsers only allow it on
 * secure pages: https://... or http://localhost. On a phone over plain http it fails.
 *
 * facingMode "user" = front (selfie) camera, "environment" = back camera.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

export type FacingMode = 'user' | 'environment'

function cameraErrorMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : ''
  switch (name) {
    case 'NotAllowedError':
      return 'Camera permission was denied. Allow camera access in your browser settings and try again.'
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'No camera was found on this device.'
    case 'NotReadableError':
      return 'The camera is being used by another app. Close it and try again.'
    default:
      return 'Could not start the camera.'
  }
}

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [active, setActive] = useState(false)
  const [starting, setStarting] = useState(false)
  const [facingMode, setFacingMode] = useState<FacingMode>('environment')
  const [canSwitch, setCanSwitch] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop()) // turns the camera light off
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setActive(false)
  }, [])

  const start = useCallback(
    async (mode: FacingMode = 'environment') => {
      setError(null)
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        setError('Camera needs a secure page (https:// or localhost) and a supported browser.')
        return
      }
      stop()
      setStarting(true)
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: mode }, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        })
        streamRef.current = stream
        const video = videoRef.current
        if (video) {
          video.srcObject = stream
          await video.play().catch(() => undefined) // autoplay quirks: muted+playsInline handles it
        }
        setFacingMode(mode)
        setActive(true)
        // Device labels/count are only reliable after permission is granted.
        const devices = await navigator.mediaDevices.enumerateDevices()
        setCanSwitch(devices.filter((d) => d.kind === 'videoinput').length > 1)
      } catch (err) {
        setError(cameraErrorMessage(err))
      } finally {
        setStarting(false)
      }
    },
    [stop],
  )

  const switchCamera = useCallback(
    () => start(facingMode === 'user' ? 'environment' : 'user'),
    [facingMode, start],
  )

  /** Draw the current video frame onto a canvas and turn it into a JPEG File. */
  const capture = useCallback(async (): Promise<File | null> => {
    const video = videoRef.current
    if (!video || !streamRef.current || video.videoWidth === 0) return null
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')?.drawImage(video, 0, 0)
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', 0.92),
    )
    return blob ? new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' }) : null
  }, [])

  // Always release the camera when the component using this hook disappears.
  useEffect(() => stop, [stop])

  return { videoRef, active, starting, facingMode, canSwitch, error, start, stop, switchCamera, capture }
}
