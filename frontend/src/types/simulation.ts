// Persona-driven simulated user testing — see backend/app/models/persona.py
// and backend/app/models/simulation.py for the source of truth.

export interface Persona {
  id: string
  user_id: string
  org_id: string | null
  project_id: string | null
  name: string
  description: string
  entry_url: string
  created_at: string
  updated_at: string
}

export type SimulationStatus = 'pending' | 'running' | 'completed' | 'failed'
export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low'

export interface SimulationFinding {
  id: string
  simulation_run_id: string
  severity: FindingSeverity
  title: string
  description: string
  reproduction_steps: string[]
  screenshot_path: string | null
  step_number: number | null
  posted_to_tracker: boolean
  notified: boolean
  created_at: string
}

export interface SimulationRun {
  id: string
  user_id: string
  org_id: string | null
  persona_id: string
  persona_name: string | null
  ticket_id: string | null
  ticket_jira_id: string | null
  ticket_url: string | null
  target_url: string
  status: SimulationStatus
  steps_taken: number
  max_steps: number
  summary: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  finding_count: number | null
  findings?: SimulationFinding[]
}
