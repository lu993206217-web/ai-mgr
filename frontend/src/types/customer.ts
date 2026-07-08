// 客户类型定义
export interface Customer {
  id: string
  customer_name: string
  country: string
  industry?: string
  customer_type: string
  contact_person?: string
  contact_phone?: string
  contact_email?: string
  address?: string
  total_projects: number
  total_amount: number
  created_at: string
  updated_at: string
}

// 创建客户请求
export interface CreateCustomerRequest {
  customer_name: string
  country: string
  industry?: string
  customer_type?: string
  contact_person?: string
  contact_phone?: string
  contact_email?: string
  address?: string
}

// 更新客户请求
export interface UpdateCustomerRequest {
  customer_name?: string
  country?: string
  industry?: string
  customer_type?: string
  contact_person?: string
  contact_phone?: string
  contact_email?: string
  address?: string
}
