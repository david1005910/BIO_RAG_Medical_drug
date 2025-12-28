/**
 * 관리자 API 서비스
 */

import api from './api'

export interface SyncRequest {
  max_pages: number
  build_vectors: boolean
}

export interface SyncResponse {
  success: boolean
  message: string
  stats: {
    fetched?: number
    processed?: number
    saved?: number
    vectors_created?: number
    errors?: number
  }
}

export interface StatsResponse {
  drugs_count: number
  vectors_count: number
  status: string
}

/**
 * 데이터 동기화 실행
 */
export async function syncData(request: SyncRequest): Promise<SyncResponse> {
  const response = await api.post<SyncResponse>('/api/v1/admin/sync', request, {
    timeout: 300000, // 5분 타임아웃 (대량 데이터 처리)
  })
  return response.data
}

/**
 * 벡터 인덱스 재구축
 */
export async function rebuildVectors(): Promise<SyncResponse> {
  const response = await api.post<SyncResponse>('/api/v1/admin/rebuild-vectors', {}, {
    timeout: 300000,
  })
  return response.data
}

/**
 * 시스템 통계 조회
 */
export async function getStats(): Promise<StatsResponse> {
  const response = await api.get<StatsResponse>('/api/v1/admin/stats')
  return response.data
}
