import request from '@/utils/request'
import type { Channel, CreateChannelRequest, UpdateChannelRequest, PaginatedResponse } from '@/types/channel'

// 获取渠道列表
export function getChannels(params: {
  page?: number
  page_size?: number
  channel_name?: string
  cooperation_status?: string
}) {
  return request.get<any, PaginatedResponse<Channel>>(`/channels`, { params })
}

// 获取渠道详情
export function getChannel(id: string) {
  return request.get<any, { data: Channel }>(`/channels/${id}`)
}

// 创建渠道
export function createChannel(data: CreateChannelRequest) {
  return request.post<any, { data: Channel }>(`/channels`, data)
}

// 更新渠道
export function updateChannel(id: string, data: UpdateChannelRequest) {
  return request.put<any, { data: Channel }>(`/channels/${id}`, data)
}

// 删除渠道
export function deleteChannel(id: string) {
  return request.delete(`/channels/${id}`)
}
