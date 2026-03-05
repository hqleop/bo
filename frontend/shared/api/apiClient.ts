import { $fetch } from "ofetch";
import { getApiErrorMessage } from "./error";

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
  dedupe?: boolean;
  cacheTtlMs?: number;
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
    dedupe?: boolean;
    cacheTtlMs?: number;
  },
) => Promise<ApiResult<T>>;

function is401(error: unknown): boolean {
  const e = error as { status?: number; statusCode?: number };
  return e?.status === 401 || e?.statusCode === 401;
}

export function createApiClient(options: ApiClientOptions) {
  const { baseURL, getAuthHeaders, refreshAccessToken, logout, onRequestStart, onRequestEnd } =
    options;
  const inFlightGetRequests = new Map<string, Promise<ApiResult<unknown>>>();
  const getResponseCache = new Map<
    string,
    { expiresAt: number; value: ApiResult<unknown> }
  >();

  function buildRequestKey(
    method: string,
    url: string,
    query?: Record<string, string>,
  ): string {
    const queryPairs = Object.entries(query ?? {})
      .filter(([, value]) => value != null && String(value).length > 0)
      .sort(([a], [b]) => a.localeCompare(b));
    const queryString = queryPairs
      .map(
        ([key, value]) =>
          `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`,
      )
      .join("&");
    return queryString
      ? `${method.toUpperCase()}::${url}?${queryString}`
      : `${method.toUpperCase()}::${url}`;
  }

  async function request<T>(endpoint: string, opts: RequestOptions = {}): Promise<ApiResult<T>> {
    const method = String(opts.method || "GET").toUpperCase();
    const url = `${baseURL.replace(/\/$/, "")}/${endpoint.replace(/^\//, "")}`;
    const requestKey = buildRequestKey(method, url, opts.query);
    const allowDedupe = method === "GET" && opts.dedupe !== false;
    const cacheTtlMs =
      method === "GET" ? Math.max(0, Number(opts.cacheTtlMs ?? 0)) : 0;

    if (cacheTtlMs > 0) {
      const cached = getResponseCache.get(requestKey);
      if (cached && cached.expiresAt > Date.now()) {
        return cached.value as ApiResult<T>;
      }
      if (cached) {
        getResponseCache.delete(requestKey);
      }
    }

    if (allowDedupe) {
      const pending = inFlightGetRequests.get(requestKey);
      if (pending) {
        return (await pending) as ApiResult<T>;
      }
    }

    const shouldTrackLoading = !opts.skipLoader;
    const requestPromise = (async (): Promise<ApiResult<T>> => {
      if (shouldTrackLoading) onRequestStart?.();

      try {
        const isFormData = opts.body instanceof FormData;
        const { skipLoader: _skipLoader, dedupe: _dedupe, cacheTtlMs: _cacheTtlMs, ...fetchOptions } = opts;
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
            return { data: null, error: getApiErrorMessage(error, "Pomylka zapytu") };
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
    })();

    const trackedPromise = requestPromise
      .then((result) => {
        if (cacheTtlMs > 0 && result.data !== null) {
          getResponseCache.set(requestKey, {
            expiresAt: Date.now() + cacheTtlMs,
            value: result as ApiResult<unknown>,
          });
        }
        return result;
      })
      .finally(() => {
        if (allowDedupe) {
          inFlightGetRequests.delete(requestKey);
        }
      });

    if (allowDedupe) {
      inFlightGetRequests.set(
        requestKey,
        trackedPromise as Promise<ApiResult<unknown>>,
      );
    }

    return trackedPromise;
  }

  return { request };
}
