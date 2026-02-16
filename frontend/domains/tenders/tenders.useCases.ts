import * as tendersApi from './tenders.api'
import type { TenderListItem, TenderDetail, CreateTenderPayload } from './tenders.types'

export function useTendersUseCases() {
  const { fetch } = useApi()
  const { getAuthHeaders } = useAuth()

  async function getTenderList(isSales: boolean): Promise<{ data: TenderListItem[] }> {
    const { data, error } = await tendersApi.getTenderList(fetch, isSales)
    if (error) return { data: [] }
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getTender(
    id: number,
    isSales: boolean
  ): Promise<{ data: TenderDetail | null; error: string | null }> {
    const { data, error } = await tendersApi.getTender(fetch, id, isSales)
    return { data: data ?? null, error: error ?? null }
  }

  async function createTender(
    isSales: boolean,
    payload: CreateTenderPayload
  ): Promise<{ data: TenderDetail | null; error: string | null }> {
    const { data, error } = await tendersApi.createTender(fetch, isSales, payload as Record<string, unknown>)
    return { data: data ?? null, error: error ?? null }
  }

  async function patchTender(
    id: number,
    isSales: boolean,
    body: Record<string, unknown>
  ): Promise<{ data: TenderDetail | null; error: string | null }> {
    const { data, error } = await tendersApi.patchTender(fetch, id, isSales, body)
    return { data: data ?? null, error: error ?? null }
  }

  async function getTenderTours(
    id: number,
    isSales: boolean
  ): Promise<{ data: { value: number; label: string }[] }> {
    const { data } = await tendersApi.getTenderTours(fetch, id, isSales)
    const list = Array.isArray(data) ? data : []
    return {
      data: list.map((t: { id?: number; tour_number?: number }) => ({
        value: t.id ?? t.tour_number ?? 0,
        label: `Тур ${t.tour_number ?? t.id ?? ''}`
      }))
    }
  }

  async function getTenderProposals(
    id: number,
    isSales: boolean
  ): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getTenderProposals(fetch, id, isSales)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function fixTenderDecision(
    id: number,
    isSales: boolean,
    body?: Record<string, unknown>
  ): Promise<{ data: { id: number; stage?: string } | null; error: string | null }> {
    const { data, error } = await tendersApi.fixTenderDecision(fetch, id, isSales, body)
    return { data: data ?? null, error: error ?? null }
  }

  async function getTenderCriteria(): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getTenderCriteria(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getCategories(): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getCategories(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getExpenses(): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getExpenses(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getBranches(): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getBranches(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getCurrencies(): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getCurrencies(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getDepartments(branchId: number): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getDepartments(fetch, branchId)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getNomenclaturesByCpv(cpvId: number): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getNomenclaturesByCpv(fetch, cpvId)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getNomenclaturesByCategory(categoryId: number): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getNomenclaturesByCategory(fetch, categoryId)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getCategory(categoryId: number): Promise<{ data: unknown }> {
    const { data } = await tendersApi.getCategory(fetch, categoryId)
    return { data: data ?? null }
  }

  async function getCpvChildren(parentLevelCode?: string): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getCpvChildren(fetch, parentLevelCode)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function addProposal(
    tenderId: number,
    isSales: boolean,
    body: Record<string, unknown>
  ): Promise<{ data: unknown; error: string | null }> {
    const { data, error } = await tendersApi.addProposal(fetch, tenderId, isSales, body)
    return { data: data ?? null, error: error ?? null }
  }

  async function getProposalPositionValues(
    tenderId: number,
    proposalId: number,
    isSales: boolean
  ): Promise<{ data: unknown[] }> {
    const { data } = await tendersApi.getProposalPositionValues(fetch, tenderId, proposalId, isSales)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function patchProposalPositionValues(
    tenderId: number,
    proposalId: number,
    isSales: boolean,
    body: { position_values: unknown[] }
  ): Promise<{ data: unknown; error: string | null }> {
    const { data, error } = await tendersApi.patchProposalPositionValues(
      fetch,
      tenderId,
      proposalId,
      isSales,
      body
    )
    return { data: data ?? null, error: error ?? null }
  }

  return {
    getTenderList,
    getTender,
    createTender,
    patchTender,
    getTenderTours,
    getTenderProposals,
    fixTenderDecision,
    getTenderCriteria,
    getCategories,
    getExpenses,
    getBranches,
    getCurrencies,
    getDepartments,
    getNomenclaturesByCpv,
    getNomenclaturesByCategory,
    getCategory,
    getCpvChildren,
    addProposal,
    getProposalPositionValues,
    patchProposalPositionValues
  }
}
