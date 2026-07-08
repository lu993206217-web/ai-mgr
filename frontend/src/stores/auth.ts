import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/utils/request'
import type { User, LoginRequest } from '@/types/auth'

// 认证 Store
export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<User | null>(null)
  const loading = ref(false)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const userName = computed(() => user.value?.full_name || '用户')
  const userRole = computed(() => user.value?.role || 'user')

  // 登录
  async function handleLogin(data: LoginRequest) {
    const res = await request.post<{ access_token: string; refresh_token: string }>('/auth/login', data)
    // 后端返回 snake_case 格式
    token.value = res.data.access_token

    // 保存 token 到 localStorage
    localStorage.setItem('token', res.data.access_token)

    // 登录后获取用户信息
    try {
      const userRes = await request.get<User>('/auth/me')
      user.value = userRes.data
      localStorage.setItem('user', JSON.stringify(userRes.data))
    } catch (e) {
      // 获取用户信息失败不影响登录
      console.warn('获取用户信息失败', e)
    }
  }

  // 获取当前用户信息
  async function fetchUser() {
    if (!token.value) return
    
    // 先从 localStorage 恢复
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      try {
        user.value = JSON.parse(savedUser)
      } catch (e) {
        // JSON 解析失败，忽略
      }
    }
    
    try {
      const res = await request.get<User>('/auth/me')
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(res.data))
    } catch (error: any) {
      // 只有 401 错误才登出，其他错误（如网络问题）保留本地缓存的用户信息
      if (error?.response?.status === 401) {
        handleLogout()
      }
      // 非 401 错误不做登出处理，保留本地状态
    }
  }

  // 登出
  function handleLogout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // 初始化（应用启动时调用）
  async function init() {
    if (token.value) {
      await fetchUser()
    }
  }

  return {
    token,
    user,
    loading,
    isLoggedIn,
    userName,
    userRole,
    handleLogin,
    fetchUser,
    handleLogout,
    init,
  }
})
