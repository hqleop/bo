import * as analyticsApi from './analytics.api'
import type {
  AnalyticsFilters,
  AnalyticsMode,
  AnalyticsDashboardPayload,
} from './analytics.types'

export function useAnalyticsUseCases() {
  const { fetch } = useApi()

  async function getAnalyticsDashboard(
    mode: AnalyticsMode,
    filters?: AnalyticsFilters
  ): Promise<{ data: AnalyticsDashboardPayload | null; error: string | null }> {
    const { data, error } = await analyticsApi.getAnalyticsDashboard(fetch, mode, filters)
    if (error || !data) return { data: null, error: error ?? null }
    return { data, error: null }
  }

  return { getAnalyticsDashboard }
}
