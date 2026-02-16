/** Supplier company (from /companies/:id/) */
export interface SupplierCompany {
  id: number
  name: string
  edrpou?: string
  [key: string]: unknown
}

/** Company-supplier relation (from /company-suppliers/) */
export interface CompanySupplierRelation {
  id: number
  supplier_company: {
    id: number
    edrpou?: string
    name: string
  }
  source?: string
  [key: string]: unknown
}

/** Company member (from /companies/:id/members/) */
export interface CompanyMember {
  user?: { email?: string; first_name?: string; last_name?: string }
  role?: { name?: string }
  status?: string
  [key: string]: unknown
}

/** Add supplier payload (POST /company-suppliers/) */
export interface AddSupplierPayload {
  edrpou: string
  name?: string
}
