// 渠道类型定义
export interface Channel {
  id: string
  channel_name: string
  country: string
  region?: string
  contact_person?: string
  contact_phone?: string
  contact_email?: string
  cooperation_level: string
  cooperation_status: string
  cooperation_start_date?: string
  total_projects: number
  total_amount: number
  win_rate: number
  last_contact_date?: string
  created_at: string
  updated_at: string
}

// 创建渠道请求
export interface CreateChannelRequest {
  channel_name: string
  country: string
  region?: string
  contact_person?: string
  contact_phone?: string
  contact_email?: string
  cooperation_level?: string
  cooperation_status?: string
  cooperation_start_date?: string
}

// 更新渠道请求
export interface UpdateChannelRequest {
  channel_name?: string
  country?: string
  region?: string
  contact_person?: string
  contact_phone?: string
  contact_email?: string
  cooperation_level?: string
  cooperation_status?: string
  cooperation_start_date?: string
}
