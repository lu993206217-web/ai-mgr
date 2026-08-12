export interface WorkflowEvidence {
  id: string
  source_type: string
  source_id: string
  activity_id?: string
  evidence_at: string
  summary: string
  decision: string
  confidence?: number
  reason?: string
}

export interface WorkflowStateEvent {
  id: string
  from_status?: string
  to_status: string
  source: string
  reason?: string
  changed_by?: string
  occurred_at: string
}

export interface WorkflowItem {
  id: string
  project_id: string
  project_name?: string
  owner_id?: string
  owner_name?: string
  title: string
  description: string
  status: string
  responsibility_party: string
  priority: string
  due_date?: string
  source_type: string
  ai_generated: boolean
  ai_confidence?: number
  ai_reason?: string
  last_progress_at: string
  completed_at?: string
  evidence_count: number
  alert_level?: string
  created_at: string
  updated_at: string
  evidences?: WorkflowEvidence[]
  state_events?: WorkflowStateEvent[]
}

export interface WorkflowSummary {
  total_open: number
  ai_pending: number
  mine_pending: number
  waiting_external: number
  due_today: number
  overdue: number
  suspected_complete: number
  active_alerts: number
}

export interface WorkflowAlert {
  id: string
  workflow_item_id?: string
  project_id: string
  project_name?: string
  item_title?: string
  alert_type: string
  level: string
  status: string
  threshold_days: number
  elapsed_days: number
  message: string
  evidence_at?: string
  first_triggered_at: string
  last_evaluated_at: string
  resolved_at?: string
}

export interface WorkflowAutomationTask {
  id: string
  task_code: 'email_sync' | 'daily_report_sync' | 'warning_evaluation' | string
  task_name: string
  description: string
  enabled: boolean
  schedule_type: 'interval' | 'daily'
  interval_minutes?: number
  schedule_hour?: number
  schedule_minute?: number
  lookback_days?: number
  source_ready: boolean
  source_message?: string
  next_run_at?: string
  last_started_at?: string
  last_finished_at?: string
  last_status?: string
  last_result?: string
  last_error?: string
}

export interface WorkflowAutomationRun {
  id: string
  task_id: string
  task_name?: string
  trigger_type: string
  status: string
  result_json?: Record<string, any>
  error_message?: string
  started_at?: string
  finished_at?: string
  created_at: string
}

export interface PaginatedWorkflow<T> {
  data: {
    items: T[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}
