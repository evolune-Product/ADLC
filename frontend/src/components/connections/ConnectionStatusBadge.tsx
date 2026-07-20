import type { ConnectionStatus } from '@/types'

const config: Record<ConnectionStatus, { label: string; classes: string }> = {
  connected: { label: 'Connected', classes: 'bg-green-100 text-green-700' },
  pending:   { label: 'Pending',   classes: 'bg-yellow-100 text-yellow-700' },
  error:     { label: 'Error',     classes: 'bg-red-100 text-red-700' },
}

export function ConnectionStatusBadge({ status }: { status: ConnectionStatus }) {
  const { label, classes } = config[status] ?? config.pending
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>
      {label}
    </span>
  )
}
