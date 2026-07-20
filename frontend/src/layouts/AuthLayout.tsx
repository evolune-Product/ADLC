import { Outlet, Link } from 'react-router-dom'

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Minimal top bar */}
      <header className="border-b border-border px-6 h-12 flex items-center shrink-0">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-foreground flex items-center justify-center">
            <span className="text-background text-[9px] font-black">A</span>
          </div>
          <span className="text-sm font-semibold tracking-tight text-foreground">Agentic SDLC</span>
        </Link>
      </header>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <Outlet />
        </div>
      </div>

      <footer className="border-t border-border px-6 h-10 flex items-center shrink-0">
        <p className="text-[11px] text-muted-foreground">
          AI-powered software development lifecycle platform.
        </p>
      </footer>
    </div>
  )
}
