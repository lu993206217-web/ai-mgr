export interface DailyReportSyncRun {
  id: string
  month: string
  trigger_type: string
  status: string
  lookback_days: number
  started_at: string
  finished_at?: string
  options_count: number
  auto_bound_count: number
  unmatched_count: number
  imported_activity_count: number
  skipped_duplicate_count: number
  error_message?: string
}

export interface DailyReportBinding {
  id: string
  project_id: string
  project_name?: string
  project_key: string
  external_project_name: string
  match_method: string
  match_score: number
  is_active: boolean
  last_sync_month?: string
  last_sync_at?: string
  created_at: string
  updated_at: string
}

export interface DailyReportUnmatchedProject {
  id: string
  month: string
  project_key: string
  external_project_name: string
  active_days: number
  last_active_date?: string
  pre_sales_entry_count: number
  implementation_entry_count: number
  service_entry_count: number
  suggested_project_id?: string
  suggested_project_name?: string
  suggested_score: number
  status: string
  created_at: string
  updated_at: string
  handled_at?: string
  imported_activity_count?: number
  skipped_duplicate_count?: number
  sample_original_summary?: string
  sample_ai_reason?: string
  sample_creator_name?: string
  sample_source_date?: string
  source_project_names?: string[]
  diagnosis_hint?: string
}

export interface DailyReportSyncRequest {
  month?: string
  start_date?: string
  end_date?: string
  project_ids?: string[]
  lookback_days?: number
  trigger_ingestion?: boolean
}

export interface DailyReportRawEntry {
  id: string
  sync_run_id?: string
  source_date: string
  project_key: string
  external_project_name: string
  creator_name?: string
  original_summary: string
  source_occurred_at?: string
  analysis_status: string
  ai_project_id?: string
  ai_project_name?: string
  ai_confidence?: number
  ai_reason?: string
  ai_summary?: string
  ai_activity_type?: string
  ai_occurred_at?: string
  error_message?: string
  activity_log_id?: string
  analyzed_at?: string
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
