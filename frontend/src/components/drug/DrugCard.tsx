/**
 * 의약품 카드 컴포넌트
 */

import { Link } from 'react-router-dom'
import { Pill, Building2, ChevronRight } from 'lucide-react'
import { DrugResult } from '../../types/drug'

interface DrugCardProps {
  drug: DrugResult
}

export default function DrugCard({ drug }: DrugCardProps) {
  const similarityPercent = Math.round(drug.similarity * 100)

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
          <p className="text-glass-muted text-sm line-clamp-2">
            {drug.efficacy || '효능 정보가 없습니다.'}
          </p>
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
