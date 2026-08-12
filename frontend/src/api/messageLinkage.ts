import request from '@/utils/request'
export type MessagePriority = 'low' | 'normal' | 'high' | 'urgent'
export type RouteMode = 'ai' | 'user' | 'employee_group'

export interface MessageLinkageRule {
  scene_key: string
  scene_name: string
  business_domain: string
  description: string
  enabled: boolean
  category: string
  source_category: string
  priority: MessagePriority
  route_mode: RouteMode
  target_id?: string | null
  target_name?: string | null
  rollout_status: string
}

export interface MessageLinkageConfig {
  enabled: boolean
  base_url: string
  api_key_configured: boolean
  source_system: string
  timeout_seconds: number
  linkage_rules: MessageLinkageRule[]
  updated_at?: string | null
}

export interface MessageLinkageConfigUpdate {
  enabled: boolean
  base_url: string
  api_key?: string
  clear_api_key: boolean
  source_system: string
  timeout_seconds: number
  linkage_rules: MessageLinkageRule[]
}

export interface MessageCenterHealthResult {
  success: boolean
  message: string
  base_url: string
  response_time_ms?: number | null
  remote_status?: string | null
}

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export function getMessageLinkageConfig() {
  return request.get<ApiResponse<MessageLinkageConfig>>('/message-linkage/config')
}

export function updateMessageLinkageConfig(data: MessageLinkageConfigUpdate) {
  return request.put<ApiResponse<MessageLinkageConfig>>('/message-linkage/config', data)
}

export function testMessageCenterHealth() {
  return request.post<ApiResponse<MessageCenterHealthResult>>('/message-linkage/health-test')
}
