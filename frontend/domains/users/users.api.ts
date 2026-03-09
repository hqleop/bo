import type { RequestFn } from '~/shared/api/apiClient'
import type { Me, MeUpdatePayload, CreateUserPayload, UpdateUserPayload } from './users.types'

export async function getMe(request: RequestFn) {
  return request<Me>('/auth/me/')
}

export async function patchMe(request: RequestFn, body: MeUpdatePayload) {
  return request<Me>('/auth/me/', { method: 'PATCH', body })
}

export async function uploadAvatar(request: RequestFn, formData: FormData) {
  return request<{ avatar: string }>('/auth/me/avatar/', { method: 'POST', body: formData })
}

export async function getMemberships(request: RequestFn) {
  return request<unknown[]>('/memberships/')
}

export async function createUser(request: RequestFn, payload: CreateUserPayload) {
  return request<unknown>('/memberships/create-user/', { method: 'POST', body: payload })
}

export async function updateUser(request: RequestFn, membershipId: number, payload: UpdateUserPayload) {
  return request<unknown>(`/memberships/${membershipId}/update-user/`, { method: 'PATCH', body: payload })
}

export async function activateMembership(request: RequestFn, membershipId: number) {
  return request<unknown>(`/memberships/${membershipId}/activate/`, { method: 'POST' })
}

export async function deactivateMembership(request: RequestFn, membershipId: number) {
  return request<unknown>(`/memberships/${membershipId}/deactivate/`, { method: 'POST' })
}

// Reference data used by users page (branches, categories, expenses, departments, *-users)
export async function getBranches(request: RequestFn) {
  return request<unknown[]>('/branches/', { cacheTtlMs: 5 * 60_000 })
}

export async function getCategories(request: RequestFn) {
  return request<unknown[]>('/categories/', { cacheTtlMs: 5 * 60_000 })
}

export async function getExpenses(request: RequestFn) {
  return request<unknown[]>('/expenses/', { cacheTtlMs: 5 * 60_000 })
}

export async function getDepartments(request: RequestFn, branchId: number) {
  return request<unknown[]>(`/departments/?branch_id=${branchId}`)
}

export async function getBranchUsers(request: RequestFn, branchId: number) {
  return request<unknown[]>(`/branch-users/?branch_id=${branchId}`)
}

export async function getDepartmentUsers(request: RequestFn, departmentId: number) {
  return request<unknown[]>(`/department-users/?department_id=${departmentId}`)
}

export async function getCategoryUsers(request: RequestFn, categoryId: number) {
  return request<unknown[]>(`/category-users/?category_id=${categoryId}`)
}

export async function getExpenseUsers(request: RequestFn, expenseId: number) {
  return request<unknown[]>(`/expense-users/?expense_id=${expenseId}`)
}

export async function registerStep1(request: RequestFn, body: Record<string, unknown>) {
  return request<{ user_id?: number }>('/registration/step1/', { method: 'POST', body })
}

export async function registerStep2New(request: RequestFn, body: unknown) {
  return request<unknown>('/registration/step2/new/', { method: 'POST', body })
}

export async function registerStep2Existing(request: RequestFn, body: Record<string, unknown>) {
  return request<unknown>('/registration/step2/existing/', { method: 'POST', body })
}

export async function registerStep3CompanyCpvs(request: RequestFn, body: Record<string, unknown>) {
  return request<unknown>('/registration/step3/company-cpvs/', { method: 'POST', body })
}

export async function getRegistrationCountryBusinessNumbers(request: RequestFn) {
  return request<unknown[]>('/registration/country-business-numbers/')
}

export async function lookupRegistrationCompanyByCode(request: RequestFn, edrpou: string) {
  return request<unknown>(`/registration/company-by-code/?edrpou=${encodeURIComponent(edrpou)}`)
}

export async function getCurrentCompanyCpvs(request: RequestFn) {
  return request<unknown>('/companies/current-cpvs/')
}

export async function updateCurrentCompanyCpvs(
  request: RequestFn,
  body: { cpv_ids?: number[]; primary_color?: string }
) {
  return request<unknown>('/companies/current-cpvs/', { method: 'PUT', body })
}

export async function getNotifications(request: RequestFn) {
  return request<{ id: number; is_read?: boolean }[]>('/notifications/')
}

export async function getRoles(request: RequestFn) {
  return request<unknown[]>('/roles/')
}

export async function getPermissions(request: RequestFn) {
  return request<unknown[]>('/permissions/')
}
