import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, CheckCheck, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import {
  useMarkAllRead, useMarkRead, useNotificationSettings, useNotifications,
  useTestSlack, useUpdateNotificationSettings,
} from '@/hooks/usePlatform'

const DOT: Record<string, string> = {
  info: 'bg-muted-foreground',
  warning: 'bg-[#E8632A]',
  critical: 'bg-red-600',
}

export default function NotificationsPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useNotifications()
  const { data: settings } = useNotificationSettings()
  const markRead = useMarkRead()
  const markAll = useMarkAllRead()
  const updateSettings = useUpdateNotificationSettings()
  const testSlack = useTestSlack()

  const [slackUrl, setSlackUrl] = useState('')

  if (isLoading) return <LoadingSkeleton />
  const notifications = data?.notifications ?? []

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Observe</p>
      <PageHeader
        title="Notifications"
        subtitle="The approval gate only works if the reviewer hears about it."
        action={
          (data?.unread_count ?? 0) > 0 ? (
            <Button variant="outline" onClick={() => markAll.mutate()}>
              <CheckCheck className="h-4 w-4 mr-2" /> Mark all read
            </Button>
          ) : undefined
        }
      />

      {/* Channels */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <p className="font-medium">Delivery channels</p>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings?.email_enabled ?? true}
            onChange={(e) => updateSettings.mutate({ email_enabled: e.target.checked })}
          />
          Email me when a run needs my approval, fails, or completes
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings?.slack_enabled ?? false}
            onChange={(e) => updateSettings.mutate({ slack_enabled: e.target.checked })}
          />
          Post to Slack
        </label>

        <div className="flex flex-wrap gap-2 items-center">
          <input
            value={slackUrl || settings?.slack_webhook_url || ''}
            onChange={(e) => setSlackUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/…"
            className="flex-1 min-w-[260px] rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <Button
            variant="outline"
            disabled={!slackUrl}
            onClick={() => testSlack.mutate(slackUrl)}
          >
            <Send className="h-3.5 w-3.5 mr-1.5" /> Test
          </Button>
          <Button
            disabled={!slackUrl}
            onClick={() =>
              updateSettings.mutate(
                { slack_webhook_url: slackUrl, slack_enabled: true },
                { onSuccess: () => setSlackUrl('') },
              )
            }
          >
            Save
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Create an Incoming Webhook in your Slack workspace and paste the URL — no app install or
          OAuth scope review needed.
        </p>
      </div>

      {/* Feed */}
      {notifications.length === 0 ? (
        <div className="bg-card rounded-lg border border-dashed border-border p-12 text-center">
          <Bell className="h-8 w-8 mx-auto text-muted-foreground" />
          <p className="font-medium mt-3">Nothing yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            Approval requests, failures and deploys will appear here.
          </p>
        </div>
      ) : (
        <div className="bg-card rounded-lg border border-border divide-y divide-border">
          {notifications.map((n) => (
            <button
              key={n.id}
              onClick={() => {
                if (!n.read) markRead.mutate(n.id)
                if (n.link) navigate(n.link)
              }}
              className={`w-full text-left px-4 py-3.5 flex items-start gap-3 hover:bg-foreground/[0.04] transition-colors ${
                n.read ? 'opacity-60' : ''
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full mt-2 shrink-0 ${DOT[n.severity]}`} />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-sm">{n.title}</p>
                {n.body && (
                  <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">{n.body}</p>
                )}
              </div>
              <span className="text-xs text-muted-foreground shrink-0">
                {new Date(n.created_at).toLocaleString()}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
