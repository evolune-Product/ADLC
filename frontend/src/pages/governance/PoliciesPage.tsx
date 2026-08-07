import { useState } from 'react'
import { Plus, Shield, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { useDeletePolicy, usePolicies, useSavePolicy } from '@/hooks/usePlatform'
import type { ApprovalPolicy, Severity } from '@/types/platform'

const SEVERITIES: (Severity | '')[] = ['', 'low', 'medium', 'high', 'critical']
const ENVIRONMENTS = ['*', 'dev', 'qa', 'staging', 'production']

const EMPTY = {
  name: '',
  environment: 'production',
  min_approvers: 1,
  approver_roles: ['owner', 'admin'],
  require_review_pass: true,
  min_review_score: 70,
  block_on_severity: 'high' as Severity | null,
  protected_paths: [] as string[],
  protected_branches: [] as string[],
  max_files_changed: 0,
  max_run_cost_cents: 0,
  is_active: true,
}

function PolicyForm({ initial, onSave, onCancel, saving }: {
  initial: Partial<ApprovalPolicy>
  onSave: (p: Record<string, unknown>) => void
  onCancel: () => void
  saving: boolean
}) {
  const [form, setForm] = useState({ ...EMPTY, ...initial })
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }))

  return (
    <div className="bg-card rounded-lg border border-foreground p-5 space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1">
          <span className="onto-label">Policy name</span>
          <input
            value={form.name}
            onChange={(e) => set({ name: e.target.value })}
            placeholder="Production deploys"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </label>
        <label className="space-y-1">
          <span className="onto-label">Environment</span>
          <select
            value={form.environment}
            onChange={(e) => set({ environment: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {ENVIRONMENTS.map((e) => (
              <option key={e} value={e}>{e === '*' ? 'All environments' : e}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <label className="space-y-1">
          <span className="onto-label">Required approvers</span>
          <input
            type="number" min={1} max={10} value={form.min_approvers}
            onChange={(e) => set({ min_approvers: Number(e.target.value) })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </label>
        <label className="space-y-1">
          <span className="onto-label">Min review score</span>
          <input
            type="number" min={0} max={100} value={form.min_review_score}
            onChange={(e) => set({ min_review_score: Number(e.target.value) })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </label>
        <label className="space-y-1">
          <span className="onto-label">Block at severity</span>
          <select
            value={form.block_on_severity ?? ''}
            onChange={(e) => set({ block_on_severity: (e.target.value || null) as Severity | null })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>{s || 'Never block'}</option>
            ))}
          </select>
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox" checked={form.require_review_pass}
          onChange={(e) => set({ require_review_pass: e.target.checked })}
        />
        Require the Reviewer agent to produce a passing verdict before deploy
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1">
          <span className="onto-label">Protected paths (one per line)</span>
          <textarea
            rows={3}
            value={form.protected_paths.join('\n')}
            onChange={(e) => set({ protected_paths: e.target.value.split('\n').filter(Boolean) })}
            placeholder={'infra/**\n**/migrations/**\n.github/workflows/*'}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
          />
        </label>
        <label className="space-y-1">
          <span className="onto-label">Protected branches (one per line)</span>
          <textarea
            rows={3}
            value={form.protected_branches.join('\n')}
            onChange={(e) => set({ protected_branches: e.target.value.split('\n').filter(Boolean) })}
            placeholder={'main\nrelease/*'}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
          />
        </label>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1">
          <span className="onto-label">Max files changed (0 = unlimited)</span>
          <input
            type="number" min={0} value={form.max_files_changed}
            onChange={(e) => set({ max_files_changed: Number(e.target.value) })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </label>
        <label className="space-y-1">
          <span className="onto-label">Max run cost, cents (0 = plan default)</span>
          <input
            type="number" min={0} value={form.max_run_cost_cents}
            onChange={(e) => set({ max_run_cost_cents: Number(e.target.value) })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </label>
      </div>

      <div className="flex gap-2">
        <Button disabled={!form.name || saving} onClick={() => onSave(form)}>Save policy</Button>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  )
}

export default function PoliciesPage() {
  const { data, isLoading } = usePolicies()
  const save = useSavePolicy()
  const remove = useDeletePolicy()
  const [editing, setEditing] = useState<Partial<ApprovalPolicy> | null>(null)

  if (isLoading) return <LoadingSkeleton />
  const policies = data?.policies ?? []

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Governance</p>
      <PageHeader
        title="Approval policies"
        subtitle="What an agent may touch, who must approve, and what it may cost — evaluated on every deploy."
        action={
          !editing && (
            <Button onClick={() => setEditing({})}>
              <Plus className="h-4 w-4 mr-2" /> New policy
            </Button>
          )
        }
      />

      {editing && (
        <PolicyForm
          initial={editing}
          saving={save.isPending}
          onCancel={() => setEditing(null)}
          onSave={(form) =>
            save.mutate({ ...(form as Partial<ApprovalPolicy>), id: editing.id },
              { onSuccess: () => setEditing(null) })
          }
        />
      )}

      {policies.length === 0 && !editing ? (
        <div className="bg-card rounded-lg border border-dashed border-border p-12 text-center">
          <Shield className="h-8 w-8 mx-auto text-muted-foreground" />
          <p className="font-medium mt-3">Running on the default policy</p>
          <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
            One approver, no reviewer gate, nothing path-protected. That is fine for a pilot —
            add a policy before you point this at a production repo.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {policies.map((p) => (
            <div key={p.id} className="bg-card rounded-lg border border-border p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{p.name}</p>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      {p.environment === '*' ? 'all envs' : p.environment}
                    </span>
                    {!p.is_active && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                        inactive
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1.5">
                    {p.min_approvers} approver{p.min_approvers === 1 ? '' : 's'}
                    {p.require_review_pass && ` · review ≥ ${p.min_review_score}`}
                    {p.block_on_severity && ` · blocks on ${p.block_on_severity}+`}
                    {p.max_files_changed > 0 && ` · ≤ ${p.max_files_changed} files`}
                  </p>
                  {(p.protected_paths.length > 0 || p.protected_branches.length > 0) && (
                    <p className="text-xs text-muted-foreground mt-1 font-mono truncate">
                      protected: {[...p.protected_paths, ...p.protected_branches].join(', ')}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="outline" onClick={() => setEditing(p)}>Edit</Button>
                  <Button size="sm" variant="outline" onClick={() => remove.mutate(p.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
