export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface RouteInfo {
  intent: string
  need_pdf_search: boolean
  user_emotion_reply?: string
  search_keywords?: string[]
  expanded_query?: string
  answer_focus?: string
}

export interface RetrievedChunk {
  source_file: string
  page: number
  chunk_id?: string
  score?: number
  match_type?: string
  text: string
}

export interface ChatResponse {
  answer: string
  route_info: RouteInfo
  retrieved_chunks: RetrievedChunk[]
  usage_note?: string
}

export interface SystemStatus {
  api_configured: boolean
  answer_model?: string
  embedding_model?: string
  textbook_dir_exists: boolean
  pdf_count: number
  index_exists: boolean
  chunk_count?: number
  has_embedding?: boolean
  has_tfidf?: boolean
  created_at?: string
}

export interface BuildIndexPayload {
  backend: 'tfidf' | 'hybrid' | 'embedding'
  force: boolean
  debug: boolean
  max_pages_per_pdf: number
  chunk_size: number
  overlap: number
}

export interface BuildIndexResponse {
  success: boolean
  message: string
  pdf_count: number
  chunk_count: number
  has_embedding: boolean
  has_tfidf: boolean
  elapsed_sec: number
  warning?: string
}
