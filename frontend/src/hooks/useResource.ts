/**
 * useResource — Generic CRUD hook factory
 * ----------------------------------------
 * Generates the five standard data hooks for any REST resource so each
 * individual hook file doesn't repeat the same boilerplate.
 *
 * Pattern
 * -------
 *   const skillHooks = createResourceHooks<Skill>({
 *     key:      'skills',      // TanStack Query cache key
 *     endpoint: '/skills',     // API base path (no trailing slash)
 *     label:    'Skill',       // Used in toast messages ("Skill created")
 *   })
 *
 *   export const useSkills       = skillHooks.useList
 *   export const useSkill        = skillHooks.useDetail
 *   export const useCreateSkill  = skillHooks.useCreate
 *   export const useUpdateSkill  = skillHooks.useUpdate
 *   export const useDeleteSkill  = skillHooks.useDelete
 *
 * Custom hooks that don't fit this pattern (e.g. useToggleAgent,
 * useDuplicatePod) are written as normal hooks in their own files.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '@/lib/api'

type ApiError = { response?: { data?: { detail?: string } } }

interface ResourceConfig {
  /** TanStack Query cache key, e.g. 'skills' */
  key: string
  /** API base path without trailing slash, e.g. '/skills' */
  endpoint: string
  /** Human-readable singular label used in toast messages, e.g. 'Skill' */
  label: string
}

export function createResourceHooks<TItem>(config: ResourceConfig) {
  const { key, endpoint, label } = config
  const KEY = [key]

  /** Fetch the full list. */
  function useList() {
    return useQuery<TItem[]>({
      queryKey: KEY,
      queryFn: () => api.get(`${endpoint}/`).then((r) => r.data),
    })
  }

  /** Fetch a single item by ID. Skips the request when `id` is empty. */
  function useDetail(id: string) {
    return useQuery<TItem>({
      queryKey: [...KEY, id],
      queryFn: () => api.get(`${endpoint}/${id}`).then((r) => r.data),
      enabled: !!id,
    })
  }

  /** POST a new item. Invalidates the list cache on success. */
  function useCreate<TBody = Partial<TItem>>() {
    const qc = useQueryClient()
    return useMutation<TItem, ApiError, TBody>({
      mutationFn: (data) => api.post(`${endpoint}/`, data).then((r) => r.data),
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: KEY })
        toast.success(`${label} created`)
      },
      onError: (err) => {
        toast.error(err.response?.data?.detail ?? `Failed to create ${label.toLowerCase()}`)
      },
    })
  }

  /** PUT updated fields for a specific item. Invalidates list + detail cache. */
  function useUpdate(id: string) {
    const qc = useQueryClient()
    return useMutation<TItem, ApiError, Partial<TItem>>({
      mutationFn: (data) => api.put(`${endpoint}/${id}`, data).then((r) => r.data),
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: KEY })
        qc.invalidateQueries({ queryKey: [...KEY, id] })
        toast.success(`${label} updated`)
      },
      onError: () => toast.error(`Failed to update ${label.toLowerCase()}`),
    })
  }

  /** DELETE by ID. Invalidates the list cache on success. */
  function useDelete() {
    const qc = useQueryClient()
    return useMutation<void, ApiError, string>({
      mutationFn: (id) => api.delete(`${endpoint}/${id}`),
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: KEY })
        toast.success(`${label} deleted`)
      },
      onError: () => toast.error(`Failed to delete ${label.toLowerCase()}`),
    })
  }

  return { useList, useDetail, useCreate, useUpdate, useDelete, KEY }
}
