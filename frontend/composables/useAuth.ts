import { createApiClient } from '~/shared/api/apiClient'

// Один активний refresh на весь застосунок — уникнути паралельних викликів і подвійного запису cookie
let refreshPromise: Promise<boolean> | null = null

export const useAuth = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase
  const { start, stop } = useGlobalLoader()

  // Клієнт для auth-запитів (login/refresh без Authorization)
  const apiClient = createApiClient({
    baseURL: apiBase,
    onRequestStart: start,
    onRequestEnd: stop
  })

  // Cookies зберігаються до виходу або очищення кешу (maxAge: 7 днів для refresh token)
  const isProd = typeof import.meta !== 'undefined' ? !import.meta.dev : process.env.NODE_ENV === 'production'
  const cookieOptions = {
    secure: isProd,
    sameSite: 'lax' as const
  }
  const accessToken = useCookie<string | null>('access_token', {
    default: () => null,
    maxAge: 60 * 60 * 24,
    ...cookieOptions
  })
  const refreshToken = useCookie<string | null>('refresh_token', {
    default: () => null,
    maxAge: 60 * 60 * 24 * 7,
    ...cookieOptions
  })

  const login = async (email: string, password: string) => {
    const result = await apiClient.request<{ access: string; refresh: string }>('/auth/login/', {
      method: 'POST',
      body: { email, password }
    })
    if (result.error) {
      return { success: false, error: result.error }
    }
    const data = result.data
    if (accessToken.value !== data.access) accessToken.value = data.access
    if (refreshToken.value !== data.refresh) refreshToken.value = data.refresh
    return { success: true }
  }

  const refreshAccessToken = async (): Promise<boolean> => {
    if (!refreshToken.value) return false
    if (refreshPromise) return refreshPromise

    refreshPromise = (async () => {
      try {
        const result = await apiClient.request<{ access: string }>('/auth/refresh/', {
          method: 'POST',
          body: { refresh: refreshToken.value }
        })
        if (result.error || !result.data) {
          accessToken.value = null
          refreshToken.value = null
          return false
        }
        if (accessToken.value !== result.data.access) accessToken.value = result.data.access
        return true
      } finally {
        refreshPromise = null
      }
    })()

    return refreshPromise
  }

  const logout = () => {
    accessToken.value = null
    refreshToken.value = null
    refreshPromise = null
    navigateTo('/')
  }

  const isAuthenticated = computed(() => !!accessToken.value)

  const getAuthHeaders = () => {
    if (!accessToken.value) return {}
    return { Authorization: `Bearer ${accessToken.value}` }
  }

  const checkAuth = async () => {
    if (!accessToken.value && refreshToken.value) await refreshAccessToken()
  }

  return {
    login,
    logout,
    refreshAccessToken,
    checkAuth,
    isAuthenticated,
    getAuthHeaders,
    accessToken: readonly(accessToken),
    refreshToken: readonly(refreshToken)
  }
}
