// 用户类型定义
export interface User {
  id: string
  username: string
  full_name: string
  email: string
  role: 'admin' | 'pm' | 'user'
  is_active: boolean
  last_login_at?: string
  created_at: string
}

// 登录请求
export interface LoginRequest {
  username: string
  password: string
}

// 登录响应
export interface LoginResponse {
  token: string
  user: User
}

// 创建用户请求
export interface CreateUserRequest {
  username: string
  password: string
  full_name: string
  email: string
  role?: 'admin' | 'pm' | 'user'
}
