import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { UserPlus, Trash2, X } from 'lucide-react'
import { useOrgs } from '@/hooks/useOrgs'
import {
  useOrgMembers, useUpdateMemberRole, useRemoveMember,
  useOrgInvitations, useRevokeInvite, useOrgRoles,
} from '@/hooks/useOrgMembers'
import InviteMemberModal from '@/components/org/InviteMemberModal'
import { useAuthStore } from '@/stores/authStore'
import { getApiError } from '@/lib/api'
import type { InviteRole } from '@/types'

// Fed from GET /orgs/roles at render time — see useOrgRoles below — rather
// than a hardcoded list, so a role added on the backend appears here
// without a frontend deploy.

export default function OrgMembersPage() {
  const { orgId } = useParams<{ orgId: string }>()
  const [showInvite, setShowInvite] = useState(false)

  const { data: orgs = [] } = useOrgs()
  const org = orgs.find((o) => o.id === orgId)
  const { data: members = [] } = useOrgMembers(orgId ?? '')
  const { data: invitations = [] } = useOrgInvitations(orgId ?? '')

  const updateRole = useUpdateMemberRole(orgId ?? '')
  const removeMember = useRemoveMember(orgId ?? '')
  const revokeInvite = useRevokeInvite(orgId ?? '')
  const user = useAuthStore((s) => s.user)

  const myMembership = members.find((m) => m.user_id === user?.id)
  const isAdmin = myMembership?.role === 'admin' || myMembership?.role === 'owner'
  const { data: roleData } = useOrgRoles()
  const invitableRoles = (roleData?.roles ?? []).filter((r) => r.invitable)
  // Multi-word role keys ('engineering_lead') read badly under CSS
  // capitalize; the catalogue's own label ('Engineering lead') is correct
  // and falls back to the raw key if the catalogue hasn't loaded yet.
  const roleLabel = (key: string) =>
    roleData?.roles.find((r) => r.key === key)?.label ?? key

  if (!orgId) return null

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="onto-label mb-1">Organization</p>
          <h1 className="text-2xl font-semibold text-foreground">{org?.name ?? 'Members'}</h1>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowInvite(true)}
            className="flex items-center gap-2 px-4 py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity"
          >
            <UserPlus className="h-4 w-4" />
            Invite member
          </button>
        )}
      </div>

      {/* Members table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              <th className="onto-label text-left px-4 py-3">Member</th>
              <th className="onto-label text-left px-4 py-3">Role</th>
              {isAdmin && <th className="onto-label text-right px-4 py-3">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-7 w-7 rounded bg-foreground/10 border border-border flex items-center justify-center text-[10px] font-semibold text-foreground shrink-0">
                      {m.user_name?.[0]?.toUpperCase() ?? '?'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{m.user_name ?? 'Unknown'}</p>
                      <p className="text-xs text-muted-foreground">{m.user_email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  {isAdmin && m.role !== 'owner' && m.user_id !== user?.id ? (
                    <select
                      value={m.role}
                      onChange={async (e) => {
                        try {
                          await updateRole.mutateAsync({ userId: m.user_id, role: e.target.value as InviteRole })
                          toast.success('Role updated')
                        } catch (err) {
                          toast.error(getApiError(err))
                        }
                      }}
                      className="text-xs border border-border rounded px-2 py-1 bg-background text-foreground focus:outline-none"
                    >
                      {invitableRoles.map((r) => (
                        <option key={r.key} value={r.key} title={r.description}>{r.label}</option>
                      ))}
                    </select>
                  ) : (
                    <span className="text-xs text-muted-foreground">{roleLabel(m.role)}</span>
                  )}
                </td>
                {isAdmin && (
                  <td className="px-4 py-3 text-right">
                    {m.role !== 'owner' && m.user_id !== user?.id && (
                      <button
                        onClick={async () => {
                          try {
                            await removeMember.mutateAsync(m.user_id)
                            toast.success('Member removed')
                          } catch (err) {
                            toast.error(getApiError(err))
                          }
                        }}
                        className="p-1.5 rounded text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pending invitations */}
      {isAdmin && invitations.length > 0 && (
        <div>
          <p className="onto-label mb-3">Pending invitations</p>
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="onto-label text-left px-4 py-3">Email</th>
                  <th className="onto-label text-left px-4 py-3">Role</th>
                  <th className="onto-label text-left px-4 py-3">Expires</th>
                  <th className="onto-label text-right px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {invitations.map((inv) => (
                  <tr key={inv.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3 text-sm text-foreground">{inv.email}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{roleLabel(inv.role)}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={async () => {
                          try {
                            await revokeInvite.mutateAsync(inv.id)
                            toast.success('Invitation revoked')
                          } catch (err) {
                            toast.error(getApiError(err))
                          }
                        }}
                        className="p-1.5 rounded text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showInvite && <InviteMemberModal orgId={orgId} onClose={() => setShowInvite(false)} />}
    </div>
  )
}
