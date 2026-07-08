import request from '@/utils/request'

// 获取用户列表
export function getUsers(params: {
  page?: number
  page_size?: number
  username?: string
  role?: string
}) {
  return request.get(`/users`, { params })
}

// 获取用户详情
export function getUser(id: string) {
  return request.get(`/users/${id}`)
}

// 创建用户
export function createUser(data: any) {
  return request.post(`/users`, data)
}

// 更新用户
export function updateUser(id: string, data: any) {
  return request.put(`/users/${id}`, data)
}

// 删除用户
export function deleteUser(id: string) {
  return request.delete(`/users/${id}`)
}
