/**
 * Departments — the org-chart layer. `app/routers/departments.py` has existed
 * since an earlier Company OS session; no frontend hook consumed it yet
 * (Desk reads its own summary endpoint, not this CRUD surface). Written for
 * the onboarding wizard's "create initial departments" step — real gap, not
 * scope creep: without it, step 21 would have nothing to call.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export interface Department {
  id: string
  organization_id: string
  name: string
  slug: string
  description: string | null
  icon: string | null
  head_user_id: string | null
  status: string
  created_at: string
  updated_at: string
}

const KEY = ['departments']

export function useDepartments() {
  return useQuery<Department[]>({
    queryKey: KEY,
    queryFn: () => api.get('/departments/').then((r) => r.data),
  })
}

export function useCreateDepartment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string; icon?: string }) =>
      api.post('/departments/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}
