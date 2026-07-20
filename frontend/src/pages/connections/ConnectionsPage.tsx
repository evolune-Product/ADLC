import { useState } from 'react'
import { Plus, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatsGrid } from '@/components/ui/StatsGrid'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ConnectionCard } from '@/components/connections/ConnectionCard'
import { AddConnectionModal } from '@/components/connections/AddConnectionModal'
import { useConnections } from '@/hooks/useConnections'

export default function ConnectionsPage() {
  const [modalOpen, setModalOpen] = useState(false)
  const { data: connections = [], isLoading } = useConnections()

  const connected = connections.filter((c) => c.status === 'connected').length
  const errors    = connections.filter((c) => c.status === 'error').length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Connections"
        subtitle="Manage your GitHub, GitLab, and Jira integrations."
        action={
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Connection
          </Button>
        }
      />

      <StatsGrid
        stats={[
          { label: 'Total',     value: connections.length },
          { label: 'Connected', value: connected },
          { label: 'Errors',    value: errors },
        ]}
      />

      {isLoading ? (
        <LoadingSkeleton height="h-20" />
      ) : connections.length === 0 ? (
        <EmptyState
          icon={<Link2 className="h-10 w-10" />}
          title="No connections yet"
          subtitle="Add a GitHub, GitLab, or Jira connection to get started."
          action={
            <Button variant="outline" onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Connection
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {connections.map((connection) => (
            <ConnectionCard key={connection.id} connection={connection} />
          ))}
        </div>
      )}

      <AddConnectionModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
