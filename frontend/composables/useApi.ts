import { createApiClient } from "~/shared/api/apiClient";

/**
 * Composable для доступу до єдиного API-клієнта в Nuxt-контексті.
 * HTTP-логіка в shared/api/apiClient. У компонентах та сторінках використовуйте useCases, не useApi напряму.
 */
export const useApi = () => {
  const config = useRuntimeConfig();
  const { getAuthHeaders, checkAuth, refreshAccessToken, logout } = useAuth();
  const { start, stop } = useGlobalLoader();

  const apiClient = createApiClient({
    baseURL: config.public.apiBase,
    getAuthHeaders,
    refreshAccessToken,
    logout,
    onRequestStart: start,
    onRequestEnd: stop,
  });

  const fetch = async <T>(
    endpoint: string,
    options: {
      method?: string
      body?: unknown
      headers?: Record<string, string>
      query?: Record<string, string>
      skipLoader?: boolean
      dedupe?: boolean
      cacheTtlMs?: number
    } = {}
  ) => {
    if (!getAuthHeaders().Authorization) {
      await checkAuth();
    }
    return apiClient.request<T>(endpoint, {
      method: options.method ?? "GET",
      body: options.body,
      headers: options.headers,
      query: options.query,
      skipLoader: options.skipLoader,
      dedupe: options.dedupe,
      cacheTtlMs: options.cacheTtlMs,
    });
  };

  return { fetch };
};

