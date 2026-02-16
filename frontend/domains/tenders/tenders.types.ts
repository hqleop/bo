/** Tender list item (procurement or sales) */
export interface TenderListItem {
  id: number
  number: number
  tour_number?: number
  name: string
  stage?: string
  stage_label?: string
  conduct_type?: string
  conduct_type_label?: string
  created_at?: string
  [key: string]: unknown
}

/** Tender detail (single tender) */
export interface TenderDetail extends TenderListItem {
  start_at?: string
  end_at?: string
  is_latest_tour?: boolean
  [key: string]: unknown
}

/** Tour option for selector */
export interface TenderTourOption {
  value: number
  label: string
}

/** Tender criteria item */
export interface TenderCriterion {
  id: number
  name: string
  type?: string
  [key: string]: unknown
}

/** Proposal (bid) on a tender */
export interface TenderProposal {
  id: number
  supplier_name?: string
  supplier_company?: { name?: string }
  position_values?: unknown[]
  [key: string]: unknown
}

/** Create tender payload */
export interface CreateTenderPayload {
  company: number
  name: string
  stage: string
  category?: number
  cpv_ids?: number[]
  expense_article?: number
  estimated_budget?: number
  branch?: number
  department?: number
  conduct_type: string
  publication_type: string
  currency: number
  general_terms?: string
}
