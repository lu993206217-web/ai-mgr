import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'dark' | 'light'

const STORAGE_KEY = 'app-theme-mode'

export const useThemeStore = defineStore('theme', () => {
  // 主题模式
  const themeMode = ref<ThemeMode>((localStorage.getItem(STORAGE_KEY) as ThemeMode) || 'dark')

  // 是否为深色模式
  const isDark = ref(themeMode.value === 'dark')

  // 应用主题到 DOM
  function applyTheme(mode: ThemeMode) {
    if (mode === 'dark') {
      document.documentElement.classList.remove('light-theme')
      document.documentElement.classList.add('dark-theme')
    } else {
      document.documentElement.classList.remove('dark-theme')
      document.documentElement.classList.add('light-theme')
    }
  }

  // 切换主题
  function toggleTheme() {
    themeMode.value = themeMode.value === 'dark' ? 'light' : 'dark'
  }

  function setTheme(mode: ThemeMode) {
    themeMode.value = mode
  }

  // 监听主题变化，自动应用
  watch(themeMode, (newMode) => {
    applyTheme(newMode)
    isDark.value = newMode === 'dark'
    localStorage.setItem(STORAGE_KEY, newMode)
  }, { immediate: true })

  return {
    themeMode,
    isDark,
    toggleTheme,
    setTheme,
  }
})
