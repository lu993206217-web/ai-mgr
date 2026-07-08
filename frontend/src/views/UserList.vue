<template>
  <div class="user-list-container fade-in">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">👤 用户管理</h2>
        <p class="page-subtitle">管理系统用户和角色</p>
      </div>
      <el-button type="primary" size="large" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        创建用户
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="filters.username"
        placeholder="搜索用户名..."
        class="filter-input"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select
        v-model="filters.role"
        placeholder="角色"
        clearable
        class="filter-select"
        @change="handleSearch"
      >
        <el-option label="管理员" value="管理员" />
        <el-option label="项目经理" value="项目经理" />
        <el-option label="销售" value="销售" />
        <el-option label="运维" value="运维" />
      </el-select>

      <el-button @click="handleSearch">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>

      <el-button @click="handleReset">
        <el-icon><Refresh /></el-icon>
        重置
      </el-button>
    </div>

    <!-- 用户表格 -->
    <div class="table-container">
      <el-table
        :data="userList"
        v-loading="loading"
        class="data-table"
      >
        <el-table-column prop="username" label="用户名" min-width="150" />

        <el-table-column prop="full_name" label="姓名" width="120">
          <template #default="{ row }">
            <span>{{ row.full_name || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="email" label="邮箱" width="200" />

        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">
              {{ row.role }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'warning'">
              {{ row.is_active ? '活跃' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="last_login_at" label="最后登录" width="180">
          <template #default="{ row }">
            <span>{{ row.last_login_at ? formatDate(row.last_login_at) : '从未登录' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="handleEdit(row)">
              编辑
            </el-button>
            <el-button
              link
              :type="row.is_active ? 'warning' : 'success'"
              @click.stop="handleToggleActive(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="danger" @click.stop="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      class="user-dialog"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userRules"
        label-width="120px"
        class="user-form"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="userForm.username" placeholder="请输入用户名" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名">
              <el-input v-model="userForm.full_name" placeholder="请输入姓名" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="userForm.email" placeholder="请输入邮箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" prop="role">
              <el-select v-model="userForm.role" placeholder="请选择角色">
                <el-option label="管理员" value="管理员" />
                <el-option label="项目经理" value="项目经理" />
                <el-option label="销售" value="销售" />
                <el-option label="运维" value="运维" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item :label="isEdit ? '新密码' : '密码'" :prop="isEdit ? '' : 'password'">
              <el-input
                v-model="userForm.password"
                type="password"
                :placeholder="isEdit ? '不填则保持原密码' : '请输入密码（至少8位）'"
                :show-password="true"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="确认密码">
              <el-input
                v-model="userForm.confirm_password"
                type="password"
                :placeholder="isEdit ? '' : '请确认密码'"
                :show-password="true"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser } from '@/api/user'
import type { User, CreateUserRequest, UpdateUserRequest } from '@/types/user'

// 数据列表
const userList = ref<User[]>([])
const loading = ref(false)

// 筛选条件
const filters = reactive({
  username: '',
  role: undefined as string | undefined,
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('创建用户')
const isEdit = ref(false)
const submitLoading = ref(false)
const userFormRef = ref()
const currentUserId = ref('')

// 用户表单
const userForm = reactive<CreateUserRequest & { confirm_password: string }>({
  username: '',
  password: '',
  confirm_password: '',
  email: '',
  full_name: '',
  role: '项目经理',
})

// 表单校验
const userRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在3-50个字符之间', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' },
  ],
}

// 获取角色标签类型
function getRoleTagType(role: string): string {
  const types: Record<string, string> = {
    '管理员': 'danger',
    '项目经理': 'primary',
    '销售': 'success',
    '运维': 'warning',
  }
  return types[role] || 'info'
}

// 格式化日期
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 加载用户列表
async function loadUsers() {
  loading.value = true
  try {
    const res = await getUsers({
      page: pagination.page,
      page_size: pagination.page_size,
      username: filters.username || undefined,
      role: filters.role,
    })
    userList.value = res.data.items
    pagination.total = res.data.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// 搜索
function handleSearch() {
  pagination.page = 1
  loadUsers()
}

// 重置
function handleReset() {
  filters.username = ''
  filters.role = undefined
  pagination.page = 1
  loadUsers()
}

// 创建用户
function handleCreate() {
  dialogTitle.value = '创建用户'
  isEdit.value = false
  currentUserId.value = ''
  resetForm()
  dialogVisible.value = true
}

// 编辑用户
function handleEdit(row: User) {
  dialogTitle.value = '编辑用户'
  isEdit.value = true
  currentUserId.value = row.id
  Object.assign(userForm, {
    username: row.username,
    full_name: row.full_name || '',
    email: row.email || '',
    role: row.role,
    password: '',
    confirm_password: '',
  })
  dialogVisible.value = true
}

// 切换用户状态
async function handleToggleActive(row: User) {
  try {
    const action = row.is_active ? '禁用' : '启用'
    await ElMessageBox.confirm(
      `确定要${action}用户「${row.username}」吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: row.is_active ? 'warning' : 'success',
      }
    )

    await updateUser(row.id, { is_active: !row.is_active })
    ElMessage.success(`${action}成功`)
    loadUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '操作失败')
    }
  }
}

// 删除用户
async function handleDelete(row: User) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${row.username}」吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await deleteUser(row.id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 提交表单
async function handleSubmit() {
  if (!userFormRef.value) return

  // 验证密码一致性
  if (userForm.password && userForm.password !== userForm.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }

  await userFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      submitLoading.value = true
      try {
        const submitData = isEdit.value
          ? ({
              email: userForm.email || undefined,
              full_name: userForm.full_name || undefined,
              role: userForm.role,
              password: userForm.password || undefined,
            } as UpdateUserRequest)
          : ({
              username: userForm.username,
              password: userForm.password,
              email: userForm.email || undefined,
              full_name: userForm.full_name || undefined,
              role: userForm.role,
            } as CreateUserRequest)

        if (isEdit.value) {
          await updateUser(currentUserId.value, submitData)
          ElMessage.success('更新成功')
        } else {
          await createUser(submitData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadUsers()
      } catch (error: any) {
        ElMessage.error(error.message || '操作失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 重置表单
function resetForm() {
  Object.assign(userForm, {
    username: '',
    password: '',
    confirm_password: '',
    email: '',
    full_name: '',
    role: '项目经理',
  })
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-list-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title-section {
  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 8px 0;
  }
  .page-subtitle {
    margin: 0;
    color: var(--text-muted);
    font-size: 14px;
  }
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.filter-input {
  width: 250px;
}

.filter-input-sm {
  width: 150px;
}

.filter-select {
  width: 150px;
}

.table-container {
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.data-table {
  width: 100%;
}

.pagination-container {
  padding: 16px;
  display: flex;
  justify-content: flex-end;
}

.user-dialog {
  .user-form {
    padding: 20px 0;
  }
}

.el-tag {
  font-size: 12px;
}
</style>
