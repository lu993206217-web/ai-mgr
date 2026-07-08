<template>
  <div class="project-list-container fade-in">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">📁 项目管理</h2>
        <p class="page-subtitle">管理所有海外项目，跟踪进度与风险</p>
      </div>
      <el-button type="primary" size="large" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        创建项目
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="filters.project_name"
        placeholder="搜索项目名称..."
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
        v-model="filters.current_stage"
        placeholder="项目阶段"
        clearable
        class="filter-select"
        @change="handleSearch"
      >
        <el-option label="售前" value="售前" />
        <el-option label="POC" value="POC" />
        <el-option label="投标" value="投标" />
        <el-option label="实施" value="实施" />
        <el-option label="验收" value="验收" />
        <el-option label="运维" value="运维" />
      </el-select>

      <el-select
        v-model="filters.health_status"
        placeholder="健康度"
        clearable
        class="filter-select"
        @change="handleSearch"
      >
        <el-option label="健康" value="健康" />
        <el-option label="关注" value="关注" />
        <el-option label="风险" value="风险" />
        <el-option label="严重风险" value="严重风险" />
      </el-select>

      <el-select
        v-model="filters.status"
        placeholder="项目状态"
        clearable
        class="filter-select"
        @change="handleSearch"
      >
        <el-option label="进行中" value="进行中" />
        <el-option label="已验收" value="已验收" />
        <el-option label="已终止" value="已终止" />
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

    <!-- 项目表格 -->
    <div class="table-container">
      <el-table
        :data="projectList"
        v-loading="loading"
        class="data-table"
        @row-click="handleRowClick"
      >
        <el-table-column prop="project_name" label="项目名称" min-width="200">
          <template #default="{ row }">
            <div class="project-name-cell">
              <span class="project-name">{{ row.project_name }}</span>
              <el-tag v-if="row.status === '已验收'" size="small" type="success">已验收</el-tag>
              <el-tag v-if="row.status === '已终止'" size="small" type="info">已终止</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="country" label="国家" width="120" />

        <el-table-column prop="current_stage" label="当前阶段" width="120">
          <template #default="{ row }">
            <el-tag :style="{ background: getStageColor(row.current_stage), color: 'white' }">
              {{ row.current_stage }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="health_status" label="健康度" width="120">
          <template #default="{ row }">
            <div class="health-indicator" :class="row.health_status">
              <div class="health-dot"></div>
              <span>{{ row.health_status }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="owner_name" label="负责人" width="120" />

        <el-table-column prop="project_amount" label="项目金额" width="150">
          <template #default="{ row }">
            <span class="amount">{{ formatCurrency(row.project_amount, row.currency) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="last_activity_at" label="最后活动" width="180">
          <template #default="{ row }">
            <span class="date-text">{{ formatDate(row.last_activity_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="handleEdit(row)">
              编辑
            </el-button>
            <el-button link type="primary" @click.stop="handleStageChange(row)">
              阶段流转
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
      width="800px"
      class="project-dialog"
    >
      <el-form
        ref="projectFormRef"
        :model="projectForm"
        :rules="projectRules"
        label-width="120px"
        class="project-form"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="项目名称" prop="project_name">
              <el-input v-model="projectForm.project_name" placeholder="请输入项目名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="国家" prop="country">
              <el-input v-model="projectForm.country" placeholder="请输入国家" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="客户" prop="customer_id">
              <el-select v-model="projectForm.customer_id" placeholder="请选择客户（可选）" filterable clearable>
                <el-option
                  v-for="c in customerOptions"
                  :key="c.id"
                  :label="c.customer_name"
                  :value="c.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="渠道">
              <el-select v-model="projectForm.channel_id" placeholder="请选择渠道" filterable clearable>
                <el-option
                  v-for="ch in channelOptions"
                  :key="ch.id"
                  :label="ch.channel_name"
                  :value="ch.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="负责人" prop="owner_id">
              <el-select v-model="projectForm.owner_id" placeholder="请选择负责人" filterable>
                <el-option
                  v-for="u in userOptions"
                  :key="u.id"
                  :label="u.full_name"
                  :value="u.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="项目来源" prop="source_type">
              <el-select v-model="projectForm.source_type" placeholder="请选择项目来源">
                <el-option label="渠道直转" value="渠道直转" />
                <el-option label="商机转项目" value="商机转项目" />
                <el-option label="POC转项目" value="POC转项目" />
                <el-option label="直接采购" value="直接采购" />
                <el-option label="招投标" value="招投标" />
                <el-option label="内部项目" value="内部" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="项目金额">
              <el-input-number
                v-model="projectForm.project_amount"
                :min="0"
                :precision="2"
                class="amount-input"
                placeholder="请输入金额"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="币种">
              <el-select v-model="projectForm.currency" placeholder="请选择币种">
                <el-option label="USD" value="USD" />
                <el-option label="EUR" value="EUR" />
                <el-option label="CNY" value="CNY" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="计划上线时间">
              <el-date-picker
                v-model="projectForm.planned_go_live"
                type="date"
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划验收时间">
              <el-date-picker
                v-model="projectForm.planned_acceptance"
                type="date"
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
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

    <!-- 阶段流转对话框 -->
    <el-dialog
      v-model="stageDialogVisible"
      title="阶段流转"
      width="500px"
    >
      <el-form label-width="120px">
        <el-form-item label="当前阶段">
          <el-tag>{{ currentProject?.current_stage }}</el-tag>
        </el-form-item>
        <el-form-item label="目标阶段" required>
          <el-select v-model="targetStage" placeholder="请选择目标阶段">
            <el-option label="售前" value="售前" />
            <el-option label="POC" value="POC" />
            <el-option label="投标" value="投标" />
            <el-option label="实施" value="实施" />
            <el-option label="验收" value="验收" />
            <el-option label="运维" value="运维" />
            <el-option label="归档" value="归档" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="stageDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleStageSubmit" :loading="stageLoading">
          确认流转
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getProjects, createProject, updateProject, deleteProject, changeStage } from '@/api/project'
import { getCustomers } from '@/api/customer'
import { getChannels } from '@/api/channel'
import { getUsers } from '@/api/user'
import type { Project, CreateProjectRequest } from '@/types/project'

const router = useRouter()

// 数据列表
const projectList = ref<Project[]>([])
const loading = ref(false)

// 筛选条件
const filters = reactive({
  project_name: '',
  current_stage: undefined as string | undefined,
  health_status: undefined as string | undefined,
  status: undefined as string | undefined,
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('创建项目')
const isEdit = ref(false)
const submitLoading = ref(false)
const projectFormRef = ref()

// 项目表单
const projectForm = reactive<CreateProjectRequest>({
  project_name: '',
  country: '',
  customer_id: '',
  channel_id: undefined,
  owner_id: undefined,  // 后端会默认使用当前用户，不发送空字符串
  source_type: '渠道直转',
  project_amount: undefined,
  currency: 'USD',
  planned_go_live: undefined,
  planned_acceptance: undefined,
})

// 表单校验
const projectRules = {
  project_name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
  ],
  country: [
    { required: true, message: '请输入国家', trigger: 'blur' },
  ],
  source_type: [
    { required: true, message: '请选择项目来源', trigger: 'change' },
  ],
}

// 阶段流转
const stageDialogVisible = ref(false)
const stageLoading = ref(false)
const currentProject = ref<Project | null>(null)
const targetStage = ref('')

// 选项数据
const customerOptions = ref<any[]>([])
const channelOptions = ref<any[]>([])
const userOptions = ref<any[]>([])

// 加载项目列表
async function loadProjects() {
  loading.value = true
  try {
    const res = await getProjects({
      page: pagination.page,
      page_size: pagination.page_size,
      project_name: filters.project_name || undefined,
      current_stage: filters.current_stage,
      health_status: filters.health_status,
      status: filters.status,
    })
    projectList.value = res.data.items
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
  loadProjects()
}

// 重置
function handleReset() {
  filters.project_name = ''
  filters.current_stage = undefined
  filters.health_status = undefined
  filters.status = undefined
  pagination.page = 1
  loadProjects()
}

// 加载选项数据（客户、渠道、用户）
async function loadOptions() {
  try {
    const [customerRes, channelRes, userRes] = await Promise.all([
      getCustomers({ page: 1, page_size: 1000 }),
      getChannels({ page: 1, page_size: 1000 }),
      getUsers({ page: 1, page_size: 1000 }),
    ])
    customerOptions.value = customerRes.data.items
    channelOptions.value = channelRes.data.items
    userOptions.value = userRes.data.items.filter(u => u.is_active).map(u => ({
      id: u.id,
      full_name: u.full_name || u.username,
    }))
  } catch (error) {
    console.error('加载选项失败', error)
  }
}

// 创建项目
function handleCreate() {
  dialogTitle.value = '创建项目'
  isEdit.value = false
  resetForm()
  loadOptions() // 打开对话框时加载选项
  dialogVisible.value = true
}

// 编辑项目
function handleEdit(row: Project) {
  dialogTitle.value = '编辑项目'
  isEdit.value = true
  currentProject.value = row
  Object.assign(projectForm, {
    project_name: row.project_name,
    country: row.country,
    customer_id: row.customer_id,
    channel_id: row.channel_id,
    owner_id: row.owner_id,
    source_type: row.source_type,
    project_amount: row.project_amount,
    currency: row.currency,
    planned_go_live: row.planned_go_live,
    planned_acceptance: row.planned_acceptance,
  })
  loadOptions() // 编辑时也加载选项
  dialogVisible.value = true
}

// 阶段流转
function handleStageChange(row: Project) {
  currentProject.value = row
  targetStage.value = ''
  stageDialogVisible.value = true
}

// 提交阶段流转
async function handleStageSubmit() {
  if (!targetStage.value) {
    ElMessage.warning('请选择目标阶段')
    return
  }
  
  stageLoading.value = true
  try {
    await changeStage(currentProject.value!.id, { target_stage: targetStage.value })
    ElMessage.success('阶段流转成功')
    stageDialogVisible.value = false
    loadProjects()
  } catch (error: any) {
    ElMessage.error(error.message || '流转失败')
  } finally {
    stageLoading.value = false
  }
}

// 删除项目
async function handleDelete(row: Project) {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目「${row.project_name}」吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await deleteProject(row.id)
    ElMessage.success('删除成功')
    loadProjects()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 提交表单
async function handleSubmit() {
  if (!projectFormRef.value) return
  
  await projectFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      submitLoading.value = true
      try {
        // 构建提交数据，过滤undefined和空字符串
        const submitData: CreateProjectRequest = {
          project_name: projectForm.project_name,
          country: projectForm.country,
          source_type: projectForm.source_type,
        }
        
        // 只添加有值的可选字段
        if (projectForm.customer_id) {
          submitData.customer_id = projectForm.customer_id
        }
        if (projectForm.channel_id) {
          submitData.channel_id = projectForm.channel_id
        }
        if (projectForm.owner_id) {
          submitData.owner_id = projectForm.owner_id
        }
        if (projectForm.project_amount !== undefined && projectForm.project_amount !== null) {
          submitData.project_amount = projectForm.project_amount
        }
        if (projectForm.currency) {
          submitData.currency = projectForm.currency
        }
        if (projectForm.planned_go_live) {
          submitData.planned_go_live = projectForm.planned_go_live
        }
        if (projectForm.planned_acceptance) {
          submitData.planned_acceptance = projectForm.planned_acceptance
        }

        if (isEdit.value) {
          await updateProject(currentProject.value!.id, submitData)
          ElMessage.success('更新成功')
        } else {
          await createProject(submitData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadProjects()
      } catch (error: any) {
        // 获取详细错误消息：兼容多种错误格式
        let errorMessage = '操作失败'
        if (error?.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error?.response?.data?.message) {
          errorMessage = error.response.data.message
        } else if (error?.message) {
          errorMessage = error.message
        }
        ElMessage.error(errorMessage)
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 重置表单
function resetForm() {
  Object.assign(projectForm, {
    project_name: '',
    country: '',
    customer_id: '',
    channel_id: undefined,
    owner_id: '',
    source_type: '渠道直转',
    project_amount: undefined,
    currency: 'USD',
    planned_go_live: undefined,
    planned_acceptance: undefined,
  })
}

// 点击行跳转详情
function handleRowClick(row: Project) {
  router.push(`/projects/${row.id}`)
}

// 获取阶段颜色
function getStageColor(stage: string) {
  const colors: Record<string, string> = {
    '售前': '#3b82f6',
    'POC': '#8b5cf6',
    '投标': '#f59e0b',
    '实施': '#10b981',
    '验收': '#ef4444',
    '运维': '#6366f1',
    '归档': '#6b7280',
  }
  return colors[stage] || '#6b7280'
}

// 格式化货币
function formatCurrency(amount: number | undefined, currency: string = 'USD') {
  if (!amount) return '-'
  return `${currency} ${amount.toLocaleString()}`
}

// 格式化日期
function formatDate(dateStr: string | undefined) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.project-list-container {
  max-width: 1600px;
  margin: 0 auto;
}

/* ============ 页面标题栏 ============ */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

/* ============ 筛选栏 ============ */

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-input {
  width: 280px;
}

.filter-select {
  width: 160px;
}

.filter-bar :deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

.filter-bar :deep(.el-input__inner) {
  color: var(--text-secondary);
}

/* ============ 表格容器 ============ */

.table-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px;
}

.data-table {
  width: 100%;
}

.data-table :deep(.el-table__header) {
  background: var(--bg-tertiary);
}

.data-table :deep(.el-table__header th) {
  background: var(--bg-tertiary) !important;
  color: var(--text-muted) !important;
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.data-table :deep(.el-table__row) {
  background: var(--bg-secondary) !important;
  cursor: pointer;
}

.data-table :deep(.el-table__row:hover) {
  background: var(--bg-tertiary) !important;
}

.data-table :deep(.el-table__row td) {
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
}

/* ============ 项目名称单元格 ============ */

.project-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-name {
  font-weight: 500;
  color: var(--text-secondary);
}

/* ============ 健康度指示器 ============ */

.health-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.health-indicator.健康 .health-dot {
  background: var(--success-color);
}

.health-indicator.关注 .health-dot {
  background: var(--warning-color);
}

.health-indicator.风险 .health-dot {
  background: var(--danger-color);
}

.health-indicator.严重风险 .health-dot {
  background: var(--danger-color);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ============ 金额样式 ============ */

.amount {
  font-weight: 600;
  color: var(--success-color);
}

/* ============ 日期文本 ============ */

.date-text {
  font-size: 13px;
  color: var(--text-muted);
}

/* ============ 分页容器 ============ */

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.pagination-container :deep(.el-pagination) {
  color: var(--text-muted);
}

.pagination-container :deep(.el-pagination button) {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.pagination-container :deep(.el-pager li) {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.pagination-container :deep(.el-pager li.is-active) {
  background: var(--accent-color);
  color: white;
}

/* ============ 对话框样式 ============ */

.project-dialog :deep(.el-dialog) {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

.project-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid var(--border-color);
}

.project-dialog :deep(.el-dialog__title) {
  color: var(--text-secondary);
}

.project-dialog :deep(.el-form-item__label) {
  color: var(--text-muted);
}

.project-form :deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

.project-form :deep(.el-input__inner) {
  color: var(--text-secondary);
}

.amount-input {
  width: 100%;
}
</style>
