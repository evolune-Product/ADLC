// ─── Integrations — model providers and plugins ──────────────────────────────
//
// Mirrors `llm_providers.catalog()` and `plugins.catalog()`. Those two
// functions are the contract; a field that moves there moves here and nowhere
// else. Neither ever carries a secret — the catalogues describe what *could*
// be connected and are safe to render for any authenticated user.

export type ProviderAuth = 'key' | 'key+url' | 'url'
export type Pricing = 'published' | 'unknown' | 'free'

export interface ModelCredential {
  id: string
  provider: string
  label: string | null
  /** `sk-ant-…9f2a`. Identifies the key without disclosing it. */
  masked_hint: string | null
  base_url: string | null
  default_model: string | null
  /** Cents per million tokens, keyed by model id. */
  price_overrides: Record<string, { input: number; output: number }>
  is_active: boolean
  status: 'unknown' | 'ok' | 'error'
  status_detail: string | null
  last_verified_at: string | null
  has_key: boolean
}

export interface Provider {
  key: string
  label: string
  wire: 'anthropic' | 'openai' | 'google' | 'ollama'
  auth: ProviderAuth
  base_url: string | null
  key_hint?: string
  url_hint?: string
  console_url?: string
  docs_url: string
  /** Autocomplete hints, deliberately not a closed set — model ids churn. */
  suggested_models: string[]
  pricing: Pricing
  notes?: string
  connected: boolean
  credential: ModelCredential | null
}

export interface ProviderGroup {
  family: string
  label: string
  providers: Provider[]
}

export interface ProviderCatalog {
  groups: ProviderGroup[]
  connected_count: number
  total: number
  /** Always true. The platform does not resell inference. */
  byo_only: boolean
}

// ─── Plugins ─────────────────────────────────────────────────────────────────

export type PluginAuth = 'token' | 'token+url' | 'basic' | 'webhook' | 'none'

/**
 * How deeply a plugin is wired in. Shown on the card, because a catalogue of
 * forty logos means nothing if most of them only store a token.
 */
export type PluginDepth =
  /** The pipeline drives it — reads issues, opens PRs, comments back. */
  | 'native'
  /** Receives run events: approvals, failures, deploys. */
  | 'notify'
  /** Credential stored and genuinely checked against the vendor, available to
   *  agents and skills, but no bespoke pipeline behaviour yet. */
  | 'verified'

export interface PluginConnection {
  id: string
  name: string
  status: string
  workspace_url: string | null
  metadata: Record<string, unknown>
}

export interface Plugin {
  key: string
  label: string
  depth: PluginDepth
  auth: PluginAuth
  token_label?: string
  token_hint?: string
  url_label?: string
  url_hint?: string
  user_label?: string
  extra_label?: string
  docs_url: string
  setup_url?: string
  scopes?: string[]
  capabilities: string[]
  notes?: string
  connections: PluginConnection[]
  connected: boolean
}

export interface PluginGroup {
  category: string
  label: string
  plugins: Plugin[]
}

export interface PluginCounts {
  total: number
  native: number
  notify: number
  verified: number
  categories: number
}

export interface PluginCatalog {
  groups: PluginGroup[]
  counts: PluginCounts
  connected_count: number
}

export interface ConnectResult {
  id: string
  type: string
  name: string
  status: string
  verified: boolean
  detail: string
  display_name: string | null
}
