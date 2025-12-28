/**
 * 로딩 컴포넌트
 */

import { Loader2 } from 'lucide-react'

interface LoadingProps {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

export default function Loading({ message = '로딩 중...', size = 'md' }: LoadingProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }

  return (
    <div className="flex flex-col items-center justify-center p-8">
      <Loader2 className={`${sizeClasses[size]} accent-cyan animate-spin`} />
      {message && <p className="mt-3 text-glass-muted">{message}</p>}
    </div>
  )
}
