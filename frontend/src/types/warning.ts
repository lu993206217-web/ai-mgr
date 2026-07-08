// 预警类型定义
export interface WarningRule {
  id: string
  rule_code: string
  rule_name: string
  description?: string
  conditions: string
  severity: string
  notify_target: string
  notify_channel: string
  cooldown_days: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// 创建预警规则请求
export interface CreateWarningRuleRequest {
  rule_code: string
  rule_name: string
  description?: string
  conditions: string
  severity?: string
  notify_target?: string
  notify_channel?: string
  cooldown_days?: number
  is_active?: boolean
}

// 更新预警规则请求
export interface UpdateWarningRuleRequest {
  rule_code?: string
  rule_name?: string
  description?: string
  conditions?: string
  severity?: string
  notify_target?: string
  notify_channel?: string
  cooldown_days?: number
  is_active?: boolean
}

// 预警实例
export interface WarningInstance {
  id: string
  rule_id: string
  rule_name?: string
  project_id?: string
  project_name?: string
  channel_id?: string
  channel_name?: string
  severity: string
  status: string
  message: string
  notified_at?: string
  resolved_at?: string
  created_at: string
}

// 创建预警实例请求
export interface CreateWarningInstanceRequest {
  rule_id: string
  project_id?: string
  channel_id?: string
  severity?: string
  message: string
}
