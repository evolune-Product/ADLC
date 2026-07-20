import { useState, useEffect, useRef } from 'react'
import MDEditor from '@uiw/react-md-editor'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CATEGORIES, CATEGORY_TEMPLATES } from '@/lib/skillTemplates'
import type { Skill } from '@/types'

interface SkillFormData {
  name: string
  description: string
  category: string
  version: string
  md_content: string
}

interface Props {
  initial?: Partial<Skill>
  onSave: (data: SkillFormData) => void
  loading: boolean
  /** If true, show editor + rendered preview side by side */
  splitView?: boolean
}

export function SkillForm({ initial, onSave, loading, splitView = false }: Props) {
  const [name, setName]               = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [category, setCategory]       = useState(initial?.category ?? '')
  const [version, setVersion]         = useState(initial?.version ?? '1.0.0')
  const [content, setContent]         = useState(initial?.md_content ?? '')
  const fileInputRef                  = useRef<HTMLInputElement>(null)

  // When category changes on a new skill (no initial), inject the template
  useEffect(() => {
    if (!initial && category && !content) {
      setContent(CATEGORY_TEMPLATES[category] ?? '')
    }
  }, [category]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleFileImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      setContent(text)
      // Auto-fill name from filename if name is empty
      if (!name) setName(file.name.replace(/\.(md|markdown)$/i, ''))
    }
    reader.readAsText(file)
    // Reset so the same file can be re-imported if needed
    e.target.value = ''
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    if (!content.trim()) return
    onSave({ name, description, category, version, md_content: content })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Meta fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label>Name *</Label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Python Coding Standards"
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label>Category</Label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">-- Select category --</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <Label>Description</Label>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="One-line summary of what this skill does"
          />
        </div>

        <div className="space-y-1.5">
          <Label>Version</Label>
          <Input
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="1.0.0"
          />
        </div>
      </div>

      {/* MD Editor */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label>Skill Content (Markdown) *</Label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="h-3.5 w-3.5 mr-1.5" />
            Import .md file
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".md,.markdown"
            className="hidden"
            onChange={handleFileImport}
          />
        </div>
        {splitView ? (
          <div data-color-mode="light" className="grid grid-cols-2 gap-4">
            <MDEditor
              value={content}
              onChange={(v) => setContent(v ?? '')}
              preview="edit"
              height={500}
            />
            <div className="rounded-md border p-4 overflow-auto h-[500px] prose prose-sm max-w-none">
              <MDEditor.Markdown source={content} />
            </div>
          </div>
        ) : (
          <div data-color-mode="light">
            <MDEditor
              value={content}
              onChange={(v) => setContent(v ?? '')}
              height={400}
            />
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={loading || !name.trim() || !content.trim()}>
          {loading ? 'Saving…' : 'Save Skill'}
        </Button>
      </div>
    </form>
  )
}
