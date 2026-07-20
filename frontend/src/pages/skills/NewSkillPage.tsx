import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SkillForm } from '@/components/skills/SkillForm'
import { useCreateSkill } from '@/hooks/useSkills'

export default function NewSkillPage() {
  const navigate = useNavigate()
  const createMutation = useCreateSkill()

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/skills')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-semibold">New Skill</h1>
          <p className="text-sm text-muted-foreground">Define a reusable markdown skill for your agents.</p>
        </div>
      </div>

      <SkillForm
        loading={createMutation.isPending}
        onSave={(data) =>
          createMutation.mutate(data, {
            onSuccess: (skill) => navigate(`/skills/${skill.id}`),
          })
        }
      />
    </div>
  )
}
