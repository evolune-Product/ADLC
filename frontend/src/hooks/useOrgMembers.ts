import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { OrgMember, OrgInvitation, InviteRole } from '@/types'

export function useOrgMembers(orgId: string) {
  return useQuery<OrgMember[]>({
    queryKey: ['org-members', orgId],
    queryFn: () => api.get(`/orgs/${orgId}/members`).then((r) => r.data),
    enabled: !!orgId,
  })
}

export function useUpdateMemberRole(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: InviteRole }) =>
      api.put(`/orgs/${orgId}/members/${userId}`, { role }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['org-members', orgId] }),
  })
}

export function useRemoveMember(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => api.delete(`/orgs/${orgId}/members/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['org-members', orgId] }),
  })
}

export function useLeaveOrg() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (orgId: string) => api.post(`/orgs/${orgId}/leave`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orgs'] }),
  })
}

export function useOrgInvitations(orgId: string) {
  return useQuery<OrgInvitation[]>({
    queryKey: ['org-invitations', orgId],
    queryFn: () => api.get(`/orgs/${orgId}/invitations`).then((r) => r.data),
    enabled: !!orgId,
  })
}

export function useInviteMember(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { email: string; role: InviteRole }) =>
      api.post(`/orgs/${orgId}/invitations`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['org-invitations', orgId] }),
  })
}

export function useRevokeInvite(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (invId: string) => api.delete(`/orgs/${orgId}/invitations/${invId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['org-invitations', orgId] }),
  })
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: (token: string) =>
      api.post(`/invitations/${token}/accept`).then((r) => r.data),
  })
}
