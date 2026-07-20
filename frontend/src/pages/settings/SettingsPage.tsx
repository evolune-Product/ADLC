import { useState, useEffect } from 'react'
import { CheckCircle2, XCircle, Key } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSettings, useUpdateProfile } from '@/hooks/useSettings'

export default function SettingsPage() {
  const { data, isLoading } = useSettings()
  const updateMutation = useUpdateProfile()

  const [name,    setName]    = useState('')
  const [orgName, setOrgName] = useState('')
  const [init,    setInit]    = useState(false)

  if (!init && data) {
    setName(data.user.name ?? '')
    setOrgName(data.user.org_name ?? '')
    setInit(true)
  }

  function handleSave(e: React.FormEvent) {
    e.preventDefault()
    updateMutation.mutate({ name, org_name: orgName })
  }

  if (isLoading) {
    return (
      <div className="max-w-lg space-y-4">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="h-48 rounded-lg border bg-muted/40 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="max-w-lg space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your profile and platform configuration.</p>
      </div>

      {/* Profile */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b pb-2">Profile</h2>

        <div className="space-y-1.5">
          <Label>Email</Label>
          <Input value={data?.user.email ?? ''} disabled className="bg-muted/30" />
          <p className="text-xs text-muted-foreground">Email cannot be changed.</p>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name">Display Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="org">Organisation</Label>
            <Input
              id="org"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Your organisation"
            />
          </div>

          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? 'Saving…' : 'Save Profile'}
          </Button>
        </form>
      </section>

      {/* LLM Config */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b pb-2">LLM Configuration</h2>

        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="text-sm font-medium">Anthropic API Key</span>
            {data?.api_key_configured
              ? <CheckCircle2 className="h-4 w-4 text-green-500 ml-auto shrink-0" />
              : <XCircle      className="h-4 w-4 text-red-500   ml-auto shrink-0" />
            }
          </div>

          {data?.api_key_configured ? (
            <p className="text-xs font-mono text-muted-foreground bg-muted/30 rounded px-3 py-1.5">
              {data.api_key_hint ?? '••••••••••••••••'}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              No API key configured. Set <code className="text-xs bg-muted rounded px-1">ANTHROPIC_API_KEY</code> in
              your <code className="text-xs bg-muted rounded px-1">backend/.env</code> and restart the server.
            </p>
          )}
        </div>

        <div className="rounded-lg border p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Default Model</span>
            <span className="ml-auto text-sm font-mono text-muted-foreground">
              {data?.llm_model ?? 'claude-sonnet-4-6'}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            The default model used by agents. Override per-agent in the Agents section.
          </p>
        </div>
      </section>
    </div>
  )
}
