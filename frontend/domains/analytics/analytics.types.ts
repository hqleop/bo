export type AnalyticsMode =
  | 'personal-organizer'
  | 'personal-participant'
  | 'summary-tenders'
  | 'summary-participation'

export type AnalyticsDateField = 'start_at' | 'end_at'
export type AnalyticsTenderType = 'all' | 'purchase' | 'sales'
export type AnalyticsStatus = 'all' | 'active' | 'completed'

export interface AnalyticsFilters {
  companyId?: number | null
  dateField?: AnalyticsDateField
  dateFrom?: string
  dateTo?: string
  tenderType?: AnalyticsTenderType
  status?: AnalyticsStatus
  branchIds?: number[]
  departmentIds?: number[]
  expenseIds?: number[]
  categoryIds?: number[]
  userIds?: number[]
}

export interface AnalyticsKpi {
  key: string
  label: string
  value: number
}

export interface AnalyticsDistributionItem {
  key: string
  label: string
  value: number
}

export interface AnalyticsMonthlySeriesItem {
  month: string
  tenders_total?: number
  tenders_completed?: number
  submitted_proposals?: number
  participations_total?: number
  wins_total?: number
}

export interface AnalyticsTopItem {
  user_id?: number
  company_id?: number
  label: string
  value: number
}

export interface AnalyticsDashboardPayload {
  mode: AnalyticsMode
  generated_at: string
  kpis: AnalyticsKpi[]
  monthly_series: AnalyticsMonthlySeriesItem[]
  distributions: {
    stage: AnalyticsDistributionItem[]
    tender_type: AnalyticsDistributionItem[]
    result: AnalyticsDistributionItem[]
  }
  top_users?: AnalyticsTopItem[]
  top_companies?: AnalyticsTopItem[]
}
