import { Link } from 'react-router-dom'
import { AlertCircle, ArrowRight } from 'lucide-react'
import { useUsageLimits } from '@/hooks/useUsageLimits'

export default function UsageLimitsCard() {
  const { data, isLoading } = useUsageLimits()

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <div className="h-6 w-32 bg-muted animate-pulse rounded" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 bg-muted animate-pulse rounded" />
          ))}
        </div>
      </div>
    )
  }

  if (!data) return null

  const items = [
    { label: 'Projects', ...data.projects },
    { label: 'Agents', ...data.agents },
    { label: 'Pods', ...data.pods },
    { label: 'Skills', ...data.skills },
    { label: 'GitHub', ...data.github_connections },
    { label: 'Jira', ...data.jira_connections },
  ]

  const atLimit = items.some((item) => item.used >= item.limit)

  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold">Free Plan Usage</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Your current usage vs limits
          </p>
        </div>
        {atLimit && (
          <AlertCircle className="h-5 w-5 text-[#E8632A] shrink-0" />
        )}
      </div>

      <div className="space-y-3">
        {items.map((item) => {
          const percentage = (item.used / item.limit) * 100
          const isAtLimit = item.used >= item.limit
          const isNearLimit = percentage >= 80

          return (
            <div key={item.label} className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <span className={isAtLimit ? 'text-[#E8632A] font-medium' : 'text-foreground'}>
                  {item.label}
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  {item.used} / {item.limit}
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full transition-all ${
                    isAtLimit
                      ? 'bg-[#E8632A]'
                      : isNearLimit
                      ? 'bg-yellow-500'
                      : 'bg-foreground'
                  }`}
                  style={{ width: `${Math.min(percentage, 100)}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      <Link
        to="/pricing"
        className="flex items-center justify-between w-full px-4 py-2.5 rounded-md bg-foreground text-background hover:opacity-85 transition-opacity text-sm font-medium group"
      >
        <span>Upgrade to Teams</span>
        <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
      </Link>
    </div>
  )
}
