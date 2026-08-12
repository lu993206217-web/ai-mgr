import request from '@/utils/request'
import type {
  DailyReportBinding,
  DailyReportSyncRequest,
  DailyReportSyncRun,
  DailyReportUnmatchedProject,
  DailyReportRawEntry,
  PaginatedResponse,
} from '@/types/dailyReport'

export function syncDailyReports(data: DailyReportSyncRequest) {
  return request.post<any, { data: DailyReportSyncRun }>('/daily-reports/sync', data)
}

export function getDailyReportRuns(params?: {
  page?: number
  page_size?: number
}) {
  return request.get<any, PaginatedResponse<DailyReportSyncRun>>('/daily-reports/runs', { params })
}

export function getDailyReportRawEntries(params?: {
  analysis_status?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}) {
  return request.get<any, PaginatedResponse<DailyReportRawEntry>>('/daily-reports/raw-entries', { params })
}

export function getDailyReportUnmatched(params?: {
  month?: string
  status?: string
  confidence_level?: 'high' | 'low'
  keyword?: string
  page?: number
  page_size?: number
}) {
  return request.get<any, PaginatedResponse<DailyReportUnmatchedProject>>('/daily-reports/unmatched', { params })
}

export function bindDailyReportUnmatched(id: string, data: {
  project_id: string
  sync_after_bind?: boolean
}) {
  return request.post<any, { data: DailyReportUnmatchedProject }>(`/daily-reports/unmatched/${id}/bind`, data)
}

export function ignoreDailyReportUnmatched(id: string) {
  return request.post<any, { data: DailyReportUnmatchedProject }>(`/daily-reports/unmatched/${id}/ignore`)
}

export function getDailyReportBindings(params?: {
  page?: number
  page_size?: number
}) {
  return request.get<any, PaginatedResponse<DailyReportBinding>>('/daily-reports/bindings', { params })
}
