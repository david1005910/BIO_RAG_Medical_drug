/**
 * Chat 커스텀 훅 - 메모리 기능 포함 대화
 */

import { useMutation } from '@tanstack/react-query'
import chatService from '../services/chatService'
import { ChatRequest, ChatResponse } from '../types/api'

export function useChat() {
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: (request) => chatService.chat(request),
  })
}

export default useChat
