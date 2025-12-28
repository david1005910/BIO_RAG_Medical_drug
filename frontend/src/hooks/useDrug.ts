/**
 * 의약품 커스텀 훅
 */

import { useQuery } from '@tanstack/react-query'
import drugService from '../services/drugService'

export function useDrug(drugId: string) {
  return useQuery({
    queryKey: ['drug', drugId],
    queryFn: () => drugService.getDrugDetail(drugId),
    enabled: !!drugId,
  })
}

export function useDrugList(params: {
  page?: number
  page_size?: number
  search?: string
}) {
  return useQuery({
    queryKey: ['drugs', params],
    queryFn: () => drugService.getDrugs(params),
  })
}
