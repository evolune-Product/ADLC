import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useEffect } from 'react'
import { toast } from 'sonner'

import ErrorBoundary from '@/components/ErrorBoundary'
import LandingPage from '@/pages/landing/LandingPage'
import AuthLayout from '@/layouts/AuthLayout'
import DashboardLayout from '@/layouts/DashboardLayout'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import GoogleCallbackPage from '@/pages/auth/GoogleCallbackPage'
import GitHubCallbackPage from '@/pages/auth/GitHubCallbackPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import ConnectionsPage from '@/pages/connections/ConnectionsPage'
import SkillsPage from '@/pages/skills/SkillsPage'
import NewSkillPage from '@/pages/skills/NewSkillPage'
import SkillDetailPage from '@/pages/skills/SkillDetailPage'
import AgentsPage from '@/pages/agents/AgentsPage'
import NewAgentPage from '@/pages/agents/NewAgentPage'
import AgentDetailPage from '@/pages/agents/AgentDetailPage'
import PodsPage from '@/pages/pods/PodsPage'
import NewPodPage from '@/pages/pods/NewPodPage'
import PodDetailPage from '@/pages/pods/PodDetailPage'
import ProjectsPage from '@/pages/projects/ProjectsPage'
import NewProjectPage from '@/pages/projects/NewProjectPage'
import ProjectDetailPage from '@/pages/projects/ProjectDetailPage'
import TicketDetailPage from '@/pages/projects/TicketDetailPage'
import RunsPage from '@/pages/runs/RunsPage'
import RunDetailPage from '@/pages/runs/RunDetailPage'
import AuditPage from '@/pages/audit/AuditPage'
import SettingsPage from '@/pages/settings/SettingsPage'
import NewOrgPage from '@/pages/org/NewOrgPage'
import OrgSettingsPage from '@/pages/org/OrgSettingsPage'
import OrgMembersPage from '@/pages/org/OrgMembersPage'
import AcceptInvitePage from '@/pages/org/AcceptInvitePage'
import BillingPage from '@/pages/billing/BillingPage'
import AnalyticsPage from '@/pages/analytics/AnalyticsPage'
import MarketplacePage from '@/pages/marketplace/MarketplacePage'
import PoliciesPage from '@/pages/governance/PoliciesPage'
import DeveloperPage from '@/pages/governance/DeveloperPage'
import CompliancePage from '@/pages/governance/CompliancePage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'

import { useAuthStore } from '@/stores/authStore'
import { isAuthenticated } from '@/lib/auth'
import api, { getApiError } from '@/lib/api'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
    mutations: {
      onError: (err) => {
        // Global fallback — individual hooks can override with their own onError
        // Only fires if the hook hasn't already handled it
        const msg = getApiError(err)
        if (msg !== 'Something went wrong') toast.error(msg)
      },
    },
  },
})

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RedirectIfAuthed({ children }: { children: React.ReactNode }) {
  if (isAuthenticated()) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function AppInit() {
  const { setUser, isAuthenticated: authed } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated() && !authed) {
      api.get('/auth/me').then((res) => {
        setUser(res.data)
        // If the user was redirected here from an invitation link, send them back
        const inviteToken = sessionStorage.getItem('invite_token')
        if (inviteToken) {
          sessionStorage.removeItem('invite_token')
          window.location.href = `/invitations/${inviteToken}`
        }
      }).catch(() => {})
    }
  }, [authed, setUser])

  return null
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppInit />
          <Routes>
            {/* Auth routes */}
            <Route element={<RedirectIfAuthed><AuthLayout /></RedirectIfAuthed>}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>

            {/* Dashboard routes */}
            <Route element={<RequireAuth><DashboardLayout /></RequireAuth>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/connections" element={<ConnectionsPage />} />
              <Route path="/skills" element={<SkillsPage />} />
              <Route path="/skills/new" element={<NewSkillPage />} />
              <Route path="/skills/:id" element={<SkillDetailPage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/agents/new" element={<NewAgentPage />} />
              <Route path="/agents/:id" element={<AgentDetailPage />} />
              <Route path="/pods" element={<PodsPage />} />
              <Route path="/pods/new" element={<NewPodPage />} />
              <Route path="/pods/:id" element={<PodDetailPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/new" element={<NewProjectPage />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
              <Route path="/projects/:id/tickets/:ticketId" element={<TicketDetailPage />} />
              <Route path="/runs" element={<RunsPage />} />
              <Route path="/runs/:runId" element={<RunDetailPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/billing" element={<BillingPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/marketplace" element={<MarketplacePage />} />
              <Route path="/policies" element={<PoliciesPage />} />
              <Route path="/developer" element={<DeveloperPage />} />
              <Route path="/compliance" element={<CompliancePage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route path="/org/new" element={<NewOrgPage />} />
              <Route path="/org/:orgId/settings" element={<OrgSettingsPage />} />
              <Route path="/org/:orgId/members" element={<OrgMembersPage />} />
            </Route>

            {/* Public invitation accept page — no auth wrapper, handles redirect itself */}
            <Route path="/invitations/:token" element={<AcceptInvitePage />} />

            <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
            <Route path="/auth/github/callback" element={<GitHubCallbackPage />} />
            <Route path="/" element={<LandingPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          <Toaster richColors position="top-right" />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
