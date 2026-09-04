import { useState } from 'react'
import {
  Database,
  FileCode2,
  Layers,
  ShieldCheck,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal, SplitHeading, DrawRule } from '../Reveal'
import { Eyebrow } from '../ui'
import { MODEL_PROVIDERS, PLATFORM_FACTS } from '../content'

export function Platform() {
  const [selectedModel, setSelectedModel] = useState<string>(MODEL_PROVIDERS[0].name)

  return (
    <section className="mk-section relative" id="platform">
      <div className="mk-shell relative z-10">
        <div className="max-w-3xl">
          <Eyebrow>Platform architecture</Eyebrow>
          <SplitHeading
            as="h1"
            text="Four things compound. None of them are portable to a competitor."
            highlight={['compound.']}
            className="mk-display mt-6 text-[clamp(32px,4.8vw,60px)] font-bold tracking-tight"
          />
          <Reveal delay={0.15}>
            <p className="mt-6 text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              Your skills, codebase memory, and compliance evidence all compound inside your
              perimeter. Zero vendor lock-in, per-agent model choice, and full repository
              ownership.
            </p>
          </Reveal>
        </div>

        {/* Bento Grid Platform Superpowers */}
        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Bento Item 1: Skill Ecosystem */}
          <Reveal className="mk-bento-card group flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-[var(--mk-ember-lit)] text-xs font-semibold mk-mono pb-3 border-b border-[var(--mk-hairline)]">
                <FileCode2 className="h-4 w-4" /> 01 — REUSABLE SKILLS
              </div>
              <h3 className="text-xl font-bold text-[var(--mk-ink)] mt-4">Plain markdown skills</h3>
              <p className="text-sm text-[var(--mk-ink-2)] mt-2 leading-relaxed">
                Teach agents domain rules with markdown files checked into your git repository.
                Attach them to agents; changing a skill changes every agent that uses it.
              </p>
            </div>
            <div className="mt-6 rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] p-3 mk-mono text-[11px] text-[var(--mk-ink-2)]">
              <span className="text-[var(--mk-ember-lit)]"># skills/django-security.md</span>
              <div className="text-[var(--mk-ink-3)] mt-1">Enforce ORM parameterization &amp; CSRF tokens on all views.</div>
            </div>
          </Reveal>

          {/* Bento Item 2: Codebase Memory */}
          <Reveal delay={0.08} className="mk-bento-card group flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold mk-mono pb-3 border-b border-[var(--mk-hairline)]">
                <Database className="h-4 w-4" /> 02 — CODEBASE MEMORY
              </div>
              <h3 className="text-xl font-bold text-[var(--mk-ink)] mt-4">Retrieval, not a cold start</h3>
              <p className="text-sm text-[var(--mk-ink-2)] mt-2 leading-relaxed">
                Repositories are chunked and embedded, and each run retrieves what is relevant to
                that ticket into the agent prompt. Merged runs write back what worked.
              </p>
            </div>
            <div className="mt-6 flex items-center justify-between rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] p-3 text-[11.5px] mk-mono text-[var(--mk-ink-2)]">
              <span>Repository memory</span>
              <span className="text-[var(--mk-pass)]">Indexed ✓</span>
            </div>
          </Reveal>

          {/* Bento Item 3: Multi-Model Agility */}
          <Reveal delay={0.16} className="mk-bento-card group flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold mk-mono pb-3 border-b border-[var(--mk-hairline)]">
                <Layers className="h-4 w-4" /> 03 — MODEL AGILITY
              </div>
              <h3 className="text-xl font-bold text-[var(--mk-ink)] mt-4">No single-model dependency</h3>
              <p className="text-sm text-[var(--mk-ink-2)] mt-2 leading-relaxed">
                Assign a different model to each agent role — your Planner and your Reviewer need
                not be the same model, or the same vendor.
              </p>
            </div>
            <div className="mt-6 rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] p-2.5 flex items-center justify-between text-xs mk-mono">
              <span className="text-[var(--mk-ink-3)]">Active:</span>
              <span className="text-purple-300 font-semibold">{selectedModel}</span>
            </div>
          </Reveal>
        </div>

        <DrawRule className="mt-20" />

        {/* Interactive Model Switcher Showcase */}
        <div className="mt-16 grid gap-12 lg:grid-cols-12 lg:gap-16 items-center" id="models">
          <div className="lg:col-span-5">
            <Eyebrow>Model freedom</Eyebrow>
            <h3 className="mk-display text-2xl sm:text-3xl font-bold text-[var(--mk-ink)] mt-4">
              Bring your own keys. Run local or cloud.
            </h3>
            <p className="text-sm text-[var(--mk-ink-2)] mt-4 leading-relaxed">
              Every inference call is metered with its token counts and costed in integer
              millicents, at zero markup. Your prompts and code go to your own tenancy, under your
              contract with the provider.
            </p>
            <div className="mt-6 space-y-2">
              <div className="flex items-center gap-2 text-xs text-[var(--mk-ink)] mk-mono">
                <ShieldCheck className="h-4 w-4 text-[var(--mk-pass)]" /> We do not train on your code or prompts
              </div>
              <div className="flex items-center gap-2 text-xs text-[var(--mk-ink)] mk-mono">
                <ShieldCheck className="h-4 w-4 text-[var(--mk-pass)]" /> Air-gapped self-hosted Ollama support
              </div>
            </div>
          </div>

          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-panel)] p-4 sm:p-6 backdrop-blur-md shadow-xl">
              <div className="text-xs font-semibold text-[var(--mk-ink-3)] mk-mono mb-4">
                MODEL PROVIDERS
              </div>
              <div className="grid gap-3">
                {MODEL_PROVIDERS.map((m) => (
                  <button
                    key={m.name}
                    type="button"
                    onClick={() => setSelectedModel(m.name)}
                    className={cn(
                      'flex items-center justify-between p-3.5 rounded-xl border transition-all text-left',
                      selectedModel === m.name
                        ? 'border-[var(--mk-ember)]/60 bg-[var(--mk-ember)]/[0.08] shadow-[0_0_15px_rgba(232,99,42,0.15)]'
                        : 'border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_5%,transparent)]',
                    )}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-[var(--mk-ink)]">{m.name}</span>
                      </div>
                      <div className="text-xs text-[var(--mk-ink-3)] mt-1">{m.detail}</div>
                    </div>
                  </button>
                ))}
              </div>
              <p className="mt-4 text-[12px] text-[var(--mk-ink-3)]">
                {PLATFORM_FACTS.apiEndpoints} endpoints across the platform API; the public v1
                surface is the scoped, key-authenticated subset.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
