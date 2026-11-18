import type { PredictionPage, PredictResponse } from '../types'
import { api } from './api'

export async function predictImage(file: File): Promise<PredictResponse> {
  const form = new FormData()
  form.append('file', file) // field name must match the FastAPI parameter "file"
  const res = await api.post<PredictResponse>('/predict', form)
  return res.data
}

export async function getPredictions(page = 1, pageSize = 10): Promise<PredictionPage> {
  const res = await api.get<PredictionPage>('/predictions', {
    params: { page, page_size: pageSize },
  })
  return res.data
}

/** Stored images are protected, so we fetch them WITH the token and make a local URL. */
export async function getImageObjectUrl(imageUrl: string): Promise<string> {
  const res = await api.get<Blob>(imageUrl, { responseType: 'blob' })
  return URL.createObjectURL(res.data)
}
