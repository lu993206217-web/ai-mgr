import request from '@/utils/request'
import type { WarningRule, CreateWarningRuleRequest, UpdateWarningRuleRequest, WarningInstance, PaginatedResponse } from '@/types/warning'

// 获取预警规则列表
export function getWarningRules(params: {
  page?: number
  page_size?: number
  is_active?: boolean
}) {
  return request.get<any, PaginatedResponse<WarningRule>>(`/warnings/rules`, { params })
}

// 获取预警规则详情
export function getWarningRule(id: string) {
  return request.get<any, { data: WarningRule }>(`/warnings/rules/${id}`)
}

// 创建预警规则
export function createWarningRule(data: CreateWarningRuleRequest) {
  return request.post<any, { data: WarningRule }>(`/warnings/rules`, data)
}

// 更新预警规则
export function updateWarningRule(id: string, data: UpdateWarningRuleRequest) {
  return request.put<any, { data: WarningRule }>(`/warnings/rules/${id}`, data)
}

// 删除预警规则
export function deleteWarningRule(id: string) {
  return request.delete(`/warnings/rules/${id}`)
}

// 获取预警实例列表
export function getWarningInstances(params: {
  page?: number
  page_size?: number
  status?: string
  severity?: string
}) {
  return request.get<any, PaginatedResponse<WarningInstance>>(`/warnings/instances`, { params })
}

// 处理预警实例
export function resolveWarningInstance(id: string) {
  return request.post(`/warnings/instances/${id}/resolve`)
}

// 手动触发预警检查
export function triggerWarningCheck() {
  return request.post(`/warnings/check`)
}
