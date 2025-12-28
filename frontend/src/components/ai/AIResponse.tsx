/**
 * AI 응답 컴포넌트
 */

import { Bot, Sparkles } from 'lucide-react'

interface AIResponseProps {
  response: string
  isLoading?: boolean
}

export default function AIResponse({ response, isLoading = false }: AIResponseProps) {
  if (isLoading) {
    return (
      <div className="glass-panel p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 icon-glass-accent rounded-full flex items-center justify-center glow-purple">
            <Bot className="w-6 h-6 text-white animate-pulse" />
          </div>
          <div>
            <h3 className="font-semibold text-glass">AI 추천</h3>
            <p className="text-sm accent-cyan">분석 중...</p>
          </div>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-white/20 rounded-full animate-pulse w-full"></div>
          <div className="h-4 bg-white/20 rounded-full animate-pulse w-3/4"></div>
          <div className="h-4 bg-white/20 rounded-full animate-pulse w-5/6"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="glass-panel p-6 animate-fade-in">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 icon-glass-accent rounded-full flex items-center justify-center glow-purple">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-glass">AI 추천</h3>
          <Sparkles className="w-4 h-4 accent-pink" />
        </div>
      </div>

      <div className="prose prose-sm max-w-none text-glass-muted">
        {response.split('\n').map((paragraph, index) => (
          <p key={index} className="mb-2 last:mb-0">
            {paragraph}
          </p>
        ))}
      </div>
    </div>
  )
}
