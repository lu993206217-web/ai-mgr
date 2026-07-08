import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { useAuthStore } from '@/stores/auth'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/',
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '驾驶舱' },
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/ProjectList.vue'),
        meta: { title: '项目管理' },
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/ProjectDetail.vue'),
        meta: { title: '项目详情' },
      },
      {
        path: 'channels',
        name: 'ChannelList',
        component: () => import('@/views/ChannelList.vue'),
        meta: { title: '渠道管理' },
      },
      {
        path: 'customers',
        name: 'CustomerList',
        component: () => import('@/views/CustomerList.vue'),
        meta: { title: '客户管理' },
      },
      {
        path: 'quotes',
        name: 'QuoteList',
        component: () => import('@/views/QuoteList.vue'),
        meta: { title: '报价管理' },
      },
      {
        path: 'warnings',
        name: 'WarningCenter',
        component: () => import('@/views/WarningCenter.vue'),
        meta: { title: '预警中心' },
      },
      {
        path: 'users',
        name: 'UserList',
        component: () => import('@/views/UserList.vue'),
        meta: { title: '用户管理' },
      },
      {
        path: 'config',
        name: 'ConfigCenter',
        component: () => import('@/views/ConfigCenter.vue'),
        meta: { title: '阈值配置' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - AI 项目推进控制塔`
  }
  
  // 检查是否需要认证
  const requiresAuth = to.meta.requiresAuth !== false
  const authStore = useAuthStore()
  
  if (requiresAuth && !authStore.token) {
    // 未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && authStore.token) {
    // 已登录，跳转到首页
    next('/')
  } else {
    next()
  }
})

export default router
