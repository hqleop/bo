// Один активний refresh на весь застосунок — уникнути паралельних викликів і подвійного запису cookie
let refreshPromise: Promise<boolean> | null = null

export const useAuth = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  // Cookies зберігаються до виходу або очищення кешу (maxAge: 7 днів для refresh token)
  // secure: тільки в production (на localhost без HTTPS cookie з secure не зберігається)
  const isProd = typeof import.meta !== 'undefined' ? !import.meta.dev : process.env.NODE_ENV === 'production'
  const cookieOptions = {
    secure: isProd,
    sameSite: 'lax' as const
  }
  const accessToken = useCookie<string | null>('access_token', {
    default: () => null,
    maxAge: 60 * 60 * 24, // 1 день — узгоджено з бекендом (ACCESS_TOKEN_LIFETIME)
    ...cookieOptions
  })
  const refreshToken = useCookie<string | null>('refresh_token', {
    default: () => null,
    maxAge: 60 * 60 * 24 * 7, // 7 днів (refresh token lifetime)
    ...cookieOptions
  })

  const login = async (email: string, password: string) => {
    try {
      const data = await $fetch<{ access: string; refresh: string }>(`${apiBase}/auth/login/`, {
        method: 'POST',
        body: { email, password }
      })
      if (accessToken.value !== data.access) accessToken.value = data.access
      if (refreshToken.value !== data.refresh) refreshToken.value = data.refresh
      return { success: true }
    } catch (error: any) {
      return { success: false, error: error.data?.detail || error.message || 'Помилка входу' }
    }
  }

  const refreshAccessToken = async (): Promise<boolean> => {
    if (!refreshToken.value) return false

    if (refreshPromise) return refreshPromise

    refreshPromise = (async () => {
      try {
        const data = await $fetch<{ access: string }>(`${apiBase}/auth/refresh/`, {
          method: 'POST',
          body: { refresh: refreshToken.value }
        })
        if (accessToken.value !== data.access) accessToken.value = data.access
        return true
      } catch (error) {
        accessToken.value = null
        refreshToken.value = null
        return false
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
    return {
      Authorization: `Bearer ${accessToken.value}`
    }
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
