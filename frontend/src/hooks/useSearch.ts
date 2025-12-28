/**
 * 검색 커스텀 훅
 */

import { useMutation } from '@tanstack/react-query'
import searchService from '../services/searchService'
import { SearchRequest, SearchResponse } from '../types/api'

export function useSearch() {
  return useMutation<SearchResponse, Error, SearchRequest>({
    mutationFn: (request) => searchService.search(request),
  })
}

export default useSearch
