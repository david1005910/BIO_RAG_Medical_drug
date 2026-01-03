/**
 * RAG 프로세스 설명 페이지
 * 검색 시스템의 동작 원리를 시각적으로 설명
 */

import { useState } from 'react'
import { Search, ArrowRight, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import RAGProcessDiagram from '../components/visualization/RAGProcessDiagram'

export default function RAGProcessPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [isSimulating, setIsSimulating] = useState(false)
  const [currentStep, setCurrentStep] = useState<string | undefined>()
  const [simulatedScores, setSimulatedScores] = useState<{
    dense_score?: number | null
    bm25_score?: number | null
    hybrid_score?: number | null
    relevance_score?: number | null
  }>({})

  // 프로세스 시뮬레이션
  const simulateProcess = async () => {
    if (!query.trim()) return

    setIsSimulating(true)
    setSimulatedScores({})

    const steps = ['input', 'embedding', 'dense', 'sparse', 'hybrid', 'rerank', 'llm', 'result']

    for (const step of steps) {
      setCurrentStep(step)

      // 각 단계별 시뮬레이션 점수
      if (step === 'dense') {
        await new Promise((r) => setTimeout(r, 800))
        setSimulatedScores((prev) => ({ ...prev, dense_score: Math.random() * 0.5 + 0.2 }))
      } else if (step === 'sparse') {
        await new Promise((r) => setTimeout(r, 800))
        setSimulatedScores((prev) => ({ ...prev, bm25_score: Math.random() * 0.7 + 0.1 }))
      } else if (step === 'hybrid') {
        await new Promise((r) => setTimeout(r, 600))
        const scores = simulatedScores
        const hybrid = (scores.bm25_score || 0) * 0.7 + (scores.dense_score || 0) * 0.3
        setSimulatedScores((prev) => ({ ...prev, hybrid_score: hybrid }))
      } else if (step === 'rerank') {
        await new Promise((r) => setTimeout(r, 700))
        setSimulatedScores((prev) => ({ ...prev, relevance_score: Math.random() * 0.3 + 0.6 }))
      } else {
        await new Promise((r) => setTimeout(r, 500))
      }
    }

    setIsSimulating(false)
    setCurrentStep(undefined)
  }

  const handleRealSearch = () => {
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* 페이지 헤더 */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-glass mb-3">RAG 검색 프로세스</h1>
        <p className="text-glass-muted max-w-2xl mx-auto">
          의약품 추천 시스템의 검색 프로세스를 단계별로 확인해보세요.
          Hybrid Search (Dense + Sparse) 와 Cohere Reranking을 사용합니다.
        </p>
      </div>

      {/* 시뮬레이션 입력 */}
      <div className="glass-card p-6 mb-6">
        <h2 className="text-lg font-semibold text-glass mb-4">프로세스 시뮬레이션</h2>
        <p className="text-sm text-glass-muted mb-4">
          검색어를 입력하고 프로세스를 시뮬레이션하거나, 실제 검색을 수행할 수 있습니다.
        </p>

        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-glass-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && simulateProcess()}
              placeholder="증상을 입력하세요... (예: 두통이 심해요)"
              className="w-full pl-12 pr-4 py-3 glass-input rounded-xl"
              disabled={isSimulating}
            />
          </div>
          <button
            onClick={simulateProcess}
            disabled={!query.trim() || isSimulating}
            className="px-5 py-3 glass-button rounded-xl flex items-center gap-2 disabled:opacity-50"
          >
            {isSimulating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                시뮬레이션 중...
              </>
            ) : (
              <>
                <ArrowRight className="w-5 h-5" />
                시뮬레이션
              </>
            )}
          </button>
        </div>

        {query.trim() && !isSimulating && (
          <button
            onClick={handleRealSearch}
            className="mt-4 w-full py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-medium hover:opacity-90 transition-opacity"
          >
            이 검색어로 실제 검색하기
          </button>
        )}
      </div>

      {/* RAG 프로세스 다이어그램 */}
      <RAGProcessDiagram
        currentStep={currentStep}
        scores={simulatedScores}
        isSearching={isSimulating}
      />

      {/* 점수 체계 설명 */}
      <div className="glass-card p-6 mt-6">
        <h2 className="text-lg font-semibold text-glass mb-4">점수 체계</h2>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
            <h3 className="font-medium text-cyan-300 mb-2">Dense Score (30%)</h3>
            <p className="text-sm text-glass-muted">
              코사인 유사도 기반 벡터 검색 점수입니다.
              OpenAI 임베딩으로 의미적 유사성을 측정합니다.
            </p>
            <div className="mt-2 text-xs text-cyan-400">범위: 0 ~ 1</div>
          </div>

          <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/30">
            <h3 className="font-medium text-orange-300 mb-2">BM25 Score (70%)</h3>
            <p className="text-sm text-glass-muted">
              BM25 알고리즘 기반 키워드 검색 점수입니다.
              한국어 토큰화와 증상 키워드 가중치를 적용합니다.
            </p>
            <div className="mt-2 text-xs text-orange-400">원점수: 0~30 → 정규화: 0~1</div>
          </div>

          <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30">
            <h3 className="font-medium text-green-300 mb-2">Hybrid Score</h3>
            <p className="text-sm text-glass-muted">
              Dense와 Sparse 점수를 결합한 최종 점수입니다.
              키워드 매칭에 더 높은 가중치를 부여합니다.
            </p>
            <div className="mt-2 text-xs text-green-400">
              계산식: BM25 × 0.7 + Dense × 0.3
            </div>
          </div>

          <div className="p-4 rounded-lg bg-pink-500/10 border border-pink-500/30">
            <h3 className="font-medium text-pink-300 mb-2">Relevance Score</h3>
            <p className="text-sm text-glass-muted">
              Cohere Rerank API를 통한 관련성 점수입니다.
              쿼리와 문서의 관련성을 정밀하게 평가합니다.
            </p>
            <div className="mt-2 text-xs text-pink-400">범위: 0 ~ 1</div>
          </div>
        </div>
      </div>
    </div>
  )
}
