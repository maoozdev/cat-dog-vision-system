import { isAxiosError } from 'axios'
import type { Label } from '../types'

export const LABEL_INFO: Record<Label, { name: string; className: string }> = {
  cat: { name: 'Cat', className: 'label-cat' },
  dog: { name: 'Dog', className: 'label-dog' },
  other: { name: 'Neither / Unknown', className: 'label-other' },
}

export const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const MAX_BYTES = 5 * 1024 * 1024

export function percent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

/** Check the file TYPE in the browser before uploading (the server checks again).
 *  Size is not checked here: big images are shrunk automatically (utils/image.ts). */
export function validateImageFile(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) return 'Please choose a JPEG, PNG or WEBP image.'
  return null
}

/** Turn any error (network, 4xx, 5xx, validation) into one friendly sentence. */
export function errorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    if (!err.response) return 'Cannot reach the server. Is the backend running?'
    const detail = (err.response.data as { detail?: unknown })?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      // FastAPI validation errors: [{loc: [...], msg: "..."}]
      return detail
        .map((d: { msg?: string }) => (d.msg ?? '').replace(/^Value error, /, ''))
        .join(' ')
    }
    return `Request failed (${err.response.status}).`
  }
  return err instanceof Error ? err.message : 'Something went wrong.'
}
