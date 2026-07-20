import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, BookOpen, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatsGrid } from '@/components/ui/StatsGrid'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { useSkills, useDeleteSkill } from '@/hooks/useSkills'
import { CATEGORIES } from '@/lib/skillTemplates'

const CATEGORY_LABEL = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]))

export default function SkillsPage() {
  const navigate = useNavigate()
  const { data: skills = [], isLoading } = useSkills()
  const deleteMutation = useDeleteSkill()
  const [search, setSearch] = useState('')

  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.description ?? '').toLowerCase().includes(search.toLowerCase()),
  )

  const active = skills.filter((s) => s.is_active).length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Skill Registry"
        subtitle="Reusable markdown-based capabilities injected into agents."
        action={
          <Button onClick={() => navigate('/skills/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Skill
          </Button>
        }
      />

      <StatsGrid
        stats={[
          { label: 'Total',    value: skills.length },
          { label: 'Active',   value: active },
          { label: 'Inactive', value: skills.length - active },
        ]}
      />

      <input
        type="text"
        placeholder="Search skills..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      />

      {isLoading ? (
        <LoadingSkeleton />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<BookOpen className="h-10 w-10" />}
          title={search ? 'No skills match your search' : 'No skills yet'}
          subtitle={!search ? 'Create your first skill to get started.' : undefined}
          action={
            !search ? (
              <Button variant="outline" onClick={() => navigate('/skills/new')}>
                <Plus className="h-4 w-4 mr-2" />
                New Skill
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((skill) => (
            <Card
              key={skill.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => navigate(`/skills/${skill.id}`)}
            >
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium truncate">{skill.name}</p>
                    {skill.category && (
                      <span className="shrink-0 rounded-full bg-secondary px-2 py-0.5 text-xs">
                        {CATEGORY_LABEL[skill.category] ?? skill.category}
                      </span>
                    )}
                    {!skill.is_active && (
                      <span className="shrink-0 rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-xs">
                        Inactive
                      </span>
                    )}
                  </div>
                  {skill.description && (
                    <p className="text-sm text-muted-foreground truncate mt-0.5">{skill.description}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">v{skill.version}</p>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  className="shrink-0 text-destructive hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteMutation.mutate(skill.id)
                  }}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
