/**
 * 검색 결과 페이지
 */

import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Clock } from 'lucide-react'
import SearchForm from '../components/search/SearchForm'
import DrugList from '../components/drug/DrugList'
import AIResponse from '../components/ai/AIResponse'
import Loading from '../components/common/Loading'
import Disclaimer from '../components/common/Disclaimer'
import RAGProcessDiagram from '../components/visualization/RAGProcessDiagram'
import useSearch from '../hooks/useSearch'
import useChat from '../hooks/useChat'
import { useSearchContext } from '../context/SearchContext'
import { useMemoryContext } from '../context/MemoryContext'

export default function SearchResultsPage() {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') || ''

  // Context에서 검색 상태 가져오기
  const { searchState, setSearchState, isValidCache } = useSearchContext()

  // 메모리 Context
  const {
    isMemoryEnabled,
    sessionId,
    setConversationTurn,
    setLastFromCache,
  } = useMemoryContext()

  // 캐시된 결과가 있으면 사용
  const searchResult = isValidCache(query) ? searchState?.result : null

  // 검색 API (메모리 비활성화 시)
  const { mutate: search, isPending: isSearchPending, error: searchError } = useSearch()

  // 채팅 API (메모리 활성화 시)
  const { mutate: chat, isPending: isChatPending, error: chatError } = useChat()

  const isPending = isSearchPending || isChatPending
  const error = searchError || chatError

  useEffect(() => {
    // 쿼리가 있고, 유효한 캐시가 없을 때만 검색 실행
    if (query && !isValidCache(query)) {
      handleSearch(query)
    }
  }, [query])

  const handleSearch = (newQuery: string) => {
    if (isMemoryEnabled) {
      // 메모리 활성화: Chat API 사용
      chat(
        {
          message: newQuery,
          session_id: sessionId,
          top_k: 5,
          use_memory: true,
        },
        {
          onSuccess: (data) => {
            // Chat 응답을 Search 응답 형식으로 변환
            const searchResponse = {
              success: data.success,
              data: {
                results: data.sources.map((source) => ({
                  id: source.id,
                  item_name: source.name,
                  entp_name: null,
                  efficacy: null,
                  use_method: null,
                  caution_info: null,
                  side_effects: null,
                  similarity: source.similarity,
                  dense_score: source.similarity,
                  bm25_score: null,
                  hybrid_score: source.similarity,
                  relevance_score: source.similarity,
                })),
                ai_response: data.message,
                disclaimer: data.disclaimer,
              },
              meta: {
                total_results: data.sources.length,
                response_time_ms: data.from_cache ? 1 : 0,
                query: newQuery,
                from_cache: data.from_cache,
              },
            }
            // Context에 검색 결과 저장
            setSearchState(newQuery, searchResponse)

            // 메모리 상태 업데이트
            setConversationTurn(data.conversation_turn)
            setLastFromCache(data.from_cache)
          },
        }
      )
    } else {
      // 메모리 비활성화: 기존 Search API 사용
      search(
        { query: newQuery, top_k: 5, include_ai_response: true },
        {
          onSuccess: (data) => {
            // Context에 검색 결과 저장
            setSearchState(newQuery, data)
            // 메모리 상태 초기화
            setConversationTurn(0)
            setLastFromCache(false)
          },
        }
      )
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* 검색 폼 */}
      <div className="mb-6 glass-panel p-4">
        <SearchForm
          initialQuery={query}
          onSearch={handleSearch}
          isLoading={isPending}
        />
      </div>

      {/* RAG 프로세스 다이어그램 */}
      <div className="mb-6">
        <RAGProcessDiagram
          isSearching={isPending}
          scores={
            searchResult?.data.results[0]
              ? {
                  dense_score: searchResult.data.results[0].dense_score,
                  bm25_score: searchResult.data.results[0].bm25_score,
                  hybrid_score: searchResult.data.results[0].hybrid_score,
                  relevance_score: searchResult.data.results[0].relevance_score,
                }
              : undefined
          }
        />
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="glass-card border-l-4 border-l-red-400 p-4 mb-6">
          <p className="text-red-300">
            검색 중 오류가 발생했습니다. 다시 시도해 주세요.
          </p>
        </div>
      )}

      {/* 로딩 */}
      {isPending && (
        <div className="space-y-6">
          <AIResponse response="" isLoading={true} />
          <Loading message="의약품을 검색하고 있습니다..." />
        </div>
      )}

      {/* 검색 결과 */}
      {!isPending && searchResult && (
        <div className="space-y-6 animate-fade-in">
          {/* 면책 조항 */}
          <Disclaimer text={searchResult.data.disclaimer} />

          {/* AI 응답 */}
          {searchResult.data.ai_response && (
            <AIResponse response={searchResult.data.ai_response} />
          )}

          {/* 검색 메타 정보 */}
          <div className="flex items-center justify-between text-sm text-glass-muted">
            <span>
              &quot;{searchResult.meta.query}&quot; 검색 결과{' '}
              <strong className="accent-cyan">
                {searchResult.meta.total_results}건
              </strong>
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              {searchResult.meta.response_time_ms}ms
            </span>
          </div>

          {/* Glass divider */}
          <div className="glass-divider" />

          {/* 의약품 목록 */}
          <div>
            <h2 className="text-lg font-semibold text-glass mb-4">
              추천 의약품
            </h2>
            <DrugList
              drugs={searchResult.data.results}
              emptyMessage="검색 결과가 없습니다. 다른 증상으로 검색해 보세요."
            />
          </div>
        </div>
      )}

      {/* 검색어가 없을 때 */}
      {!isPending && !searchResult && !query && (
        <div className="text-center py-12">
          <p className="text-glass-muted">증상을 입력하여 검색해 주세요.</p>
        </div>
      )}
    </div>
  )
}
