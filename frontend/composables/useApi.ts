import { createApiClient } from '~/shared/api/apiClient'

/**
 * Composable для доступу до єдиного API-клієнта в Nuxt-контексті.
 * HTTP-логіка в shared/api/apiClient. У компонентах та сторінках використовуйте useCases, не useApi напряму.
 */
export const useApi = () => {
  const config = useRuntimeConfig()
  const { getAuthHeaders, checkAuth, refreshAccessToken, logout } = useAuth()

  const apiClient = createApiClient({
    baseURL: config.public.apiBase,
    getAuthHeaders,
    refreshAccessToken,
    logout
  })

  const fetch = async <T>(endpoint: string, options: Record<string, unknown> = {}) => {
    if (!getAuthHeaders().Authorization) {
      await checkAuth()
    }
    return apiClient.request<T>(endpoint, {
      method: (options.method as string) ?? 'GET',
      body: options.body,
      headers: options.headers as Record<string, string> | undefined,
      query: options.query as Record<string, string> | undefined
    })
  }

  return { fetch }
}

