/** Types for tenders API (minimal shapes; extend as needed) */
export interface TenderListItem {
  id: number
  number?: string
  tour_number?: number
  name?: string
  stage_label?: string
  conduct_type_label?: string
  created_at?: string
  [key: string]: unknown
}

export interface TenderDetail extends TenderListItem {
  [key: string]: unknown
}

export interface TenderProposal {
  id: number
  supplier_company?: { name?: string; edrpou?: string }
  supplier_name?: string
  [key: string]: unknown
}

export interface TenderCriterion {
  id: number
  name?: string
  type?: string
  [key: string]: unknown
}
