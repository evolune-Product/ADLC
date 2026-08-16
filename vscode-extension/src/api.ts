/**
 * Thin client for ADLC's public API v1 (`backend/app/routers/public_api.py`).
 *
 * Deliberately not a generated client: the surface is nine endpoints and a
 * generator adds a build step for less type safety than hand-writing it here.
 * Every method name and shape below should match that router 1:1 — if the
 * backend adds an endpoint, mirror it here rather than growing a third shape.
 */
import * as vscode from 'vscode'

export interface AdlcRun {
  id: string
  project_id: string
  ticket_id: string | null
  status: string
  current_step: string | null
  branch: string | null
  pr_url: string | null
  error: string | null
  created_at: string | null
  completed_at: string | null
}

export interface AdlcProject {
  id: string
  name: string
  repo: string | null
  pod_id: string | null
  status: string
}

export interface AdlcTicket {
  id: string
  jira_id: string
  title: string
  type: string | null
  priority: string | null
  status: string | null
}

export interface DiffFile {
  filename: string
  status: string
  additions: number
  deletions: number
  patch: string
}

export class AdlcApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

const SECRET_KEY = 'adlc.apiKey'

export class AdlcClient {
  constructor(private context: vscode.ExtensionContext) {}

  private baseUrl(): string {
    const url = vscode.workspace.getConfiguration('adlc').get<string>('apiUrl', 'http://localhost:8000')
    return url.replace(/\/+$/, '')
  }

  async getApiKey(): Promise<string | undefined> {
    return this.context.secrets.get(SECRET_KEY)
  }

  async setApiKey(key: string): Promise<void> {
    await this.context.secrets.store(SECRET_KEY, key)
  }

  async hasApiKey(): Promise<boolean> {
    return !!(await this.getApiKey())
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const key = await this.getApiKey()
    if (!key) {
      throw new AdlcApiError(401, 'No ADLC API key configured — run "ADLC: Set API Key".')
    }
    const res = await fetch(`${this.baseUrl()}/v1${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
        ...(init.headers || {}),
      },
    })
    if (!res.ok) {
      let detail = res.statusText
      try {
        const body = (await res.json()) as { detail?: string }
        detail = body.detail || detail
      } catch {
        // response wasn't JSON — fall back to statusText
      }
      throw new AdlcApiError(res.status, detail)
    }
    if (res.status === 204) return undefined as T
    return (await res.json()) as T
  }

  whoami() {
    return this.request<{ key_name: string; prefix: string; scopes: string[]; org_id: string | null }>('/whoami')
  }

  listProjects() {
    return this.request<AdlcProject[]>('/projects')
  }

  listTickets(projectId: string) {
    return this.request<AdlcTicket[]>(`/projects/${projectId}/tickets`)
  }

  listRuns(status?: string, limit = 50) {
    const qs = new URLSearchParams({ limit: String(limit), ...(status ? { status } : {}) })
    return this.request<AdlcRun[]>(`/runs?${qs}`)
  }

  getRun(runId: string) {
    return this.request<AdlcRun>(`/runs/${runId}`)
  }

  getDiff(runId: string) {
    return this.request<DiffFile[]>(`/runs/${runId}/diff`)
  }

  triggerRun(projectId: string, ticketId?: string, podId?: string) {
    return this.request<AdlcRun>('/runs', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, ticket_id: ticketId, pod_id: podId }),
    })
  }

  approveRun(runId: string, decision: 'approved' | 'changes_requested', comment?: string) {
    return this.request<AdlcRun>(`/runs/${runId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ decision, comment }),
    })
  }
}
