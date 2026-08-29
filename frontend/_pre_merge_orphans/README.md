# Pre-merge orphaned frontend code

These files predate the Phase 11/12 merge (billing, governance, admin, usage
limits) and were left disconnected by it — same pattern as the backend's
`plan_service.py` / `usage_limit.py` / `routers/admin.py` (see
`E:\Skills\Platforms\ADLC\TECHNICAL_ARCHITECTURE.md`, Section 0).

They were quarantined here (moved out of `src/`, which is all `tsc`/`vite`
compile) because:

- `hooks/useAdmin.ts`, `pages/admin/AdminPage.tsx` — called the old,
  never-mounted `backend/app/routers/admin.py`. The merge's own governance
  layer (`src/pages/governance/*`) covers policy/API-key/compliance admin now.
- `hooks/useUsageLimits.ts`, `components/dashboard/UsageLimitsCard.tsx` —
  read the old `UsageLimit`/`plan_service.py` resource-count system, which is
  dead; the live system is `metering_service.py` + `src/pages/billing/*`.
- `hooks/useLLMConfig.ts` — imported `LLMConfig`/`LLMConfigUpdate`/etc. from
  `@/types`, which no longer export those (superseded by the multi-provider
  `src/pages/settings/ProvidersPage.tsx` + `ModelCredential` model).
- `lib/errors.ts` — an unused canonical-error-shape helper with no importers,
  same category as the backend's orphaned `app/core/errors.py`.
- `pages/pricing/PricingPage.tsx` — superseded by `src/pages/landing/PricingPage.tsx`,
  which the merge added and which `App.tsx` actually routes to.
- `hooks/usePollingQuery.ts` — zero importers found anywhere.

None of this was deleted — it's parked here in case any of it is worth
reconciling with the new billing/governance/admin surfaces rather than
discarding outright. It was blocking `npm run build` (and therefore the
Docker image) with TypeScript errors against types that no longer exist.
