import * as tendersApi from './tenders.api'

export function useTendersUseCases() {
  const { fetch } = useApi()

  async function getTenderList(isSales: boolean) {
    return tendersApi.getTenderList(fetch, isSales)
  }

  async function getTenderJournalList(
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
    return tendersApi.getTenderJournalList(fetch, isSales, filters)
  }

  async function getTenderActiveTasks(
    isSales: boolean,
    options?: { limit?: number; skipLoader?: boolean }
  ) {
    const { data, error } = await tendersApi.getTenderActiveTasks(fetch, isSales, options)
    const payload = data as { count?: number; limit?: number; results?: unknown[] } | null
    const results = Array.isArray(payload?.results) ? (payload?.results as unknown[]) : []
    return {
      data: {
        count: Number(payload?.count ?? 0),
        limit: Number(payload?.limit ?? 0),
        results,
      },
      error,
    }
  }

  async function getTenderActiveTasksCount(
    isSales: boolean,
    options?: { skipLoader?: boolean }
  ) {
    const { data, error } = await tendersApi.getTenderActiveTasksCount(fetch, isSales, options)
    return { data: { count: Number((data as any)?.count ?? 0) }, error }
  }

  async function getTendersForParticipation(
    isSales: boolean,
    tab: 'active' | 'processing' | 'completed' | 'journal',
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

  async function bulkDeleteTenders(isSales: boolean, ids: number[]) {
    return tendersApi.bulkDeleteTenders(fetch, isSales, ids)
  }

  async function bulkCopyTenders(isSales: boolean, ids: number[]) {
    return tendersApi.bulkCopyTenders(fetch, isSales, ids)
  }

  async function getTenderTours(id: number, isSales: boolean) {
    return tendersApi.getTenderTours(fetch, id, isSales)
  }

  async function getDecisionMarketReference(
    id: number,
    isSales: boolean,
    options?: { skipLoader?: boolean }
  ) {
    return tendersApi.getDecisionMarketReference(fetch, id, isSales, options)
  }

  async function getTenderProposals(
    id: number,
    isSales: boolean,
    options?: {
      skipLoader?: boolean
      proposalIds?: number[]
      statusOnly?: boolean
      updatedSince?: string
    }
  ) {
    return tendersApi.getTenderProposals(fetch, id, isSales, options)
  }

  async function getTenderProposalDetail(
    id: number,
    proposalId: number,
    isSales: boolean,
    options?: { skipLoader?: boolean }
  ) {
    return tendersApi.getTenderProposalDetail(fetch, id, proposalId, isSales, options)
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

  async function getTenderBidHistory(
    id: number,
    isSales: boolean,
    tenderPositionId: number
  ) {
    const { data, error } = await tendersApi.getTenderBidHistory(fetch, id, isSales, tenderPositionId)
    return { data: Array.isArray(data) ? data : [], error }
  }

  async function getTenderChatThreads(id: number, isSales: boolean) {
    const { data, error } = await tendersApi.getTenderChatThreads(fetch, id, isSales)
    return { data: Array.isArray(data) ? data : [], error }
  }

  async function getTenderChatMessages(
    id: number,
    isSales: boolean,
    supplierCompanyId?: number | null
  ) {
    const { data, error } = await tendersApi.getTenderChatMessages(
      fetch,
      id,
      isSales,
      supplierCompanyId
    )
    return { data: Array.isArray(data) ? data : [], error }
  }

  async function sendTenderChatMessage(
    id: number,
    isSales: boolean,
    body: { body: string; supplier_company_id?: number | null }
  ) {
    return tendersApi.sendTenderChatMessage(fetch, id, isSales, body)
  }

  async function getTenderProposalChangeReport(id: number, isSales: boolean) {
    const { data, error } = await tendersApi.getTenderProposalChangeReport(fetch, id, isSales)
    return { data: Array.isArray(data) ? data : [], error }
  }

  async function disqualifyTenderProposals(
    id: number,
    isSales: boolean,
    body: { items: Array<{ proposal_id: number; disqualify: boolean; comment?: string }> }
  ) {
    return tendersApi.disqualifyTenderProposals(fetch, id, isSales, body)
  }

  async function carryPreviousTourProposals(id: number) {
    return tendersApi.carryPreviousTourProposals(fetch, id)
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

  async function getTenderAttributesByType(tenderType: 'procurement' | 'sales') {
    return tendersApi.getTenderAttributesByType(fetch, tenderType)
  }

  async function createTenderAttribute(body: {
    company: number
    name: string
    type: string
    tender_type: 'procurement' | 'sales'
    category?: number | null
    is_required?: boolean
    options?: Record<string, unknown>
  }) {
    return tendersApi.createTenderAttribute(fetch, body)
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

  async function getTenderConditionTemplates(companyId?: number | null) {
    const { data, error } = await tendersApi.getTenderConditionTemplates(fetch, companyId)
    return { data: Array.isArray(data) ? data : [], error }
  }

  async function createTenderConditionTemplate(body: {
    company: number
    name: string
    content: string
  }) {
    return tendersApi.createTenderConditionTemplate(fetch, body)
  }

  async function updateTenderConditionTemplate(
    id: number,
    body: { name: string; content: string }
  ) {
    return tendersApi.updateTenderConditionTemplate(fetch, id, body)
  }

  async function deleteTenderConditionTemplate(id: number) {
    return tendersApi.deleteTenderConditionTemplate(fetch, id)
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

  async function getDepartments(branchId?: number | null) {
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
    body: { position_values: unknown[] },
    options?: { skipLoader?: boolean }
  ) {
    return tendersApi.patchProposalPositionValues(
      fetch,
      tenderId,
      proposalId,
      isSales,
      body,
      options
    )
  }

  async function submitProposal(tenderId: number, isSales: boolean) {
    return tendersApi.submitProposal(fetch, tenderId, isSales)
  }

  async function withdrawProposal(tenderId: number, isSales: boolean) {
    return tendersApi.withdrawProposal(fetch, tenderId, isSales)
  }

  async function getTenderApprovalJournal(tenderId: number, isSales: boolean) {
    const { data, error } = await tendersApi.getTenderApprovalJournal(fetch, tenderId, isSales)
    return { data: Array.isArray(data) ? data : [], error }
  }

  async function getTenderApprovalRoute(tenderId: number, isSales: boolean) {
    return tendersApi.getTenderApprovalRoute(fetch, tenderId, isSales)
  }

  async function submitTenderApprovalSubmit(
    tenderId: number,
    isSales: boolean,
    body?: { comment?: string }
  ) {
    return tendersApi.submitTenderApprovalSubmit(fetch, tenderId, isSales, body)
  }

  async function submitTenderApprovalAction(
    tenderId: number,
    isSales: boolean,
    body: { action: "approved" | "rejected"; comment?: string }
  ) {
    return tendersApi.submitTenderApprovalAction(fetch, tenderId, isSales, body)
  }

  async function getAvailableApprovalModels(params: {
    companyId: number
    application: 'procurement' | 'sales'
    categoryId?: number | null
    estimatedBudget?: number | null
  }) {
    const { data, error } = await tendersApi.getAvailableApprovalModels(fetch, params)
    return { data: Array.isArray(data) ? data : [], error }
  }

  return {
    getTenderList,
    getTenderJournalList,
    getTenderActiveTasks,
    getTenderActiveTasksCount,
    getTendersForParticipation,
    confirmParticipation,
    getTender,
    patchTender,
    createTender,
    bulkDeleteTenders,
    bulkCopyTenders,
    getTenderTours,
    getDecisionMarketReference,
    getTenderProposals,
    getTenderProposalDetail,
    getTenderFiles,
    uploadTenderFile,
    deleteTenderFile,
    patchTenderFile,
    fixTenderDecision,
    getTenderBidHistory,
    getTenderChatThreads,
    getTenderChatMessages,
    sendTenderChatMessage,
    getTenderProposalChangeReport,
    disqualifyTenderProposals,
    carryPreviousTourProposals,
    getTenderCriteria,
    getTenderCriteriaByType,
    createTenderCriterion,
    getTenderAttributesByType,
    createTenderAttribute,
    getUnits,
    createNomenclature,
    getCategories,
    getTenderConditionTemplates,
    createTenderConditionTemplate,
    updateTenderConditionTemplate,
    deleteTenderConditionTemplate,
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
    withdrawProposal,
    getTenderApprovalJournal,
    getTenderApprovalRoute,
    submitTenderApprovalSubmit,
    submitTenderApprovalAction,
    getAvailableApprovalModels
  }
}
