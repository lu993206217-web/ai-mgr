import request from '@/utils/request'
export interface CriterionConfig {
  code: `c${number}`
  title: string
  required: boolean
  requirement: string
  evidence_requirements: string[]
  enabled: boolean
  thresholds: Record<string, number>
}

export interface PerformanceConfig {
  enabled: boolean
  scope: 'all_projects' | 'owned_projects'
  schedule_frequency: 'monthly' | 'quarterly'
  schedule_day: number
  schedule_hour: number
  schedule_minute: number
  criteria: CriterionConfig[]
  last_run_at?: string | null
}

export interface CriterionResult extends CriterionConfig {
  status: string
  conclusion: string
  metrics: Array<{ label: string; value: number | string; unit: string }>
  evidence: string[]
  gaps: string[]
  records: any
}

export interface PerformanceSummary {
  period: {
    label: string
    type: string
    start_date: string
    end_date: string
    scope: string
  }
  source_summary: Record<'projects' | 'activities' | 'emails' | 'files', number>
  status_summary: Record<string, number>
  criteria: CriterionResult[]
  generated_at: string
  notice: string
}

export interface PerformanceReport {
  id: string
  period_label: string
  period_type: string
  start_date: string
  end_date: string
  scope: string
  trigger_type: string
  status: string
  generated_at: string
  summary: PerformanceSummary
  error_message?: string | null
}

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export function getPerformanceConfig() {
  return request.get<ApiResponse<PerformanceConfig>>('/overseas-performance/config')
}

export function updatePerformanceConfig(data: PerformanceConfig) {
  return request.put<ApiResponse<PerformanceConfig>>('/overseas-performance/config', data)
}

export function generatePerformanceReport(data: {
  period_type: string
  start_date: string
  end_date: string
  period_label: string
  scope: 'all_projects' | 'owned_projects'
}) {
  return request.post<ApiResponse<PerformanceReport>>('/overseas-performance/generate', data)
}

export function getPerformanceReports(limit = 20) {
  return request.get<ApiResponse<{ items: Omit<PerformanceReport, 'summary'>[]; total: number }>>(
    '/overseas-performance/reports',
    { params: { limit } },
  )
}

export function getPerformanceReport(id: string) {
  return request.get<ApiResponse<PerformanceReport>>(`/overseas-performance/reports/${id}`)
}
