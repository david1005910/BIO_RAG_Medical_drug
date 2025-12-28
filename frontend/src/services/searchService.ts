/**
 * 검색 서비스
 */

import api from './api'
import { SearchRequest, SearchResponse } from '../types/api'

export const searchService = {
  /**
   * 증상 기반 의약품 검색
   */
  async search(request: SearchRequest): Promise<SearchResponse> {
    const response = await api.post<SearchResponse>('/api/v1/search', request)
    return response.data
  },
}

export default searchService
