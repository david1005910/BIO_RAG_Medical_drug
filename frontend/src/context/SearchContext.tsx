/**
 * 검색 상태 관리 Context
 * 페이지 이동 후에도 검색 결과를 유지
 */

import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react'
import { SearchResponse } from '../types/api'

interface SearchState {
  query: string
  result: SearchResponse | null
  timestamp: number
}

interface SearchContextType {
  searchState: SearchState | null
  setSearchState: (query: string, result: SearchResponse) => void
  clearSearchState: () => void
  isValidCache: (query: string) => boolean
}

const SearchContext = createContext<SearchContextType | null>(null)

// 캐시 유효 시간 (5분)
const CACHE_DURATION = 5 * 60 * 1000

// sessionStorage 키
const STORAGE_KEY = 'medical-rag-search-state'

export function SearchProvider({ children }: { children: ReactNode }) {
  const [searchState, setSearchStateInternal] = useState<SearchState | null>(() => {
    // 초기화 시 sessionStorage에서 복원
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved) as SearchState
        // 캐시 유효성 검사
        if (Date.now() - parsed.timestamp < CACHE_DURATION) {
          return parsed
        }
      }
    } catch {
      // 파싱 실패 시 무시
    }
    return null
  })

  // 상태 변경 시 sessionStorage에 저장
  useEffect(() => {
    if (searchState) {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(searchState))
      } catch {
        // 저장 실패 시 무시
      }
    }
  }, [searchState])

  const setSearchState = useCallback((query: string, result: SearchResponse) => {
    setSearchStateInternal({
      query,
      result,
      timestamp: Date.now(),
    })
  }, [])

  const clearSearchState = useCallback(() => {
    setSearchStateInternal(null)
    try {
      sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      // 삭제 실패 시 무시
    }
  }, [])

  const isValidCache = useCallback((query: string) => {
    if (!searchState) return false
    if (searchState.query !== query) return false
    if (Date.now() - searchState.timestamp > CACHE_DURATION) return false
    return true
  }, [searchState])

  return (
    <SearchContext.Provider value={{ searchState, setSearchState, clearSearchState, isValidCache }}>
      {children}
    </SearchContext.Provider>
  )
}

export function useSearchContext() {
  const context = useContext(SearchContext)
  if (!context) {
    throw new Error('useSearchContext must be used within a SearchProvider')
  }
  return context
}

export default SearchContext
