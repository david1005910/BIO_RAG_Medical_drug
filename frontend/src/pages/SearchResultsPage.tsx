/**
 * 검색 결과 페이지
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Clock } from 'lucide-react'
import SearchForm from '../components/search/SearchForm'
import DrugList from '../components/drug/DrugList'
import AIResponse from '../components/ai/AIResponse'
import Loading from '../components/common/Loading'
import Disclaimer from '../components/common/Disclaimer'
import useSearch from '../hooks/useSearch'
import { SearchResponse } from '../types/api'

export default function SearchResultsPage() {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') || ''
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null)

  const { mutate: search, isPending, error } = useSearch()

  useEffect(() => {
    if (query) {
      handleSearch(query)
    }
  }, [query])

  const handleSearch = (newQuery: string) => {
    search(
      { query: newQuery, top_k: 5, include_ai_response: true },
      {
        onSuccess: (data) => {
          setSearchResult(data)
        },
      }
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* 검색 폼 */}
      <div className="mb-8 glass-panel p-4">
        <SearchForm
          initialQuery={query}
          onSearch={handleSearch}
          isLoading={isPending}
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
