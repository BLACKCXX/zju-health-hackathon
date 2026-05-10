import axios from 'axios'
import type {
  AskResponse,
  BuildIndexPayload,
  FeedbackResponse,
  GraphBuildResponse,
  NodeDetailResponse,
  ReportExportResponse,
  SystemStatus,
  IntegratedGraphResponse,
  GraphUpdateResponse,
  SingleBookGraphResponse,
} from '../types/api'
import type { GraphJSON } from '../types/graph'

export interface TextbookSummary {
  textbook_id: string
  filename: string
  title: string
  format: string
  total_pages: number
  total_chars: number
  chapter_count: number
  parse_status: string
  error: string
  indexed: boolean
}

export interface RAGStatus {
  indexed: boolean
  textbook_count: number
  chunk_count: number
  embedding_model: string
  backend: string
  fallback_backend: string
  created_at: string
}

export interface RAGQueryResult {
  answer: string
  citations: Array<{
    textbook: string
    chapter: string
    page: number
    relevance_score: number
    quote: string
  }>
  source_chunks: Array<{
    chunk_id: string
    textbook: string
    chapter: string
    page_start: number
    page_end: number
    text: string
    relevance_score: number
  }>
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:18000'

const client = axios.create({ baseURL: apiBaseUrl, timeout: 180000 })

function friendlyError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail || error.response?.data?.message
    return new Error(detail || '后端服务不可用，请确认 FastAPI 已启动')
  }
  return new Error('请求失败，请稍后重试')
}

export async function getStatus(): Promise<SystemStatus> {
  try {
    const response = await client.get<SystemStatus>('/api/status')
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function buildIndex(payload: BuildIndexPayload) {
  try {
    const response = await client.post('/api/index/build', payload)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function askQuestion(question: string, topK = 8): Promise<AskResponse> {
  try {
    const response = await client.post<AskResponse>('/api/ask', { question, top_k: topK })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function buildSingleBookGraph(payload: {
  textbook_id: string
  chapter_id?: string
  top_k?: number
}): Promise<SingleBookGraphResponse> {
  try {
    const response = await client.post<SingleBookGraphResponse>('/api/graph/single', payload)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function buildIntegratedGraph(payload: {
  topic: string
  textbook_ids?: string[]
  top_k_per_book?: number
  global_top_k?: number
}): Promise<IntegratedGraphResponse> {
  try {
    const response = await client.post<IntegratedGraphResponse>('/api/graph/integrated', payload)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function updateGraph(instruction: string, currentGraph: GraphJSON): Promise<GraphUpdateResponse> {
  try {
    const response = await client.post<GraphUpdateResponse>('/api/graph/update', {
      instruction,
      current_graph: currentGraph,
    })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function getNodeDetail(nodeId: string, nodeName: string, graph: GraphJSON): Promise<NodeDetailResponse> {
  try {
    const response = await client.post<NodeDetailResponse>('/api/graph/node-detail', {
      node_id: nodeId,
      node_name: nodeName,
      graph_context: graph,
    })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function sendFeedback(payload: {
  action: 'keep' | 'delete' | 'split' | 'merge' | 'edit'
  target_type: 'node' | 'edge' | 'decision'
  target_id: string
  comment: string
  graph: GraphJSON
}): Promise<FeedbackResponse> {
  try {
    const response = await client.post<FeedbackResponse>('/api/feedback', payload)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function exportReport(graph: GraphJSON): Promise<ReportExportResponse> {
  try {
    const response = await client.post<ReportExportResponse>('/api/report/export', {
      graph,
      format: 'markdown',
    })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

// ============ Textbook Management APIs ============

export async function listTextbooks(): Promise<TextbookSummary[]> {
  try {
    const response = await client.get<TextbookSummary[]>('/api/textbooks')
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function uploadTextbooks(files: File[]): Promise<{ success: boolean; message: string; files: string[] }> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  try {
    const response = await client.post('/api/textbooks/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function parseTextbooks(filenames: string[]): Promise<{ success: boolean; textbooks: TextbookSummary[]; errors: { filename: string; error: string }[] }> {
  try {
    const response = await client.post('/api/textbooks/parse', { filenames })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function getTextbookDetail(textbookId: string) {
  try {
    const response = await client.get(`/api/textbooks/${textbookId}`)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

// ============ RAG APIs ============

export async function buildRAGIndex(payload: {
  source?: 'uploads' | 'textbooks' | 'all'
  force?: boolean
  chunk_size?: number
  chunk_overlap?: number
  backend?: 'faiss' | 'tfidf' | 'hybrid'
}) {
  try {
    const response = await client.post('/api/rag/index', payload)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function getRAGStatus(): Promise<RAGStatus> {
  try {
    const response = await client.get<RAGStatus>('/api/rag/status')
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function queryRAG(question: string, topK = 5): Promise<RAGQueryResult> {
  try {
    const response = await client.post<RAGQueryResult>('/api/rag/query', { question, top_k: topK })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}
