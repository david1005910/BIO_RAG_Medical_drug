/**
 * 의약품 상세 페이지
 */

import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Pill,
  Building2,
  Activity,
  Clock,
  AlertTriangle,
  AlertCircle,
  Package,
  RefreshCw,
} from 'lucide-react'
import { useDrug } from '../hooks/useDrug'
import Loading from '../components/common/Loading'
import Disclaimer from '../components/common/Disclaimer'

export default function DrugDetailPage() {
  const { drugId } = useParams<{ drugId: string }>()
  const { data: drug, isLoading, error } = useDrug(drugId || '')

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Loading message="의약품 정보를 불러오는 중..." />
      </div>
    )
  }

  if (error || !drug) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            의약품을 찾을 수 없습니다
          </h2>
          <p className="text-gray-600 mb-4">
            요청하신 의약품 정보가 존재하지 않습니다.
          </p>
          <Link to="/" className="btn-primary inline-block">
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* 뒤로가기 */}
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-primary-600 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>뒤로가기</span>
      </Link>

      {/* 헤더 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center flex-shrink-0">
            <Pill className="w-8 h-8 text-primary-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {drug.item_name}
            </h1>
            <div className="flex flex-wrap gap-4 text-sm text-gray-600">
              <span className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {drug.entp_name || '정보 없음'}
              </span>
              <span className="flex items-center gap-1">
                <Package className="w-4 h-4" />
                품목코드: {drug.id}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 면책 조항 */}
      <div className="mb-6">
        <Disclaimer />
      </div>

      {/* 상세 정보 */}
      <div className="space-y-6">
        {/* 효능효과 */}
        {drug.efficacy && (
          <InfoSection
            icon={<Activity className="w-5 h-5 text-green-600" />}
            title="효능효과"
            content={drug.efficacy}
            bgColor="bg-green-50"
            borderColor="border-green-100"
          />
        )}

        {/* 용법용량 */}
        {drug.use_method && (
          <InfoSection
            icon={<Clock className="w-5 h-5 text-blue-600" />}
            title="용법용량"
            content={drug.use_method}
            bgColor="bg-blue-50"
            borderColor="border-blue-100"
          />
        )}

        {/* 경고 */}
        {drug.warning_info && (
          <InfoSection
            icon={<AlertTriangle className="w-5 h-5 text-red-600" />}
            title="경고"
            content={drug.warning_info}
            bgColor="bg-red-50"
            borderColor="border-red-100"
          />
        )}

        {/* 주의사항 */}
        {drug.caution_info && (
          <InfoSection
            icon={<AlertCircle className="w-5 h-5 text-yellow-600" />}
            title="주의사항"
            content={drug.caution_info}
            bgColor="bg-yellow-50"
            borderColor="border-yellow-100"
          />
        )}

        {/* 상호작용 */}
        {drug.interaction && (
          <InfoSection
            icon={<RefreshCw className="w-5 h-5 text-purple-600" />}
            title="상호작용"
            content={drug.interaction}
            bgColor="bg-purple-50"
            borderColor="border-purple-100"
          />
        )}

        {/* 부작용 */}
        {drug.side_effects && (
          <InfoSection
            icon={<AlertTriangle className="w-5 h-5 text-orange-600" />}
            title="부작용"
            content={drug.side_effects}
            bgColor="bg-orange-50"
            borderColor="border-orange-100"
          />
        )}

        {/* 보관법 */}
        {drug.storage_method && (
          <InfoSection
            icon={<Package className="w-5 h-5 text-gray-600" />}
            title="보관법"
            content={drug.storage_method}
            bgColor="bg-gray-50"
            borderColor="border-gray-100"
          />
        )}
      </div>

      {/* 데이터 출처 */}
      <div className="mt-8 pt-6 border-t border-gray-200 text-sm text-gray-500">
        <p>데이터 출처: {drug.data_source}</p>
        <p>마지막 업데이트: {new Date(drug.updated_at).toLocaleDateString('ko-KR')}</p>
      </div>
    </div>
  )
}

interface InfoSectionProps {
  icon: React.ReactNode
  title: string
  content: string
  bgColor: string
  borderColor: string
}

function InfoSection({ icon, title, content, bgColor, borderColor }: InfoSectionProps) {
  return (
    <div className={`${bgColor} ${borderColor} border rounded-lg p-5`}>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h2 className="font-semibold text-gray-900">{title}</h2>
      </div>
      <div className="text-gray-700 whitespace-pre-line">{content}</div>
    </div>
  )
}
