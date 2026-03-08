import type { RequestFn } from '~/shared/api/apiClient'
import type {
  ParticipationListResponse,
  TenderDetail,
  DecisionMarketReferencePayload,
  TenderJournalListResponse,
  TenderListItem,
  TenderProposal,
  TenderCriterion,
  TenderAttribute,
  TenderFile,
  TenderApprovalRoutePayload
} from './tenders.types'

const PROCUREMENT_PREFIX = '/procurement-tenders'
const SALES_PREFIX = '/sales-tenders'

function listEndpoint(isSales: boolean) {
  return isSales ? `${SALES_PREFIX}/` : `${PROCUREMENT_PREFIX}/`
}

function detailEndpoint(isSales: boolean, id: number) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return `${prefix}/${id}/`
}

export async function getTenderList(request: RequestFn, isSales: boolean) {
  return request<TenderListItem[]>(listEndpoint(isSales))
}

export async function getTenderJournalList(
  request: RequestFn,
  isSales: boolean,
  filters?: {
    page?: number
    pageSize?: number
    search?: string
    status?: 'active' | 'completed' | 'all'
    authorId?: number | null
    branchIds?: number[]
    departmentIds?: number[]
    expenseIds?: number[]
    conductType?: 'all' | 'registration' | 'rfx' | 'online_auction'
    stage?: string
  }
) {
  const query: Record<string, string> = {
    page: String(filters?.page ?? 1),
    page_size: String(filters?.pageSize ?? 20),
    status: String(filters?.status ?? 'active'),
  }

  const normalizedSearch = String(filters?.search || '').trim()
  if (normalizedSearch) query.search = normalizedSearch
  if (filters?.authorId && Number(filters.authorId) > 0) {
    query.author_id = String(Math.trunc(Number(filters.authorId)))
  }

  const branchIds = Array.from(
    new Set((filters?.branchIds ?? []).map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0))
  )
  if (branchIds.length > 0) query.branch_ids = branchIds.join(',')

  const departmentIds = Array.from(
    new Set((filters?.departmentIds ?? []).map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0))
  )
  if (departmentIds.length > 0) query.department_ids = departmentIds.join(',')

  const expenseIds = Array.from(
    new Set((filters?.expenseIds ?? []).map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0))
  )
  if (expenseIds.length > 0) query.expense_ids = expenseIds.join(',')

  if (
    filters?.conductType &&
    filters.conductType !== 'all' &&
    ['registration', 'rfx', 'online_auction'].includes(filters.conductType)
  ) {
    query.conduct_type = filters.conductType
  }

  const stage = String(filters?.stage || '').trim()
  if (stage && stage !== 'all') query.stage = stage

  return request<TenderJournalListResponse>(listEndpoint(isSales), { query })
}

export async function getTenderActiveTasks(
  request: RequestFn,
  isSales: boolean,
  options?: { limit?: number; skipLoader?: boolean }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  const params = new URLSearchParams()
  if (options?.limit && Number.isFinite(options.limit) && options.limit > 0) {
    params.set("limit", String(Math.trunc(options.limit)))
  }
  const query = params.toString()
  return request<{ count: number; limit: number; results: TenderListItem[] }>(
    `${prefix}/active-tasks/${query ? `?${query}` : ""}`,
    {
      skipLoader: options?.skipLoader,
      cacheTtlMs: 30_000,
    }
  )
}

export async function getTenderActiveTasksCount(
  request: RequestFn,
  isSales: boolean,
  options?: { skipLoader?: boolean }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<{ count: number }>(`${prefix}/active-tasks/?count_only=true`, {
    skipLoader: options?.skipLoader,
    cacheTtlMs: 15_000,
  })
}

export type ParticipationTab = 'active' | 'processing' | 'completed' | 'journal'

