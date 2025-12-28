/**
 * 의약품 관련 타입 정의
 */

export interface DrugResult {
  id: string
  item_name: string
  entp_name: string | null
  efficacy: string | null
  use_method: string | null
  caution_info: string | null
  side_effects: string | null
  similarity: number
}

export interface DrugDetail {
  id: string
  item_name: string
  entp_name: string | null
  efficacy: string | null
  use_method: string | null
  warning_info: string | null
  caution_info: string | null
  interaction: string | null
  side_effects: string | null
  storage_method: string | null
  data_source: string
  created_at: string
  updated_at: string
}
