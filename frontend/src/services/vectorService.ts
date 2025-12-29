/**
 * 벡터 시각화 API 서비스
 */

import api from './api'

export interface VectorPoint {
  id: string
  name: string
  x: number
  y: number
  z: number
  similarity: number
  similarity_level: number
  color: string
}

export interface SimilarityLevel {
  level: number
  label: string
  range: string
  color: string
}

export interface VectorSpaceData {
  success: boolean
  query: string
  query_point: VectorPoint
  drug_points: VectorPoint[]
  similarity_levels: SimilarityLevel[]
}

/**
 * 벡터 공간 시각화 데이터 가져오기
 */
export async function getVectorSpace(query: string, topK: number = 20): Promise<VectorSpaceData> {
  const response = await api.get<VectorSpaceData>('/api/v1/vector-space', {
    params: { query, top_k: topK },
  })
  return response.data
}