export async function getTendersForParticipation(
  request: RequestFn,
  isSales: boolean,
  tab: ParticipationTab,
  filters?: {
    page?: number
    cursor?: string | null
    cursorMode?: boolean
    companyId?: number | null
    cpvIds?: number[]
    receptionStarted?: boolean
    conductType?: 'all' | 'rfx' | 'online_auction'
    tenderNumber?: string
    submittedOnly?: boolean
    participationResult?: 'participation' | 'win'
  }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  const params = new URLSearchParams()
  params.set('tab', tab)
  params.set('page', String(filters?.page ?? 1))
  if (filters?.cursorMode) params.set('cursor_mode', 'true')
  if (filters?.cursor?.trim()) params.set('cursor', filters.cursor.trim())
  if (filters?.companyId) params.set('company_id', String(filters.companyId))
  if (filters?.cpvIds?.length) params.set('cpv_ids', filters.cpvIds.join(','))
  if (filters?.receptionStarted && tab === 'active') params.set('reception_started', 'true')
  if (filters?.conductType && filters.conductType !== 'all') params.set('conduct_type', filters.conductType)
  if (filters?.tenderNumber?.trim()) params.set('tender_number', filters.tenderNumber.trim())
  if (filters?.submittedOnly) params.set('submitted_only', 'true')
  if (filters?.participationResult) params.set('participation_result', filters.participationResult)
  return request<ParticipationListResponse>(`${prefix}/for-participation/?${params.toString()}`)
}

export async function confirmParticipation(
  request: RequestFn,
  tenderId: number,
  isSales: boolean
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderProposal>(`${prefix}/${tenderId}/confirm-participation/`, {
    method: 'POST'
  })
}

export async function getTender(request: RequestFn, id: number, isSales: boolean) {
  return request<TenderDetail>(detailEndpoint(isSales, id))
}

export async function patchTender(
  request: RequestFn,
  id: number,
  isSales: boolean,
  body: Record<string, unknown>
) {
  return request<TenderDetail>(detailEndpoint(isSales, id), { method: 'PATCH', body })
}

export async function createTender(
  request: RequestFn,
  isSales: boolean,
  body: Record<string, unknown>
) {
  return request<TenderDetail>(listEndpoint(isSales), { method: 'POST', body })
}

export async function getTenderTours(request: RequestFn, id: number, isSales: boolean) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<unknown[]>(`${prefix}/${id}/tours/`)
}

export async function getDecisionMarketReference(
  request: RequestFn,
  id: number,
  isSales: boolean,
  options?: { skipLoader?: boolean }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<DecisionMarketReferencePayload>(
    `${prefix}/${id}/decision-market-reference/`,
    {
      skipLoader: options?.skipLoader,
      cacheTtlMs: 15_000,
    }
  )
}

export async function getTenderProposals(
  request: RequestFn,
  id: number,
  isSales: boolean,
  options?: {
    skipLoader?: boolean
    proposalIds?: number[]
    statusOnly?: boolean
    updatedSince?: string
  }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  const normalizedProposalIds = Array.from(
    new Set(
      (options?.proposalIds ?? [])
        .map((proposalId) => Number(proposalId))
        .filter((proposalId) => Number.isInteger(proposalId) && proposalId > 0)
    )
  )
  const params = new URLSearchParams()
  if (normalizedProposalIds.length > 0) {
    params.set('ids', normalizedProposalIds.join(','))
  }
  if (options?.statusOnly) {
    params.set('view', 'status')
  }
  const updatedSince = String(options?.updatedSince || '').trim()
  if (updatedSince.length > 0) {
    params.set('updated_since', updatedSince)
  }
  let endpoint = `${prefix}/${id}/proposals/`
  if (params.size > 0) {
    endpoint = `${endpoint}?${params.toString()}`
  }
  return request<TenderProposal[]>(endpoint, {
    skipLoader: options?.skipLoader
  })
}

export async function getTenderProposalDetail(
  request: RequestFn,
  id: number,
  proposalId: number,
  isSales: boolean,
  options?: { skipLoader?: boolean }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderProposal>(`${prefix}/${id}/proposals/${proposalId}/`, {
    skipLoader: options?.skipLoader
  })
}

export async function getTenderFiles(request: RequestFn, id: number, isSales: boolean) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderFile[]>(`${prefix}/${id}/files/`)
}

export async function uploadTenderFile(
  request: RequestFn,
  id: number,
  isSales: boolean,
  form: FormData
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderFile>(`${prefix}/${id}/files/upload/`, { method: 'POST', body: form })
}

