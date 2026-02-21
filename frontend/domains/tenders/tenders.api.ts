import type { RequestFn } from '~/shared/api/apiClient'
import type {
  ParticipationListResponse,
  TenderDetail,
  TenderListItem,
  TenderProposal,
  TenderCriterion,
  TenderFile
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

export type ParticipationTab = 'active' | 'processing' | 'completed'

export async function getTendersForParticipation(
  request: RequestFn,
  isSales: boolean,
  tab: ParticipationTab,
  filters?: {
    page?: number
    companyId?: number | null
    cpvIds?: number[]
    receptionStarted?: boolean
    conductType?: 'all' | 'rfx' | 'online_auction'
  }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  const params = new URLSearchParams()
  params.set('tab', tab)
  params.set('page', String(filters?.page ?? 1))
  if (filters?.companyId) params.set('company_id', String(filters.companyId))
  if (filters?.cpvIds?.length) params.set('cpv_ids', filters.cpvIds.join(','))
  if (filters?.receptionStarted && tab === 'active') params.set('reception_started', 'true')
  if (filters?.conductType && filters.conductType !== 'all') params.set('conduct_type', filters.conductType)
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

export async function getTenderProposals(request: RequestFn, id: number, isSales: boolean) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<TenderProposal[]>(`${prefix}/${id}/proposals/`)
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

export async function createTenderCriterion(
  request: RequestFn,
  body: { company: number; name: string; type: string; application?: string; options?: Record<string, unknown> }
) {
  return request<TenderCriterion>('/tender-criteria/', {
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
  return request<unknown[]>('/categories/')
}

export async function getExpenses(request: RequestFn) {
  return request<unknown[]>('/expenses/')
}

export async function getBranches(request: RequestFn) {
  return request<unknown[]>('/branches/')
}

export async function getCurrencies(request: RequestFn) {
  return request<unknown[]>('/currencies/')
}

export async function getDepartments(request: RequestFn, branchId: number) {
  return request<unknown[]>(`/departments/?branch_id=${branchId}`)
}

export async function getNomenclaturesByCpv(request: RequestFn, cpvId: number) {
  return request<unknown[]>(`/nomenclatures/?cpv_id=${cpvId}`)
}

export async function getNomenclaturesByCategory(request: RequestFn, categoryId: number) {
  return request<unknown[]>(`/nomenclatures/?category_id=${categoryId}`)
}

export async function getCategory(request: RequestFn, categoryId: number) {
  return request<unknown>(`/categories/${categoryId}/`)
}

export async function getCpvChildren(request: RequestFn, parentLevelCode?: string) {
  const query = parentLevelCode
    ? `?parent_level_code=${encodeURIComponent(parentLevelCode)}`
    : ''
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
  body: { position_values: unknown[] }
) {
  const prefix = isSales ? SALES_PREFIX : PROCUREMENT_PREFIX
  return request<unknown>(`${prefix}/${tenderId}/proposals/${proposalId}/position-values/`, {
    method: 'PATCH',
    body
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
