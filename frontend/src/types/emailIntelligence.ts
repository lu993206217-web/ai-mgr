export interface EmailAttachment {
  id: string
  file_name: string
  mime_type?: string
  size_bytes?: number
  extraction_status: string
  document_type?: string
  summary?: string
}

export interface IntelligenceEmail {
  id: string
  provider: string
  external_id: string
  thread_id?: string
  subject: string
  sender: string
  recipients: string[]
  cc: string[]
  received_at: string
  body_text: string
  project_id?: string
  project_name?: string
  match_status: string
  match_method?: string
  match_score?: number
  analysis_status: string
  summary?: string
  customer_request?: string
  customer_attitude?: string
  action_items: string[]
  risks: string[]
  activity_id?: string
  attachments: EmailAttachment[]
  created_at: string
}

export interface EmailConnectionStatus {
  provider: string
  configured: boolean
  connected: boolean
  account_email?: string
  message: string
  receive_host?: string
  receive_port?: number
  send_host?: string
  send_port?: number
}

export interface EmailConnections {
  providers: EmailConnectionStatus[]
}

export interface DingTalkMailSyncResult {
  folders: string[]
  scanned_count: number
  imported_count: number
  duplicate_count: number
  matched_count: number
  activity_count: number
  failed_count: number
  errors: string[]
}

export interface DingTalkMailConfig {
  enabled: boolean
  account_email?: string
  password_configured: boolean
  imap_host: string
  imap_port: number
  smtp_host: string
  smtp_port: number
  inbox_folder: string
  sent_folder?: string
}

export interface DingTalkMailConfigUpdate {
  enabled: boolean
  account_email: string
  app_password?: string
  sent_folder?: string
  clear_password?: boolean
}

export interface ManualEmailIngest {
  external_id?: string
  thread_id?: string
  subject: string
  sender: string
  recipients: string[]
  cc: string[]
  received_at: string
  body_text: string
}
