import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useCreateOrg } from '@/hooks/useOrgs'
import { useOrgStore } from '@/stores/orgStore'
import { getApiError } from '@/lib/api'

export default function NewOrgPage() {
  const [name, setName] = useState('')
  const navigate = useNavigate()
  const createOrg = useCreateOrg()
  const setActiveOrg = useOrgStore((s) => s.setActiveOrg)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const org = await createOrg.mutateAsync({ name })
      setActiveOrg(org)
      toast.success('Organization created')
      window.location.href = '/dashboard'
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <p className="onto-label mb-1">Organizations</p>
      <h1 className="text-2xl font-semibold text-foreground mb-6">Create organization</h1>

      <div className="bg-card border border-border rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="onto-label mb-1.5 block">Organization name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Corp"
              className="w-full px-3 py-2 rounded border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex-1 py-2 rounded border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createOrg.isPending || !name.trim()}
              className="flex-1 py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity disabled:opacity-50"
            >
              {createOrg.isPending ? 'Creating...' : 'Create organization'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
