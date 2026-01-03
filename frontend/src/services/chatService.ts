/**
 * Chat 서비스 - 메모리 기능 포함 대화 API
 */

import api from './api'
import {
  ChatRequest,
  ChatResponse,
  ConversationHistoryResponse,
  MemoryStatusResponse,
} from '../types/api'

export const chatService = {
  /**
   * 대화형 RAG 검색 (메모리 기능 포함)
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/api/v1/chat', request)
    return response.data
  },

  /**
   * 대화 히스토리 조회
   */
  async getHistory(sessionId: string, limit?: number): Promise<ConversationHistoryResponse> {
    const params = limit ? { limit } : {}
    const response = await api.get<ConversationHistoryResponse>(
      `/api/v1/chat/history/${sessionId}`,
      { params }
    )
    return response.data
  },

  /**
   * 대화 히스토리 삭제
   */
  async clearHistory(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(`/api/v1/chat/history/${sessionId}`)
    return response.data
  },

  /**
   * 메모리 서비스 상태 확인
   */
  async getMemoryStatus(): Promise<MemoryStatusResponse> {
    const response = await api.get<MemoryStatusResponse>('/api/v1/chat/memory/status')
    return response.data
  },
}

export default chatService
