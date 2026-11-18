/**
 * Shrink big photos in the browser BEFORE uploading.
 *
 * Phone photos are often 6-15 MB (4000x3000 pixels), but the model only looks at
 * a 224x224 version. So we resize the longest side to MAX_SIDE pixels and save as
 * JPEG: a 12 MB photo becomes a few hundred KB, uploads faster, and fits the 5 MB limit.
 */
import { MAX_BYTES } from './format'

const MAX_SIDE = 1600 // pixels; still plenty for the preview and the history page
const JPEG_QUALITY = 0.9

export interface PreparedImage {
  file: File
  resized: boolean
  originalSize: number
}

export async function prepareImage(file: File): Promise<PreparedImage> {
  // Small enough already -> upload the original untouched.
  if (file.size <= MAX_BYTES) return { file, resized: false, originalSize: file.size }

  // Decode the image. imageOrientation: 'from-image' applies the phone's rotation info.
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    throw new Error('This image could not be read. It may be corrupted.')
  }

  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
  const width = Math.round(bitmap.width * scale)
  const height = Math.round(bitmap.height * scale)

  // Draw the smaller version on a canvas and export it as JPEG.
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Your browser could not resize this image.')
  ctx.fillStyle = '#fff' // PNGs with transparency get a white background, not black
  ctx.fillRect(0, 0, width, height)
  ctx.drawImage(bitmap, 0, 0, width, height)
  bitmap.close() // free the memory of the big decoded image

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY),
  )
  if (!blob) throw new Error('Your browser could not resize this image.')
  if (blob.size > MAX_BYTES) throw new Error('This image is too large even after resizing.')

  const name = file.name.replace(/\.[^.]+$/, '') + '.jpg'
  return { file: new File([blob], name, { type: 'image/jpeg' }), resized: true, originalSize: file.size }
}

export function formatBytes(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`
}
