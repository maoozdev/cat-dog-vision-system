/** Live camera: start / stop / switch front-back / capture a photo. */
import { useCamera } from '../hooks/useCamera'

interface Props {
  onCapture: (file: File) => void
  disabled?: boolean
}

export default function CameraCapture({ onCapture, disabled }: Props) {
  const { videoRef, active, starting, facingMode, canSwitch, error, start, stop, switchCamera, capture } =
    useCamera()

  const takePhoto = async () => {
    const file = await capture()
    if (file) {
      onCapture(file)
      stop() // photo taken -> release the camera
    }
  }

  return (
    <div className="camera">
      {/* The <video> is always rendered so videoRef exists before the camera starts. */}
      <div className={`camera-view ${active ? '' : 'idle'}`}>
        <video
          ref={videoRef}
          playsInline // iPhone: play inline instead of fullscreen
          muted
          className={facingMode === 'user' ? 'mirrored' : ''}
          hidden={!active}
        />
        {!active && <p className="muted">{starting ? 'Starting camera…' : 'Camera is off'}</p>}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="camera-controls">
        {!active ? (
          <button type="button" className="btn btn-primary" onClick={() => start()} disabled={disabled || starting}>
            Start camera
          </button>
        ) : (
          <>
            <button type="button" className="btn btn-primary" onClick={takePhoto} disabled={disabled}>
              Capture photo
            </button>
            {canSwitch && (
              <button type="button" className="btn btn-secondary" onClick={switchCamera}>
                Switch to {facingMode === 'user' ? 'back' : 'front'} camera
              </button>
            )}
            <button type="button" className="btn btn-ghost" onClick={stop}>
              Stop camera
            </button>
          </>
        )}
      </div>
    </div>
  )
}
