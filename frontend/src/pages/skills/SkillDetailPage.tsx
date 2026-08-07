import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SkillForm } from '@/components/skills/SkillForm'
import { useSkill, useUpdateSkill, useDeleteSkill } from '@/hooks/useSkills'
import type { Skill } from '@/types'

export default function SkillDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: skill, isLoading } = useSkill(id!)
  const updateMutation = useUpdateSkill(id!)
  const deleteMutation = useDeleteSkill()

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        <div className="h-96 bg-muted animate-pulse rounded" />
      </div>
    )
  }

  if (!skill) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Skill not found.{' '}
        <button className="underline" onClick={() => navigate('/skills')}>
          Go back
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/skills')}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-semibold">{skill.name}</h1>
            <p className="text-sm text-muted-foreground">v{skill.version}</p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          disabled={deleteMutation.isPending}
          onClick={() =>
            deleteMutation.mutate(skill.id, {
              onSuccess: () => navigate('/skills'),
            })
          }
        >
          <Trash2 className="h-4 w-4 mr-1" />
          Delete
        </Button>
      </div>

      <SkillForm
        initial={skill}
        splitView
        loading={updateMutation.isPending}
        onSave={(data) => updateMutation.mutate(data as Partial<Skill>)}
      />
    </div>
  )
}
