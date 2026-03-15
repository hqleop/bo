import * as usersApi from './users.api'
import { useUsersStore } from './users.store'
import type { Me, MeUpdatePayload, CreateUserPayload, UpdateUserPayload } from './users.types'

let meRefreshPromise: Promise<Me | null> | null = null

function normalizeMeResponse(data: unknown): Me | null {
  if (!data || typeof data !== 'object') return null
  const d = data as Record<string, unknown>
  const userFromMembership = (d.memberships as unknown[])?.[0] as Record<string, unknown> | undefined
  const userFromMembershipUser = userFromMembership?.user
  const user = d.user
    ? { ...(d.user as object) }
    : userFromMembershipUser
      ? { ...(userFromMembershipUser as object) }
      : undefined
  return {
    user: user as Me['user'],
    memberships: Array.isArray(d.memberships) ? d.memberships : [],
    permissions: Array.isArray(d.permissions) ? d.permissions : [],
    registration_step:
      typeof d.registration_step === 'number'
        ? d.registration_step
        : undefined,
    registration_company_id:
      typeof d.registration_company_id === 'number'
        ? d.registration_company_id
        : undefined
  }
}

export function useUsersUseCases() {
  const { fetch } = useApi()
  const { getAuthHeaders, checkAuth } = useAuth()
  const { me } = useUsersStore()

  async function refreshMe(): Promise<Me | null> {
    if (meRefreshPromise) return meRefreshPromise
    await checkAuth()
    if (!getAuthHeaders().Authorization) {
      me.value = null
      resetCompanyPrimaryColor()
      return null
    }
    meRefreshPromise = (async () => {
      try {
        const { data, error } = await usersApi.getMe(fetch)
        if (error || !data) {
          me.value = null
          resetCompanyPrimaryColor()
          return null
        }
        const payload = normalizeMeResponse(data)
        me.value = payload
        applyCompanyPrimaryColor(resolveCompanyPrimaryColorFromMe(payload))
        return payload
      } finally {
        meRefreshPromise = null
      }
    })()
    return meRefreshPromise
  }

  async function updateProfile(payload: MeUpdatePayload): Promise<{ error: string | null }> {
    const { error } = await usersApi.patchMe(fetch, payload)
    if (error) return { error }
    await refreshMe()
    return { error: null }
  }

  async function uploadAvatar(file: File): Promise<{ error: string | null }> {
    const formData = new FormData()
    formData.append('avatar', file)
    const { data, error } = await usersApi.uploadAvatar(fetch, formData)
    if (error) return { error }
    if (data?.avatar) await refreshMe()
    return { error: null }
  }

  async function getMemberships(): Promise<{ data: unknown[] | null; error: string | null }> {
    const { data, error } = await usersApi.getMemberships(fetch)
    if (error) return { data: null, error }
    return { data: Array.isArray(data) ? data : [], error: null }
  }

  async function createUser(payload: CreateUserPayload): Promise<{ error: string | null }> {
    const { error } = await usersApi.createUser(fetch, payload)
    return { error: error ?? null }
  }

  async function updateUser(
    membershipId: number,
    payload: UpdateUserPayload
  ): Promise<{ error: string | null }> {
    const { error } = await usersApi.updateUser(fetch, membershipId, payload)
    return { error: error ?? null }
  }

  async function activateMembership(membershipId: number): Promise<{ error: string | null }> {
    const { error } = await usersApi.activateMembership(fetch, membershipId)
    return { error: error ?? null }
  }

  async function deactivateMembership(membershipId: number): Promise<{ error: string | null }> {
    const { error } = await usersApi.deactivateMembership(fetch, membershipId)
    return { error: error ?? null }
  }

  async function getBranches(): Promise<{ data: unknown[] }> {
    const { data } = await usersApi.getBranches(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getCategories(): Promise<{ data: unknown[] }> {
    const { data } = await usersApi.getCategories(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getExpenses(): Promise<{ data: unknown[] }> {
    const { data } = await usersApi.getExpenses(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getDepartments(branchId: number): Promise<{ data: unknown[] }> {
    const { data } = await usersApi.getDepartments(fetch, branchId)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getBranchUserIds(branchId: number): Promise<Set<number>> {
    const { data } = await usersApi.getBranchUsers(fetch, branchId)
    const list = Array.isArray(data) ? data : []
    const ids = new Set<number>()
    for (const bu of list as { user?: { id?: number } }[]) {
      if (bu?.user?.id) ids.add(bu.user.id)
    }
    return ids
  }

  async function getDepartmentUserIds(departmentId: number): Promise<Set<number>> {
    const { data } = await usersApi.getDepartmentUsers(fetch, departmentId)
    const list = Array.isArray(data) ? data : []
    const ids = new Set<number>()
    for (const du of list as { user?: { id?: number } }[]) {
      if (du?.user?.id) ids.add(du.user.id)
    }
    return ids
  }

  async function getCategoryUserIds(categoryId: number): Promise<Set<number>> {
    const { data } = await usersApi.getCategoryUsers(fetch, categoryId)
    const list = Array.isArray(data) ? data : []
    const ids = new Set<number>()
    for (const cu of list as { user?: { id?: number } }[]) {
      if (cu?.user?.id) ids.add(cu.user.id)
    }
    return ids
  }

  async function getExpenseUserIds(expenseId: number): Promise<Set<number>> {
    const { data } = await usersApi.getExpenseUsers(fetch, expenseId)
    const list = Array.isArray(data) ? data : []
    const ids = new Set<number>()
    for (const eu of list as { user?: { id?: number } }[]) {
      if (eu?.user?.id) ids.add(eu.user.id)
    }
    return ids
  }

  async function registerStep1(payload: Record<string, unknown>): Promise<{
    data: { user_id?: number } | null
    error: string | null
  }> {
    const { data, error } = await usersApi.registerStep1(fetch, payload)
    return { data: data ?? null, error: error ?? null }
  }

  async function registerStep2New(payload: unknown): Promise<{
    data?: unknown
    error: string | null
  }> {
    const { data, error } = await usersApi.registerStep2New(fetch, payload)
    return { ...(data ? { data } : {}), error: error ?? null }
  }

  async function registerStep2Existing(payload: Record<string, unknown>): Promise<{
    data?: unknown
    error: string | null
  }> {
    const { data, error } = await usersApi.registerStep2Existing(fetch, payload)
    return { ...(data ? { data } : {}), error: error ?? null }
  }

  async function registerStep3CompanyCpvs(payload: {
    user_id: number
    company_id: number
    goal_tenders: boolean
    goal_participation: boolean
    agree_participation_visibility: boolean
    cpv_ids: number[]
  }): Promise<{ error: string | null }> {
    const { error } = await usersApi.registerStep3CompanyCpvs(fetch, payload)
    return { error: error ?? null }
  }

  async function getRegistrationCountryBusinessNumbers(): Promise<{ data: unknown[] }> {
    const { data } = await usersApi.getRegistrationCountryBusinessNumbers(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function lookupRegistrationCompanyByCode(edrpou: string): Promise<{
    data: {
      exists: boolean
      has_registered_users: boolean
      company?: {
        id?: number
        edrpou?: string
        name?: string
        subject_type?: 'fop_resident' | 'legal_resident' | 'non_resident' | 'individual'
        registration_country?: string
        company_address?: string
      } | null
    } | null
    error: string | null
  }> {
    const { data, error } = await usersApi.lookupRegistrationCompanyByCode(fetch, edrpou)
    if (error || !data) return { data: null, error: error ?? null }
    return { data: data as any, error: null }
  }

  async function getCurrentCompanyCpvs(): Promise<{
    data: {
      id: number
      edrpou: string
      name: string
      primary_color?: string | null
      cpv_categories: { id: number; label: string }[]
    } | null
    error: string | null
  }> {
    const { data, error } = await usersApi.getCurrentCompanyCpvs(fetch)
    if (error || !data) return { data: null, error: error ?? null }
    return { data: data as any, error: null }
  }

  async function updateCurrentCompanyCpvs(params: {
    cpvIds?: number[]
    primaryColor?: string
  }): Promise<{ error: string | null }> {
    const body: { cpv_ids?: number[]; primary_color?: string } = {}
    if (Array.isArray(params.cpvIds)) body.cpv_ids = params.cpvIds
    if (typeof params.primaryColor === 'string' && params.primaryColor.trim()) {
      body.primary_color = params.primaryColor.trim()
    }
    const { error } = await usersApi.updateCurrentCompanyCpvs(fetch, body)
    return { error: error ?? null }
  }

  async function getNotifications(
    options?: { skipLoader?: boolean; cacheTtlMs?: number }
  ): Promise<{ data: { id: number; is_read?: boolean }[] }> {
    const { data } = await usersApi.getNotifications(fetch, options)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function removeNotification(notificationId: number) {
    return usersApi.removeNotification(fetch, notificationId)
  }

  async function getRoles(): Promise<{ data: unknown[] }> {
    const { data } = await usersApi.getRoles(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  async function getPermissions(): Promise<{ data: unknown[] }> {
    const { data } = await usersApi.getPermissions(fetch)
    return { data: Array.isArray(data) ? data : [] }
  }

  return {
    refreshMe,
    updateProfile,
    uploadAvatar,
    getMemberships,
    createUser,
    updateUser,
    activateMembership,
    deactivateMembership,
    getBranches,
    getCategories,
    getExpenses,
    getDepartments,
    getBranchUserIds,
    getDepartmentUserIds,
    getCategoryUserIds,
    getExpenseUserIds,
    registerStep1,
    registerStep2New,
    registerStep2Existing,
    registerStep3CompanyCpvs,
    getRegistrationCountryBusinessNumbers,
    lookupRegistrationCompanyByCode,
    getCurrentCompanyCpvs,
    updateCurrentCompanyCpvs,
    getNotifications,
    removeNotification,
    getRoles,
    getPermissions
  }
}
