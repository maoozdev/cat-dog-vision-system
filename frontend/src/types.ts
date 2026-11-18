// Shapes of the JSON the backend sends. They mirror backend/app/schemas/*.py

export interface User {
  id: string
  email: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export type Label = 'cat' | 'dog' | 'other'

export interface Prediction {
  id: string
  predicted_label: Label
  confidence: number
  probabilities: Record<Label, number>
  model_version: string
  created_at: string
  image_url: string
}

export interface PredictResponse extends Prediction {
  low_confidence: boolean
  threshold: number
}

export interface PredictionPage {
  items: Prediction[]
  total: number
  page: number
  page_size: number
  pages: number
}
