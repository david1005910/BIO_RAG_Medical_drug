/**
 * 의약품 카드 컴포넌트
 */

import { Link } from 'react-router-dom'
import { Pill, Building2, ChevronRight, BarChart3 } from 'lucide-react'
import { DrugResult } from '../../types/drug'

interface DrugCardProps {
  drug: DrugResult
}

// 스코어 텍스트 컴포넌트 (막대그래프 제거)
function ScoreText({
  label,
  score,
  color,
  scale,
}: {
  label: string
  score: number | null
  color: string
  scale: string
}) {
  if (score === null || score === undefined) return null

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-glass-muted">{label}</span>
      <span style={{ color }} className="font-medium">
        {score.toFixed(2)}
      </span>
      <span className="text-glass-subtle text-[10px]">({scale})</span>
    </div>
  )
}

export default function DrugCard({ drug }: DrugCardProps) {
  const similarityPercent = Math.round(drug.similarity * 100)
  const hasScores = drug.dense_score !== null || drug.bm25_score !== null || drug.hybrid_score !== null

  const getSimilarityStyle = (percent: number) => {
    if (percent >= 80) return 'badge-high'
    if (percent >= 60) return 'badge-medium'
    return 'badge-low'
  }

  return (
    <Link
      to={`/drugs/${drug.id}`}
      className="block glass-card p-4 animate-fade-in"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* 제품명 */}
          <div className="flex items-center gap-2 mb-2">
            <Pill className="w-5 h-5 accent-pink flex-shrink-0" />
            <h3 className="font-semibold text-lg text-glass truncate">
              {drug.item_name}
            </h3>
          </div>

          {/* 제조사 */}
          <div className="flex items-center gap-1 text-sm text-glass-muted mb-3">
            <Building2 className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{drug.entp_name || '정보 없음'}</span>
          </div>

          {/* 효능효과 */}
          <p className="text-glass-muted text-sm line-clamp-2 mb-3">
            {drug.efficacy || '효능 정보가 없습니다.'}
          </p>

          {/* 검색 점수 표시 */}
          {hasScores && (
            <div className="pt-2 border-t border-white/10">
              <div className="flex items-center gap-1 text-xs text-glass-muted mb-2">
                <BarChart3 className="w-3 h-3" />
                <span>검색 점수</span>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                <ScoreText
                  label="Dense"
                  score={drug.dense_score}
                  color="#3b82f6"
                  scale="0-1"
                />
                <ScoreText
                  label="SPLADE"
                  score={drug.bm25_score !== null ? drug.bm25_score * 30 : null}
                  color="#22c55e"
                  scale="0-30"
                />
                <ScoreText
                  label="Hybrid"
                  score={drug.hybrid_score}
                  color="#a855f7"
                  scale="0-1"
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col items-end gap-2 ml-4 flex-shrink-0">
          {/* 유사도 */}
          <span
            className={`px-3 py-1 rounded-full text-sm ${getSimilarityStyle(similarityPercent)}`}
          >
            {similarityPercent}% 일치
          </span>
          <ChevronRight className="w-5 h-5 text-glass-subtle" />
        </div>
      </div>
    </Link>
  )
}
