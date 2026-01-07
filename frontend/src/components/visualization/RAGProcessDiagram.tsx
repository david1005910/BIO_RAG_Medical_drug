/**
 * RAG 프로세스 단계별 다이어그램 컴포넌트
 * 검색 프로세스의 각 단계를 애니메이션으로 시각적으로 보여줌
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Search,
  Brain,
  Database,
  FileText,
  Zap,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Target,
  Layers,
  Shuffle,
  CheckCircle2,
  Loader2,
  Play,
  Clock,
} from 'lucide-react'

interface ProcessStep {
  id: string
  title: string
  subtitle: string
  description: string
  icon: React.ReactNode
  color: string
  bgColor: string
  details: string[]
  duration: number // ms - 단계별 애니메이션 지속 시간
  metrics?: {
    label: string
    value: string | number
  }[]
}

interface RAGProcessDiagramProps {
  currentStep?: string
  scores?: {
    dense_score?: number | null
    bm25_score?: number | null
    hybrid_score?: number | null
    relevance_score?: number | null
  }
  isSearching?: boolean
}

const processSteps: ProcessStep[] = [
  {
    id: 'input',
    title: '1. 사용자 입력',
    subtitle: 'User Query',
    description: '사용자가 증상이나 의약품 관련 질문을 입력합니다.',
    icon: <Search className="w-6 h-6" />,
    color: 'from-blue-500 to-blue-600',
    bgColor: 'bg-blue-500/20',
    duration: 500,
    details: [
      '자연어 형태의 질문 입력',
      '예: "두통이 심해요", "감기약 추천해주세요"',
      '한국어/영어 모두 지원',
    ],
  },
  {
    id: 'embedding',
    title: '2. 쿼리 임베딩',
    subtitle: 'Query Embedding',
    description: 'OpenAI text-embedding-3-small 모델로 쿼리를 벡터로 변환합니다.',
    icon: <Brain className="w-6 h-6" />,
    color: 'from-purple-500 to-purple-600',
    bgColor: 'bg-purple-500/20',
    duration: 800,
    details: [
      'OpenAI Embedding API 호출',
      '1536차원 벡터로 변환',
      '의미적 유사도 계산 가능',
    ],
  },
  {
    id: 'dense',
    title: '3. Dense Search',
    subtitle: 'Vector Similarity',
    description: 'Qdrant/PGVector를 사용해 코사인 유사도 기반 벡터 검색을 수행합니다.',
    icon: <Target className="w-6 h-6" />,
    color: 'from-cyan-500 to-cyan-600',
    bgColor: 'bg-cyan-500/20',
    duration: 1000,
    details: [
      'Qdrant 또는 PGVector 벡터 DB',
      '코사인 유사도 계산 (0~1)',
      '의미적으로 유사한 문서 검색',
    ],
    metrics: [
      { label: 'Dense Score', value: '0~1' },
      { label: '가중치', value: '70%' },
    ],
  },
  {
    id: 'sparse',
    title: '4. SPLADE Search',
    subtitle: 'Sparse Lexical',
    description: 'SPLADE 알고리즘으로 희소 벡터 기반 키워드 검색을 수행합니다.',
    icon: <FileText className="w-6 h-6" />,
    color: 'from-orange-500 to-orange-600',
    bgColor: 'bg-orange-500/20',
    duration: 800,
    details: [
      'SPLADE: 신경망 기반 희소 벡터',
      '키워드 확장 및 가중치 학습',
      '0~30점 기준 정규화 (0~1)',
    ],
    metrics: [
      { label: 'SPLADE Score', value: '0~30 → 0~1' },
      { label: '가중치', value: '30%' },
    ],
  },
  {
    id: 'hybrid',
    title: '5. Hybrid 점수 계산',
    subtitle: 'Score Fusion',
    description: 'Dense와 SPLADE 점수를 결합하여 최종 Hybrid 점수를 계산합니다.',
    icon: <Shuffle className="w-6 h-6" />,
    color: 'from-green-500 to-green-600',
    bgColor: 'bg-green-500/20',
    duration: 600,
    details: [
      'Hybrid = Dense×0.7 + SPLADE×0.3',
      '의미적 유사도에 더 높은 가중치',
      '키워드 매칭으로 보완',
    ],
    metrics: [
      { label: 'Hybrid Score', value: '0~1' },
      { label: '수식', value: 'D×0.7 + S×0.3' },
    ],
  },
  {
    id: 'rerank',
    title: '6. Reranking',
    subtitle: 'Cohere Rerank',
    description: 'Cohere Rerank API로 검색 결과의 관련성을 재평가합니다.',
    icon: <Layers className="w-6 h-6" />,
    color: 'from-pink-500 to-pink-600',
    bgColor: 'bg-pink-500/20',
    duration: 1200,
    details: [
      'Cohere rerank-multilingual-v3.0',
      '쿼리-문서 관련성 정밀 평가',
      '상위 5개 결과 반환',
    ],
    metrics: [{ label: 'Relevance Score', value: '0~1' }],
  },
  {
    id: 'llm',
    title: '7. LLM 응답 생성',
    subtitle: 'GPT-4o-mini',
    description: '검색된 의약품 정보를 바탕으로 AI 응답을 생성합니다.',
    icon: <MessageSquare className="w-6 h-6" />,
    color: 'from-indigo-500 to-indigo-600',
    bgColor: 'bg-indigo-500/20',
    duration: 1500,
    details: [
      'OpenAI GPT-4o-mini 모델',
      '검색 결과 기반 RAG 응답',
      '의약품 추천 및 설명 생성',
    ],
  },
  {
    id: 'result',
    title: '8. 결과 반환',
    subtitle: 'Response',
    description: '최종 검색 결과와 AI 응답을 사용자에게 제공합니다.',
    icon: <Zap className="w-6 h-6" />,
    color: 'from-yellow-500 to-yellow-600',
    bgColor: 'bg-yellow-500/20',
    duration: 300,
    details: ['추천 의약품 목록', '각 의약품별 점수 표시', 'AI 분석 응답'],
  },
]

export default function RAGProcessDiagram({
  currentStep,
  scores,
  isSearching = false,
}: RAGProcessDiagramProps) {
  const [expandedStep, setExpandedStep] = useState<string | null>(null)
  const [showFullDiagram, setShowFullDiagram] = useState(false)
  const [animatingStep, setAnimatingStep] = useState<number>(-1)
  const [isAnimating, setIsAnimating] = useState(false)

  // 검색 시간 측정
  const [elapsedTime, setElapsedTime] = useState(0)
  const [finalTime, setFinalTime] = useState<number | null>(null)
  const [progressWidth, setProgressWidth] = useState(0)
  const startTimeRef = useRef<number | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 예상 검색 시간 (ms) - 진행률 계산용
  const EXPECTED_SEARCH_TIME = 5000

  // 검색 시작/종료 시 타이머 관리
  useEffect(() => {
    if (isSearching) {
      // 검색 시작
      startTimeRef.current = Date.now()
      setElapsedTime(0)
      setFinalTime(null)
      setProgressWidth(0)

      timerRef.current = setInterval(() => {
        if (startTimeRef.current) {
          const elapsed = Date.now() - startTimeRef.current
          setElapsedTime(elapsed)

          // 진행률 계산: 처음엔 빠르게, 나중엔 천천히 (로그 곡선)
          // 최대 90%까지만 진행 (완료 시 100%로 점프)
          const progress = Math.min(90, (1 - Math.exp(-elapsed / EXPECTED_SEARCH_TIME)) * 100)
          setProgressWidth(progress)
        }
      }, 50) // 50ms 간격으로 부드러운 업데이트
    } else {
      // 검색 종료
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      if (startTimeRef.current && elapsedTime > 0) {
        setFinalTime(elapsedTime)
        setProgressWidth(100) // 완료 시 100%
      }
      startTimeRef.current = null
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [isSearching])

  // 시간 포맷팅 (초.밀리초)
  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    const milliseconds = Math.floor((ms % 1000) / 100)
    return `${seconds}.${milliseconds}s`
  }

  const toggleStep = (stepId: string) => {
    setExpandedStep(expandedStep === stepId ? null : stepId)
  }

  // 데모 애니메이션 실행
  const runDemoAnimation = useCallback(() => {
    if (isAnimating) return

    setIsAnimating(true)
    setAnimatingStep(0)

    let currentIndex = 0
    const runStep = () => {
      if (currentIndex >= processSteps.length) {
        setIsAnimating(false)
        setAnimatingStep(-1)
        return
      }

      setAnimatingStep(currentIndex)
      const duration = processSteps[currentIndex].duration

      setTimeout(() => {
        currentIndex++
        runStep()
      }, duration)
    }

    runStep()
  }, [isAnimating])

  // 실제 검색 중일 때 애니메이션 동기화
  useEffect(() => {
    if (isSearching && currentStep) {
      const stepIndex = processSteps.findIndex((s) => s.id === currentStep)
      if (stepIndex !== -1) {
        setAnimatingStep(stepIndex)
        setIsAnimating(true)
      }
    } else if (!isSearching && isAnimating) {
      // 검색이 끝났으면 마지막 단계까지 완료 처리
      setAnimatingStep(processSteps.length)
      setTimeout(() => {
        setIsAnimating(false)
        setAnimatingStep(-1)
      }, 500)
    }
  }, [isSearching, currentStep])

  const getStepStatus = (stepIndex: number) => {
    if (animatingStep === -1) return 'idle'
    if (stepIndex < animatingStep) return 'completed'
    if (stepIndex === animatingStep) return 'active'
    return 'pending'
  }

  const getProgressPercentage = () => {
    if (animatingStep === -1) return 0
    return Math.min(((animatingStep + 1) / processSteps.length) * 100, 100)
  }

  return (
    <div className="w-full">
      {/* CSS 애니메이션 스타일 */}
      <style>{`
        @keyframes flow-particle {
          0% {
            transform: translate(-50%, -50%) scale(0);
            opacity: 0;
          }
          20% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
          }
          100% {
            transform: translate(calc(-50% + 40px), -50%) scale(0.5);
            opacity: 0;
          }
        }

        @keyframes pulse-ring {
          0% {
            transform: scale(1);
            opacity: 0.8;
          }
          100% {
            transform: scale(1.5);
            opacity: 0;
          }
        }

        @keyframes slide-in {
          0% {
            transform: translateX(-20px);
            opacity: 0;
          }
          100% {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes bounce-in {
          0% {
            transform: scale(0.3);
            opacity: 0;
          }
          50% {
            transform: scale(1.1);
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }

        @keyframes glow {
          0%, 100% {
            box-shadow: 0 0 5px currentColor, 0 0 10px currentColor;
          }
          50% {
            box-shadow: 0 0 20px currentColor, 0 0 30px currentColor;
          }
        }

        .animate-flow-particle {
          animation: flow-particle 1s ease-out infinite;
        }

        .animate-pulse-ring {
          animation: pulse-ring 1.5s ease-out infinite;
        }

        .animate-slide-in {
          animation: slide-in 0.3s ease-out forwards;
        }

        .animate-bounce-in {
          animation: bounce-in 0.5s ease-out forwards;
        }

        .animate-glow {
          animation: glow 1.5s ease-in-out infinite;
        }
      `}</style>

      {/* 전체 다이어그램 토글 버튼 */}
      <button
        onClick={() => setShowFullDiagram(!showFullDiagram)}
        className="w-full mb-4 glass-card p-4 flex items-center justify-between hover:bg-white/10 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h3 className="text-lg font-semibold text-glass">RAG 검색 프로세스</h3>
            <p className="text-sm text-glass-muted">
              {showFullDiagram ? '접기' : '클릭하여 전체 프로세스 보기'}
            </p>
          </div>
        </div>
        {showFullDiagram ? (
          <ChevronUp className="w-5 h-5 text-glass-muted" />
        ) : (
          <ChevronDown className="w-5 h-5 text-glass-muted" />
        )}
      </button>

      {/* 전체 다이어그램 */}
      {showFullDiagram && (
        <div className="glass-card p-6 mb-6 animate-fade-in">
          {/* 상단 컨트롤 및 진행률 */}
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={runDemoAnimation}
              disabled={isAnimating || isSearching}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                isAnimating || isSearching
                  ? 'bg-white/5 text-glass-muted cursor-not-allowed'
                  : 'bg-gradient-to-r from-cyan-500 to-purple-500 text-white hover:shadow-lg hover:shadow-cyan-500/30'
              }`}
            >
              {isAnimating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>{isAnimating ? '애니메이션 진행 중...' : '데모 애니메이션 실행'}</span>
            </button>

            {/* 진행률 표시 */}
            {(isAnimating || isSearching) && (
              <div className="flex items-center gap-3">
                <div className="w-32 h-2 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all duration-300"
                    style={{ width: `${getProgressPercentage()}%` }}
                  />
                </div>
                <span className="text-sm text-glass-muted">
                  {Math.round(getProgressPercentage())}%
                </span>
              </div>
            )}
          </div>

          {/* 간단한 플로우 다이어그램 (가로 스크롤) */}
          <div className="relative mb-8">
            <div className="flex items-center justify-start gap-1 overflow-x-auto pb-4 px-2">
              {processSteps.map((step, index) => {
                const status = getStepStatus(index)

                return (
                  <div key={step.id} className="flex items-center flex-shrink-0">
                    {/* 단계 아이콘 */}
                    <button
                      onClick={() => toggleStep(step.id)}
                      className="relative group"
                    >
                      {/* 활성 상태 링 애니메이션 */}
                      {status === 'active' && (
                        <div
                          className={`absolute inset-0 rounded-xl bg-gradient-to-br ${step.color} animate-pulse-ring`}
                        />
                      )}

                      <div
                        className={`relative w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 ${
                          status === 'active'
                            ? `bg-gradient-to-br ${step.color} scale-110 shadow-lg`
                            : status === 'completed'
                            ? 'bg-green-500 scale-100'
                            : 'bg-white/10 scale-100'
                        }`}
                        style={
                          status === 'active'
                            ? { boxShadow: '0 0 20px rgba(0,255,255,0.5)' }
                            : {}
                        }
                      >
                        {status === 'completed' ? (
                          <CheckCircle2 className="w-6 h-6 text-white animate-bounce-in" />
                        ) : status === 'active' ? (
                          <div className="animate-pulse">{step.icon}</div>
                        ) : (
                          step.icon
                        )}
                      </div>

                      {/* 단계 이름 툴팁 */}
                      <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap">
                        <span
                          className={`text-xs ${
                            status === 'active'
                              ? 'text-cyan-400 font-semibold'
                              : status === 'completed'
                              ? 'text-green-400'
                              : 'text-glass-muted'
                          }`}
                        >
                          {index + 1}
                        </span>
                      </div>
                    </button>

                    {/* 연결선 */}
                    {index < processSteps.length - 1 && (
                      <div className="relative mx-1 w-8">
                        {/* 배경 선 */}
                        <div className="h-0.5 bg-white/10" />

                        {/* 활성화된 선 */}
                        <div
                          className={`absolute top-0 left-0 h-0.5 transition-all duration-500 ${
                            status === 'completed' || status === 'active'
                              ? 'bg-gradient-to-r from-green-400 to-cyan-400'
                              : 'bg-transparent'
                          }`}
                          style={{
                            width:
                              status === 'completed'
                                ? '100%'
                                : status === 'active'
                                ? '50%'
                                : '0%',
                          }}
                        />

                        {/* 데이터 플로우 파티클 */}
                        {status === 'active' && (
                          <div className="absolute top-1/2 left-0 w-full">
                            <div className="relative h-2">
                              {[...Array(3)].map((_, i) => (
                                <div
                                  key={i}
                                  className="absolute w-1.5 h-1.5 rounded-full bg-cyan-400"
                                  style={{
                                    animation: `flow-particle 0.8s ease-out infinite`,
                                    animationDelay: `${i * 250}ms`,
                                    top: '-3px',
                                  }}
                                />
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 현재 진행 중인 단계 상세 (애니메이션) */}
          {animatingStep >= 0 && animatingStep < processSteps.length && (
            <div
              className={`mb-6 p-4 rounded-xl ${processSteps[animatingStep].bgColor} border border-white/10 animate-slide-in`}
            >
              <div className="flex items-center gap-4">
                <div
                  className={`w-14 h-14 rounded-xl bg-gradient-to-br ${processSteps[animatingStep].color} flex items-center justify-center animate-pulse`}
                >
                  {processSteps[animatingStep].icon}
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-glass">
                    {processSteps[animatingStep].title}
                  </h4>
                  <p className="text-sm text-glass-muted">
                    {processSteps[animatingStep].description}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 단계별 상세 정보 */}
          <div className="grid gap-4">
            {processSteps.map((step, index) => {
              const status = getStepStatus(index)
              const isExpanded = expandedStep === step.id

              return (
                <div
                  key={step.id}
                  className={`rounded-xl overflow-hidden transition-all duration-300 ${
                    status === 'active'
                      ? `ring-2 ring-cyan-400 ${step.bgColor}`
                      : status === 'completed'
                      ? 'bg-green-500/10'
                      : 'bg-white/5'
                  }`}
                  style={{
                    animationDelay: `${index * 50}ms`,
                  }}
                >
                  <button
                    onClick={() => toggleStep(step.id)}
                    className="w-full p-4 flex items-center gap-4 text-left hover:bg-white/5 transition-colors"
                  >
                    <div
                      className={`w-12 h-12 rounded-xl bg-gradient-to-br ${step.color} flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                        status === 'active' ? 'scale-110 shadow-lg' : ''
                      }`}
                    >
                      {status === 'completed' ? (
                        <CheckCircle2 className="w-6 h-6 text-white" />
                      ) : status === 'active' ? (
                        <Loader2 className="w-6 h-6 text-white animate-spin" />
                      ) : (
                        step.icon
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-glass">{step.title}</h4>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            status === 'active'
                              ? 'bg-cyan-500/30 text-cyan-300'
                              : status === 'completed'
                              ? 'bg-green-500/30 text-green-300'
                              : 'bg-white/10 text-glass-muted'
                          }`}
                        >
                          {status === 'active'
                            ? '진행 중'
                            : status === 'completed'
                            ? '완료'
                            : step.subtitle}
                        </span>
                      </div>
                      <p className="text-sm text-glass-muted mt-1 truncate">
                        {step.description}
                      </p>
                    </div>
                    <div className="flex-shrink-0">
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-glass-muted" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-glass-muted" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="px-4 pb-4 pt-0 animate-fade-in">
                      <div className="ml-16 pl-4 border-l border-white/10">
                        <ul className="space-y-2">
                          {step.details.map((detail, idx) => (
                            <li
                              key={idx}
                              className="text-sm text-glass-muted flex items-start gap-2 animate-slide-in"
                              style={{ animationDelay: `${idx * 100}ms` }}
                            >
                              <span className="text-cyan-400 mt-1">•</span>
                              {detail}
                            </li>
                          ))}
                        </ul>

                        {step.metrics && (
                          <div className="mt-4 flex flex-wrap gap-3">
                            {step.metrics.map((metric, idx) => (
                              <div
                                key={idx}
                                className="px-3 py-2 rounded-lg bg-white/10 text-sm animate-bounce-in"
                                style={{ animationDelay: `${idx * 150}ms` }}
                              >
                                <span className="text-glass-muted">{metric.label}: </span>
                                <span className="text-glass font-medium">{metric.value}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* 실시간 점수 표시 (텍스트만) */}
                        {scores && step.id === 'dense' && scores.dense_score != null && (
                          <div className="mt-3 p-3 rounded-lg bg-cyan-500/20 animate-slide-in">
                            <div className="flex items-center justify-between">
                              <span className="text-cyan-300 text-sm">현재 Dense Score:</span>
                              <span className="text-cyan-200 font-bold text-lg">
                                {(scores.dense_score ?? 0).toFixed(3)}
                                <span className="text-xs text-cyan-400 ml-1">(0-1)</span>
                              </span>
                            </div>
                          </div>
                        )}
                        {scores && step.id === 'sparse' && scores.bm25_score != null && (
                          <div className="mt-3 p-3 rounded-lg bg-orange-500/20 animate-slide-in">
                            <div className="flex items-center justify-between">
                              <span className="text-orange-300 text-sm">현재 SPLADE Score:</span>
                              <span className="text-orange-200 font-bold text-lg">
                                {((scores.bm25_score ?? 0) * 30).toFixed(2)}
                                <span className="text-xs text-orange-400 ml-1">(0-30)</span>
                              </span>
                            </div>
                          </div>
                        )}
                        {scores && step.id === 'hybrid' && scores.hybrid_score != null && (
                          <div className="mt-3 p-3 rounded-lg bg-green-500/20 animate-slide-in">
                            <div className="flex items-center justify-between">
                              <span className="text-green-300 text-sm">현재 Hybrid Score:</span>
                              <span className="text-green-200 font-bold text-lg">
                                {(scores.hybrid_score ?? 0).toFixed(3)}
                                <span className="text-xs text-green-400 ml-1">(0-1)</span>
                              </span>
                            </div>
                          </div>
                        )}
                        {scores && step.id === 'rerank' && scores.relevance_score != null && (
                          <div className="mt-3 p-3 rounded-lg bg-pink-500/20 animate-slide-in">
                            <div className="flex items-center justify-between">
                              <span className="text-pink-300 text-sm">현재 Relevance Score:</span>
                              <span className="text-pink-200 font-bold text-lg">
                                {(scores.relevance_score ?? 0).toFixed(3)}
                                <span className="text-xs text-pink-400 ml-1">(0-1)</span>
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 축소된 상태에서의 미니 프로세스 바 */}
      {!showFullDiagram && (isSearching || isAnimating || finalTime !== null) && (
        <div className="glass-card p-4 mb-4">
          {/* 검색 시간 표시 */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className={`w-4 h-4 ${isSearching ? 'text-cyan-400 animate-pulse' : 'text-green-400'}`} />
              <span className="text-sm text-glass-muted">검색 시간</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-lg font-mono font-bold ${isSearching ? 'text-cyan-400' : 'text-green-400'}`}>
                {isSearching ? formatTime(elapsedTime) : finalTime !== null ? formatTime(finalTime) : '0.0s'}
              </span>
              {!isSearching && finalTime !== null && (
                <span className="text-xs text-green-400 bg-green-500/20 px-2 py-0.5 rounded">완료</span>
              )}
            </div>
          </div>

          {/* 진행률 바 */}
          <div className="mb-3">
            <div className="flex items-center gap-2">
              <div className="flex-1 h-3 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-150 ease-out ${
                    isSearching
                      ? 'bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500'
                      : 'bg-gradient-to-r from-green-400 to-green-500'
                  }`}
                  style={{ width: `${progressWidth}%` }}
                />
              </div>
              <span className="text-xs text-glass-muted w-10 text-right">
                {Math.round(progressWidth)}%
              </span>
            </div>
          </div>

          {/* 미니 아이콘 */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {processSteps.map((step, index) => {
              const status = getStepStatus(index)
              return (
                <div key={step.id} className="flex items-center flex-shrink-0">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-300 ${
                      status === 'active'
                        ? `bg-gradient-to-br ${step.color} scale-110 shadow-lg`
                        : status === 'completed'
                        ? 'bg-green-500'
                        : 'bg-white/10'
                    }`}
                    style={
                      status === 'active'
                        ? { boxShadow: '0 0 15px rgba(0,255,255,0.5)' }
                        : {}
                    }
                  >
                    {status === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    ) : status === 'active' ? (
                      <div className="animate-pulse">{step.icon}</div>
                    ) : (
                      step.icon
                    )}
                  </div>
                  {index < processSteps.length - 1 && (
                    <div
                      className={`w-4 h-0.5 mx-1 transition-all duration-300 ${
                        status === 'completed'
                          ? 'bg-green-400'
                          : status === 'active'
                          ? 'bg-gradient-to-r from-green-400 to-white/20'
                          : 'bg-white/20'
                      }`}
                    />
                  )}
                </div>
              )
            })}
          </div>

          {/* 현재 단계 표시 */}
          {isSearching && animatingStep >= 0 && animatingStep < processSteps.length && (
            <div className="mt-3 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
              <span className="text-sm text-cyan-300">
                {processSteps[animatingStep].title} 진행 중...
              </span>
            </div>
          )}
          {!isSearching && finalTime !== null && (
            <div className="mt-3 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-300">
                검색 완료 ({formatTime(finalTime)})
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
