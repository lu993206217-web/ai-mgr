// 用户类型定义
export interface User {
  id: string
  username: string
  email?: string
  full_name?: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
  last_login_at?: string
}

// 创建用户请求
export interface CreateUserRequest {
  username: string
  password: string
  email?: string
  full_name?: string
  role?: string
}

// 更新用户请求
export interface UpdateUserRequest {
  email?: string
  full_name?: string
  role?: string
  is_active?: boolean
  password?: string
}
