/**
 * 메모리 상태 관리 Context
 * 대화 메모리 기능 on/off 및 세션 관리
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  ReactNode,
} from 'react'

interface MemoryContextType {
  // 메모리 기능 활성화 여부
  isMemoryEnabled: boolean
  setMemoryEnabled: (enabled: boolean) => void
  toggleMemory: () => void

  // 세션 관리
  sessionId: string
  resetSession: () => void

  // 대화 턴 정보
  conversationTurn: number
  setConversationTurn: (turn: number) => void

  // 캐시 히트 여부
  lastFromCache: boolean
  setLastFromCache: (fromCache: boolean) => void
}

const MemoryContext = createContext<MemoryContextType | null>(null)

// LocalStorage 키
const MEMORY_ENABLED_KEY = 'medical-rag-memory-enabled'
const SESSION_ID_KEY = 'medical-rag-session-id'

// 세션 ID 생성
function generateSessionId(): string {
  // crypto.randomUUID()는 모던 브라우저에서 지원
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `session-${crypto.randomUUID()}`
  }
  // 폴백: 간단한 랜덤 ID
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export function MemoryProvider({ children }: { children: ReactNode }) {
  // 메모리 기능 활성화 여부 (localStorage에서 복원)
  const [isMemoryEnabled, setIsMemoryEnabled] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem(MEMORY_ENABLED_KEY)
      return saved !== null ? JSON.parse(saved) : true // 기본값: 활성화
    } catch {
      return true
    }
  })

  // 세션 ID (localStorage에서 복원)
  const [sessionId, setSessionId] = useState<string>(() => {
    try {
      const saved = localStorage.getItem(SESSION_ID_KEY)
      return saved || generateSessionId()
    } catch {
      return generateSessionId()
    }
  })

  // 대화 턴 정보
  const [conversationTurn, setConversationTurn] = useState(0)

  // 마지막 응답이 캐시에서 왔는지
  const [lastFromCache, setLastFromCache] = useState(false)

  // 메모리 설정 변경 시 localStorage에 저장
  useEffect(() => {
    try {
      localStorage.setItem(MEMORY_ENABLED_KEY, JSON.stringify(isMemoryEnabled))
    } catch {
      // 저장 실패 시 무시
    }
  }, [isMemoryEnabled])

  // 세션 ID 변경 시 localStorage에 저장
  useEffect(() => {
    try {
      localStorage.setItem(SESSION_ID_KEY, sessionId)
    } catch {
      // 저장 실패 시 무시
    }
  }, [sessionId])

  const setMemoryEnabled = useCallback((enabled: boolean) => {
    setIsMemoryEnabled(enabled)
    // 메모리 비활성화 시 대화 턴 초기화
    if (!enabled) {
      setConversationTurn(0)
      setLastFromCache(false)
    }
  }, [])

  const toggleMemory = useCallback(() => {
    setIsMemoryEnabled((prev) => {
      const newValue = !prev
      if (!newValue) {
        setConversationTurn(0)
        setLastFromCache(false)
      }
      return newValue
    })
  }, [])

  const resetSession = useCallback(() => {
    const newSessionId = generateSessionId()
    setSessionId(newSessionId)
    setConversationTurn(0)
    setLastFromCache(false)
  }, [])

  return (
    <MemoryContext.Provider
      value={{
        isMemoryEnabled,
        setMemoryEnabled,
        toggleMemory,
        sessionId,
        resetSession,
        conversationTurn,
        setConversationTurn,
        lastFromCache,
        setLastFromCache,
      }}
    >
      {children}
    </MemoryContext.Provider>
  )
}

export function useMemoryContext() {
  const context = useContext(MemoryContext)
  if (!context) {
    throw new Error('useMemoryContext must be used within a MemoryProvider')
  }
  return context
}

export default MemoryContext
