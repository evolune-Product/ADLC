import { useState } from 'react'
import { Shield, Users, Building2, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePlatformStats, useSetUserPlan, useSetOrgPlan } from '@/hooks/useAdmin'
import { useAuthStore } from '@/stores/authStore'
import { Navigate } from 'react-router-dom'

const PLATFORM_ADMIN_EMAIL = 'harshilhk@evolune.in'

export default function AdminPage() {
  const { user } = useAuthStore()
  const { data: stats, isLoading } = usePlatformStats()
  const setUserPlanMutation = useSetUserPlan()
  const setOrgPlanMutation = useSetOrgPlan()

  const [userId, setUserId] = useState('')
  const [userPlan, setUserPlan] = useState('free')
  const [orgId, setOrgId] = useState('')
  const [orgPlan, setOrgPlan] = useState('teams')

  // Only platform admin can access
  if (user?.email !== PLATFORM_ADMIN_EMAIL) {
    return <Navigate to="/dashboard" replace />
  }

  function handleSetUserPlan(e: React.FormEvent) {
    e.preventDefault()
    if (!userId.trim()) return alert('Enter user ID')
    setUserPlanMutation.mutate({ userId, planType: userPlan })
  }

  function handleSetOrgPlan(e: React.FormEvent) {
    e.preventDefault()
    if (!orgId.trim()) return alert('Enter organization ID')
    setOrgPlanMutation.mutate({ orgId, planType: orgPlan })
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Shield className="h-4 w-4 text-[#E8632A]" />
          <p className="onto-label">Platform Admin</p>
        </div>
        <h1 className="text-2xl font-semibold">Admin Controls</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage plans and view platform statistics
        </p>
      </div>

      {/* Platform Stats */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b pb-2">Platform Statistics</h2>

        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 rounded-lg border bg-muted/40 animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                icon={Users}
                label="Total Users"
                value={stats?.total_users ?? 0}
              />
              <StatCard
                icon={Building2}
                label="Organizations"
                value={stats?.total_organizations ?? 0}
              />
              <StatCard
                icon={TrendingUp}
                label="Free Users"
                value={stats?.free_users ?? 0}
              />
              <StatCard
                icon={TrendingUp}
                label="Paid Users"
                value={(stats?.teams_users ?? 0) + (stats?.enterprise_users ?? 0)}
              />
            </div>

            <div className="rounded-lg border bg-card p-4">
              <p className="text-xs font-semibold text-muted-foreground mb-3">Breakdown</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Teams Users</p>
                  <p className="text-lg font-semibold text-foreground">{stats?.teams_users ?? 0}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Enterprise Users</p>
                  <p className="text-lg font-semibold text-foreground">{stats?.enterprise_users ?? 0}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Teams Orgs</p>
                  <p className="text-lg font-semibold text-foreground">{stats?.teams_orgs ?? 0}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Enterprise Orgs</p>
                  <p className="text-lg font-semibold text-foreground">{stats?.enterprise_orgs ?? 0}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Legacy Orgs</p>
                  <p className="text-lg font-semibold text-foreground">{stats?.legacy_orgs ?? 0}</p>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Set User Plan */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b pb-2">Set User Plan</h2>
        <form onSubmit={handleSetUserPlan} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="user-id">User ID (UUID)</Label>
            <Input
              id="user-id"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g., 123e4567-e89b-12d3-a456-426614174000"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="user-plan">Plan Type</Label>
            <select
              id="user-plan"
              value={userPlan}
              onChange={(e) => setUserPlan(e.target.value)}
              className="flex h-9 w-full rounded-md border border-border bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="free">Free</option>
              <option value="teams">Teams</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          <Button type="submit" disabled={setUserPlanMutation.isPending}>
            {setUserPlanMutation.isPending ? 'Updating...' : 'Set User Plan'}
          </Button>
        </form>
      </section>

      {/* Set Org Plan */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b pb-2">Set Organization Plan</h2>
        <form onSubmit={handleSetOrgPlan} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="org-id">Organization ID (UUID)</Label>
            <Input
              id="org-id"
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              placeholder="e.g., 123e4567-e89b-12d3-a456-426614174000"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="org-plan">Plan Type</Label>
            <select
              id="org-plan"
              value={orgPlan}
              onChange={(e) => setOrgPlan(e.target.value)}
              className="flex h-9 w-full rounded-md border border-border bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="teams">Teams</option>
              <option value="enterprise">Enterprise</option>
              <option value="legacy">Legacy</option>
            </select>
          </div>

          <Button type="submit" disabled={setOrgPlanMutation.isPending}>
            {setOrgPlanMutation.isPending ? 'Updating...' : 'Set Organization Plan'}
          </Button>
        </form>
      </section>
    </div>
  )
}

function StatCard({ icon: Icon, label, value }: { icon: any; label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
      <p className="text-2xl font-bold text-foreground">{value}</p>
    </div>
  )
}
