import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { GitBranch, Building2, Zap } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreateConnection } from '@/hooks/useConnections'
import type { ConnectionType } from '@/types'

// ─── Provider grid ───────────────────────────────────────────────────────────

// `LucideIcon`, not `React.ElementType`: the latter is a union of every
// intrinsic tag, so React 19's types intersect their props and `className`
// resolves to `never`.
const PROVIDERS: { type: ConnectionType; label: string; description: string; Icon: LucideIcon }[] = [
  { type: 'github',         label: 'GitHub',         description: 'Source control & CI/CD',   Icon: GitBranch },
  { type: 'gitlab',         label: 'GitLab',         description: 'Source control & CI/CD',   Icon: GitBranch },
  { type: 'jira',           label: 'Jira',           description: 'Issue tracker',             Icon: Building2 },
  { type: 'github_actions', label: 'GitHub Actions', description: 'CI/CD pipelines',          Icon: Zap },
]

// ─── Schemas ─────────────────────────────────────────────────────────────────

const gitSchema = z.object({
  name:         z.string().min(1, 'Required'),
  access_token: z.string().min(1, 'Personal Access Token is required'),
})

const jiraSchema = z.object({
  name:          z.string().min(1, 'Required'),
  workspace_url: z.string().url('Must be a valid URL (e.g. https://yourorg.atlassian.net)'),
  email:         z.string().email('Must be a valid email'),
  access_token:  z.string().min(1, 'API token is required'),
})

type GitForm  = z.infer<typeof gitSchema>
type JiraForm = z.infer<typeof jiraSchema>

// ─── Component ───────────────────────────────────────────────────────────────

interface Props {
  open: boolean
  onClose: () => void
}

export function AddConnectionModal({ open, onClose }: Props) {
  const [selectedType, setSelectedType] = useState<ConnectionType | null>(null)
  const createMutation = useCreateConnection()

  function handleClose() {
    setSelectedType(null)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Connection</DialogTitle>
          <DialogDescription>
            {selectedType ? 'Fill in the details below.' : 'Choose a provider to connect.'}
          </DialogDescription>
        </DialogHeader>

        {!selectedType ? (
          <div className="grid grid-cols-2 gap-3 mt-2">
            {PROVIDERS.map(({ type, label, description, Icon }) => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className="flex flex-col items-start gap-2 rounded-lg border p-4 text-left hover:bg-accent transition-colors"
              >
                <Icon className="h-6 w-6" />
                <div>
                  <p className="font-medium text-sm">{label}</p>
                  <p className="text-xs text-muted-foreground">{description}</p>
                </div>
              </button>
            ))}
          </div>
        ) : selectedType === 'jira' ? (
          <JiraForm
            onSubmit={(data) =>
              createMutation.mutate(
                { ...data, type: 'jira' },
                { onSuccess: handleClose },
              )
            }
            onBack={() => setSelectedType(null)}
            loading={createMutation.isPending}
          />
        ) : (
          <GitForm
            type={selectedType}
            onSubmit={(data) =>
              createMutation.mutate(
                { ...data, type: selectedType },
                { onSuccess: handleClose },
              )
            }
            onBack={() => setSelectedType(null)}
            loading={createMutation.isPending}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

// ─── GitHub / GitLab form ────────────────────────────────────────────────────

function GitForm({
  type,
  onSubmit,
  onBack,
  loading,
}: {
  type: ConnectionType
  onSubmit: (data: GitForm) => void
  onBack: () => void
  loading: boolean
}) {
  const { register, handleSubmit, formState: { errors } } = useForm<GitForm>({
    resolver: zodResolver(gitSchema),
  })
  const label = type === 'github' ? 'GitHub' : type === 'gitlab' ? 'GitLab' : 'GitHub Actions'

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
      <div className="space-y-1.5">
        <Label>Connection name</Label>
        <Input placeholder={`My ${label}`} {...register('name')} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label>Personal Access Token</Label>
        <Input type="password" placeholder="ghp_xxxxxxxxxxxx" {...register('access_token')} />
        {errors.access_token && <p className="text-xs text-destructive">{errors.access_token.message}</p>}
        <p className="text-xs text-muted-foreground">
          Needs <code>repo</code> and <code>user</code> scopes.
        </p>
      </div>

      <div className="flex gap-2 justify-end pt-2">
        <Button type="button" variant="outline" onClick={onBack}>Back</Button>
        <Button type="submit" disabled={loading}>{loading ? 'Connecting…' : 'Connect'}</Button>
      </div>
    </form>
  )
}

// ─── Jira form ───────────────────────────────────────────────────────────────

function JiraForm({
  onSubmit,
  onBack,
  loading,
}: {
  onSubmit: (data: JiraForm) => void
  onBack: () => void
  loading: boolean
}) {
  const { register, handleSubmit, formState: { errors } } = useForm<JiraForm>({
    resolver: zodResolver(jiraSchema),
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
      <div className="space-y-1.5">
        <Label>Connection name</Label>
        <Input placeholder="My Jira" {...register('name')} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label>Workspace URL</Label>
        <Input placeholder="https://yourorg.atlassian.net" {...register('workspace_url')} />
        {errors.workspace_url && <p className="text-xs text-destructive">{errors.workspace_url.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label>Jira email</Label>
        <Input type="email" placeholder="you@example.com" {...register('email')} />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label>API token</Label>
        <Input type="password" placeholder="Your Jira API token" {...register('access_token')} />
        {errors.access_token && <p className="text-xs text-destructive">{errors.access_token.message}</p>}
        <p className="text-xs text-muted-foreground">
          Generate at <span className="font-mono">id.atlassian.com/manage-profile/security/api-tokens</span>
        </p>
      </div>

      <div className="flex gap-2 justify-end pt-2">
        <Button type="button" variant="outline" onClick={onBack}>Back</Button>
        <Button type="submit" disabled={loading}>{loading ? 'Connecting…' : 'Connect'}</Button>
      </div>
    </form>
  )
}