export async function deleteTenderFile(
  request: RequestFn,
  id: number,
  isSales: boolean,
  fileId: number
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<unknown>(`${prefix}/${id}/files/${fileId}/`, { method: 'DELETE' })
}

export async function patchTenderFile(
  request: RequestFn,
  id: number,
  isSales: boolean,
  fileId: number,
  body: { visible_to_participants: boolean }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderFile>(`${prefix}/${id}/files/${fileId}/`, { method: 'PATCH', body })
}

export async function fixTenderDecision(
  request: RequestFn,
  id: number,
  isSales: boolean,
  body?: Record<string, unknown>
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<{ id: number; stage?: string }>(`${prefix}/${id}/fix-decision/`, {
    method: 'POST',
    body: body ?? {}
  })
}

export async function getTenderCriteria(request: RequestFn) {
  return request<TenderCriterion[]>('/tender-criteria/')
}

export type TenderCriteriaType = 'procurement' | 'sales'

export async function getTenderCriteriaByType(request: RequestFn, tenderType: TenderCriteriaType) {
  return request<TenderCriterion[]>(`/tender-criteria/?tender_type=${tenderType}`)
}

export async function createTenderCriterion(
  request: RequestFn,
  body: {
    company: number
    name: string
    type: string
    tender_type: TenderCriteriaType
    application?: string
    is_required?: boolean
    options?: Record<string, unknown>
  }
) {
  return request<TenderCriterion>('/tender-criteria/', {
    method: 'POST',
    body: body as unknown as Record<string, unknown>
  })
}

export type TenderAttributesType = 'procurement' | 'sales'

export async function getTenderAttributesByType(request: RequestFn, tenderType: TenderAttributesType) {
  return request<TenderAttribute[]>(`/tender-attributes/?tender_type=${tenderType}`)
}

export async function createTenderAttribute(
  request: RequestFn,
  body: {
    company: number
    name: string
    type: string
    tender_type: TenderAttributesType
    category?: number | null
    is_required?: boolean
    options?: Record<string, unknown>
  }
) {
  return request<TenderAttribute>('/tender-attributes/', {
    method: 'POST',
    body: body as unknown as Record<string, unknown>
  })
}

export async function getUnits(request: RequestFn) {
  return request<{ id: number; name_ua?: string; short_name_ua?: string; name_en?: string }[]>('/units/')
}

export async function createNomenclature(
  request: RequestFn,
  body: { company: number; name: string; unit: number; cpv_ids?: number[] }
) {
  return request<{ id: number; name?: string; unit_name?: string }>('/nomenclatures/', {
    method: 'POST',
    body: body as unknown as Record<string, unknown>
  })
}

// Reference data used by tender pages
export async function getCategories(request: RequestFn) {
  return request<unknown[]>('/categories/', { cacheTtlMs: 5 * 60_000 })
}

export async function getExpenses(request: RequestFn) {
  return request<unknown[]>('/expenses/?assigned_only=1', { cacheTtlMs: 5 * 60_000 })
}

export async function getBranches(request: RequestFn) {
  return request<unknown[]>('/branches/?assigned_only=1', { cacheTtlMs: 5 * 60_000 })
}

export async function getCurrencies(request: RequestFn) {
  return request<unknown[]>('/currencies/', { cacheTtlMs: 5 * 60_000 })
}

export async function getDepartments(request: RequestFn, branchId: number) {
  return request<unknown[]>(`/departments/?branch_id=${branchId}&assigned_only=1`, {
    cacheTtlMs: 2 * 60_000,
  })
}

export async function getNomenclaturesByCpv(request: RequestFn, cpvId: number) {
  return request<unknown[]>(`/nomenclatures/?cpv_id=${cpvId}`)
}

