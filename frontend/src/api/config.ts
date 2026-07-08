import request from '@/utils/request'

// 驾驶舱阈值配置接口
export interface DashboardThresholds {
  zombie_project_days: number
  fake_progress_count: number
  sunk_channel_days: number
  overdue_acceptance_days: number
  sunk_channel_warning_days: number
  waiting_too_long_days: number
  today_followup_limit: number
  poc_overdue_days: number
  acceptance_overdue_days: number
  acceptance_plan_overdue_days: number
  no_activity_warning_days: number
  quote_no_progress_days: number
  updated_at?: string
}

// 获取阈值配置
export function getThresholds() {
  return request.get('/config/thresholds')
}

// 更新阈值配置
export function updateThresholds(data: Partial<DashboardThresholds>) {
  return request.put('/config/thresholds', data)
}

// 重置为默认阈值
export function resetThresholds() {
  return request.post('/config/thresholds/reset')
}
