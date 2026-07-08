<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="sidebar-header">
        <h1 class="logo" v-if="!isCollapsed">🏗️ 控制塔</h1>
        <h1 class="logo collapsed-logo" v-else>🏗️</h1>
      </div>
      
      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="active"
        >
          <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
          <span class="nav-text" v-if="!isCollapsed">{{ item.title }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 顶部导航 -->
      <header class="top-header">
        <div class="header-left">
          <el-button
            class="collapse-btn"
            :icon="isCollapsed ? Expand : Fold"
            @click="isCollapsed = !isCollapsed"
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title">
              {{ $route.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-tooltip :content="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'" placement="bottom">
            <el-button
              :icon="themeStore.isDark ? Sunny : Moon"
              circle
              class="theme-toggle-btn"
              @click="themeStore.toggleTheme()"
            />
          </el-tooltip>

          <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="notification-badge">
            <el-button :icon="Bell" circle @click="handleNotificationClick" />
          </el-badge>

          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-info">
              <el-avatar :size="32" class="user-avatar">
                {{ userStore.user?.full_name?.[0] || 'U' }}
              </el-avatar>
              <span class="user-name">{{ userStore.user?.full_name || '用户' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  系统设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 通知弹窗 -->
      <el-dialog
        v-model="notificationDialogVisible"
        title="通知中心"
        width="520px"
        :show-close="true"
        class="notification-dialog"
      >
        <div v-if="notifications.length === 0" class="empty-notifications">
          <el-icon class="empty-icon"><BellFilled /></el-icon>
          <p>暂无未读通知</p>
        </div>
        <div v-else class="notification-list">
          <div
            v-for="item in notifications"
            :key="item.id"
            class="notification-item"
            :class="`severity-${item.severity}`"
            @click="handleNotificationItemClick(item)"
          >
            <div class="notification-icon">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div class="notification-content">
              <div class="notification-title">
                {{ item.rule_name || '预警通知' }}
                <el-tag :type="getSeverityType(item.severity)" size="small" effect="dark">
                  {{ item.severity }}
                </el-tag>
              </div>
              <div class="notification-message">{{ item.message }}</div>
              <div class="notification-time">{{ formatTime(item.created_at) }}</div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="notificationDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="goToWarningCenter">查看全部预警</el-button>
        </template>
      </el-dialog>

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { ElMessage } from 'element-plus'
import { getWarningInstances } from '@/api/warning'
import {
  HomeFilled,
  FolderOpened,
  Connection,
  User as UserIcon,
  Document,
  WarningFilled,
  Setting,
  Tools,
  Fold,
  Expand,
  Bell,
  BellFilled,
  ArrowDown,
  User,
  SwitchButton,
  Sunny,
  Moon,
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useAuthStore()
const themeStore = useThemeStore()

const isCollapsed = ref(false)

// 通知相关
const notificationDialogVisible = ref(false)
const notifications = ref<any[]>([])
const unreadCount = ref(0)

async function loadNotifications() {
  try {
    // 获取活跃状态的预警实例
    const res = await getWarningInstances({ status: '活跃', page: 1, page_size: 5 })
    notifications.value = res.data?.items || []
    unreadCount.value = res.data?.total || 0
  } catch (error) {
    // 静默失败，不打扰用户
    console.warn('加载通知失败', error)
    notifications.value = []
    unreadCount.value = 0
  }
}

function handleNotificationClick() {
  notificationDialogVisible.value = true
  loadNotifications()
}

function handleNotificationItemClick(item: any) {
  notificationDialogVisible.value = false
  if (item.project_id) {
    router.push(`/projects/${item.project_id}`)
  } else {
    router.push('/warnings')
  }
}

function goToWarningCenter() {
  notificationDialogVisible.value = false
  router.push('/warnings')
}

function getSeverityType(severity: string) {
  const map: Record<string, any> = {
    '严重': 'danger',
    '高': 'danger',
    '中': 'warning',
    '低': 'info',
  }
  return map[severity] || 'info'
}

function formatTime(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
  return date.toLocaleDateString('zh-CN')
}

const menuItems = [
  { path: '/', title: '驾驶舱', icon: HomeFilled },
  { path: '/projects', title: '项目管理', icon: FolderOpened },
  { path: '/channels', title: '渠道管理', icon: Connection },
  { path: '/customers', title: '客户管理', icon: UserIcon },
  { path: '/quotes', title: '报价管理', icon: Document },
  { path: '/warnings', title: '预警中心', icon: WarningFilled },
  { path: '/users', title: '用户管理', icon: Setting },
  { path: '/config', title: '系统设置', icon: Tools },
]

function handleUserCommand(command: string) {
  if (command === 'logout') {
    userStore.handleLogout()
    router.push('/login')
  } else if (command === 'profile') {
    // 跳转到用户管理页面查看个人信息
    router.push('/users')
  } else if (command === 'settings') {
    // 跳转到阈值配置页面
    router.push('/config')
  }
}

// 路由变化时重新加载通知
watch(
  () => route.path,
  () => {
    loadNotifications()
  },
  { immediate: true }
)
</script>

<style scoped>
.main-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* ============ 侧边栏样式 ============ */

.sidebar {
  width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  transition: width 0.3s ease;
  display: flex;
  flex-direction: column;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border-color);
  padding: 0 16px;
}

.logo {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-secondary);
  margin: 0;
  white-space: nowrap;
}

.collapsed-logo {
  font-size: 24px;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 4px;
  border-radius: 8px;
  color: var(--text-tertiary);
  text-decoration: none;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.nav-item.active {
  background: linear-gradient(135deg, var(--accent-color) 0%, var(--accent-color-dark) 100%);
  color: white;
}

.nav-icon {
  font-size: 18px;
  margin-right: 12px;
  flex-shrink: 0;
}

.nav-text {
  font-size: 14px;
  font-weight: 500;
}

/* ============ 主内容区样式 ============ */

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-header {
  height: 60px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  font-size: 18px;
}

.collapse-btn:hover {
  color: var(--text-secondary);
  background: var(--bg-tertiary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.notification-badge {
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s ease;
}

.user-info:hover {
  background: var(--bg-tertiary);
}

.user-avatar {
  background: linear-gradient(135deg, var(--accent-color) 0%, var(--accent-color-dark) 100%);
  color: white;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* ============ 通知弹窗样式 ============ */

.notification-list {
  max-height: 400px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-color);
}

.notification-item:hover {
  background: var(--bg-hover);
  transform: translateX(2px);
}

.notification-item:last-child {
  margin-bottom: 0;
}

.notification-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.notification-item.severity-高 .notification-icon,
.notification-item.severity-严重 .notification-icon {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger-color);
}

.notification-item.severity-中 .notification-icon {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning-color);
}

.notification-item.severity-低 .notification-icon {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-color);
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 4px;
}

.notification-message {
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 4px;
  word-break: break-word;
}

.notification-time {
  color: var(--text-muted);
  font-size: 12px;
}

.empty-notifications {
  text-align: center;
  padding: 40px 0;
  color: var(--text-muted);
}

.empty-notifications .empty-icon {
  font-size: 48px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.empty-notifications p {
  margin: 0;
  font-size: 14px;
}

:deep(.notification-dialog) {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

:deep(.notification-dialog .el-dialog__title) {
  color: var(--text-primary);
}

:deep(.notification-dialog .el-dialog__body) {
  padding: 16px 20px;
  color: var(--text-secondary);
}

:deep(.notification-dialog .el-dialog__header) {
  border-bottom: 1px solid var(--border-color);
}

/* ============ 页面内容区样式 ============ */

.page-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background: var(--bg-primary);
}
</style>
