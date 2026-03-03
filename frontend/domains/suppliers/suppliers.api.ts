import type { RequestFn } from '~/shared/api/apiClient'
import type { SupplierCompany, CompanySupplierRelation, CompanyMember, AddSupplierPayload, SupplierTender } from './suppliers.types'

export async function getCompanySuppliers(request: RequestFn) {
  return request<CompanySupplierRelation[]>('/company-suppliers/')
}

export async function addCompanySupplier(request: RequestFn, payload: AddSupplierPayload) {
  return request<CompanySupplierRelation>('/company-suppliers/', { method: 'POST', body: payload })
}

export async function getCompanyByEdrpou(request: RequestFn, edrpou: string) {
  return request<{ id: number; edrpou?: string; name?: string }[]>(
    `/companies/?edrpou=${encodeURIComponent(edrpou)}`
  )
}

export async function getCompany(request: RequestFn, id: number) {
  return request<SupplierCompany>(`/companies/${id}/`)
}

export async function getCompanyMembers(request: RequestFn, companyId: number) {
  return request<CompanyMember[]>(`/companies/${companyId}/members/`)
}

export async function getCompanySupplierTenders(request: RequestFn, relationId: number) {
  return request<SupplierTender[]>(`/company-suppliers/${relationId}/tenders/`)
}
