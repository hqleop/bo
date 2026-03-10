/** Types for tenders API (minimal shapes; extend as needed) */
export interface TenderListItem {
  id: number
  number?: string
  tour_number?: number
  name?: string
  stage?: string
  task_kind?: 'author' | 'approver'
  task_action?: string
  task_created_at?: string
  created_by?: number | null
  created_by_display?: string
  stage_label?: string
  conduct_type_label?: string
  branch_name?: string
  department_name?: string
  expense_article_name?: string
  category_name?: string
  cpv_label?: string
  decision_label?: string
  total_amount?: string | null
  economy_amount?: string | null
  profit_amount?: string | null
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
  status_updated_at?: string
  [key: string]: unknown
}

export interface TenderCriterion {
  id: number
  reference_criterion_id?: number | null
  name?: string
  type?: string
  tender_type?: 'procurement' | 'sales'
  is_required?: boolean
  [key: string]: unknown
}

export interface TenderAttribute {
  id: number
  name?: string
  type?: string
  tender_type?: 'procurement' | 'sales'
  is_required?: boolean
  options?: Record<string, unknown>
  [key: string]: unknown
}

export interface TenderConditionTemplate {
  id: number
  company: number
  name: string
  content: string
  created_by?: number | null
  created_at?: string
  updated_at?: string
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
  count: number | null
  page: number
  page_size: number
  total_pages: number | null
  next_cursor?: string | null
  has_more?: boolean
  companies: ParticipationCompanyOption[]
  cpv_tree?: unknown[]
  results: TenderDetail[]
}

export interface TenderActiveTasksResponse {
  count: number
  limit: number
  results: TenderListItem[]
}

export type TenderJournalStatus = 'active' | 'completed' | 'all'

export interface TenderJournalListResponse {
  count: number
  page: number
  page_size: number
  total_pages: number
  has_more?: boolean
  results: TenderListItem[]
}

export interface TenderApprovalRouteUser {
  id?: number | null
  full_name?: string
  short_name?: string
  status?: 'active' | 'approved' | 'waiting'
}

export interface TenderApprovalRouteNode {
  kind?: 'author' | 'role'
  label?: string
  order?: number
  approval_rule?: string
  users?: TenderApprovalRouteUser[]
}

export interface TenderApprovalRoutePayload {
  stage?: string
  has_approvers?: boolean
  status?: string
  can_author_submit?: boolean
  can_author_publish?: boolean
  can_approver_action?: boolean
  nodes?: TenderApprovalRouteNode[]
}

export interface DecisionMarketReferenceItem {
  position_id: number
  nomenclature_id: number
  market_price?: string | number | null
  source_tour_id?: number | null
  source_tour_number?: number | null
}

export interface DecisionMarketReferencePayload {
  mode_default?: 'first_tour' | 'current_tour'
  position_market?: DecisionMarketReferenceItem[]
}
