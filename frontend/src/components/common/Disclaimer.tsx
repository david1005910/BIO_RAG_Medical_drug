/**
 * 면책 조항 컴포넌트
 */

import { AlertCircle } from 'lucide-react'

interface DisclaimerProps {
  text?: string
  variant?: 'warning' | 'info'
}

export default function Disclaimer({
  text = '이 정보는 참고용입니다. 실제 복약은 의사/약사와 상담하세요.',
  variant = 'warning',
}: DisclaimerProps) {
  const variants = {
    warning: {
      border: 'border-l-amber-400',
      icon: 'accent-warning',
      text: 'text-glass-muted',
    },
    info: {
      border: 'border-l-cyan-400',
      icon: 'accent-cyan',
      text: 'text-glass-muted',
    },
  }

  const style = variants[variant]

  return (
    <div className={`glass-card border-l-4 ${style.border} p-3 flex items-start gap-2`}>
      <AlertCircle className={`w-5 h-5 ${style.icon} flex-shrink-0 mt-0.5`} />
      <p className={`text-sm ${style.text}`}>{text}</p>
    </div>
  )
}
