/**
 * 레이아웃 컴포넌트
 */

import { ReactNode } from 'react'
import Header from './Header'
import Footer from './Footer'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Animated Gradient Orbs for Glassmorphism backdrop */}
      <div className="glass-orb glass-orb-1" />
      <div className="glass-orb glass-orb-2" />
      <div className="glass-orb glass-orb-3" />
      <div className="glass-orb glass-orb-4" />

      <Header />
      <main className="flex-1 relative z-10">{children}</main>
      <Footer />
    </div>
  )
}
