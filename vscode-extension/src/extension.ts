import * as vscode from 'vscode'
import { AdlcApiError, AdlcClient } from './api'
import { showDiff } from './diffPanel'
import { RunItem, RunsProvider } from './runsProvider'

let statusBarItem: vscode.StatusBarItem
let pollTimer: ReturnType<typeof setInterval> | undefined

export function activate(context: vscode.ExtensionContext) {
  const client = new AdlcClient(context)

  const approvalsProvider = new RunsProvider(client, 'awaiting_approval', 'pendingRun')
  const runsProvider = new RunsProvider(client, undefined, 'run')
  vscode.window.registerTreeDataProvider('adlcApprovals', approvalsProvider)
  vscode.window.registerTreeDataProvider('adlcRuns', runsProvider)

  statusBarItem = vscode.window.createStatusBarItem('adlc.status', vscode.StatusBarAlignment.Left, 100)
  statusBarItem.command = 'adlc.refresh'
  context.subscriptions.push(statusBarItem)

  const refreshAll = async () => {
    approvalsProvider.refresh()
    runsProvider.refresh()
    await updateStatusBar(client)
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('adlc.setApiKey', async () => {
      const key = await vscode.window.showInputBox({
        prompt: 'ADLC API key (Settings → Governance → Developer in the web app)',
        password: true,
        placeHolder: 'adlc_live_…',
        ignoreFocusOut: true,
      })
      if (!key) return
      await client.setApiKey(key)
      try {
        const who = await client.whoami()
        vscode.window.showInformationMessage(`ADLC: connected as "${who.key_name}" (scopes: ${who.scopes.join(', ')})`)
      } catch (err) {
        vscode.window.showErrorMessage(`ADLC: key saved, but verification failed — ${errMessage(err)}`)
      }
      refreshAll()
    }),

    vscode.commands.registerCommand('adlc.refresh', refreshAll),

    vscode.commands.registerCommand('adlc.assignToAi', async () => {
      if (!(await guardApiKey(client))) return
      try {
        const projects = await client.listProjects()
        if (projects.length === 0) {
          vscode.window.showWarningMessage('ADLC: no projects visible to this API key.')
          return
        }
        const project = await vscode.window.showQuickPick(
          projects.map((p) => ({ label: p.name, description: p.repo ?? undefined, project: p })),
          { placeHolder: 'Which project?' },
        )
        if (!project) return

        const tickets = await client.listTickets(project.project.id)
        if (tickets.length === 0) {
          vscode.window.showWarningMessage(`ADLC: no synced tickets in ${project.project.name}. Sync from the web app first.`)
          return
        }
        const ticket = await vscode.window.showQuickPick(
          tickets.map((t) => ({
            label: `${t.jira_id} — ${t.title}`,
            description: [t.type, t.priority, t.status].filter(Boolean).join(' · '),
            ticket: t,
          })),
          { placeHolder: 'Assign which ticket to AI?' },
        )
        if (!ticket) return

        const run = await client.triggerRun(project.project.id, ticket.ticket.id, project.project.pod_id ?? undefined)
        vscode.window.showInformationMessage(`ADLC: started a run on ${ticket.ticket.jira_id} (${run.status}).`)
        refreshAll()
      } catch (err) {
        vscode.window.showErrorMessage(`ADLC: could not start a run — ${errMessage(err)}`)
      }
    }),

    vscode.commands.registerCommand('adlc.approveRun', async (item?: RunItem) => {
      const run = await resolveRun(item)
      if (!run) return
      const comment = await vscode.window.showInputBox({ prompt: 'Approval comment (optional)', ignoreFocusOut: true })
      try {
        await client.approveRun(run.id, 'approved', comment || undefined)
        vscode.window.showInformationMessage(`ADLC: approved ${run.id.slice(0, 8)}.`)
        refreshAll()
      } catch (err) {
        vscode.window.showErrorMessage(`ADLC: approval failed — ${errMessage(err)}`)
      }
    }),

    vscode.commands.registerCommand('adlc.requestChanges', async (item?: RunItem) => {
      const run = await resolveRun(item)
      if (!run) return
      const comment = await vscode.window.showInputBox({
        prompt: 'What needs to change? (this is posted back on the run)',
        ignoreFocusOut: true,
      })
      if (comment === undefined) return
      try {
        await client.approveRun(run.id, 'changes_requested', comment || undefined)
        vscode.window.showInformationMessage(`ADLC: requested changes on ${run.id.slice(0, 8)}.`)
        refreshAll()
      } catch (err) {
        vscode.window.showErrorMessage(`ADLC: could not request changes — ${errMessage(err)}`)
      }
    }),

    vscode.commands.registerCommand('adlc.viewDiff', async (item?: RunItem) => {
      const run = await resolveRun(item)
      if (!run) return
      try {
        const files = await client.getDiff(run.id)
        showDiff(run.id, files)
      } catch (err) {
        vscode.window.showErrorMessage(`ADLC: could not load diff — ${errMessage(err)}`)
      }
    }),

    vscode.commands.registerCommand('adlc.openRunInBrowser', async (item?: RunItem) => {
      const run = await resolveRun(item)
      if (!run) return
      const base = vscode.workspace.getConfiguration('adlc').get<string>('apiUrl', '').replace(/\/+$/, '')
      // The API and the SPA are typically different origins/ports in dev; this
      // is a best-effort guess (same host, SPA's default dev port) rather than
      // a guarantee — there is no "frontend_url" field on the public API.
      const guess = base.replace(/:8000$/, ':5173')
      vscode.env.openExternal(vscode.Uri.parse(`${guess}/runs/${run.id}`))
    }),
  )

  async function resolveRun(item?: RunItem) {
    if (item) return item.run
    // Invoked from the command palette rather than a tree item — ask which run.
    if (!(await guardApiKey(client))) return undefined
    const runs = await client.listRuns('awaiting_approval', 30)
    if (runs.length === 0) {
      vscode.window.showInformationMessage('ADLC: nothing is awaiting approval.')
      return undefined
    }
    const picked = await vscode.window.showQuickPick(
      runs.map((r) => ({ label: r.id.slice(0, 8), description: r.branch ?? r.status, run: r })),
      { placeHolder: 'Which run?' },
    )
    return picked?.run
  }

  refreshAll()
  const seconds = vscode.workspace.getConfiguration('adlc').get<number>('pollIntervalSeconds', 20)
  pollTimer = setInterval(refreshAll, Math.max(seconds, 5) * 1000)
  context.subscriptions.push({ dispose: () => pollTimer && clearInterval(pollTimer) })

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('adlc.apiUrl') || e.affectsConfiguration('adlc.pollIntervalSeconds')) {
        refreshAll()
      }
    }),
  )
}

