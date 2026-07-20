import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { AlertTriangle } from 'lucide-react'
import { useOrgs, useUpdateOrg, useDeleteOrg } from '@/hooks/useOrgs'
import { useOrgStore } from '@/stores/orgStore'
import { useAuthStore } from '@/stores/authStore'
import { getApiError } from '@/lib/api'

export default function OrgSettingsPage() {
  const { orgId } = useParams<{ orgId: string }>()
  const navigate = useNavigate()
  const { data: orgs = [] } = useOrgs()
  const org = orgs.find((o) => o.id === orgId)

  const [name, setName] = useState(org?.name ?? '')
  const [showDelete, setShowDelete] = useState(false)

  const updateOrg = useUpdateOrg()
  const deleteOrg = useDeleteOrg()
  const { clearActiveOrg } = useOrgStore()
  const user = useAuthStore((s) => s.user)

  const isOwner = org?.role === 'owner'

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!orgId) return
    try {
      await updateOrg.mutateAsync({ id: orgId, name })
      toast.success('Organization updated')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleDelete() {
    if (!orgId) return
    try {
      await deleteOrg.mutateAsync(orgId)
      clearActiveOrg()
      toast.success('Organization deleted')
      window.location.href = '/dashboard'
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  if (!org) {
    return <p className="text-sm text-muted-foreground">Organization not found.</p>
  }

  return (
    <div className="max-w-lg">
      <p className="onto-label mb-1">Organization</p>
      <h1 className="text-2xl font-semibold text-foreground mb-1">{org.name}</h1>
      <p className="text-sm text-muted-foreground mb-6">Manage settings for your organization</p>

      {/* General settings */}
      <div className="bg-card border border-border rounded-lg p-5 mb-6">
        <h2 className="text-sm font-semibold text-foreground mb-4">General</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="onto-label mb-1.5 block">Organization name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!isOwner && org.role !== 'admin'}
              className="w-full px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground disabled:opacity-50"
            />
          </div>
          <div>
            <label className="onto-label mb-1.5 block">Slug</label>
            <p className="px-3 py-2 rounded border border-border bg-muted text-sm text-muted-foreground font-mono">{org.slug}</p>
          </div>
          {(isOwner || org.role === 'admin') && (
            <button
              type="submit"
              disabled={updateOrg.isPending}
              className="px-4 py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity disabled:opacity-50"
            >
              {updateOrg.isPending ? 'Saving...' : 'Save changes'}
            </button>
          )}
        </form>
      </div>

      {/* Danger zone — owner only */}
      {isOwner && (
        <div className="bg-card border border-red-200 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-red-600 mb-1">Danger zone</h2>
          <p className="text-xs text-muted-foreground mb-4">
            Deleting the organization permanently removes all its resources.
          </p>
          {!showDelete ? (
            <button
              onClick={() => setShowDelete(true)}
              className="px-4 py-2 rounded border border-red-300 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              Delete organization
            </button>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start gap-2 p-3 bg-red-50 rounded border border-red-200">
                <AlertTriangle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                <p className="text-xs text-red-700">
                  This action cannot be undone. All connections, skills, agents, pods, and projects in this organization will be permanently deleted.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDelete(false)}
                  className="flex-1 py-2 rounded border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleteOrg.isPending}
                  className="flex-1 py-2 rounded bg-red-600 text-white text-sm font-medium hover:opacity-85 transition-opacity disabled:opacity-50"
                >
                  {deleteOrg.isPending ? 'Deleting...' : 'Delete permanently'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
