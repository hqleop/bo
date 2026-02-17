import * as tendersApi from './tenders.api'

export function useTendersUseCases() {
  const { fetch } = useApi()

  async function getTenderList(isSales: boolean) {
    return tendersApi.getTenderList(fetch, isSales)
  }

  async function getTender(id: number, isSales: boolean) {
    return tendersApi.getTender(fetch, id, isSales)
  }

  async function patchTender(
    id: number,
    isSales: boolean,
    body: Record<string, unknown>
  ) {
    return tendersApi.patchTender(fetch, id, isSales, body)
  }

  async function createTender(isSales: boolean, body: Record<string, unknown>) {
    return tendersApi.createTender(fetch, isSales, body)
  }

  async function getTenderTours(id: number, isSales: boolean) {
    return tendersApi.getTenderTours(fetch, id, isSales)
  }

  async function getTenderProposals(id: number, isSales: boolean) {
    return tendersApi.getTenderProposals(fetch, id, isSales)
  }

  async function fixTenderDecision(
    id: number,
    isSales: boolean,
    body?: Record<string, unknown>
  ) {
    return tendersApi.fixTenderDecision(fetch, id, isSales, body)
  }

  async function getTenderCriteria() {
    return tendersApi.getTenderCriteria(fetch)
  }

  async function getCategories() {
    return tendersApi.getCategories(fetch)
  }

  async function getExpenses() {
    return tendersApi.getExpenses(fetch)
  }

  async function getBranches() {
    return tendersApi.getBranches(fetch)
  }

  async function getCurrencies() {
    return tendersApi.getCurrencies(fetch)
  }

  async function getDepartments(branchId: number) {
    return tendersApi.getDepartments(fetch, branchId)
  }

  async function getNomenclaturesByCpv(cpvId: number) {
    return tendersApi.getNomenclaturesByCpv(fetch, cpvId)
  }

  async function getNomenclaturesByCategory(categoryId: number) {
    return tendersApi.getNomenclaturesByCategory(fetch, categoryId)
  }

  async function getCategory(categoryId: number) {
    return tendersApi.getCategory(fetch, categoryId)
  }

  async function getCpvChildren(parentLevelCode?: string) {
    return tendersApi.getCpvChildren(fetch, parentLevelCode)
  }

  async function addProposal(
    tenderId: number,
    isSales: boolean,
    body: Record<string, unknown>
  ) {
    return tendersApi.addProposal(fetch, tenderId, isSales, body)
  }

  async function getProposalPositionValues(
    tenderId: number,
    proposalId: number,
    isSales: boolean
  ) {
    return tendersApi.getProposalPositionValues(
      fetch,
      tenderId,
      proposalId,
      isSales
    )
  }

  async function patchProposalPositionValues(
    tenderId: number,
    proposalId: number,
    isSales: boolean,
    body: { position_values: unknown[] }
  ) {
    return tendersApi.patchProposalPositionValues(
      fetch,
      tenderId,
      proposalId,
      isSales,
      body
    )
  }

  return {
    getTenderList,
    getTender,
    patchTender,
    createTender,
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
