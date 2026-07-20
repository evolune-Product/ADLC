/**
 * EmptyState
 * ----------
 * Dashed-border empty placeholder shown when a list has no items.
 *
 * Usage:
 *   <EmptyState
 *     icon={<Bot className="h-10 w-10" />}
 *     title="No agents yet"
 *     subtitle="Create an agent by combining skills."
 *     action={
 *       <Button variant="outline" onClick={() => navigate('/agents/new')}>
 *         <Plus className="h-4 w-4 mr-2" /> New Agent
 *       </Button>
 *     }
 *   />
 */

import { type ReactNode } from 'react'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  subtitle?: string
  /** Optional CTA button or any node rendered below the text. */
  action?: ReactNode
}

export function EmptyState({ icon, title, subtitle, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 gap-3">
      <div className="text-muted-foreground">{icon}</div>
      <div className="text-center">
        <p className="font-medium">{title}</p>
        {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
