// 项目类型定义
export interface Project {
  id: string
  project_name: string
  country: string
  customer_id?: string
  customer_name?: string
  channel_id?: string
  channel_name?: string
  owner_id: string
  owner_name: string
  project_amount?: number
  currency: string
  source_type: string
  current_stage: string
  stage_entered_at?: string
  planned_go_live?: string
  planned_acceptance?: string
  last_activity_at?: string
  health_status: string
  risk_level: string
  status: string
  created_at: string
  updated_at: string
}

// 创建项目请求
export interface CreateProjectRequest {
  project_name: string
  country: string
  customer_id?: string
  channel_id?: string
  owner_id?: string
  source_type: string
  project_amount?: number
  currency?: string
  planned_go_live?: string
  planned_acceptance?: string
}

// 更新项目请求
export interface UpdateProjectRequest {
  project_name?: string
  country?: string
  customer_id?: string
  channel_id?: string
  owner_id?: string
  source_type?: string
  project_amount?: number
  currency?: string
  planned_go_live?: string
  planned_acceptance?: string
  status?: string
}

// 阶段流转请求
export interface ChangeStageRequest {
  target_stage: string
}

// 活动日志
export interface ActivityLog {
  id: string
  project_id: string
  project_name?: string
  activity_type: string
  activity_content: string
  next_action?: string
  next_action_deadline?: string
  blocker_flag: boolean
  owner_id: string
  owner_name?: string
  source: string
  occurred_at: string
  created_at: string
}

// 创建活动日志请求
export interface CreateActivityRequest {
  activity_type: string
  activity_content: string
  next_action?: string
  blocker_flag?: boolean
  occurred_at?: string
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