async function guardApiKey(client: AdlcClient): Promise<boolean> {
  if (await client.hasApiKey()) return true
  const choice = await vscode.window.showWarningMessage(
    'ADLC: no API key configured.', 'Set API Key',
  )
  if (choice === 'Set API Key') {
    await vscode.commands.executeCommand('adlc.setApiKey')
  }
  return false
}

async function updateStatusBar(client: AdlcClient) {
  if (!(await client.hasApiKey())) {
    statusBarItem.text = '$(circle-slash) ADLC: not connected'
    statusBarItem.tooltip = 'Click to set your API key'
    statusBarItem.command = 'adlc.setApiKey'
    statusBarItem.show()
    return
  }
  try {
    const pending = await client.listRuns('awaiting_approval', 200)
    statusBarItem.text = pending.length > 0
      ? `$(bell-dot) ADLC: ${pending.length} awaiting approval`
      : '$(check) ADLC: clear'
    statusBarItem.tooltip = 'Open the ADLC sidebar'
    statusBarItem.command = 'workbench.view.extension.adlc'
    statusBarItem.show()
  } catch (err) {
    statusBarItem.text = '$(warning) ADLC: unreachable'
    statusBarItem.tooltip = errMessage(err)
    statusBarItem.show()
  }
}

function errMessage(err: unknown): string {
  if (err instanceof AdlcApiError) return `${err.message} (HTTP ${err.status})`
  return err instanceof Error ? err.message : String(err)
}

export function deactivate() {
  if (pollTimer) clearInterval(pollTimer)
}
