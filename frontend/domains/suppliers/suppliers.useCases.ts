import * as suppliersApi from './suppliers.api'
import type { CompanySupplierRelation, SupplierCompany, CompanyMember, AddSupplierPayload } from './suppliers.types'

export function useSuppliersUseCases() {
  const { fetch } = useApi()

  async function getSupplierRelations(): Promise<{
    data: CompanySupplierRelation[]
    error: string | null
  }> {
    const { data, error } = await suppliersApi.getCompanySuppliers(fetch)
    return {
      data: Array.isArray(data) ? data : [],
      error: error ?? null
    }
  }

  async function addSupplier(payload: AddSupplierPayload): Promise<{
    data: CompanySupplierRelation | null
    error: string | null
  }> {
    const { data, error } = await suppliersApi.addCompanySupplier(fetch, payload)
    return { data: data ?? null, error: error ?? null }
  }

  async function findCompanyByEdrpou(edrpou: string): Promise<{
    data: { id: number; edrpou: string; name: string } | null
  }> {
    const { data } = await suppliersApi.getCompanyByEdrpou(fetch, edrpou)
    const list = Array.isArray(data) ? data : []
    const found = list[0]
    if (!found) return { data: null }
    return {
      data: {
        id: found.id,
        edrpou: found.edrpou ?? edrpou,
        name: found.name ?? ''
      }
    }
  }

  async function getSupplier(id: number): Promise<{
    data: SupplierCompany | null
    error: string | null
  }> {
    const { data, error } = await suppliersApi.getCompany(fetch, id)
    return { data: data ?? null, error: error ?? null }
  }

  async function getSupplierMembers(companyId: number): Promise<{
    data: CompanyMember[]
    error: string | null
  }> {
    const { data, error } = await suppliersApi.getCompanyMembers(fetch, companyId)
    return {
      data: Array.isArray(data) ? data : [],
      error: error ?? null
    }
  }

  return {
    getSupplierRelations,
    addSupplier,
    findCompanyByEdrpou,
    getSupplier,
    getSupplierMembers
  }
}
