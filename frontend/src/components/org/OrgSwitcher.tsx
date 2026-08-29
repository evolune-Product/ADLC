import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, Building2, User, Plus, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useOrgStore } from '@/stores/orgStore'
import { useOrgs, useCanCreateOrg } from '@/hooks/useOrgs'
import type { Organization } from '@/types'

export default function OrgSwitcher() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { activeOrg, setActiveOrg } = useOrgStore()
  const { data: orgs = [] } = useOrgs()
  const { data: canCreate } = useCanCreateOrg()

  function switchTo(org: Organization | null) {
    setActiveOrg(org)
    setOpen(false)
    // Reload to flush TanStack Query cache so all data refetches under the new context
    window.location.reload()
  }

  const label = activeOrg ? activeOrg.name : 'Personal'

  return (
    <div className="relative px-2 mb-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded border border-border bg-card text-sm text-foreground hover:bg-muted transition-colors"
      >
        <div className="h-5 w-5 rounded bg-foreground/10 border border-border flex items-center justify-center shrink-0">
          {activeOrg ? (
            <Building2 className="h-3 w-3 text-foreground" />
          ) : (
            <User className="h-3 w-3 text-foreground" />
          )}
        </div>
        <span className="flex-1 text-left truncate text-xs font-medium">{label}</span>
        <ChevronDown className={cn('h-3 w-3 text-muted-foreground shrink-0 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute left-2 right-2 top-full mt-1 z-50 bg-card border border-border rounded-lg shadow-lg overflow-hidden">
          {/* Personal workspace */}
          <button
            onClick={() => switchTo(null)}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-muted transition-colors"
          >
            <User className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <span className="flex-1 font-medium text-foreground">Personal</span>
            {!activeOrg && <Check className="h-3 w-3 text-[#E8632A]" />}
          </button>

          {orgs.length > 0 && (
            <div className="border-t border-border">
              {orgs.map((org) => (
                <button
                  key={org.id}
                  onClick={() => switchTo(org)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-muted transition-colors"
                >
                  <Building2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span className="flex-1 font-medium text-foreground truncate">{org.name}</span>
                  {activeOrg?.id === org.id && <Check className="h-3 w-3 text-[#E8632A]" />}
                </button>
              ))}
            </div>
          )}

          {canCreate?.allowed && (
            <div className="border-t border-border">
              <button
                onClick={() => { setOpen(false); navigate('/org/new') }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                Create organization
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
