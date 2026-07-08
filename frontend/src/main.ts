import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import { useThemeStore } from './stores/theme'
import './style.css'
import './styles/theme.css'

// 创建 Vue 应用实例
const app = createApp(App)

// 注册 Element Plus
app.use(ElementPlus)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册 Pinia（状态管理）
const pinia = createPinia()
app.use(pinia)

// 初始化主题（在 Pinia 注册后立即使用 store，让 watch 立即执行）
useThemeStore()

// 初始化认证状态（从 localStorage 恢复）
const authStore = useAuthStore()
authStore.init()

// 注册 Vue Router
app.use(router)

// 挂载应用
app.mount('#app')
