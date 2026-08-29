import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export interface WorkflowNode {
  id: string
  type: string
  config?: Record<string, unknown>
  next?: string | string[] | { field?: string; branches?: Record<string, string>; default?: string }
}

export interface WorkflowDefinition {
  start_node_id: string
  nodes: WorkflowNode[]
}

export interface Workflow {
  id:              string
  organization_id: string
  department_id:   string | null
  name:            string
  description:     string | null
  trigger_type:    string
  definition:      WorkflowDefinition
  is_active:       boolean
  version:         number
  created_by:      string | null
  created_at:      string
  updated_at:      string
}

export interface WorkflowExecutionStep {
  id:            string
  execution_id:  string
  node_id:       string
  node_type:     string
  status:        string
  input:         Record<string, unknown>
  output:        Record<string, unknown> | null
  error:         string | null
  started_at:    string
  completed_at:  string | null
}

export interface WorkflowExecution {
  id:               string
  workflow_id:      string
  organization_id:  string
  work_id:          string | null
  status:           string
  current_node_id:  string | null
  context:          Record<string, unknown>
  started_at:       string
  completed_at:     string | null
  error:            string | null
}

export interface WorkflowExecutionDetail extends WorkflowExecution {
  steps: WorkflowExecutionStep[]
}

const KEY = ['workflows']

export function useWorkflows() {
  return useQuery<Workflow[]>({
    queryKey: KEY,
    queryFn: () => api.get('/workflows/').then((r) => r.data),
  })
}

export function useWorkflow(id: string | undefined) {
  return useQuery<Workflow>({
    queryKey: [...KEY, id],
    queryFn: () => api.get(`/workflows/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useWorkflowExecutions(id: string | undefined) {
  return useQuery<WorkflowExecution[]>({
    queryKey: [...KEY, id, 'executions'],
    queryFn: () => api.get(`/workflows/${id}/executions`).then((r) => r.data),
    enabled: !!id,
    refetchInterval: 5000,
  })
}

export function useWorkflowExecution(executionId: string | undefined) {
  return useQuery<WorkflowExecutionDetail>({
    queryKey: [...KEY, 'executions', executionId],
    queryFn: () => api.get(`/workflows/executions/${executionId}`).then((r) => r.data),
    enabled: !!executionId,
    refetchInterval: (q) => (q.state.data && ['completed', 'failed', 'cancelled'].includes(q.state.data.status) ? false : 4000),
  })
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      name: string; description?: string; department_id?: string | null;
      trigger_type: string; definition: WorkflowDefinition; is_active: boolean;
    }) => api.post('/workflows/', body).then((r) => r.data as Workflow),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  })
}

export function useDeactivateWorkflow() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/workflows/${id}/deactivate`).then((r) => r.data as Workflow),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  })
}

export function useExecuteWorkflow() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, work_id, initial_context }: { id: string; work_id?: string; initial_context?: Record<string, unknown> }) =>
      api.post(`/workflows/${id}/execute`, { work_id, initial_context: initial_context ?? {} }).then((r) => r.data as WorkflowExecution),
    onSuccess: (_data, vars) => queryClient.invalidateQueries({ queryKey: [...KEY, vars.id, 'executions'] }),
  })
}

export function useResumeExecution() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (executionId: string) => api.post(`/workflows/executions/${executionId}/resume`).then((r) => r.data as WorkflowExecution),
    onSuccess: (_data, executionId) => queryClient.invalidateQueries({ queryKey: [...KEY, 'executions', executionId] }),
  })
}
