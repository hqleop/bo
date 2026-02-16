import type { CompanySupplierRelation } from './suppliers.types'

/** Optional cache for supplier list. Pages can use useCases directly. */
export function useSuppliersStore() {
  const relations = useState<CompanySupplierRelation[] | null>('suppliers-relations', () => null)
  return { relations }
}
