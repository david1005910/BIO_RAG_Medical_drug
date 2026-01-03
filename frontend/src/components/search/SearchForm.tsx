/**
 * 검색 폼 컴포넌트
 */

import { useState, FormEvent, ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, Brain, BrainCircuit } from 'lucide-react'
import { useMemoryContext } from '../../context/MemoryContext'

interface SearchFormProps {
  initialQuery?: string
  onSearch?: (query: string) => void
  isLoading?: boolean
  variant?: 'default' | 'hero'
}

const EXAMPLE_QUERIES = [
  '두통이 심해요',
  '소화가 안돼요',
  '감기 기운이 있어요',
  '목이 아파요',
]

export default function SearchForm({
  initialQuery = '',
  onSearch,
  isLoading = false,
  variant = 'default',
}: SearchFormProps) {
  const [query, setQuery] = useState(initialQuery)
  const navigate = useNavigate()
  const { isMemoryEnabled, toggleMemory, conversationTurn, lastFromCache } = useMemoryContext()

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    if (onSearch) {
      onSearch(query)
    } else {
      navigate(`/search?q=${encodeURIComponent(query)}`)
    }
  }

  const handleExampleClick = (example: string) => {
    setQuery(example)
    if (onSearch) {
      onSearch(example)
    } else {
      navigate(`/search?q=${encodeURIComponent(example)}`)
    }
  }

  const isHero = variant === 'hero'

  return (
    <div className={isHero ? 'w-full max-w-2xl mx-auto' : 'w-full'}>
      <form onSubmit={handleSubmit}>
        <div className={`flex items-center gap-2 ${isHero ? 'flex-col sm:flex-row' : ''}`}>
          <div className="relative flex-1 w-full">
            <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-glass-subtle pointer-events-none z-10">
              <Search className={isHero ? 'w-6 h-6' : 'w-5 h-5'} />
            </span>
            <input
              type="text"
              value={query}
              onChange={handleInputChange}
              placeholder="증상을 입력하세요 (예: 두통이 심해요)"
              disabled={isLoading}
              autoComplete="off"
              autoFocus={isHero}
              className={`
                input-glass w-full
                disabled:opacity-50 transition-all
                pl-12 pr-4 py-3
                ${isHero ? 'text-lg py-4' : ''}
              `}
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim() || isLoading}
            className={`
              btn-glass px-6 py-3
              flex items-center justify-center gap-2
              ${isHero ? 'w-full sm:w-auto py-4 px-8' : ''}
            `}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                검색 중...
              </>
            ) : (
              '검색'
            )}
          </button>
        </div>
      </form>

      {/* 메모리 토글 및 상태 */}
      <div className="mt-4 flex items-center justify-center gap-4">
        <button
          type="button"
          onClick={toggleMemory}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-300
            ${isMemoryEnabled
              ? 'bg-cyan-500/20 border border-cyan-400/50 text-cyan-300 hover:bg-cyan-500/30'
              : 'bg-gray-500/20 border border-gray-500/50 text-gray-400 hover:bg-gray-500/30'
            }
          `}
          title={isMemoryEnabled ? '메모리 기능 켜짐 - 대화 기록이 저장됩니다' : '메모리 기능 꺼짐'}
        >
          {isMemoryEnabled ? (
            <BrainCircuit className="w-5 h-5" />
          ) : (
            <Brain className="w-5 h-5" />
          )}
          <span className="text-sm font-medium">
            Memory {isMemoryEnabled ? 'ON' : 'OFF'}
          </span>
        </button>

        {/* 메모리 상태 표시 */}
        {isMemoryEnabled && conversationTurn > 0 && (
          <div className="flex items-center gap-2 text-sm text-glass-muted">
            <span className="px-2 py-1 bg-glass-subtle rounded">
              대화 {conversationTurn}턴
            </span>
            {lastFromCache && (
              <span className="px-2 py-1 bg-green-500/20 text-green-300 rounded text-xs">
                캐시
              </span>
            )}
          </div>
        )}
      </div>

      {/* 예시 검색어 */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        <span className="text-sm text-glass-muted">예시:</span>
        {EXAMPLE_QUERIES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => handleExampleClick(example)}
            className="text-sm accent-cyan hover:text-white hover:underline cursor-pointer transition-colors"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  )
}
