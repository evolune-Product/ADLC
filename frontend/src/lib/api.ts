import axios from 'axios'
import { useOrgStore } from '@/stores/orgStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  const activeOrg = useOrgStore.getState().activeOrg
  if (activeOrg) config.headers['X-Org-ID'] = activeOrg.id
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ─── Error extraction utility ────────────────────────────────────────────────

type ApiErr = {
  response?: {
    status?: number
    data?: { detail?: string | Array<{ msg: string }> }
  }
  message?: string
}

/**
 * Extract a human-readable error message from an Axios error.
 * Handles FastAPI validation errors (detail array), plain string details,
 * network errors, and common HTTP status codes.
 */
export function getApiError(err: unknown, fallback = 'Something went wrong'): string {
  const e = err as ApiErr

  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg).join('; ')
  }

  const status = e?.response?.status
  if (status === 502 || status === 503) return 'Service temporarily unavailable. Please try again.'
  if (status === 429) return 'Too many requests. Please slow down.'
  if (!e?.response && e?.message === 'Network Error') {
    return 'Cannot connect to the server. Check your connection.'
  }

  return fallback
}

export default api
