import type { RequestFn } from '~/shared/api/apiClient'
import type { TenderDetail, TenderListItem, TenderProposal, TenderCriterion } from './tenders.types'

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
