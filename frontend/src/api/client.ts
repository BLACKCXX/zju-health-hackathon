import axios from 'axios'
import type { BuildIndexPayload, BuildIndexResponse, ChatMessage, ChatResponse, SystemStatus } from '../types/api'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const client = axios.create({
  baseURL: apiBaseUrl,
  timeout: 180000,
})

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

export async function sendChatMessage(payload: {
  message: string
  history: ChatMessage[]
  top_k: number
  force_pdf_search: boolean
}): Promise<ChatResponse> {
  try {
    const response = await client.post<ChatResponse>('/api/chat', payload)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function buildIndex(payload: BuildIndexPayload): Promise<BuildIndexResponse> {
  try {
    const response = await client.post<BuildIndexResponse>('/api/build-index', payload)
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function getIndexStatus() {
  try {
    const response = await client.get('/api/index-status')
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}

export async function uploadPdf(files: File[]) {
  try {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    const response = await client.post('/api/upload-pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  } catch (error) {
    throw friendlyError(error)
  }
}
