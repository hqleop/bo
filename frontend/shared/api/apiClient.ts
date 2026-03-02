import { $fetch } from "ofetch";

export type ApiClientOptions = {
  baseURL: string;
  getAuthHeaders?: () => Record<string, string>;
  refreshAccessToken?: () => Promise<boolean>;
  logout?: () => void;
  onRequestStart?: () => void;
  onRequestEnd?: () => void;
};

export type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  query?: Record<string, string>;
  skipLoader?: boolean;
};

export type ApiResult<T> = { data: T; error: null } | { data: null; error: string };

export type RequestFn = <T>(
  endpoint: string,
  options?: {
    method?: string;
    body?: unknown;
    headers?: Record<string, string>;
    query?: Record<string, string>;
    skipLoader?: boolean;
  },
) => Promise<ApiResult<T>>;

function is401(error: unknown): boolean {
  const e = error as { status?: number; statusCode?: number };
  return e?.status === 401 || e?.statusCode === 401;
}

function getErrorMessage(error: unknown): string {
  const e = error as { data?: unknown; message?: string };
  const data = e?.data as Record<string, unknown> | undefined;
  const detail = data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;

  const extractFirstMessage = (payload: unknown): string | null => {
    if (typeof payload === "string" && payload.trim()) return payload;
    if (Array.isArray(payload)) {
      for (const item of payload) {
        const nested = extractFirstMessage(item);
        if (nested) return nested;
      }
      return null;
    }
    if (payload && typeof payload === "object") {
      for (const value of Object.values(payload as Record<string, unknown>)) {
        const nested = extractFirstMessage(value);
        if (nested) return nested;
      }
    }
    return null;
  };

  const fieldError = extractFirstMessage(data);
  if (fieldError) return fieldError;

  return e?.message || "Pomylka zapytu";
}

export function createApiClient(options: ApiClientOptions) {
  const { baseURL, getAuthHeaders, refreshAccessToken, logout, onRequestStart, onRequestEnd } =
    options;

  async function request<T>(endpoint: string, opts: RequestOptions = {}): Promise<ApiResult<T>> {
    const shouldTrackLoading = !opts.skipLoader;
    if (shouldTrackLoading) onRequestStart?.();

    try {
      const url = `${baseURL.replace(/\/$/, "")}/${endpoint.replace(/^\//, "")}`;
      const isFormData = opts.body instanceof FormData;
      const { skipLoader: _skipLoader, ...fetchOptions } = opts;
      const headers: Record<string, string> = {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(getAuthHeaders?.() ?? {}),
        ...(opts.headers ?? {}),
      };

      const doFetch = () =>
        $fetch<T>(url, {
          ...fetchOptions,
          headers,
        });

      try {
        const response = await doFetch();
        return { data: response, error: null };
      } catch (error: unknown) {
        if (!is401(error) || !refreshAccessToken || !logout) {
          return { data: null, error: getErrorMessage(error) };
        }

        const refreshed = await refreshAccessToken();
        if (!refreshed) {
          logout();
          return { data: null, error: "Session expired. Please sign in again." };
        }

        try {
          const newHeaders = {
            ...(isFormData ? {} : { "Content-Type": "application/json" }),
            ...(getAuthHeaders?.() ?? {}),
            ...(opts.headers ?? {}),
          };
          const response = await $fetch<T>(url, { ...fetchOptions, headers: newHeaders });
          return { data: response, error: null };
        } catch {
          logout();
          return { data: null, error: "Session expired. Please sign in again." };
        }
      }
    } finally {
      if (shouldTrackLoading) onRequestEnd?.();
    }
  }

  return { request };
}
