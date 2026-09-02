import { Badge } from '@/components/ui/badge'
import type { FindingSeverity } from '@/types/simulation'

const VARIANT: Record<FindingSeverity, 'destructive' | 'warning' | 'secondary' | 'outline'> = {
  critical: 'destructive',
  high: 'warning',
  medium: 'secondary',
  low: 'outline',
}

export function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  return <Badge variant={VARIANT[severity] ?? 'secondary'}>{severity}</Badge>
}

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-muted-foreground',
  running: 'bg-amber-500 animate-pulse',
  completed: 'bg-emerald-500',
  failed: 'bg-destructive',
}

export function StatusDot({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[status] ?? 'bg-muted-foreground'}`} />
      <span className="text-xs font-medium capitalize">{status}</span>
    </span>
  )
}
