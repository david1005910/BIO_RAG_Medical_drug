/**
 * 홈페이지 - 메인 검색 페이지
 */

import { Pill, Search, Sparkles, Shield } from 'lucide-react'
import SearchForm from '../components/search/SearchForm'

export default function HomePage() {
  return (
    <div className="min-h-[calc(100vh-180px)]">
      {/* 히어로 섹션 */}
      <section className="py-20 relative">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 icon-glass-accent rounded-2xl flex items-center justify-center glow-purple">
              <Pill className="w-12 h-12 text-white" />
            </div>
          </div>

          <h1 className="text-4xl md:text-5xl font-bold mb-4 gradient-text">
            AI 의약품 추천 시스템
          </h1>
          <p className="text-xl text-glass-muted mb-8">
            증상을 입력하면 AI가 적합한 의약품을 추천해 드립니다
          </p>

          {/* 검색 폼 */}
          <div className="glass-panel-strong p-6">
            <SearchForm variant="hero" />
          </div>
        </div>
      </section>

      {/* Glass divider */}
      <div className="glass-divider max-w-4xl mx-auto" />

      {/* 특징 섹션 */}
      <section className="py-16">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-center text-glass mb-12">
            주요 기능
          </h2>

          <div className="grid md:grid-cols-3 gap-8">
            {/* 기능 1 */}
            <div className="glass-card p-6">
              <div className="w-12 h-12 icon-glass rounded-lg flex items-center justify-center mb-4 glow-cyan">
                <Search className="w-6 h-6 accent-cyan" />
              </div>
              <h3 className="text-lg font-semibold text-glass mb-2">
                자연어 검색
              </h3>
              <p className="text-glass-muted">
                "두통이 심해요", "소화가 안돼요" 등 일상 언어로 증상을 설명하면
                관련 의약품을 찾아드립니다.
              </p>
            </div>

            {/* 기능 2 */}
            <div className="glass-card p-6">
              <div className="w-12 h-12 icon-glass rounded-lg flex items-center justify-center mb-4 glow-purple">
                <Sparkles className="w-6 h-6 accent-purple" />
              </div>
              <h3 className="text-lg font-semibold text-glass mb-2">
                AI 맞춤 설명
              </h3>
              <p className="text-glass-muted">
                복잡한 의학 용어를 AI가 쉽게 풀어서 설명해 드립니다.
                각 의약품의 효능과 주의사항을 한눈에 파악하세요.
              </p>
            </div>

            {/* 기능 3 */}
            <div className="glass-card p-6">
              <div className="w-12 h-12 icon-glass rounded-lg flex items-center justify-center mb-4 glow-pink">
                <Shield className="w-6 h-6 accent-pink" />
              </div>
              <h3 className="text-lg font-semibold text-glass mb-2">
                공인 데이터
              </h3>
              <p className="text-glass-muted">
                공공데이터포털(data.go.kr)의 공식 의약품 정보를 기반으로
                신뢰할 수 있는 정보를 제공합니다.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 사용 안내 */}
      <section className="py-16">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-center text-glass mb-8">
            이용 방법
          </h2>

          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1 flex items-center gap-4 glass-card p-4">
              <div className="w-10 h-10 flex items-center justify-center rounded-full font-bold flex-shrink-0 text-white icon-glass-accent glow-purple">
                1
              </div>
              <div>
                <h3 className="font-semibold text-glass">증상 입력</h3>
                <p className="text-sm text-glass-muted">
                  검색창에 현재 증상을 자연어로 입력하세요
                </p>
              </div>
            </div>

            <div className="flex-1 flex items-center gap-4 glass-card p-4">
              <div className="w-10 h-10 flex items-center justify-center rounded-full font-bold flex-shrink-0 text-white icon-glass-accent glow-cyan">
                2
              </div>
              <div>
                <h3 className="font-semibold text-glass">결과 확인</h3>
                <p className="text-sm text-glass-muted">
                  AI가 추천하는 의약품 목록을 확인하세요
                </p>
              </div>
            </div>

            <div className="flex-1 flex items-center gap-4 glass-card p-4">
              <div className="w-10 h-10 flex items-center justify-center rounded-full font-bold flex-shrink-0 text-white icon-glass-accent glow-pink">
                3
              </div>
              <div>
                <h3 className="font-semibold text-glass">상세 정보</h3>
                <p className="text-sm text-glass-muted">
                  의약품 상세 정보와 주의사항을 확인하세요
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
