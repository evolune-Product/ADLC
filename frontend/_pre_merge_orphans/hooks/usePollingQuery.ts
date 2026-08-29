/**
 * usePollingQuery — wraps TanStack Query with error-backoff polling.
 *
 * Doubles the refetch interval on each consecutive error, capped at maxBackoffMs.
 * Uses useRef for the error count to avoid triggering re-renders.
 *
 * Usage:
 *   const query = usePollingQuery({
 *     queryKey: ['run', runId],
 *     queryFn: () => api.get(`/runs/${runId}`).then(r => r.data),
 *     shouldPoll: (data) => ['queued', 'running'].includes(data?.status ?? ''),
 *     baseIntervalMs: 3000,
 *     maxBackoffMs: 60_000,
 *   })
 */
import { useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { UseQueryOptions, UseQueryResult } from '@tanstack/react-query'

export interface UsePollingQueryOptions<TData, TError = unknown>
  extends Omit<UseQueryOptions<TData, TError>, 'refetchInterval'> {
  /** Return true while the query should keep polling */
  shouldPoll: (data: TData | undefined) => boolean
  /** Normal poll interval in ms (default 3000) */
  baseIntervalMs?: number
  /** Maximum backoff interval after errors in ms (default 60_000) */
  maxBackoffMs?: number
}

export function usePollingQuery<TData, TError = unknown>(
  options: UsePollingQueryOptions<TData, TError>,
): UseQueryResult<TData, TError> {
  const {
    shouldPoll,
    baseIntervalMs = 3_000,
    maxBackoffMs = 60_000,
    ...queryOptions
  } = options

  // Track consecutive error count without causing re-renders
  const errorCountRef = useRef(0)

  return useQuery<TData, TError>({
    ...queryOptions,
    refetchInterval: (query) => {
      if (!shouldPoll(query.state.data)) return false

      if (query.state.status === 'error') {
        errorCountRef.current += 1
        // Exponential backoff: base * 2^errorCount, capped at max
        const interval = Math.min(
          baseIntervalMs * 2 ** errorCountRef.current,
          maxBackoffMs,
        )
        return interval
      }

      // Successful fetch — reset error counter
      errorCountRef.current = 0
      return baseIntervalMs
    },
  })
}
