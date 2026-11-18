/**
 * Choose an image by: drag & drop, clicking (file picker), or - on phones -
 * the native camera app (<input capture="environment">).
 */
import { useRef, useState, type DragEvent } from 'react'

interface Props {
  onFile: (file: File) => void
  disabled?: boolean
}

const isTouchDevice = typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches

export default function ImageUploader({ onFile, disabled }: Props) {
  const fileInput = useRef<HTMLInputElement>(null)
  const cameraInput = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0]
    if (file) onFile(file)
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault() // stop the browser from opening the image itself
    setDragging(false)
    if (!disabled) handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="uploader">
      <div
        className={`dropzone ${dragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
        role="button"
        tabIndex={0}
        aria-label="Upload an image: drag and drop or press Enter to browse"
        onClick={() => !disabled && fileInput.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
            e.preventDefault()
            fileInput.current?.click()
          }
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 16V4m0 0-4 4m4-4 4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <p className="dropzone-title">
          {dragging ? 'Drop the image here' : 'Drag & drop an image, or click to browse'}
        </p>
        <p className="muted small">JPEG, PNG or WEBP · max 5 MB</p>
      </div>

      <input
        ref={fileInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(e) => {
          handleFiles(e.target.files)
          e.target.value = '' // allow picking the same file again
        }}
      />

      {isTouchDevice && (
        <>
          <button
            type="button"
            className="btn btn-secondary btn-block"
            disabled={disabled}
            onClick={() => cameraInput.current?.click()}
          >
            Take a photo with your phone camera
          </button>
          <input
            ref={cameraInput}
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={(e) => {
              handleFiles(e.target.files)
              e.target.value = ''
            }}
          />
        </>
      )}
    </div>
  )
}
