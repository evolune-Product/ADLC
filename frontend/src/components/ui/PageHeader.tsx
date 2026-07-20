/**
 * PageHeader
 * ----------
 * Top section of every dashboard page: title, optional subtitle, optional action button.
 *
 * Usage:
 *   <PageHeader
 *     title="Skill Registry"
 *     subtitle="Reusable markdown-based capabilities injected into agents."
 *     action={
 *       <Button onClick={() => navigate('/skills/new')}>
 *         <Plus className="h-4 w-4 mr-2" /> New Skill
 *       </Button>
 *     }
 *   />
 */

import { type ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  /** Rendered on the right side — typically a primary action button. */
  action?: ReactNode
}

export function PageHeader({ title, subtitle, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
