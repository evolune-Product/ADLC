import * as vscode from 'vscode'
import { DiffFile } from './api'

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/** Colours a unified diff's +/- lines without a highlighting library — the
 * patch text VS Code's own diff view uses is already a unified diff, and a
 * webview has no filesystem access to hand it to the native diff editor
 * without writing temp files, which would leave stale copies on disk. */
function renderPatch(patch: string): string {
  return patch
    .split('\n')
    .map((line) => {
      const cls = line.startsWith('+') && !line.startsWith('+++') ? 'add'
        : line.startsWith('-') && !line.startsWith('---') ? 'del'
        : line.startsWith('@@') ? 'hunk'
        : ''
      return `<span class="${cls}">${escapeHtml(line) || ' '}</span>`
    })
    .join('\n')
}

export function showDiff(runId: string, files: DiffFile[]) {
  const panel = vscode.window.createWebviewPanel(
    'adlcDiff',
    `ADLC Run ${runId.slice(0, 8)} — Diff`,
    vscode.ViewColumn.Active,
    { enableScripts: false },
  )

  const body = files.length === 0
    ? '<p class="empty">No files changed, or no PR yet for this run.</p>'
    : files.map((f) => `
        <section>
          <header>
            <span class="filename">${escapeHtml(f.filename)}</span>
            <span class="stats"><span class="add">+${f.additions}</span> <span class="del">-${f.deletions}</span> · ${escapeHtml(f.status)}</span>
          </header>
          <pre>${renderPatch(f.patch)}</pre>
        </section>
      `).join('\n')

  panel.webview.html = `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { font-family: var(--vscode-editor-font-family, monospace); font-size: 13px; padding: 0 16px 16px; color: var(--vscode-foreground); }
  h1 { font-size: 14px; font-weight: 600; position: sticky; top: 0; background: var(--vscode-editor-background); padding: 12px 0; }
  section { margin-bottom: 20px; border: 1px solid var(--vscode-panel-border); border-radius: 6px; overflow: hidden; }
  header { display: flex; justify-content: space-between; padding: 6px 10px; background: var(--vscode-editorWidget-background); font-weight: 600; }
  .filename { font-family: var(--vscode-editor-font-family, monospace); }
  .stats { font-weight: 400; opacity: 0.8; }
  pre { margin: 0; padding: 8px 10px; overflow-x: auto; white-space: pre; }
  pre span { display: block; }
  .add { color: var(--vscode-gitDecoration-addedResourceForeground, #4caf50); }
  .del { color: var(--vscode-gitDecoration-deletedResourceForeground, #f44336); }
  .hunk { color: var(--vscode-textLink-foreground); opacity: 0.8; }
  .empty { opacity: 0.7; padding: 20px 0; }
</style>
</head>
<body>
<h1>Run ${runId.slice(0, 8)} — ${files.length} file${files.length === 1 ? '' : 's'} changed</h1>
${body}
</body>
</html>`
}