export async function getNomenclaturesByCpvs(request: RequestFn, cpvIds: number[]) {
  const normalized = Array.from(
    new Set(
      (cpvIds || [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0)
    )
  )
  if (!normalized.length) return Promise.resolve({ data: [] as unknown[], error: null })
  return request<unknown[]>(`/nomenclatures/?cpv_ids=${normalized.join(",")}`)
}

export async function getNomenclaturesByCategory(request: RequestFn, categoryId: number) {
  return request<unknown[]>(`/nomenclatures/?category_id=${categoryId}`)
}

export async function getCategory(request: RequestFn, categoryId: number) {
  return request<unknown>(`/categories/${categoryId}/`, { cacheTtlMs: 5 * 60_000 })
}

export async function getCpvChildren(
  request: RequestFn,
  parentLevelCode?: string,
  search?: string
) {
  const params = new URLSearchParams()
  if (parentLevelCode) params.set('parent_level_code', parentLevelCode)
  if (search?.trim()) params.set('search', search.trim())
  const query = params.toString() ? `?${params.toString()}` : ''
  return request<unknown[]>(`/cpv/children/${query}`.replace(/\/\?/, '?'))
}

export async function getCpvWithCompanies(request: RequestFn) {
  return request<{ id: number; cpv_code: string; name_ua: string; label: string }[]>('/cpv/with-companies/')
}

export async function addProposal(
  request: RequestFn,
  tenderId: number,
  isSales: boolean,
  body: Record<string, unknown>
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<unknown>(`${prefix}/${tenderId}/proposals/add/`, { method: 'POST', body })
}

export async function getProposalPositionValues(
  request: RequestFn,
  tenderId: number,
  proposalId: number,
  isSales: boolean
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<unknown[]>(`${prefix}/${tenderId}/proposals/${proposalId}/position-values/`)
}

export async function patchProposalPositionValues(
  request: RequestFn,
  tenderId: number,
  proposalId: number,
  isSales: boolean,
  body: { position_values: unknown[] },
  options?: { skipLoader?: boolean }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<unknown>(`${prefix}/${tenderId}/proposals/${proposalId}/position-values/`, {
    method: 'PATCH',
    body,
    skipLoader: options?.skipLoader
  })
}

export async function submitProposal(request: RequestFn, tenderId: number, isSales: boolean) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderProposal>(`${prefix}/${tenderId}/submit-proposal/`, { method: 'POST' })
}

export async function withdrawProposal(request: RequestFn, tenderId: number, isSales: boolean) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderProposal>(`${prefix}/${tenderId}/withdraw-proposal/`, { method: 'POST' })
}

export async function getTenderApprovalJournal(
  request: RequestFn,
  tenderId: number,
  isSales: boolean
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<unknown[]>(`${prefix}/${tenderId}/approval-journal/`)
}

export async function getTenderApprovalRoute(
  request: RequestFn,
  tenderId: number,
  isSales: boolean
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderApprovalRoutePayload>(`${prefix}/${tenderId}/approval-route/`)
}

export async function submitTenderApprovalSubmit(
  request: RequestFn,
  tenderId: number,
  isSales: boolean,
  body?: { comment?: string }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<{ id: number; stage?: string; route?: TenderApprovalRoutePayload }>(
    `${prefix}/${tenderId}/approval-submit/`,
    {
      method: "POST",
      body: (body ?? {}) as unknown as Record<string, unknown>,
    }
  )
}

export async function submitTenderApprovalAction(
  request: RequestFn,
  tenderId: number,
  isSales: boolean,
  body: { action: "approved" | "rejected"; comment?: string }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<{ id: number; stage?: string; route?: TenderApprovalRoutePayload }>(`${prefix}/${tenderId}/approval-action/`, {
    method: "POST",
    body: body as unknown as Record<string, unknown>,
  })
}

export async function getAvailableApprovalModels(
  request: RequestFn,
  params: {
    companyId: number
    application: 'procurement' | 'sales'
    categoryId?: number | null
    estimatedBudget?: number | null
  }
) {
  const q = new URLSearchParams()
  q.set("company_id", String(params.companyId))
  q.set("application", params.application)
  if (params.categoryId) q.set("category_id", String(params.categoryId))
  if (params.estimatedBudget != null && Number.isFinite(Number(params.estimatedBudget))) {
    q.set("estimated_budget", String(params.estimatedBudget))
  }
  return request<unknown[]>(`/approval-models/available-for-tender/?${q.toString()}`, {
    cacheTtlMs: 30_000,
  })
}
