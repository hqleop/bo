/**
 * Єдиний API-клієнт проєкту.
 * Усі HTTP-запити мають йти через createApiClient (викликається з useApi / useAuth).
 * Тут зосереджені: baseURL, HTTP ($fetch з ofetch), заголовки, refresh при 401, обробка помилок.
 */

import { $fetch } from 'ofetch'

export type ApiClientOptions = {
  baseURL: string
  getAuthHeaders?: () => Record<string, string>
  refreshAccessToken?: () => Promise<boolean>
  logout?: () => void
}

export type RequestOptions = {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  query?: Record<string, string>
}

export type ApiResult<T> = { data: T; error: null } | { data: null; error: string }

/** Request function type used by domain APIs (same signature as useApi().fetch) */
export type RequestFn = <T>(
  endpoint: string,
  options?: { method?: string; body?: unknown; headers?: Record<string, string>; query?: Record<string, string> }
) => Promise<ApiResult<T>>

function is401(error: unknown): boolean {
  const e = error as { status?: number; statusCode?: number }
  return e?.status === 401 || e?.statusCode === 401
}

function getErrorMessage(error: unknown): string {
  const e = error as { data?: { detail?: string }; message?: string }
  return (e?.data?.detail ?? e?.message) || 'Помилка запиту'
}

/**
 * Створює клієнт з єдиною точкою HTTP та логікою refresh/logout.
 */
export function createApiClient(options: ApiClientOptions) {
  const { baseURL, getAuthHeaders, refreshAccessToken, logout } = options

  async function request<T>(endpoint: string, opts: RequestOptions = {}): Promise<ApiResult<T>> {
    const url = `${baseURL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`
    const isFormData = opts.body instanceof FormData
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(getAuthHeaders?.() ?? {}),
      ...(opts.headers ?? {})
    }

    const doFetch = () =>
      $fetch<T>(url, {
        ...opts,
        headers
      })

    try {
      const response = await doFetch()
      return { data: response, error: null }
    } catch (error: unknown) {
      if (!is401(error) || !refreshAccessToken || !logout) {
        return { data: null, error: getErrorMessage(error) }
      }

      const refreshed = await refreshAccessToken()
      if (!refreshed) {
        logout()
        return { data: null, error: 'Сесія закінчилась. Будь ласка, увійдіть знову.' }
      }

      try {
        const newHeaders = {
          ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
          ...(getAuthHeaders?.() ?? {}),
          ...(opts.headers ?? {})
        }
        const response = await $fetch<T>(url, { ...opts, headers: newHeaders })
        return { data: response, error: null }
      } catch {
        logout()
        return { data: null, error: 'Сесія закінчилась. Будь ласка, увійдіть знову.' }
      }
    }
  }

  return { request }
}
