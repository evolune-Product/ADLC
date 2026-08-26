import { useState } from 'react'
import { Check, CreditCard, Key, Landmark, Wallet, X, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import {
  useBilling, useBillingPortal, useCancelSubscription, useCheckout, useClearLlmKey,
  usePlans, useSetLlmKey,
} from '@/hooks/usePlatform'
import type { PaymentGateway } from '@/types/platform'

// Icon + label per gateway. Razorpay has no lucide icon of its own, so
// Landmark (a bank building) stands in for "the India bank-rail option" —
// closer to what it actually is (UPI/netbanking/bank transfer) than a
// generic card icon would be.
const GATEWAYS: { key: PaymentGateway; label: string; icon: typeof CreditCard }[] = [
  { key: 'stripe', label: 'Card (Stripe)', icon: CreditCard },
  { key: 'razorpay', label: 'UPI / Razorpay', icon: Landmark },
  { key: 'paypal', label: 'PayPal', icon: Wallet },
]

const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic (Claude)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'azure', label: 'Azure OpenAI' },
  { value: 'ollama', label: 'Ollama (self-hosted)' },
]

function money(cents: number) {
  return cents === 0 ? 'Free' : `$${(cents / 100).toLocaleString()}`
}

export default function BillingPage() {
  const { data: billing, isLoading } = useBilling()
  const { data: plans = [] } = usePlans()
  const checkout = useCheckout()
  const portal = useBillingPortal()
  const cancelSub = useCancelSubscription()
  const [gateway, setGateway] = useState<PaymentGateway>('stripe')
  const setKey = useSetLlmKey()
  const clearKey = useClearLlmKey()

  const [provider, setProvider] = useState('anthropic')
  const [apiKey, setApiKey] = useState('')

  if (isLoading || !billing) return <LoadingSkeleton />

  const { subscription: sub, quota } = billing
  const pct = quota.runs_included
    ? Math.min(100, Math.round((quota.runs_used / quota.runs_included) * 100))
    : 0
  const nearLimit = pct >= 80

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Billing</p>
      <PageHeader
        title="Plan and usage"
        subtitle="Runs are the billing unit — one ticket through a pod, end to end."
        action={
          sub.payment_provider === 'stripe' && sub.stripe_customer_id ? (
            <Button variant="outline" onClick={() => portal.mutate()}>
              <CreditCard className="h-4 w-4 mr-2" />
              Manage billing
            </Button>
          ) : sub.payment_provider && sub.plan !== 'free' ? (
            <Button
              variant="outline"
              disabled={cancelSub.isPending || sub.cancel_at_period_end}
              onClick={() => {
                if (window.confirm('Cancel your subscription at the end of the current period?')) {
                  cancelSub.mutate()
                }
              }}
            >
              <X className="h-4 w-4 mr-2" />
              {sub.cancel_at_period_end ? 'Cancels at period end' : 'Cancel subscription'}
            </Button>
          ) : undefined
        }
      />

      {/* Current period */}
      <div className="bg-card rounded-lg border border-border p-5">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="onto-label mb-1">Current plan</p>
            <p className="text-2xl font-semibold">{sub.plan_name}</p>
            <p className="text-sm text-muted-foreground mt-1">
              Status: {sub.status}
              {sub.current_period_end &&
                ` · renews ${new Date(sub.current_period_end).toLocaleDateString()}`}
              {sub.cancel_at_period_end && ' · cancels at period end'}
            </p>
          </div>
          <div className="text-right">
            <p className="onto-label mb-1">Spend this period</p>
            <p className="text-2xl font-semibold">${quota.spend_usd.toFixed(2)}</p>
            <p className="text-sm text-muted-foreground mt-1">actual model cost</p>
          </div>
        </div>

        <div className="mt-5">
          <div className="flex justify-between text-sm mb-1.5">
            <span className="text-muted-foreground">
              {quota.runs_used} of {quota.runs_included || '∞'} runs used
            </span>
            {quota.overage_runs > 0 && (
              <span className="text-[#E8632A]">
                {quota.overage_runs} overage · {money(quota.overage_cents)}
              </span>
            )}
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${nearLimit ? 'bg-[#E8632A]' : 'bg-foreground'}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          {!quota.allowed && quota.reason && (
            <p className="mt-3 text-sm text-[#C0392B]">{quota.reason}</p>
          )}
        </div>
      </div>

      {/* Plans */}
      <div>
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <p className="onto-label">01 — Plans</p>

          {/* Which gateway an upgrade below will use. Every gateway hands back
              a redirect URL — a hosted checkout or approval page — so picking
              one here is the only gateway-specific UI in the product; nothing
              downstream needs to know which was chosen. */}
          <div className="flex rounded-md border border-border overflow-hidden">
            {GATEWAYS.map((g) => {
              const Icon = g.icon
              const enabled = billing.gateways_enabled[g.key]
              return (
                <button
                  key={g.key}
                  onClick={() => setGateway(g.key)}
                  title={enabled ? undefined : `${g.label} isn’t configured on this install — upgrading will apply the plan directly`}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${
                    gateway === g.key
                      ? 'bg-foreground text-background font-medium'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {g.label}
                  {!enabled && <span className="opacity-60">·sim</span>}
                </button>
              )
            })}
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {plans.map((plan) => {
            const current = plan.key === sub.plan
            return (
              <div
                key={plan.key}
                className={`bg-card rounded-lg border p-5 flex flex-col ${
                  current ? 'border-foreground' : 'border-border'
                }`}
              >
                <p className="onto-label mb-1">{plan.name}</p>
                <p className="text-2xl font-semibold">
                  {money(plan.price_cents)}
                  {plan.price_cents > 0 && (
                    <span className="text-sm font-normal text-muted-foreground">/mo</span>
                  )}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {plan.included_runs === 0
                    ? 'Unlimited runs'
                    : `${plan.included_runs.toLocaleString()} runs included`}
                  {plan.overage_cents_per_run > 0 &&
                    ` · then $${(plan.overage_cents_per_run / 100).toFixed(2)}/run`}
                </p>

                <ul className="mt-4 space-y-1.5 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="h-3.5 w-3.5 mt-0.5 shrink-0 text-[#E8632A]" />
                      <span className="text-muted-foreground">{f}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="mt-5 w-full"
                  variant={current ? 'outline' : 'default'}
                  disabled={current || checkout.isPending}
                  onClick={() => checkout.mutate({ plan: plan.key, gateway })}
                >
                  {current ? 'Current plan' : plan.key === 'enterprise' ? 'Contact sales' : 'Upgrade'}
                </Button>
              </div>
            )
          })}
        </div>
        {!billing.gateways_enabled[gateway] && (
          <p className="text-xs text-muted-foreground mt-3">
            {GATEWAYS.find((g) => g.key === gateway)?.label} isn’t configured on this install —
            an upgrade applies the plan directly instead of charging a card. Set the{' '}
            {gateway === 'stripe' && <code>STRIPE_SECRET_KEY</code>}
            {gateway === 'razorpay' && <code>RAZORPAY_KEY_ID</code>}
            {gateway === 'paypal' && <code>PAYPAL_CLIENT_ID</code>}
            {' '}environment variable to enable real checkout.
          </p>
        )}
        {sub.payment_provider && (
          <p className="text-xs text-muted-foreground mt-2">
            Currently billed via <strong>{GATEWAYS.find((g) => g.key === sub.payment_provider)?.label ?? sub.payment_provider}</strong>.
            Switching gateways starts a new subscription — cancel the current one first if you
            want to move.
          </p>
        )}
      </div>

      {/* Bring your own model key */}
      <div className="bg-card rounded-lg border border-border p-5">
        <div className="flex items-center gap-2 mb-1">
          <Key className="h-4 w-4" />
          <p className="font-medium">Bring your own model provider</p>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Use your own Anthropic, OpenAI, Azure or local Ollama key. Agent runs bill to your
          vendor account instead of ours, and no model traffic touches our key.
          {sub.byo_llm_configured && (
            <span className="text-foreground">
              {' '}Currently using your <strong>{sub.byo_llm_provider}</strong> key.
            </span>
          )}
        </p>

        <div className="flex flex-wrap gap-2 items-center">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <input
            type="password"
            placeholder="sk-…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="flex-1 min-w-[240px] rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <Button
            disabled={!apiKey || setKey.isPending}
            onClick={() => setKey.mutate({ provider, api_key: apiKey }, { onSuccess: () => setApiKey('') })}
          >
            Save key
          </Button>
          {sub.byo_llm_configured && (
            <Button variant="outline" onClick={() => clearKey.mutate()}>
              Remove
            </Button>
          )}
        </div>
      </div>

      {/* Model spend breakdown */}
      {billing.usage_by_model.length > 0 && (
        <div>
          <p className="onto-label mb-2">02 — Model spend this period</p>
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="onto-label text-left px-4 py-2.5">Model</th>
                  <th className="onto-label text-right px-4 py-2.5">Calls</th>
                  <th className="onto-label text-right px-4 py-2.5">Input</th>
                  <th className="onto-label text-right px-4 py-2.5">Output</th>
                  <th className="onto-label text-right px-4 py-2.5">Cost</th>
                </tr>
              </thead>
              <tbody>
                {billing.usage_by_model.map((row) => (
                  <tr key={row.model} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5 font-mono text-xs">{row.model}</td>
                    <td className="px-4 py-2.5 text-right">{row.calls}</td>
                    <td className="px-4 py-2.5 text-right text-muted-foreground">
                      {row.input_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right text-muted-foreground">
                      {row.output_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right">${row.cost_usd.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1.5">
            <Zap className="h-3 w-3" />
            Per-run budget cap: ${(sub.run_budget_cents / 100).toFixed(2)} — a run that projects
            above this is stopped rather than allowed to run away.
          </p>
        </div>
      )}
    </div>
  )
}
