import * as tendersApi from './tenders.api'

export function useTendersUseCases() {
  const { fetch } = useApi()

  async function getTenderList(isSales: boolean) {
    return tendersApi.getTenderList(fetch, isSales)
  }

  async function getTendersForParticipation(
    isSales: boolean,
    tab: 'active' | 'processing' | 'completed' | 'journal',
    filters?: {
      page?: number
      companyId?: number | null
      cpvIds?: number[]
      receptionStarted?: boolean
      conductType?: 'all' | 'rfx' | 'online_auction'
      tenderNumber?: string
      submittedOnly?: boolean
      participationResult?: 'participation' | 'win'
    }
  ) {
    const response = await tendersApi.getTendersForParticipation(fetch, isSales, tab, filters)
    if (!filters) {
      const payload = response.data as any
      return {
        ...response,
        data: Array.isArray(payload?.results) ? payload.results : Array.isArray(payload) ? payload : []
      }
    }
    return response
  }

  async function confirmParticipation(tenderId: number, isSales: boolean) {
    return tendersApi.confirmParticipation(fetch, tenderId, isSales)
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

  async function getTenderFiles(id: number, isSales: boolean) {
    return tendersApi.getTenderFiles(fetch, id, isSales)
  }

  async function uploadTenderFile(id: number, isSales: boolean, form: FormData) {
    return tendersApi.uploadTenderFile(fetch, id, isSales, form)
  }

  async function deleteTenderFile(id: number, isSales: boolean, fileId: number) {
    return tendersApi.deleteTenderFile(fetch, id, isSales, fileId)
  }

  async function patchTenderFile(
    id: number,
    isSales: boolean,
    fileId: number,
    body: { visible_to_participants: boolean }
  ) {
    return tendersApi.patchTenderFile(fetch, id, isSales, fileId, body)
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

  async function getTenderCriteriaByType(tenderType: 'procurement' | 'sales') {
    return tendersApi.getTenderCriteriaByType(fetch, tenderType)
  }

  async function createTenderCriterion(body: {
    company: number
    name: string
    type: string
    tender_type: 'procurement' | 'sales'
    application?: string
    is_required?: boolean
    options?: Record<string, unknown>
  }) {
    return tendersApi.createTenderCriterion(fetch, body)
  }

  async function getUnits() {
    return tendersApi.getUnits(fetch)
  }

  async function createNomenclature(body: {
    company: number
    name: string
    unit: number
    cpv_ids?: number[]
  }) {
    return tendersApi.createNomenclature(fetch, body)
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

  async function getNomenclaturesByCpvs(cpvIds: number[]) {
    return tendersApi.getNomenclaturesByCpvs(fetch, cpvIds)
  }

  async function getNomenclaturesByCategory(categoryId: number) {
    return tendersApi.getNomenclaturesByCategory(fetch, categoryId)
  }

  async function getCategory(categoryId: number) {
    return tendersApi.getCategory(fetch, categoryId)
  }

  async function getCpvChildren(parentLevelCode?: string, search?: string) {
    return tendersApi.getCpvChildren(fetch, parentLevelCode, search)
  }

  async function getCpvWithCompanies() {
    return tendersApi.getCpvWithCompanies(fetch)
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

  async function submitProposal(tenderId: number, isSales: boolean) {
    return tendersApi.submitProposal(fetch, tenderId, isSales)
  }

  async function withdrawProposal(tenderId: number, isSales: boolean) {
    return tendersApi.withdrawProposal(fetch, tenderId, isSales)
  }

  return {
    getTenderList,
    getTendersForParticipation,
    confirmParticipation,
    getTender,
    patchTender,
    createTender,
    getTenderTours,
    getTenderProposals,
    getTenderFiles,
    uploadTenderFile,
    deleteTenderFile,
    patchTenderFile,
    fixTenderDecision,
    getTenderCriteria,
    getTenderCriteriaByType,
    createTenderCriterion,
    getUnits,
    createNomenclature,
    getCategories,
    getExpenses,
    getBranches,
    getCurrencies,
    getDepartments,
    getNomenclaturesByCpv,
    getNomenclaturesByCpvs,
    getNomenclaturesByCategory,
    getCategory,
    getCpvChildren,
    getCpvWithCompanies,
    addProposal,
    getProposalPositionValues,
    patchProposalPositionValues,
    submitProposal,
    withdrawProposal
  }
}
