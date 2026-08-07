import { Download, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { useCompliance } from '@/hooks/usePlatform'

const STATUS_STYLE: Record<string, string> = {
  enforced: 'bg-emerald-600',
  configured: 'bg-emerald-600',
  available: 'bg-[#E8632A]',
  default: 'bg-[#E8632A]',
}

export default function CompliancePage() {
  const { data, isLoading } = useCompliance()
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  if (isLoading || !data) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Governance</p>
      <PageHeader
        title="Compliance posture"
        subtitle="What is actually configured on this install — not what the product is capable of."
        action={
          <a href={`${apiBase}/compliance/evidence.csv?days=90`} download>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" /> Evidence export
            </Button>
          </a>
        }
      />

      <div className="bg-card rounded-lg border border-border divide-y divide-border">
        {data.controls.map((c) => (
          <div key={c.id} className="px-4 py-3.5 flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="font-medium">{c.name}</p>
              <p className="text-sm text-muted-foreground mt-0.5">{c.evidence}</p>
            </div>
            <span className="flex items-center gap-1.5 shrink-0 text-sm">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  STATUS_STYLE[c.status.split(' ')[0]] ?? 'bg-muted-foreground'
                }`}
              />
              {c.status}
            </span>
          </div>
        ))}
      </div>

      <div className="bg-card rounded-lg border border-border p-5">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="h-4 w-4" />
          <p className="font-medium">What the evidence export contains</p>
        </div>
        <p className="text-sm text-muted-foreground">
          One row per governed run: which change was proposed, what the Reviewer agent found, which
          humans approved it, when, and which environments it reached. This is the artefact for the
          question "show me that a human approved every production change" — and the transparency
          record EU AI Act Article 50 expects from 2 August 2026 for AI-generated content.
        </p>
        <p className="text-sm text-muted-foreground mt-3">
          Deployment mode: <strong>{data.deployment_mode}</strong> · audit retention:{' '}
          <strong>{data.audit_retention_days} days</strong> (enforced nightly).
        </p>
      </div>
    </div>
  )
}
