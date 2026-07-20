import { GitBranch, Building2, Zap, Trash2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ConnectionStatusBadge } from './ConnectionStatusBadge'
import { useDeleteConnection, useTestConnection } from '@/hooks/useConnections'
import type { Connection, ConnectionType } from '@/types'

const TYPE_META: Record<ConnectionType, { label: string; Icon: React.ElementType }> = {
  github:         { label: 'GitHub',         Icon: GitBranch },
  gitlab:         { label: 'GitLab',         Icon: GitBranch },
  jira:           { label: 'Jira',           Icon: Building2 },
  github_actions: { label: 'GitHub Actions', Icon: Zap },
}

export function ConnectionCard({ connection }: { connection: Connection }) {
  const { label, Icon } = TYPE_META[connection.type] ?? { label: connection.type, Icon: Building2 }
  const deleteMutation = useDeleteConnection()
  const testMutation = useTestConnection()

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
          <Icon className="h-5 w-5" />
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{connection.name}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
          {connection.workspace_url && (
            <p className="text-xs text-muted-foreground truncate">{connection.workspace_url}</p>
          )}
        </div>

        <ConnectionStatusBadge status={connection.status} />

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => testMutation.mutate(connection.id)}
            disabled={testMutation.isPending}
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${testMutation.isPending ? 'animate-spin' : ''}`} />
            Test
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => deleteMutation.mutate(connection.id)}
            disabled={deleteMutation.isPending}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
