// 报价类型定义 - 软件报价单（授权+服务）

// 授权类型
export type LicenseType = 'perpetual' | 'annual_subscription' | 'concurrent' | 'named'
// 服务类型
export type ServiceType = 'implementation' | 'training' | 'customization' | 'data_migration' | 'integration' | 'support'
// 报价状态
export type QuoteStatus = '草稿' | '已发送' | '已接受' | '已拒绝' | '已过期'

// 授权明细项
export interface LicenseItem {
  product_name: string
  version?: string
  license_type: LicenseType
  qty: number
  unit_price: number
  subtotal: number
  description?: string
}

// 实施服务项
export interface ServiceItem {
  service_type: ServiceType
  description?: string
  quantity: number   // 天数或人天
  daily_rate: number // 人天费率
  subtotal: number
  notes?: string
}

// 软件报价单
export interface Quote {
  id: string
  quote_no: string
  quote_title: string
  customer_id: string
  customer_name?: string
  project_id?: string
  project_name?: string
  channel_id?: string
  channel_name?: string
  quote_date: string
  valid_until?: string
  currency: string
  status: QuoteStatus

  // 授权明细
  license_items: LicenseItem[]
  license_subtotal: number

  // 服务明细
  service_items: ServiceItem[]
  service_subtotal: number

  // 汇总
  discount_rate: number
  discount_amount: number
  tax_rate: number
  tax_amount: number
  grand_total: number

  owner_id: string
  owner_name?: string
  internal_notes?: string
  customer_notes?: string

  created_at: string
  updated_at: string
}

// 创建报价请求
export interface CreateQuoteRequest {
  customer_id: string
  project_id?: string
  channel_id?: string
  quote_no?: string
  quote_title: string
  quote_date: string
  valid_until?: string
  currency?: string

  license_items: LicenseItem[]
  license_subtotal?: number
  service_items: ServiceItem[]
  service_subtotal?: number

  discount_rate?: number
  discount_amount?: number
  tax_rate?: number
  tax_amount?: number
  grand_total?: number

  internal_notes?: string
  customer_notes?: string
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
