import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Link2, BookOpen, Bot, Layers,
  FolderOpen, Play, ClipboardList, Settings, LogOut,
  Menu, X, Users, Building2,
  BarChart3, CreditCard, Shield, Store, Terminal, FileCheck,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'
import { useOrgStore } from '@/stores/orgStore'
import OrgSwitcher from '@/components/org/OrgSwitcher'
import NotificationBell from '@/components/notifications/NotificationBell'

const NAV = [
  {
    items: [
      { label: 'Dashboard',   to: '/dashboard',   icon: LayoutDashboard },
    ],
  },
  {
    group: 'Build',
    items: [
      { label: 'Connections', to: '/connections', icon: Link2 },
      { label: 'Skills',      to: '/skills',      icon: BookOpen },
      { label: 'Agents',      to: '/agents',      icon: Bot },
      { label: 'Pods',        to: '/pods',        icon: Layers },
      { label: 'Marketplace', to: '/marketplace', icon: Store },
    ],
  },
  {
    group: 'Work',
    items: [
      { label: 'Projects',    to: '/projects',    icon: FolderOpen },
      { label: 'Runs',        to: '/runs',        icon: Play },
    ],
  },
  {
    group: 'Observe',
    items: [
      { label: 'Insights',    to: '/analytics',   icon: BarChart3 },
      { label: 'Audit Log',   to: '/audit',       icon: ClipboardList },
      { label: 'Compliance',  to: '/compliance',  icon: FileCheck },
    ],
  },
  {
    group: 'Govern',
    items: [
      { label: 'Policies',    to: '/policies',    icon: Shield },
      { label: 'Developer',   to: '/developer',   icon: Terminal },
      { label: 'Billing',     to: '/billing',     icon: CreditCard },
      { label: 'Settings',    to: '/settings',    icon: Settings },
    ],
  },
]

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const activeOrg = useOrgStore((s) => s.activeOrg)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 w-56 flex flex-col',
        'bg-background border-r border-border',
        'transition-transform duration-200 ease-in-out',
        open ? 'translate-x-0' : '-translate-x-full',
        'lg:static lg:translate-x-0 lg:transition-none',
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-4 h-12 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-foreground flex items-center justify-center">
            <span className="text-background text-[9px] font-black tracking-tight">A</span>
          </div>
          <span className="text-sm font-semibold tracking-tight text-foreground">Agentic SDLC</span>
        </div>
        <button
          onClick={onClose}
          className="lg:hidden p-1 rounded hover:bg-border/60 text-muted-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        {/* Org switcher sits above all nav groups */}
        <OrgSwitcher />
        {/* Org-specific links when inside an org */}
        {activeOrg && (
          <div>
            <p className="onto-label px-2 mb-1.5">Organization</p>
            <div className="space-y-0.5">
              <NavLink
                to={`/org/${activeOrg.id}/members`}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2.5 px-2.5 py-1.5 rounded text-sm transition-colors',
                    isActive
                      ? 'bg-foreground text-background font-medium'
                      : 'text-muted-foreground hover:text-foreground hover:bg-black/5',
                  )
                }
              >
                <Users className="h-3.5 w-3.5 shrink-0" />
                Members
              </NavLink>
              {(activeOrg.role === 'owner' || activeOrg.role === 'admin') && (
                <NavLink
                  to={`/org/${activeOrg.id}/settings`}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-2.5 px-2.5 py-1.5 rounded text-sm transition-colors',
                      isActive
                        ? 'bg-foreground text-background font-medium'
                        : 'text-muted-foreground hover:text-foreground hover:bg-black/5',
                    )
                  }
                >
                  <Building2 className="h-3.5 w-3.5 shrink-0" />
                  Org settings
                </NavLink>
              )}
            </div>
          </div>
        )}
        {NAV.map((section, si) => (
          <div key={si}>
            {section.group && (
              <p className="onto-label px-2 mb-1.5">{section.group}</p>
            )}
            <div className="space-y-0.5">
              {section.items.map(({ label, to, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-2.5 px-2.5 py-1.5 rounded text-sm transition-colors',
                      isActive
                        ? 'bg-foreground text-background font-medium'
                        : 'text-muted-foreground hover:text-foreground hover:bg-black/5',
                    )
                  }
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" />
                  {label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="border-t border-border p-3 shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <div className="h-6 w-6 rounded bg-foreground/10 border border-border flex items-center justify-center text-[10px] font-semibold text-foreground shrink-0">
            {user?.name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-foreground truncate">{user?.name ?? 'User'}</p>
            <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs text-muted-foreground hover:text-foreground hover:bg-black/5 transition-colors"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  )
}

// ─── Topbar ───────────────────────────────────────────────────────────────────

function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <header className="h-12 border-b border-border bg-background flex items-center px-4 shrink-0 gap-3">
      <button
        onClick={onMenuClick}
        className="lg:hidden p-1.5 -ml-1 rounded hover:bg-border/60 text-muted-foreground"
        aria-label="Toggle sidebar"
      >
        <Menu className="h-4 w-4" />
      </button>
      <span className="lg:hidden text-sm font-semibold text-foreground">Agentic SDLC</span>
      {/* The approval gate is worthless if the reviewer never hears about it. */}
      <div className="ml-auto">
        <NotificationBell />
      </div>
    </header>
  )
}

// ─── Layout ───────────────────────────────────────────────────────────────────

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-foreground/20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Topbar onMenuClick={() => setSidebarOpen((v) => !v)} />
        <main className="flex-1 overflow-y-auto p-5 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
