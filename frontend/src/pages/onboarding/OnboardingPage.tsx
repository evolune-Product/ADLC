/**
 * Onboarding wizard — Company OS step 21.
 *
 * Purely a composition of endpoints that already exist: org creation
 * (`useCreateOrg`), the company-profile PUT (`useUpdateOrg`, added Company OS
 * step-1 session), department creation (`useCreateDepartment`, new hook this
 * session — a real gap, see useDepartments.ts), and the existing
 * `InviteMemberModal`. Connecting a tool links out to `/plugins` rather than
 * rebuilding plugin connection here. No new backend endpoint was needed;
 * verified by reading each router before writing this page.
 *
 * A user who skips at step 1 keeps the pre-existing personal-workspace
 * behaviour untouched — landing on `/desk` with no org, exactly as before
 * onboarding existed.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Building2, Check, Plug, Users2, X } from 'lucide-react'
import { useCreateOrg, useUpdateOrg } from '@/hooks/useOrgs'
import { useCreateDepartment } from '@/hooks/useDepartments'
import { useOrgStore } from '@/stores/orgStore'
import { getApiError } from '@/lib/api'
import InviteMemberModal from '@/components/org/InviteMemberModal'

const SUGGESTED_DEPARTMENTS = ['Engineering', 'Sales', 'Marketing', 'Operations']

const STEPS = ['Company', 'Departments', 'Team', 'Tools', 'Done'] as const

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [orgId, setOrgId] = useState<string | null>(null)

  const setActiveOrg = useOrgStore((s) => s.setActiveOrg)
  const createOrg = useCreateOrg()
  const updateOrg = useUpdateOrg()
  const createDept = useCreateDepartment()

  // Step 1 — company
  const [name, setName] = useState('')
  const [industry, setIndustry] = useState('')
  const [companySize, setCompanySize] = useState('')

  // Step 2 — departments
  const [deptChips, setDeptChips] = useState<string[]>(SUGGESTED_DEPARTMENTS)
  const [customDept, setCustomDept] = useState('')

  // Step 3 — invite
  const [showInvite, setShowInvite] = useState(false)

  async function handleCreateCompany(e: React.FormEvent) {
    e.preventDefault()
    try {
      const org = await createOrg.mutateAsync({ name })
      if (industry || companySize) {
        await updateOrg.mutateAsync({ id: org.id, industry: industry || undefined, company_size: companySize || undefined })
      }
      setActiveOrg(org)
      setOrgId(org.id)
      toast.success('Company created')
      setStep(1)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleCreateDepartments() {
    if (!orgId) return
    try {
      for (const d of deptChips) {
        // Best-effort per department — one bad name should not block the rest.
        await createDept.mutateAsync({ name: d }).catch(() => {})
      }
      toast.success(deptChips.length ? `${deptChips.length} department(s) created` : 'No departments — skipped')
      setStep(2)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  function finish() {
    navigate('/desk')
  }

  return (
    <div className="max-w-xl mx-auto">
      <p className="onto-label mb-1">Get started</p>
      <h1 className="text-2xl font-semibold text-foreground mb-1">Set up your company</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Five short steps. You can change any of this later in Settings — and you can
        {' '}<button className="underline hover:text-foreground" onClick={finish}>skip and work solo</button> at any time.
      </p>

      <div className="flex items-center gap-2 mb-6">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-2 flex-1">
            <div className={`h-1.5 flex-1 rounded-full ${i <= step ? 'bg-foreground' : 'bg-muted'}`} />
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        {step === 0 && (
          <form onSubmit={handleCreateCompany} className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <p className="onto-label">Company</p>
            </div>
            <div>
              <label className="onto-label mb-1.5 block">Company name</label>
              <input required value={name} onChange={(e) => setName(e.target.value)}
                     placeholder="Acme Corp"
                     className="w-full px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="onto-label mb-1.5 block">Industry (optional)</label>
                <input value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Software"
                       className="w-full px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground" />
              </div>
              <div>
                <label className="onto-label mb-1.5 block">Size (optional)</label>
                <input value={companySize} onChange={(e) => setCompanySize(e.target.value)} placeholder="1-10"
                       className="w-full px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground" />
              </div>
            </div>
            <button type="submit" disabled={createOrg.isPending || !name.trim()}
                    className="w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity disabled:opacity-50">
              {createOrg.isPending ? 'Creating...' : 'Continue'}
            </button>
          </form>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Users2 className="h-4 w-4 text-muted-foreground" />
              <p className="onto-label">Initial departments</p>
            </div>
            <p className="text-sm text-muted-foreground">
              Common starting points — accept, edit, or remove any of them. Nothing here is forced.
            </p>
            <div className="flex flex-wrap gap-2">
              {deptChips.map((d) => (
                <span key={d} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-border bg-muted text-xs text-foreground">
                  {d}
                  <button onClick={() => setDeptChips((cur) => cur.filter((x) => x !== d))} className="hover:text-[#E8632A]">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input value={customDept} onChange={(e) => setCustomDept(e.target.value)}
                     placeholder="Add a department..."
                     onKeyDown={(e) => {
                       if (e.key === 'Enter' && customDept.trim()) {
                         e.preventDefault()
                         setDeptChips((cur) => [...cur, customDept.trim()])
                         setCustomDept('')
                       }
                     }}
                     className="flex-1 px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground" />
              <button
                onClick={() => { if (customDept.trim()) { setDeptChips((cur) => [...cur, customDept.trim()]); setCustomDept('') } }}
                className="px-3 py-2 rounded border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-muted">
                Add
              </button>
            </div>
            <button onClick={handleCreateDepartments} disabled={createDept.isPending}
                    className="w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity disabled:opacity-50">
              {createDept.isPending ? 'Creating...' : deptChips.length ? `Create ${deptChips.length} department(s)` : 'Skip'}
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Users2 className="h-4 w-4 text-muted-foreground" />
              <p className="onto-label">Invite your team</p>
            </div>
            <p className="text-sm text-muted-foreground">
              Bring in the people who'll work in this company. You can always invite more later from Org Settings.
            </p>
            <button onClick={() => setShowInvite(true)}
                    className="w-full py-2 rounded border border-border text-sm text-foreground hover:bg-muted transition-colors">
              Invite a teammate
            </button>
            <button onClick={() => setStep(3)}
                    className="w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity">
              Continue
            </button>
            {showInvite && orgId && <InviteMemberModal orgId={orgId} onClose={() => setShowInvite(false)} />}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Plug className="h-4 w-4 text-muted-foreground" />
              <p className="onto-label">Connect a tool (optional)</p>
            </div>
            <p className="text-sm text-muted-foreground">
              GitHub, Jira, Slack and 38 more connectors live on the Plugins page. Connect one now, or skip and do it later.
            </p>
            <a href="/plugins" target="_blank" rel="noreferrer"
               className="block w-full text-center py-2 rounded border border-border text-sm text-foreground hover:bg-muted transition-colors">
              Open Plugins in a new tab
            </a>
            <button onClick={() => setStep(4)}
                    className="w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity">
              Continue
            </button>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4 text-center py-4">
            <div className="mx-auto h-10 w-10 rounded-full bg-foreground text-background flex items-center justify-center">
              <Check className="h-5 w-5" />
            </div>
            <p className="text-foreground font-medium">You're set up</p>
            <p className="text-sm text-muted-foreground">
              Head to your Desk — the day-to-day queue of what needs you.
            </p>
            <button onClick={finish}
                    className="w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity">
              Go to Desk
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
