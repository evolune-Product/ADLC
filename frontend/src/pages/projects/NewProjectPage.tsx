import { useNavigate } from 'react-router-dom'
import { ProjectWizard } from '@/components/projects/ProjectWizard'
import { useCreateProject, type ProjectFormData } from '@/hooks/useProjects'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const createMutation = useCreateProject()

  function handleSave(data: ProjectFormData) {
    createMutation.mutate(data, {
      onSuccess: (project) => navigate(`/projects/${project.id}`),
    })
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">New Project</h1>
        <p className="text-sm text-muted-foreground mt-1">Connect your repo, issue tracker, and pod in 4 steps.</p>
      </div>
      <ProjectWizard onSave={handleSave} loading={createMutation.isPending} />
    </div>
  )
}
