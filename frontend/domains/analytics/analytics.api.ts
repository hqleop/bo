import type { RequestFn } from '~/shared/api/apiClient'
import type {
  AnalyticsDashboardPayload,
  AnalyticsFilters,
  AnalyticsMode,
} from './analytics.types'

function normalizeIds(ids: number[] | undefined): number[] {
  return Array.from(
    new Set(
      (ids ?? [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0)
    )
  )
}

export async function getAnalyticsDashboard(
  request: RequestFn,
  mode: AnalyticsMode,
  filters?: AnalyticsFilters
) {
  const query: Record<string, string> = { mode }

  if (filters?.companyId && Number(filters.companyId) > 0) {
    query.company_id = String(Math.trunc(Number(filters.companyId)))
  }
  if (filters?.dateField && ['start_at', 'end_at'].includes(filters.dateField)) {
    query.date_field = filters.dateField
  }
  const dateFrom = String(filters?.dateFrom ?? '').trim()
  if (dateFrom.length > 0) query.date_from = dateFrom
  const dateTo = String(filters?.dateTo ?? '').trim()
  if (dateTo.length > 0) query.date_to = dateTo

  if (filters?.tenderType && ['all', 'purchase', 'sales'].includes(filters.tenderType)) {
    query.tender_type = filters.tenderType
  }
  if (filters?.status && ['all', 'active', 'completed'].includes(filters.status)) {
    query.status = filters.status
  }

  const branchIds = normalizeIds(filters?.branchIds)
  if (branchIds.length > 0) query.branch_ids = branchIds.join(',')
  const departmentIds = normalizeIds(filters?.departmentIds)
  if (departmentIds.length > 0) query.department_ids = departmentIds.join(',')
  const expenseIds = normalizeIds(filters?.expenseIds)
  if (expenseIds.length > 0) query.expense_ids = expenseIds.join(',')
  const categoryIds = normalizeIds(filters?.categoryIds)
  if (categoryIds.length > 0) query.category_ids = categoryIds.join(',')
  const userIds = normalizeIds(filters?.userIds)
  if (userIds.length > 0) query.user_ids = userIds.join(',')

  return request<AnalyticsDashboardPayload>('/analytics/dashboard/', {
    query,
    cacheTtlMs: 30_000,
  })
}
