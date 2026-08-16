# ADLC for VS Code

Bring the run stream into the editor: assign a ticket to the agent pipeline,
watch runs update, review the PR diff, and approve or reject — without
switching to the web dashboard. Talks to the same `/v1` public API as CI
integrations and ChatOps bots (`backend/app/routers/public_api.py`); nothing
here is a special extension-only backend path.

## Setup

1. In the ADLC web app: **Settings → Developer**, create an API key with at
   least `projects:read`, `runs:read` and `runs:write` scopes (add
   `runs:approve` if this key should also be able to approve/reject —
   deliberately a separate scope, same reasoning as CI tokens).
2. In VS Code: **ADLC: Set API Key** (Command Palette), paste it in.
3. Set `adlc.apiUrl` in Settings if the backend isn't on `http://localhost:8000`.

## What it does

- **Sidebar** (ADLC icon in the activity bar): *Awaiting Approval* and
  *Recent Runs*, polling every `adlc.pollIntervalSeconds` (default 20s).
- **Status bar**: a live count of runs awaiting approval; click to open the
  sidebar.
- **ADLC: Assign Ticket to AI** — pick a project, pick a synced ticket,
  starts a run. Requires the project to already have a pod configured (same
  rule as the web app and the CI trigger endpoint).
- **Approve / Request Changes** — inline icons on a pending run, or from the
  Command Palette (prompts you to pick a run if not invoked from the tree).
- **View Diff** — click a run to open its PR's per-file patches in a webview.
  This renders the same files the web app's `PrDiffViewer` shows; it is not
  routed through VS Code's native diff editor, since that needs real files on
  disk and a webview has no filesystem access without writing temp copies
  that would go stale.

## What it deliberately does not do

- No write access beyond what the API key's scopes allow — a `runs:write`
  key without `runs:approve` can start work but the Approve/Request Changes
  commands will fail with a 403, same as any other API-key client. This
  mirrors the platform's own separation, not a client-side restriction that
  could be bypassed.
- No local secret storage beyond VS Code's built-in `SecretStorage` — the key
  never touches `settings.json` or gets synced as plain text.
- "Open Run in Browser" guesses the SPA's dev URL by swapping the API port
  (`:8000` → `:5173`); the public API has no `frontend_url` field to ask for
  the real one. Works for local dev, not guaranteed in every deployment.

## Developing

```bash
npm install
npm run watch      # tsc -w
```

Press F5 in VS Code (with this folder open) to launch an Extension
Development Host. There's no test suite here yet — the API client
(`src/api.ts`) is thin enough that `tsc`'s type-check is most of the safety
net; see the backend's own `tests/test_platform_units.py` for the tests that
matter (the endpoints this extension calls are the same public API those
exercise indirectly via the scoping/approval logic).
