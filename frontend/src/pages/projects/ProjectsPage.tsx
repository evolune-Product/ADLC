import { useNavigate } from 'react-router-dom'
import { Plus, FolderOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatsGrid } from '@/components/ui/StatsGrid'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { useProjects } from '@/hooks/useProjects'

const TYPE_LABEL: Record<string, string> = {
  backend: 'Backend', frontend: 'Frontend', fullstack: 'Fullstack',
  mobile: 'Mobile', data: 'Data', other: 'Other',
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const { data: projects = [], isLoading } = useProjects()

  const active   = projects.filter((p) => p.status === 'active').length
  const archived = projects.filter((p) => p.status === 'archived').length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Projects"
        subtitle="Onboard a codebase, connect Jira, assign a pod."
        action={
          <Button onClick={() => navigate('/projects/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Project
          </Button>
        }
      />

      <StatsGrid
        stats={[
          { label: 'Total',    value: projects.length },
          { label: 'Active',   value: active },
          { label: 'Archived', value: archived },
        ]}
      />

      {isLoading ? (
        <LoadingSkeleton />
      ) : projects.length === 0 ? (
        <EmptyState
          icon={<FolderOpen className="h-10 w-10" />}
          title="No projects yet"
          subtitle="Create your first project to start running agents."
          action={
            <Button variant="outline" onClick={() => navigate('/projects/new')}>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {projects.map((project) => (
            <Card
              key={project.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => navigate(`/projects/${project.id}`)}
            >
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
                  <FolderOpen className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium truncate">{project.name}</p>
                    {project.type && (
                      <span className="rounded-full bg-secondary px-2 py-0.5 text-xs shrink-0">
                        {TYPE_LABEL[project.type] ?? project.type}
                      </span>
                    )}
                    {project.status === 'archived' && (
                      <span className="rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-xs shrink-0">
                        Archived
                      </span>
                    )}
                  </div>
                  {project.description && (
                    <p className="text-sm text-muted-foreground truncate mt-0.5">{project.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
                    {project.repo_name && <span>Repo: {project.repo_name}</span>}
                    {project.jira_project_key && <span>Jira: {project.jira_project_key}</span>}
                    {project.pod_name && <span>Pod: {project.pod_name}</span>}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
