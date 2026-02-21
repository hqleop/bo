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
  /** Чи поточна компанія вже має пропозицію (підтвердила участь). */
  current_user_has_proposal?: boolean
  [key: string]: unknown
}

export interface TenderProposal {
  id: number
  supplier_company?: { name?: string; edrpou?: string }
  supplier_company_id?: number
  supplier_name?: string
  submitted_at?: string | null
  [key: string]: unknown
}

export interface TenderCriterion {
  id: number
  name?: string
  type?: string
  [key: string]: unknown
}

export interface TenderFile {
  id: number
  name?: string
  file_url?: string
  uploaded_at?: string
  uploaded_by?: number | null
  uploaded_by_display?: string
  visible_to_participants?: boolean
}

export interface ParticipationCompanyOption {
  id: number
  name: string
  edrpou?: string
  label: string
}

export interface ParticipationListResponse {
  count: number
  page: number
  page_size: number
  total_pages: number
  companies: ParticipationCompanyOption[]
  cpv_tree?: unknown[]
  results: TenderDetail[]
}
