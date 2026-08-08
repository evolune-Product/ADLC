import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Check, Copy, KeyRound, ShieldAlert } from 'lucide-react'
import api, { getApiError } from '@/lib/api'

/**
 * An organisation's identity provider.
 *
 * Two decisions worth keeping:
 *
 * **The client secret is write-only.** The form shows whether one is set and
 * never what it is, and saving with the field blank keeps the stored value. A
 * settings page that can echo a secret back is a settings page that leaks it
 * through a screen share.
 *
 * **The redirect URI is displayed first, not last.** It is the one value the
 * admin has to paste into their IdP before anything else will work, and every
 * SSO setup that goes wrong goes wrong there.
 */

type SsoState = {
  configured: boolean
  redirect_uri: string
  id?: string
  label?: string
  issuer?: string
  client_id?: string
  client_secret_set?: boolean
  email_domains?: string[]
  default_role?: string
  enforced?: boolean
  enabled?: boolean
  last_login_at?: string | null
}

export default function SsoPanel({ orgId, isOwner }: { orgId: string; isOwner: boolean }) {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery<SsoState>({
    queryKey: ['orgs', orgId, 'sso'],
    queryFn: () => api.get(`/orgs/${orgId}/sso`).then((r) => r.data),
  })

  const [label, setLabel] = useState('Okta')
  const [issuer, setIssuer] = useState('')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [domains, setDomains] = useState('')
  const [enforced, setEnforced] = useState(false)
  const [enabled, setEnabled] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!data?.configured) return
    setLabel(data.label ?? 'SSO')
    setIssuer(data.issuer ?? '')
    setClientId(data.client_id ?? '')
    setDomains((data.email_domains ?? []).join(', '))
    setEnforced(!!data.enforced)
    setEnabled(!!data.enabled)
  }, [data])

  const save = useMutation({
    mutationFn: () =>
      api.put(`/orgs/${orgId}/sso`, {
        label,
        issuer: issuer.trim(),
        client_id: clientId.trim(),
        // Omitted rather than sent empty, so the server knows to keep the
        // existing secret instead of overwriting it with nothing.
        client_secret: clientSecret.trim() || undefined,
        email_domains: domains.split(',').map((d) => d.trim()).filter(Boolean),
        enforced,
        enabled,
      }),
    onSuccess: () => {
      setClientSecret('')
      qc.invalidateQueries({ queryKey: ['orgs', orgId, 'sso'] })
      toast.success('Single sign-on saved')
    },
    onError: (e) => toast.error(getApiError(e, 'Could not save the connection')),
  })

  const remove = useMutation({
    mutationFn: () => api.delete(`/orgs/${orgId}/sso`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orgs', orgId, 'sso'] })
      toast.success('Single sign-on removed')
    },
    onError: (e) => toast.error(getApiError(e)),
  })

  if (isLoading) return <div className="h-40 rounded-lg border border-border bg-muted/30 animate-pulse" />

  function copyRedirect() {
    navigator.clipboard.writeText(data?.redirect_uri ?? '')
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between border-b border-border pb-2">
        <h2 className="text-base font-semibold">Single sign-on</h2>
        {data?.configured && (
          <span className="onto-label">{data.enabled ? 'Active' : 'Disabled'}</span>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        Connect an OpenID Connect provider — Okta, Entra ID, Google Workspace, Auth0, Keycloak or
        PingFederate. People signing in with a matching email domain are routed to it and added to
        this organisation automatically. SAML-only providers are not supported.
      </p>

      {/* Step one, always visible: this is what has to be registered with the IdP. */}
      <div className="rounded-lg border border-border bg-muted/30 p-3">
        <p className="onto-label mb-1.5">Redirect URI — add this to your provider first</p>
        <div className="flex items-center gap-2">
          <code className="flex-1 truncate text-xs font-mono">{data?.redirect_uri}</code>
          <button
            onClick={copyRedirect}
            className="shrink-0 rounded p-1.5 text-muted-foreground hover:bg-foreground/5 hover:text-foreground"
            aria-label="Copy redirect URI"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {!isOwner ? (
        <p className="text-xs text-muted-foreground">
          Only the organisation owner can change this. An admin who could point the organisation at
          an identity provider they control could sign in as anyone in it.
        </p>
      ) : (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            save.mutate()
          }}
        >
          <Field label="Button label" hint="Shown on the sign-in page: “Continue with …”">
            <input value={label} onChange={(e) => setLabel(e.target.value)} className={INPUT} />
          </Field>

          <Field label="Issuer URL" hint="We read {issuer}/.well-known/openid-configuration">
            <input
              required
              value={issuer}
              onChange={(e) => setIssuer(e.target.value)}
              placeholder="https://acme.okta.com/oauth2/default"
              className={INPUT}
            />
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Client ID">
              <input required value={clientId} onChange={(e) => setClientId(e.target.value)} className={INPUT} />
            </Field>
            <Field
              label="Client secret"
              hint={data?.client_secret_set ? 'Stored. Leave blank to keep it.' : 'Required'}
            >
              <input
                type="password"
                value={clientSecret}
                onChange={(e) => setClientSecret(e.target.value)}
                placeholder={data?.client_secret_set ? '••••••••' : ''}
                className={INPUT}
              />
            </Field>
          </div>

          <Field label="Email domains" hint="Comma separated. Each domain can only be claimed by one organisation.">
            <input
              required
              value={domains}
              onChange={(e) => setDomains(e.target.value)}
              placeholder="acme.com, acme.co.uk"
              className={INPUT}
            />
          </Field>

          <label className="flex items-start gap-2.5 rounded-lg border border-border p-3">
            <input
              type="checkbox"
              checked={enforced}
              onChange={(e) => setEnforced(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              <span className="flex items-center gap-1.5 text-sm font-medium">
                <ShieldAlert className="h-3.5 w-3.5 text-[#E8632A]" />
                Require SSO for these domains
              </span>
              <span className="mt-0.5 block text-xs text-muted-foreground">
                Password sign-in is refused for anyone on a claimed domain. Without this, SSO is
                offered alongside passwords rather than replacing them — make sure you can sign in
                through your provider before turning it on.
              </span>
            </span>
          </label>

          <label className="flex items-center gap-2.5 text-sm">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
            Connection enabled
          </label>

          <div className="flex items-center gap-2 pt-1">
            <button
              type="submit"
              disabled={save.isPending}
              className="inline-flex items-center gap-2 rounded bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:opacity-50"
            >
              <KeyRound className="h-3.5 w-3.5" />
              {save.isPending ? 'Verifying…' : data?.configured ? 'Save connection' : 'Connect provider'}
            </button>
            {data?.configured && (
              <button
                type="button"
                onClick={() => remove.mutate()}
                disabled={remove.isPending}
                className="rounded border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Remove
              </button>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            Saving checks the issuer is reachable and publishes signing keys, so a typo fails here
            rather than on Monday morning.
          </p>
        </form>
      )}
    </section>
  )
}

const INPUT =
  'w-full rounded border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-foreground/20'

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium uppercase tracking-wide text-foreground">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}
