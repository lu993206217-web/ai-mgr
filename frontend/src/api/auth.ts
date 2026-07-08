import request from '@/utils/request'
import type { LoginRequest, LoginResponse, User } from '@/types/auth'

// 登录
export function login(data: LoginRequest) {
  return request.post<LoginResponse>('/auth/login', data)
}

// 获取当前用户信息
export function getUserInfo() {
  return request.get<User>('/auth/me')
}

// 刷新 Token
export function refreshToken(refreshToken: string) {
  return request.post<LoginResponse>('/auth/refresh', { refresh_token: refreshToken })
}

// 退出登录
export function logout() {
  return request.post('/auth/logout')
}
