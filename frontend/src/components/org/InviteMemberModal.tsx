import { useState } from 'react'
import { Copy, Check, X, AlertCircle, UserX, Ban } from 'lucide-react'
import { toast } from 'sonner'
import { useBulkInviteMembers, useOrgRoles, type BulkInviteResult } from '@/hooks/useOrgMembers'
import { getApiError } from '@/lib/api'
import type { InviteRole } from '@/types'

interface Props {
  orgId: string
  onClose: () => void
}

function parseEmails(raw: string): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const piece of raw.split(/[\s,;]+/)) {
    const email = piece.trim().toLowerCase()
    if (email && !seen.has(email)) {
      seen.add(email)
      out.push(email)
    }
  }
  return out
}

const STATUS_META: Record<BulkInviteResult['status'], { label: string; icon: typeof Check; className: string }> = {
  sent: { label: 'Invited', icon: Check, className: 'text-green-600' },
  already_member: { label: 'Already a member', icon: UserX, className: 'text-muted-foreground' },
  invalid: { label: 'Invalid email', icon: AlertCircle, className: 'text-destructive' },
  seat_limit: { label: 'Seat limit reached', icon: Ban, className: 'text-[#E8632A]' },
}

export default function InviteMemberModal({ orgId, onClose }: Props) {
  const [emailsText, setEmailsText] = useState('')
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
  const [results, setResults] = useState<BulkInviteResult[] | null>(null)
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null)

  const bulkInvite = useBulkInviteMembers(orgId)
  const emails = parseEmails(emailsText)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const data = await bulkInvite.mutateAsync({ emails, role })
      setResults(data.results)
      if (data.sent > 0) toast.success(`Sent ${data.sent} invitation${data.sent === 1 ? '' : 's'}`)
      if (data.skipped > 0) toast.warning(`${data.skipped} address${data.skipped === 1 ? '' : 'es'} skipped — see details below`)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  function copyUrl(email: string, url: string) {
    navigator.clipboard.writeText(url)
    setCopiedEmail(email)
    setTimeout(() => setCopiedEmail((cur) => (cur === email ? null : cur)), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-foreground/20">
      <div className="bg-card border border-border rounded-lg w-full max-w-md shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Invite members</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-border/60 text-muted-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {results ? (
          <div className="p-5 space-y-4">
            <p className="text-sm text-muted-foreground">
              {results.length} address{results.length === 1 ? '' : 'es'} processed.
            </p>
            <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1">
              {results.map((r) => {
                const meta = STATUS_META[r.status]
                const Icon = meta.icon
                return (
                  <div
                    key={r.email}
                    className="flex items-center gap-2 p-2.5 bg-muted rounded border border-border"
                  >
                    <Icon className={`h-3.5 w-3.5 shrink-0 ${meta.className}`} />
                    <span className="flex-1 text-xs text-foreground truncate font-mono">{r.email}</span>
                    <span className={`text-xs shrink-0 ${meta.className}`}>{meta.label}</span>
                    {r.status === 'sent' && r.invite_url && (
                      <button
                        onClick={() => copyUrl(r.email, r.invite_url!)}
                        title="Copy invite link"
                        className="shrink-0 p-1 rounded hover:bg-border/60 text-muted-foreground"
                      >
                        {copiedEmail === r.email ? (
                          <Check className="h-3.5 w-3.5 text-green-600" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    )}
                  </div>
                )
              })}
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
              <label className="onto-label mb-1.5 block">Email addresses</label>
              <textarea
                required
                rows={4}
                value={emailsText}
                onChange={(e) => setEmailsText(e.target.value)}
                placeholder="colleague@company.com, another@company.com&#10;or one per line"
                className="w-full px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground resize-none"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Paste as many as you like, separated by commas, spaces or new lines.
                {emails.length > 0 && ` ${emails.length} address${emails.length === 1 ? '' : 'es'} detected.`}
              </p>
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
                disabled={bulkInvite.isPending || emails.length === 0}
                className="flex-1 py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity disabled:opacity-50"
              >
                {bulkInvite.isPending
                  ? 'Sending...'
                  : emails.length > 1
                  ? `Send ${emails.length} invites`
                  : 'Send invite'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
