import * as vscode from 'vscode'
import { AdlcClient, AdlcRun } from './api'

const STATUS_ICON: Record<string, vscode.ThemeIcon> = {
  queued: new vscode.ThemeIcon('circle-outline'),
  running: new vscode.ThemeIcon('sync~spin'),
  awaiting_approval: new vscode.ThemeIcon('question', new vscode.ThemeColor('charts.orange')),
  approved: new vscode.ThemeIcon('check'),
  completed: new vscode.ThemeIcon('check-all', new vscode.ThemeColor('charts.green')),
  failed: new vscode.ThemeIcon('error', new vscode.ThemeColor('charts.red')),
}

export class RunItem extends vscode.TreeItem {
  constructor(public readonly run: AdlcRun, contextValue: string) {
    super(RunItem.label(run), vscode.TreeItemCollapsibleState.None)
    this.description = run.current_step ?? run.status
    this.iconPath = STATUS_ICON[run.status] ?? new vscode.ThemeIcon('circle-outline')
    this.contextValue = contextValue
    this.tooltip = `${run.status}${run.branch ? ` · ${run.branch}` : ''}${run.error ? `\n${run.error}` : ''}`
    this.command = { command: 'adlc.viewDiff', title: 'View Diff', arguments: [this] }
  }

  private static label(run: AdlcRun): string {
    const short = run.id.slice(0, 8)
    return run.pr_url ? `PR — ${short}` : short
  }
}

/**
 * One provider class backs both sidebar views (Awaiting Approval / Recent
 * Runs) — same data shape, different status filter and TreeItem
 * contextValue, so the context-menu commands can tell them apart without a
 * second implementation to keep in sync.
 */
export class RunsProvider implements vscode.TreeDataProvider<RunItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<void>()
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event

  constructor(
    private client: AdlcClient,
    private statusFilter: string | undefined,
    private contextValue: string,
  ) {}

  refresh(): void {
    this._onDidChangeTreeData.fire()
  }

  getTreeItem(element: RunItem): vscode.TreeItem {
    return element
  }

  async getChildren(): Promise<RunItem[]> {
    if (!(await this.client.hasApiKey())) return []
    try {
      const runs = await this.client.listRuns(this.statusFilter, 30)
      return runs.map((r) => new RunItem(r, this.contextValue))
    } catch (err) {
      vscode.window.setStatusBarMessage(`ADLC: ${err instanceof Error ? err.message : 'failed to load runs'}`, 5000)
      return []
    }
  }
}
