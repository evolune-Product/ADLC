import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useEffect } from 'react'
import { toast } from 'sonner'

import ErrorBoundary from '@/components/ErrorBoundary'
import LandingPage from '@/pages/landing/LandingPage'
import PricingPage from '@/pages/landing/PricingPage'
import SecurityPage from '@/pages/landing/SecurityPage'
import HowItWorksPage from '@/pages/landing/HowItWorksPage'
import TheGatePage from '@/pages/landing/TheGatePage'
import PlatformPage from '@/pages/landing/PlatformPage'
import AuthLayout from '@/layouts/AuthLayout'
import DashboardLayout from '@/layouts/DashboardLayout'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import GoogleCallbackPage from '@/pages/auth/GoogleCallbackPage'
import GitHubCallbackPage from '@/pages/auth/GitHubCallbackPage'
import SsoCallbackPage from '@/pages/auth/SsoCallbackPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import CompanyDashboardPage from '@/pages/dashboard/CompanyDashboardPage'
import DeskPage from '@/pages/desk/DeskPage'
import WorkflowsPage from '@/pages/workflows/WorkflowsPage'
import NewWorkflowPage from '@/pages/workflows/NewWorkflowPage'
import WorkflowDetailPage from '@/pages/workflows/WorkflowDetailPage'
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
import PersonasPage from '@/pages/personas/PersonasPage'
import NewPersonaPage from '@/pages/personas/NewPersonaPage'
import PersonaDetailPage from '@/pages/personas/PersonaDetailPage'
import SimulationsPage from '@/pages/simulations/SimulationsPage'
import SimulationDetailPage from '@/pages/simulations/SimulationDetailPage'
import AuditPage from '@/pages/audit/AuditPage'
import SettingsPage from '@/pages/settings/SettingsPage'
import NewOrgPage from '@/pages/org/NewOrgPage'
import OnboardingPage from '@/pages/onboarding/OnboardingPage'
import OrgSettingsPage from '@/pages/org/OrgSettingsPage'
import OrgMembersPage from '@/pages/org/OrgMembersPage'
import AcceptInvitePage from '@/pages/org/AcceptInvitePage'
import BillingPage from '@/pages/billing/BillingPage'
import AnalyticsPage from '@/pages/analytics/AnalyticsPage'
import PulsePage from '@/pages/analytics/PulsePage'
import MarketplacePage from '@/pages/marketplace/MarketplacePage'
import PoliciesPage from '@/pages/governance/PoliciesPage'
import DeveloperPage from '@/pages/governance/DeveloperPage'
import CompliancePage from '@/pages/governance/CompliancePage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'
import WorkspacePage from '@/pages/workspace/WorkspacePage'
import ProvidersPage from '@/pages/settings/ProvidersPage'

import NotFoundPage from '@/pages/NotFoundPage'

import { useAuthStore } from '@/stores/authStore'
import { isAuthenticated } from '@/lib/auth'
import api, { getApiError } from '@/lib/api'
import { connectSocket, joinUserRoom } from '@/lib/socket'

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

/** How often the client tells the server it is still here. Must be comfortably
 *  under the server's PRESENCE_TTL (5 minutes) or an active user goes grey. */
const PRESENCE_HEARTBEAT_MS = 90_000

function AppInit() {
  const { setUser, user, isAuthenticated: authed } = useAuthStore()

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

  // The socket is connected once for the whole session rather than per page.
  // The workspace needs it everywhere — a DM that arrives while you are on the
  // Runs page has to light up the sidebar there, not on the next refresh.
  useEffect(() => {
    if (!user?.id) return
    connectSocket()
    joinUserRoom(user.id)

    // Presence heartbeat. Every failure is swallowed: being shown as offline is
    // a cosmetic problem, and a toast about it on every tick would not be.
    const beat = () => { api.put('/workspace/presence', { status: 'active' }).catch(() => {}) }
    beat()
    const timer = setInterval(beat, PRESENCE_HEARTBEAT_MS)

    // Coming back to the tab is the strongest signal that someone is present,
    // and the cheapest place to catch a heartbeat the browser froze while the
    // tab was backgrounded.
    const onVisible = () => { if (document.visibilityState === 'visible') beat() }
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [user?.id])

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
              <Route path="/desk" element={<DeskPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/company" element={<CompanyDashboardPage />} />
              <Route path="/onboarding" element={<OnboardingPage />} />
              <Route path="/connections" element={<ConnectionsPage />} />
              {/* /plugins merged into /connections — the old Plugins gallery
                  is now what /connections renders. Redirect rather than 404
                  anyone with the old URL bookmarked. */}
              <Route path="/plugins" element={<Navigate to="/connections" replace />} />
              <Route path="/providers" element={<ProvidersPage />} />
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
              <Route path="/personas" element={<PersonasPage />} />
              <Route path="/personas/new" element={<NewPersonaPage />} />
              <Route path="/personas/:id" element={<PersonaDetailPage />} />
              <Route path="/simulations" element={<SimulationsPage />} />
              <Route path="/simulations/:id" element={<SimulationDetailPage />} />
              <Route path="/workflows" element={<WorkflowsPage />} />
              <Route path="/workflows/new" element={<NewWorkflowPage />} />
              <Route path="/workflows/:id" element={<WorkflowDetailPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/billing" element={<BillingPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/pulse" element={<PulsePage />} />
              <Route path="/marketplace" element={<MarketplacePage />} />
              <Route path="/policies" element={<PoliciesPage />} />
              <Route path="/developer" element={<DeveloperPage />} />
              <Route path="/compliance" element={<CompliancePage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              {/* Both forms render the same page; the bare path picks a
                  channel rather than showing an empty pane. */}
              <Route path="/workspace" element={<WorkspacePage />} />
              <Route path="/workspace/:channelId" element={<WorkspacePage />} />
              <Route path="/org/new" element={<NewOrgPage />} />
              <Route path="/org/:orgId/settings" element={<OrgSettingsPage />} />
              <Route path="/org/:orgId/members" element={<OrgMembersPage />} />
            </Route>

            {/* Public invitation accept page — no auth wrapper, handles redirect itself */}
            <Route path="/invitations/:token" element={<AcceptInvitePage />} />

            <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
            <Route path="/auth/github/callback" element={<GitHubCallbackPage />} />
            <Route path="/auth/sso/callback" element={<SsoCallbackPage />} />
            <Route path="/" element={<LandingPage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/security" element={<SecurityPage />} />
            <Route path="/how-it-works" element={<HowItWorksPage />} />
            <Route path="/the-gate" element={<TheGatePage />} />
            <Route path="/platform" element={<PlatformPage />} />
            {/* A real 404. This used to redirect every unknown URL to
                /dashboard, which sent signed-out visitors who mistyped a path —
                or followed a stale link — through /dashboard to /login, and
                told search engines that every 404 was a soft redirect. */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
          <Toaster richColors position="top-right" />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
