/**
 * Re-export from shared API client. All HTTP logic lives in shared/api/apiClient.ts.
 */
export {
  createApiClient,
  type ApiClientOptions,
  type RequestOptions,
  type ApiResult,
  type RequestFn
} from '~/shared/api/apiClient'
