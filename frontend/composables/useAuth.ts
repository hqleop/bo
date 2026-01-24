export const useAuth = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  // Cookies зберігаються до виходу або очищення кешу (maxAge: 7 днів для refresh token)
  const accessToken = useCookie<string | null>('access_token', { 
    default: () => null,
    maxAge: 60 * 15, // 15 хвилин (access token lifetime)
    secure: true,
    sameSite: 'lax'
  })
  const refreshToken = useCookie<string | null>('refresh_token', { 
    default: () => null,
    maxAge: 60 * 60 * 24 * 7, // 7 днів (refresh token lifetime)
    secure: true,
    sameSite: 'lax'
  })

  const login = async (email: string, password: string) => {
    try {
      const data = await $fetch<{ access: string; refresh: string }>(`${apiBase}/auth/login/`, {
        method: 'POST',
        body: { email, password }
      })
      accessToken.value = data.access
      refreshToken.value = data.refresh
      return { success: true }
    } catch (error: any) {
      return { success: false, error: error.data?.detail || error.message || 'Помилка входу' }
    }
  }

  const refreshAccessToken = async () => {
    if (!refreshToken.value) {
      return false
    }

    try {
      const data = await $fetch<{ access: string }>(`${apiBase}/auth/refresh/`, {
        method: 'POST',
        body: { refresh: refreshToken.value }
      })
      accessToken.value = data.access
      return true
    } catch (error) {
      // Якщо refresh не вдався - очищаємо токени
      accessToken.value = null
      refreshToken.value = null
      return false
    }
  }

  const logout = () => {
    accessToken.value = null
    refreshToken.value = null
    navigateTo('/')
  }

  const isAuthenticated = computed(() => !!accessToken.value)

  const getAuthHeaders = () => {
    if (!accessToken.value) return {}
    return {
      Authorization: `Bearer ${accessToken.value}`
    }
  }

  // Перевірка валідності токена при ініціалізації
  const checkAuth = async () => {
    if (!accessToken.value && refreshToken.value) {
      // Спробуємо оновити access token
      await refreshAccessToken()
    }
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
