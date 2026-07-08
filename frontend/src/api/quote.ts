import request from '@/utils/request'
import type { Quote, CreateQuoteRequest, PaginatedResponse } from '@/types/quote'

// 获取报价列表
export function getQuotes(params?: {
  page?: number
  page_size?: number
  customer_id?: string
  project_id?: string
}) {
  return request.get<any, PaginatedResponse<Quote>>('/quotes', { params })
}

// 获取报价详情
export function getQuote(id: string) {
  return request.get<any, { data: Quote }>(`/quotes/${id}`)
}

// 创建报价单（软件授权+服务）
export function createQuote(data: CreateQuoteRequest) {
  return request.post<any, { data: Quote }>('/quotes', data)
}

// 更新报价单
export function updateQuote(id: string, data: Partial<CreateQuoteRequest>) {
  return request.put<any, { data: Quote }>(`/quotes/${id}`, data)
}

// 删除报价单
export function deleteQuote(id: string) {
  return request.delete(`/quotes/${id}`)
}
