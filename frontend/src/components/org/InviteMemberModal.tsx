import { useState } from 'react'
import { Copy, Check, X } from 'lucide-react'
import { toast } from 'sonner'
import { useInviteMember, useOrgRoles } from '@/hooks/useOrgMembers'
import { getApiError } from '@/lib/api'
import type { InviteRole } from '@/types'

interface Props {
  orgId: string
  onClose: () => void
}

export default function InviteMemberModal({ orgId, onClose }: Props) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<InviteRole>('member')
  const { data: roleData } = useOrgRoles()
  // The invite form only ever offers roles the invitee can actually be
  // assigned — owner is deliberately absent from the catalogue's
  // invitable set, since ownership moves by transfer, not by invite.
  const roles = (roleData?.roles ?? []).filter((r) => r.invitable)
  const grouped = roles.reduce<Record<string, typeof roles>>((acc, r) => {
    (acc[r.category] ??= []).push(r)
    return acc
  }, {})
  const [inviteUrl, setInviteUrl] = useState('')
  const [copied, setCopied] = useState(false)

  const invite = useInviteMember(orgId)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const data = await invite.mutateAsync({ email, role })
      setInviteUrl(data.invite_url || '')
      toast.success('Invitation created')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  function copyUrl() {
    navigator.clipboard.writeText(inviteUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-foreground/20">
      <div className="bg-card border border-border rounded-lg w-full max-w-md shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Invite member</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-border/60 text-muted-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {inviteUrl ? (
          <div className="p-5 space-y-4">
            <p className="text-sm text-muted-foreground">
              Share this link with the invitee. It expires in 7 days.
            </p>
            <div className="flex items-center gap-2 p-3 bg-muted rounded border border-border">
              <span className="flex-1 text-xs text-foreground break-all font-mono">{inviteUrl}</span>
              <button
                onClick={copyUrl}
                className="shrink-0 p-1.5 rounded hover:bg-border/60 text-muted-foreground"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
            <button
              onClick={onClose}
              className="w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            <div>
              <label className="onto-label mb-1.5 block">Email address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="w-full px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground"
              />
            </div>

            <div>
              <label className="onto-label mb-1.5 block">Role</label>
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {Object.entries(grouped).map(([category, items]) => (
                  <div key={category}>
                    <p className="onto-label mb-1 capitalize">{category}</p>
                    <div className="space-y-1.5">
                      {items.map((r) => (
                        <label key={r.key} className="flex items-start gap-3 cursor-pointer group">
                          <input
                            type="radio"
                            name="role"
                            value={r.key}
                            checked={role === r.key}
                            onChange={() => setRole(r.key)}
                            className="mt-0.5"
                          />
                          <div>
                            <p className="text-sm font-medium text-foreground">{r.label}</p>
                            <p className="text-xs text-muted-foreground">{r.description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2 rounded border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={invite.isPending}
                className="flex-1 py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity disabled:opacity-50"
              >
                {invite.isPending ? 'Creating...' : 'Create invite link'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
