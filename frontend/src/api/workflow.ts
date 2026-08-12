import request from '@/utils/request'
import type { WorkflowAlert, WorkflowAutomationRun, WorkflowAutomationTask, WorkflowItem, WorkflowSummary } from '@/types/workflow'

export function getWorkflowSummary() {
  return request.get<any, { data: WorkflowSummary }>('/workflow-center/summary')
}

export function getWorkflowItems(params: Record<string, any>) {
  return request.get<any, { data: { items: WorkflowItem[]; total: number; page: number; page_size: number; total_pages: number } }>(
    '/workflow-center/items',
    { params },
  )
}

export function getWorkflowItem(id: string) {
  return request.get<any, { data: WorkflowItem }>(`/workflow-center/items/${id}`)
}

export function createWorkflowItem(data: Record<string, any>) {
  return request.post<any, { data: WorkflowItem }>('/workflow-center/items', data)
}

export function transitionWorkflowItem(id: string, status: string, note?: string) {
  return request.post<any, { data: WorkflowItem }>(`/workflow-center/items/${id}/transition`, { status, note })
}

export function assignWorkflowItem(id: string, ownerId: string) {
  return request.post<any, { data: WorkflowItem }>(`/workflow-center/items/${id}/assign`, { owner_id: ownerId })
}

export function evaluateWorkflowAlerts() {
  return request.post<any, { data: { created: number; updated: number; resolved: number } }>(
    '/workflow-center/alerts/evaluate',
  )
}

export function getWorkflowAlerts(params: Record<string, any>) {
  return request.get<any, { data: { items: WorkflowAlert[]; total: number; page: number; page_size: number; total_pages: number } }>(
    '/workflow-center/alerts',
    { params },
  )
}

export function handleWorkflowAlert(id: string, status = '已解除', note?: string) {
  return request.post(`/workflow-center/alerts/${id}/handle`, { status, note })
}

export function getWorkflowAutomationTasks() {
  return request.get<any, { data: WorkflowAutomationTask[] }>('/workflow-center/automation/tasks')
}

export function updateWorkflowAutomationTask(id: string, data: Record<string, any>) {
  return request.put<any, { data: WorkflowAutomationTask }>(`/workflow-center/automation/tasks/${id}`, data)
}

export function runWorkflowAutomationTask(id: string) {
  return request.post<any, { data: WorkflowAutomationRun }>(`/workflow-center/automation/tasks/${id}/run`)
}

export function getWorkflowAutomationRuns(params: Record<string, any> = {}) {
  return request.get<any, { data: { items: WorkflowAutomationRun[]; total: number; page: number; page_size: number; total_pages: number } }>(
    '/workflow-center/automation/runs',
    { params },
  )
}
