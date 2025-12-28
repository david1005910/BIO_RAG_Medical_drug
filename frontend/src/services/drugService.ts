/**
 * 의약품 서비스
 */

import api from './api'
import { DrugDetail } from '../types/drug'
import { PaginatedResponse } from '../types/api'

export const drugService = {
  /**
   * 의약품 상세 정보 조회
   */
  async getDrugDetail(drugId: string): Promise<DrugDetail> {
    const response = await api.get<DrugDetail>(`/api/v1/drugs/${drugId}`)
    return response.data
  },

  /**
   * 의약품 목록 조회
   */
  async getDrugs(params: {
    page?: number
    page_size?: number
    search?: string
  }): Promise<PaginatedResponse<DrugDetail>> {
    const response = await api.get<PaginatedResponse<DrugDetail>>('/api/v1/drugs', {
      params,
    })
    return response.data
  },
}

export default drugService
