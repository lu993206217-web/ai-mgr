import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建 Axios 实例
const service: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 防止重复跳转登录页
let isRedirecting = false

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    // 直接从 localStorage 获取 token，避免依赖 Pinia store 初始化问题
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data

    // 如果返回格式是 { code, message, data }
    if (res.code !== undefined) {
      if (res.code === 200) {
        // 成功：直接返回数据，不做转换
        return res
      } else {
        ElMessage.error(res.message || '请求失败')
        return Promise.reject(new Error(res.message || '请求失败'))
      }
    }

    // 兼容非标准响应格式
    return res
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response

      if (status === 401) {
        // Token 过期或无效，直接清除 localStorage
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        // 防止多个 401 同时触发多次跳转
        if (!isRedirecting) {
          isRedirecting = true
          ElMessage.error('登录已过期，请重新登录')
          router.push('/login').finally(() => {
            isRedirecting = false
          })
        }
      } else if (status === 403) {
        ElMessage.error('没有权限访问')
      }
      // 其他业务错误（400, 404等）由调用方自己处理，不在这里显示
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }

    return Promise.reject(error)
  }
)

// 通用请求方法
const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.get(url, config)
  },

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.post(url, data, config)
  },

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.put(url, data, config)
  },

  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.delete(url, config)
  },
}

export default request
