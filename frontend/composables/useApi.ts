export const useApi = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase
  const { getAuthHeaders, checkAuth, refreshAccessToken, logout } = useAuth()

  const fetch = async <T>(endpoint: string, options: any = {}) => {
    // Якщо токена немає — спробувати оновити з refresh перед запитом
    if (!getAuthHeaders().Authorization) {
      await checkAuth()
    }
    const authHeaders = getAuthHeaders()
    const headers = {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...(options.headers || {})
    }

    try {
      const response = await $fetch<T>(`${apiBase}${endpoint}`, {
        ...options,
        headers
      })
      return { data: response, error: null }
    } catch (error: any) {
      // Якщо 401 - спробуємо оновити токен
      if (error.status === 401 || error.statusCode === 401) {
        const refreshed = await refreshAccessToken()
        if (refreshed) {
          // Повторюємо запит з новим токеном
          const newHeaders = {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
            ...options.headers
          }
          try {
            const response = await $fetch<T>(`${apiBase}${endpoint}`, {
              ...options,
              headers: newHeaders
            })
            return { data: response, error: null }
          } catch (retryError: any) {
            // Якщо повторний запит не вдався - виходимо
            logout()
            return { data: null, error: 'Сесія закінчилась. Будь ласка, увійдіть знову.' }
          }
        } else {
          // Не вдалося оновити токен - виходимо
          logout()
          return { data: null, error: 'Сесія закінчилась. Будь ласка, увійдіть знову.' }
        }
      }
      return { data: null, error: error.data || error.message || 'Помилка запиту' }
    }
  }

  return { fetch }
}

// Global fetch wrapper for useFetch
export const useApiFetch = (url: string, options: any = {}) => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase
  const { getAuthHeaders } = useAuth()

  return useFetch(`${apiBase}${url}`, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers
    }
  })
}
