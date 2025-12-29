/**
 * 벡터 공간 시각화 페이지
 * 검색어와 의약품들의 유사도 관계를 3D로 시각화
 */

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Search, RotateCcw, Info, Loader2 } from 'lucide-react'
import VectorSpace3D from '../components/visualization/VectorSpace3D'
import { getVectorSpace, VectorSpaceData, VectorPoint } from '../services/vectorService'

// 로딩 컴포넌트
function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center h-[600px] glass-panel rounded-2xl">
      <Loader2 className="w-12 h-12 text-purple-400 animate-spin mb-4" />
      <p className="text-glass-muted">벡터 공간을 계산하고 있습니다...</p>
    </div>
  )
}

// 에러 컴포넌트
function ErrorMessage({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-[600px] glass-panel rounded-2xl">
      <p className="text-red-400 mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="glass-button px-4 py-2 flex items-center gap-2"
      >
        <RotateCcw className="w-4 h-4" />
        다시 시도
      </button>
    </div>
  )
}

// 통계 카드
function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="glass-card p-4">
      <p className="text-xs text-glass-muted mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color }}>
        {value}
      </p>
    </div>
  )
}

export default function VectorSpacePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryParam = searchParams.get('q') || ''

  const [query, setQuery] = useState(queryParam)
  const [inputValue, setInputValue] = useState(queryParam)
  const [data, setData] = useState<VectorSpaceData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [, setSelectedPoint] = useState<VectorPoint | null>(null)

  // 데이터 로드
  const loadData = async (searchQuery: string) => {
    if (!searchQuery.trim()) return

    setLoading(true)
    setError(null)

    try {
      const result = await getVectorSpace(searchQuery, 30)
      setData(result)
    } catch (err) {
      setError('벡터 데이터를 불러오는데 실패했습니다.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // 검색 실행
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim()) return

    setQuery(inputValue)
    navigate(`/vector-space?q=${encodeURIComponent(inputValue)}`)
    loadData(inputValue)
  }

  // 초기 로드
  useEffect(() => {
    if (queryParam) {
      loadData(queryParam)
    }
  }, [])

  // 유사도 레벨별 통계 계산
  const levelStats = data?.drug_points.reduce(
    (acc, point) => {
      acc[point.similarity_level] = (acc[point.similarity_level] || 0) + 1
      return acc
    },
    {} as Record<number, number>
  )

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
        {/* 헤더 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            3D 벡터 공간 시각화
          </h1>
          <p className="text-glass-muted">
            검색어와 의약품들의 유사도 관계를 3D 공간에서 확인하세요
          </p>
        </div>

        {/* 검색 폼 */}
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4 max-w-2xl mx-auto">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-glass-muted" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="증상을 입력하세요 (예: 두통이 심해요)"
                className="glass-input w-full pl-12 pr-4 py-3"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !inputValue.trim()}
              className="glass-button-primary px-6 py-3 disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                '시각화'
              )}
            </button>
          </div>
        </form>

        {/* 설명 (쿼리가 없을 때) */}
        {!query && !loading && (
          <div className="glass-panel p-8 rounded-2xl text-center">
            <Info className="w-12 h-12 text-purple-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">
              벡터 공간이란?
            </h2>
            <p className="text-glass-muted max-w-2xl mx-auto mb-6">
              의약품과 검색어는 고차원 벡터로 표현됩니다. 이 시각화는 유사도에 따라
              벡터들을 3D 공간에 배치하여, 검색어와 의약품들의 관계를 직관적으로
              보여줍니다. 중심에 가까울수록 유사도가 높습니다.
            </p>
            <div className="grid grid-cols-5 gap-4 max-w-xl mx-auto">
              {[
                { level: 1, label: '매우 높음', color: '#22c55e' },
                { level: 2, label: '높음', color: '#84cc16' },
                { level: 3, label: '중간', color: '#eab308' },
                { level: 4, label: '낮음', color: '#f97316' },
                { level: 5, label: '매우 낮음', color: '#ef4444' },
              ].map((item) => (
                <div key={item.level} className="text-center">
                  <div
                    className="w-8 h-8 rounded-full mx-auto mb-2"
                    style={{ backgroundColor: item.color }}
                  />
                  <p className="text-xs text-glass-muted">{item.label}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 로딩 */}
        {loading && <LoadingSpinner />}

        {/* 에러 */}
        {error && <ErrorMessage message={error} onRetry={() => loadData(query)} />}

        {/* 시각화 결과 */}
        {data && !loading && !error && (
          <>
            {/* 통계 카드 */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
              <StatCard
                label="검색어"
                value={data.query.slice(0, 10) + (data.query.length > 10 ? '...' : '')}
                color="#a855f7"
              />
              <StatCard
                label="총 의약품"
                value={data.drug_points.length}
                color="#3b82f6"
              />
              {data.similarity_levels.slice(0, 3).map((level) => (
                <StatCard
                  key={level.level}
                  label={level.label}
                  value={levelStats?.[level.level] || 0}
                  color={level.color}
                />
              ))}
            </div>

            {/* 3D 시각화 */}
            <Suspense fallback={<LoadingSpinner />}>
              <VectorSpace3D
                queryPoint={data.query_point}
                drugPoints={data.drug_points}
                similarityLevels={data.similarity_levels}
                onPointClick={setSelectedPoint}
              />
            </Suspense>

            {/* 의약품 목록 */}
            <div className="mt-8">
              <h2 className="text-xl font-bold text-white mb-4">
                유사도 순 의약품 목록
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.drug_points
                  .sort((a, b) => b.similarity - a.similarity)
                  .slice(0, 12)
                  .map((point) => (
                    <div
                      key={point.id}
                      className="glass-card p-4 cursor-pointer hover:scale-105 transition-transform"
                      onClick={() => setSelectedPoint(point)}
                      style={{ borderLeft: `4px solid ${point.color}` }}
                    >
                      <h3 className="font-medium text-white truncate">
                        {point.name}
                      </h3>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-xs text-glass-muted">
                          유사도: {(point.similarity * 100).toFixed(1)}%
                        </span>
                        <span
                          className="text-xs px-2 py-1 rounded-full"
                          style={{ backgroundColor: point.color + '30', color: point.color }}
                        >
                          {point.similarity_level}단계
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </>
        )}
    </div>
  )
}
