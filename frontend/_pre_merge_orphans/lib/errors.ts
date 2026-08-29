/**
 * Typed API error class and multi-shape parser.
 *
 * Handles four response shapes in priority order:
 *   1. New canonical  { error_code, message, request_id }
 *   2. Legacy         { detail: string }
 *   3. Legacy Pydantic{ detail: [{ msg }] }
 *   4. HTTP status fallbacks + network error
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly errorCode: string,
    public readonly httpStatus: number,
    public readonly requestId?: string,
    public readonly detail?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// ─── Response shape types ─────────────────────────────────────────────────────

type CanonicalError = {
  error_code: string
  message: string
  request_id?: string
  detail?: string
}

type LegacyStringDetail = { detail: string }
type LegacyArrayDetail  = { detail: Array<{ msg: string }> }

type AxiosLikeError = {
  response?: {
    status?: number
    data?: unknown
    headers?: Record<string, string>
  }
  message?: string
}

// ─── Parser ───────────────────────────────────────────────────────────────────

/**
 * Extract a human-readable error message from an Axios/fetch error.
 * Returns `fallback` only when no message can be determined.
 */
export function parseApiError(
  err: unknown,
  fallback = 'Something went wrong',
): string {
  const e = err as AxiosLikeError
  const data = e?.response?.data as Record<string, unknown> | undefined
  const status = e?.response?.status

  // 1. Canonical shape from app.core.errors
  if (data && typeof data['message'] === 'string' && data['error_code']) {
    return data['message'] as string
  }

  // 2. Legacy FastAPI string detail
  if (data && typeof data['detail'] === 'string') {
    return data['detail'] as string
  }

  // 3. Legacy Pydantic validation array
  if (data && Array.isArray(data['detail'])) {
    const msgs = (data['detail'] as Array<{ msg?: string }>)
      .map((d) => d.msg)
      .filter(Boolean)
    if (msgs.length > 0) return msgs.join('; ')
  }

  // 4. HTTP status fallbacks
  if (status === 429) return 'Too many requests. Please slow down.'
  if (status === 502 || status === 503) return 'Service temporarily unavailable. Please try again.'
  if (status === 401) return 'Your session has expired. Please log in again.'
  if (status === 403) return 'You do not have permission to perform this action.'
  if (status === 404) return 'The requested resource was not found.'

  // 5. Network error
  if (!e?.response && e?.message === 'Network Error') {
    return 'Cannot connect to the server. Check your connection.'
  }

  return fallback
}

/**
 * Extract the request_id from an error response for bug report display.
 */
export function getRequestId(err: unknown): string | undefined {
  const e = err as AxiosLikeError
  const data = e?.response?.data as Record<string, unknown> | undefined
  if (data && typeof data['request_id'] === 'string') {
    return data['request_id'] as string
  }
  // Also check response header
  return e?.response?.headers?.['x-request-id']
}
