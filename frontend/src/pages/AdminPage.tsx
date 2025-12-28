/**
 * 관리자 페이지 - 데이터 동기화 및 시스템 관리
 */

import { useState, useEffect } from 'react'
import { RefreshCw, Database, Zap, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { syncData, rebuildVectors, getStats, type StatsResponse, type SyncResponse } from '../services/adminService'

export default function AdminPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [rebuilding, setRebuilding] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [syncPages, setSyncPages] = useState(10)
  const [lastSyncResult, setLastSyncResult] = useState<SyncResponse | null>(null)

  // 통계 조회
  const fetchStats = async () => {
    setLoading(true)
    try {
      const data = await getStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
      setMessage({ type: 'error', text: '통계 조회 실패' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  // 데이터 동기화
  const handleSync = async () => {
    setSyncing(true)
    setMessage(null)
    setLastSyncResult(null)

    try {
      const result = await syncData({
        max_pages: syncPages,
        build_vectors: true,
      })
      setLastSyncResult(result)
      setMessage({ type: 'success', text: result.message })
      fetchStats() // 통계 갱신
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || '동기화 중 오류가 발생했습니다'
      setMessage({ type: 'error', text: errorMsg })
    } finally {
      setSyncing(false)
    }
  }

  // 벡터 재구축
  const handleRebuildVectors = async () => {
    setRebuilding(true)
    setMessage(null)

    try {
      const result = await rebuildVectors()
      setMessage({ type: 'success', text: result.message })
      fetchStats()
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || '벡터 재구축 중 오류가 발생했습니다'
      setMessage({ type: 'error', text: errorMsg })
    } finally {
      setRebuilding(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">시스템 관리</h1>

      {/* 알림 메시지 */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* 시스템 통계 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">시스템 통계</h2>
          <button
            onClick={fetchStats}
            disabled={loading}
            className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {stats ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Database className="w-8 h-8 text-blue-600" />
                <div>
                  <p className="text-sm text-blue-600 font-medium">의약품 수</p>
                  <p className="text-2xl font-bold text-blue-900">{stats.drugs_count.toLocaleString()}</p>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Zap className="w-8 h-8 text-purple-600" />
                <div>
                  <p className="text-sm text-purple-600 font-medium">벡터 수</p>
                  <p className="text-2xl font-bold text-purple-900">{stats.vectors_count.toLocaleString()}</p>
                </div>
              </div>
            </div>

            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-sm text-green-600 font-medium">시스템 상태</p>
                  <p className="text-2xl font-bold text-green-900">{stats.status}</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-24 text-gray-500">
            {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : '통계를 불러올 수 없습니다'}
          </div>
        )}
      </div>

      {/* 데이터 동기화 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">데이터 동기화</h2>
        <p className="text-gray-600 mb-4">
          공공데이터포털(data.go.kr)에서 최신 의약품 정보를 가져와 데이터베이스에 저장합니다.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
          <div className="flex-1">
            <label htmlFor="syncPages" className="block text-sm font-medium text-gray-700 mb-1">
              동기화할 페이지 수 (1페이지 = 100개)
            </label>
            <input
              type="number"
              id="syncPages"
              min={1}
              max={100}
              value={syncPages}
              onChange={(e) => setSyncPages(Math.min(100, Math.max(1, parseInt(e.target.value) || 1)))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            <p className="text-sm text-gray-500 mt-1">
              예상 수집량: 약 {(syncPages * 100).toLocaleString()}개
            </p>
          </div>

          <button
            onClick={handleSync}
            disabled={syncing || rebuilding}
            className="px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2 whitespace-nowrap"
          >
            {syncing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                동기화 중...
              </>
            ) : (
              <>
                <RefreshCw className="w-5 h-5" />
                데이터 동기화
              </>
            )}
          </button>
        </div>

        {/* 동기화 결과 */}
        {lastSyncResult && lastSyncResult.stats && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium text-gray-900 mb-2">동기화 결과</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-500">수집:</span>{' '}
                <span className="font-medium">{lastSyncResult.stats.fetched?.toLocaleString()}개</span>
              </div>
              <div>
                <span className="text-gray-500">전처리:</span>{' '}
                <span className="font-medium">{lastSyncResult.stats.processed?.toLocaleString()}개</span>
              </div>
              <div>
                <span className="text-gray-500">저장:</span>{' '}
                <span className="font-medium">{lastSyncResult.stats.saved?.toLocaleString()}개</span>
              </div>
              <div>
                <span className="text-gray-500">벡터:</span>{' '}
                <span className="font-medium">{lastSyncResult.stats.vectors_created?.toLocaleString()}개</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 벡터 재구축 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">벡터 인덱스 재구축</h2>
        <p className="text-gray-600 mb-4">
          기존 의약품 데이터로 벡터 임베딩을 다시 생성합니다. 검색 품질 개선이 필요할 때 사용하세요.
        </p>

        <button
          onClick={handleRebuildVectors}
          disabled={syncing || rebuilding}
          className="px-6 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {rebuilding ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              재구축 중...
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              벡터 재구축
            </>
          )}
        </button>
      </div>
    </div>
  )
}
