/**
 * 의약품 리스트 컴포넌트
 */

import { DrugResult } from '../../types/drug'
import DrugCard from './DrugCard'

interface DrugListProps {
  drugs: DrugResult[]
  emptyMessage?: string
}

export default function DrugList({
  drugs,
  emptyMessage = '검색 결과가 없습니다.',
}: DrugListProps) {
  if (drugs.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-glass-muted">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {drugs.map((drug) => (
        <DrugCard key={drug.id} drug={drug} />
      ))}
    </div>
  )
}
