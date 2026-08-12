import request from '@/utils/request'
import type { Project, CreateProjectRequest, UpdateProjectRequest, ChangeStageRequest, ActivityLog, CreateActivityRequest, ProjectFile, CreateProjectFileRequest, ProjectStateEvent, PaginatedResponse } from '@/types/project'

// 获取项目列表
export function getProjects(params: {
  page?: number
  page_size?: number
  project_name?: string
  current_stage?: string
  health_status?: string
  status?: string
}) {
  return request.get<any, PaginatedResponse<Project>>(`/projects`, { params })
}

// 获取项目详情
export function getProject(id: string) {
  return request.get<any, { data: Project }>(`/projects/${id}`)
}

// 创建项目
export function createProject(data: CreateProjectRequest) {
  return request.post<any, { data: Project }>(`/projects`, data)
}

// 更新项目
export function updateProject(id: string, data: UpdateProjectRequest) {
  return request.put<any, { data: Project }>(`/projects/${id}`, data)
}

// 删除项目
export function deleteProject(id: string) {
  return request.delete(`/projects/${id}`)
}

// 阶段流转
export function changeStage(id: string, data: ChangeStageRequest) {
  return request.post<any, { data: Project }>(`/projects/${id}/stage`, data)
}

// 获取项目阶段和状态的事实记录
export function getProjectStateEvents(id: string) {
  return request.get<any, { data: ProjectStateEvent[] }>(`/projects/${id}/state-events`)
}

// 获取项目活动日志
export function getActivities(id: string, params?: {
  page?: number
  page_size?: number
}) {
  return request.get<any, PaginatedResponse<ActivityLog>>(`/projects/${id}/activities`, { params })
}

// 创建活动日志
export function createActivity(id: string, data: CreateActivityRequest) {
  return request.post<any, { data: ActivityLog }>(`/projects/${id}/activities`, data)
}

// 获取项目文件
export function getProjectFiles(id: string, params?: {
  page?: number
  page_size?: number
  file_category?: string
  keyword?: string
}) {
  return request.get<any, PaginatedResponse<ProjectFile>>(`/projects/${id}/files`, { params })
}

// 创建项目文件
export function createProjectFile(id: string, data: CreateProjectFileRequest) {
  return request.post<any, { data: ProjectFile }>(`/projects/${id}/files`, data)
}

// 更新项目文件
export function updateProjectFile(id: string, fileId: string, data: Partial<CreateProjectFileRequest>) {
  return request.put<any, { data: ProjectFile }>(`/projects/${id}/files/${fileId}`, data)
}

// 删除项目文件
export function deleteProjectFile(id: string, fileId: string) {
  return request.delete(`/projects/${id}/files/${fileId}`)
}
