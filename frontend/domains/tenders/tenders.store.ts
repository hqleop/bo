import type { TenderListItem } from './tenders.types'

/** Optional cache for tender lists (purchase/sales). Pages can use useCases directly without store. */
export function useTendersStore() {
  const procurementList = useState<TenderListItem[] | null>('tenders-procurement-list', () => null)
  const salesList = useState<TenderListItem[] | null>('tenders-sales-list', () => null)
  return { procurementList, salesList }
}
