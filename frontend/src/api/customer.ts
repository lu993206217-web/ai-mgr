import request from '@/utils/request'

// 获取客户列表
export function getCustomers(params: {
  page?: number
  page_size?: number
  customer_name?: string
  country?: string
}) {
  return request.get(`/customers`, { params })
}

// 获取客户详情
export function getCustomer(id: string) {
  return request.get(`/customers/${id}`)
}

// 创建客户
export function createCustomer(data: any) {
  return request.post(`/customers`, data)
}

// 更新客户
export function updateCustomer(id: string, data: any) {
  return request.put(`/customers/${id}`, data)
}

// 删除客户
export function deleteCustomer(id: string) {
  return request.delete(`/customers/${id}`)
}
