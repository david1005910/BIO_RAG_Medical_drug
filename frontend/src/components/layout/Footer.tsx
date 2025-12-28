/**
 * 푸터 컴포넌트
 */

import { AlertTriangle } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="glass-footer relative z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 면책 조항 */}
        <div className="glass-card p-4 mb-6 border-l-4 border-l-amber-400">
          <div className="flex gap-3">
            <AlertTriangle className="w-5 h-5 accent-warning flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium accent-warning mb-1">면책 조항</p>
              <p className="text-glass-muted">
                이 서비스는 <strong className="text-white">참고 정보 제공</strong>만을 목적으로 합니다.
                의료 진단이나 처방을 대체하지 않으며, 실제 복약은 반드시 의사/약사와 상담 후 결정하세요.
                응급 상황에서는 즉시 119에 연락하거나 병원을 방문하세요.
              </p>
            </div>
          </div>
        </div>

        {/* Glass divider */}
        <div className="glass-divider mb-6" />

        {/* 저작권 */}
        <div className="flex flex-col md:flex-row justify-between items-center text-sm text-glass-muted">
          <p>데이터 출처: 공공데이터포털 (data.go.kr) e약은요 API</p>
          <p className="mt-2 md:mt-0">
            &copy; {new Date().getFullYear()} Medical RAG System
          </p>
        </div>
      </div>
    </footer>
  )
}
