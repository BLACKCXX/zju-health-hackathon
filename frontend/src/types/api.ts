import type { GraphJSON } from './graph'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SystemStatus {
  api_configured: boolean
  textbook_dir_exists: boolean
  pdf_count: number
  index_exists: boolean
  chunk_count: number
  retrieval_backend: string
  models: Record<string, string>
  answer_model?: string
  embedding_model?: string
  has_embedding?: boolean
  has_tfidf?: boolean
}

export interface Citation {
  book: string
  chapter: string
  page: number
  quote: string
}

export interface Flashcard {
  title: string
  definition: string
  key_points: string[]
  related_terms: string[]
  source_refs: Array<{ book: string; page: number }>
}

export interface AskResponse {
  answer: string
  keywords: string[]
  citations: Citation[]
  flashcards: Flashcard[]
  agent_trace: Record<string, unknown>
}

export interface GraphBuildResponse {
  topic: string
  graph: GraphJSON
  evidence: GraphJSON['evidence']
  integration_summary: string
  agent_trace: Record<string, unknown>
}

export interface SingleBookGraphResponse {
  graph: GraphJSON
  evidence: GraphJSON['evidence']
  agent_trace: Record<string, unknown>
}

export interface IntegratedGraphResponse {
  graph: GraphJSON
  integration_summary: string
  decisions: Array<Record<string, unknown>>
  evidence: GraphJSON['evidence']
}

export interface GraphUpdateResponse {
  graph: GraphJSON
  patch: {
    added_nodes: GraphJSON['nodes']
    added_edges: GraphJSON['edges']
    updated_nodes: GraphJSON['nodes']
    highlight_nodes: string[]
  }
  feedback_record: Record<string, unknown>
}

export interface NodeDetailResponse {
  node_id: string
  name: string
  definition: string
  detail: string
  overlap_analysis: string
  complement_analysis: string
  sources: Citation[]
}

export interface FeedbackResponse {
  success: boolean
  updated_graph: GraphJSON
  feedback_record: Record<string, unknown>
}

export interface ReportExportResponse {
  markdown: string
  filename: string
}

export interface BuildIndexPayload {
  force: boolean
  debug: boolean
  max_pages_per_pdf: number
  backend?: 'tfidf' | 'hybrid' | 'embedding'
  chunk_size?: number
  overlap?: number
}
