/**
 * API 응답 타입 정의
 */

import { DrugResult } from './drug'

export interface SearchRequest {
  query: string
  top_k?: number
  include_ai_response?: boolean
}

export interface SearchData {
  results: DrugResult[]
  ai_response: string | null
  disclaimer: string
}

export interface SearchMeta {
  total_results: number
  response_time_ms: number
  query: string
}

export interface SearchResponse {
  success: boolean
  data: SearchData
  meta: SearchMeta
}

export interface PaginationMeta {
  page: number
  page_size: number
  total_items: number
  total_pages: number
}

export interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  meta: PaginationMeta
}

export interface ChatRequest {
  message: string
  session_id?: string
  top_k?: number
  use_memory?: boolean
}

export interface ChatSource {
  id: string
  name: string
  similarity: number
}

export interface ChatResponse {
  success: boolean
  message: string
  sources: ChatSource[]
  disclaimer: string
  session_id?: string
  from_cache: boolean
  conversation_turn: number
}

export interface ConversationHistoryItem {
  query: string
  response: string
  timestamp: string
}

export interface ConversationHistoryResponse {
  success: boolean
  session_id: string
  history: ConversationHistoryItem[]
  total_turns: number
}

export interface MemoryStatusResponse {
  success: boolean
  memory_enabled: boolean
  stats: {
    enabled: boolean
    cache_ttl: number
    history_ttl: number
    max_history: number
  }
}

export interface APIError {
  detail: string
}
