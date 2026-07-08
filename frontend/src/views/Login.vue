<template>
  <div class="login-container">
    <div class="login-card fade-in">
      <div class="login-header">
        <h1 class="login-title">🏗️ AI 项目推进控制塔</h1>
        <p class="login-subtitle">AI Project Control Tower</p>
      </div>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-button"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <p>默认账号：admin / admin123</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authStore.handleLogin({
          username: loginForm.username,
          password: loginForm.password,
        })
        ElMessage.success('登录成功')
        router.push('/')
      } catch (error: any) {
        ElMessage.error(error.message || '登录失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: var(--bg-secondary);
  border-radius: 16px;
  padding: 48px 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  letter-spacing: 2px;
  text-transform: uppercase;
}

.login-form {
  margin-bottom: 24px;
}

.login-form :deep(.el-input__wrapper) {
  background-color: var(--bg-tertiary);
  box-shadow: 0 0 0 1px var(--border-color) inset;
  border-radius: 8px;
}

.login-form :deep(.el-input__inner) {
  color: var(--text-primary);
  height: 44px;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: var(--text-muted);
}

.login-button {
  width: 100%;
  height: 44px;
  font-size: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent-color) 0%, var(--accent-color-dark) 100%);
  border: none;
  letter-spacing: 8px;
  font-weight: 600;
}

.login-button:hover {
  background: linear-gradient(135deg, var(--accent-color-dark) 0%, var(--accent-color-darker) 100%);
}

.login-footer {
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.login-footer p {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
