import request from '@/utils/request'
import type {
  EmailConnectionStatus,
  EmailConnections,
  DingTalkMailSyncResult,
  DingTalkMailConfig,
  DingTalkMailConfigUpdate,
  IntelligenceEmail,
  ManualEmailIngest,
} from '@/types/emailIntelligence'

export function getEmailConnectionStatus() {
  return request.get<any>(`/email-intelligence/connection`) as Promise<{
    data: EmailConnectionStatus
  }>
}

export function getDingTalkMailConfig() {
  return request.get<any>(`/email-intelligence/providers/dingtalk/config`) as Promise<{
    data: DingTalkMailConfig
  }>
}

export function updateDingTalkMailConfig(data: DingTalkMailConfigUpdate) {
  return request.put<any>(`/email-intelligence/providers/dingtalk/config`, data) as Promise<{
    data: DingTalkMailConfig
    message?: string
  }>
}

export function getEmailConnections() {
  return request.get<any>(`/email-intelligence/connections`) as Promise<{
    data: EmailConnections
  }>
}

export function testDingTalkMailConnection() {
  return request.post<any>(`/email-intelligence/providers/dingtalk/test`) as Promise<{
    data: EmailConnectionStatus
    message?: string
  }>
}

export function syncDingTalkMail(maxMessages = 50, unseenOnly = false) {
  return request.post<any>(`/email-intelligence/providers/dingtalk/sync`, {
    max_messages: maxMessages,
    unseen_only: unseenOnly,
  }) as Promise<{
    data: DingTalkMailSyncResult
    message?: string
  }>
}

export function getIntelligenceEmails(params: {
  page?: number
  page_size?: number
  match_status?: string
  keyword?: string
}) {
  return request.get<any>(`/email-intelligence`, { params }) as Promise<{
    data: {
      items: IntelligenceEmail[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }
  }>
}

export function manualIngestEmail(data: ManualEmailIngest) {
  return request.post<any>(`/email-intelligence/manual-ingest`, data) as Promise<{
    data: IntelligenceEmail
    message: string
  }>
}

export function bindEmailToProject(emailId: string, projectId: string, reason?: string) {
  return request.post<any>(`/email-intelligence/${emailId}/bind`, {
    project_id: projectId,
    create_activity: true,
    reason,
  }) as Promise<{ data: IntelligenceEmail }>
}
