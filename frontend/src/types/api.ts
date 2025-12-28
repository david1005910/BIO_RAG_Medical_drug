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
  top_k?: number
}

export interface ChatResponse {
  success: boolean
  message: string
  sources: Array<{
    id: string
    name: string
    similarity: number
  }>
  disclaimer: string
}

export interface APIError {
  detail: string
}
