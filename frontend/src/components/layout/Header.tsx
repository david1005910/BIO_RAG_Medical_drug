/**
 * 헤더 컴포넌트
 */

import { Link } from 'react-router-dom'
import { Pill, Settings } from 'lucide-react'

export default function Header() {
  return (
    <header className="glass-header sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-10 h-10 icon-glass-accent flex items-center justify-center glow-purple">
              <Pill className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-glass">의약품 추천</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            <Link to="/" className="text-glass-muted hover:text-white transition-colors">
              홈
            </Link>
            <Link to="/admin" className="text-glass-muted hover:text-white transition-colors flex items-center gap-1">
              <Settings className="w-4 h-4" />
              관리
            </Link>
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-glass-muted hover:text-white transition-colors"
            >
              API 문서
            </a>
          </nav>
        </div>
      </div>
    </header>
  )
}
