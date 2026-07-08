<template>
  <div class="channel-list-container fade-in">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">🤝 渠道管理</h2>
        <p class="page-subtitle">管理海外渠道商信息，跟踪合作历史</p>
      </div>
      <el-button type="primary" size="large" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        创建渠道
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="filters.channel_name"
        placeholder="搜索渠道名称..."
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
        v-model="filters.cooperation_status"
        placeholder="合作状态"
        clearable
        class="filter-select"
        @change="handleSearch"
      >
        <el-option label="活跃" value="活跃" />
        <el-option label="暂停" value="暂停" />
        <el-option label="终止" value="终止" />
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

    <!-- 渠道表格 -->
    <div class="table-container">
      <el-table
        :data="channelList"
        v-loading="loading"
        class="data-table"
        @row-click="handleRowClick"
      >
        <el-table-column prop="channel_name" label="渠道名称" min-width="180">
          <template #default="{ row }">
            <span class="channel-name">{{ row.channel_name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="country" label="国家" width="120" />

        <el-table-column prop="region" label="区域" width="120" />

        <el-table-column prop="contact_person" label="联系人" width="120" />

        <el-table-column prop="cooperation_status" label="合作状态" width="120">
          <template #default="{ row }">
            <el-tag
              :type="row.cooperation_status === '活跃' ? 'success' : row.cooperation_status === '暂停' ? 'warning' : 'info'"
            >
              {{ row.cooperation_status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="total_projects" label="项目数" width="100" align="center">
          <template #default="{ row }">
            <span class="stat-value">{{ row.total_projects }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="total_amount" label="成交金额" width="150">
          <template #default="{ row }">
            <span class="amount">{{ formatCurrency(row.total_amount) }}</span>
          </template>
        </el-table-column>



        <el-table-column prop="last_contact_date" label="最近联系" width="180">
          <template #default="{ row }">
            <span class="date-text">{{ formatDate(row.last_contact_date) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="handleEdit(row)">
              编辑
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
      class="channel-dialog"
    >
      <el-form
        ref="channelFormRef"
        :model="channelForm"
        :rules="channelRules"
        label-width="120px"
        class="channel-form"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="渠道名称" prop="channel_name">
              <el-input v-model="channelForm.channel_name" placeholder="请输入渠道名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="国家" prop="country">
              <el-input v-model="channelForm.country" placeholder="请输入国家" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="区域">
              <el-input v-model="channelForm.region" placeholder="请输入区域" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合作等级">
              <el-select v-model="channelForm.cooperation_level" placeholder="请选择合作等级">
                <el-option label="A级" value="A" />
                <el-option label="B级" value="B" />
                <el-option label="C级" value="C" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="channelForm.contact_person" placeholder="请输入联系人" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="channelForm.contact_phone" placeholder="请输入联系电话" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="联系邮箱">
              <el-input v-model="channelForm.contact_email" placeholder="请输入联系邮箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合作状态">
              <el-select v-model="channelForm.cooperation_status" placeholder="请选择合作状态">
                <el-option label="活跃" value="活跃" />
                <el-option label="暂停" value="暂停" />
                <el-option label="终止" value="终止" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="合作开始时间">
              <el-date-picker
                v-model="channelForm.cooperation_start_date"
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getChannels, createChannel, updateChannel, deleteChannel } from '@/api/channel'
import type { Channel, CreateChannelRequest } from '@/types/channel'

const router = useRouter()

// 数据列表
const channelList = ref<Channel[]>([])
const loading = ref(false)

// 筛选条件
const filters = reactive({
  channel_name: '',
  cooperation_status: undefined as string | undefined,
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('创建渠道')
const isEdit = ref(false)
const submitLoading = ref(false)
const channelFormRef = ref()
const currentChannelId = ref('')

// 渠道表单
const channelForm = reactive<CreateChannelRequest>({
  channel_name: '',
  country: '',
  region: undefined,
  contact_person: undefined,
  contact_phone: undefined,
  contact_email: undefined,
  cooperation_level: 'B',
  cooperation_status: '活跃',
  cooperation_start_date: undefined,
})

// 表单校验
const channelRules = {
  channel_name: [
    { required: true, message: '请输入渠道名称', trigger: 'blur' },
  ],
  country: [
    { required: true, message: '请输入国家', trigger: 'blur' },
  ],
}

// 加载渠道列表
async function loadChannels() {
  loading.value = true
  try {
    const res = await getChannels({
      page: pagination.page,
      page_size: pagination.page_size,
      channel_name: filters.channel_name || undefined,
      cooperation_status: filters.cooperation_status,
    })
    channelList.value = res.data.items
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
  loadChannels()
}

// 重置
function handleReset() {
  filters.channel_name = ''
  filters.cooperation_status = undefined
  pagination.page = 1
  loadChannels()
}

// 创建渠道
function handleCreate() {
  dialogTitle.value = '创建渠道'
  isEdit.value = false
  currentChannelId.value = ''
  resetForm()
  dialogVisible.value = true
}

// 编辑渠道
function handleEdit(row: Channel) {
  dialogTitle.value = '编辑渠道'
  isEdit.value = true
  currentChannelId.value = row.id
  Object.assign(channelForm, {
    channel_name: row.channel_name,
    country: row.country,
    region: row.region || undefined,
    contact_person: row.contact_person || undefined,
    contact_phone: row.contact_phone || undefined,
    contact_email: row.contact_email || undefined,
    cooperation_level: row.cooperation_level || 'B',
    cooperation_status: row.cooperation_status,
    cooperation_start_date: row.cooperation_start_date || undefined,
  })
  dialogVisible.value = true
}

// 删除渠道
async function handleDelete(row: Channel) {
  try {
    await ElMessageBox.confirm(
      `确定要删除渠道「${row.channel_name}」吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await deleteChannel(row.id)
    ElMessage.success('删除成功')
    loadChannels()
  } catch (error: any) {
    if (error !== 'cancel') {
      // 获取详细错误消息：可能在 error.response.data.detail 或 error.message
      const errorMessage = error?.response?.data?.detail || error?.message || '删除失败'
      ElMessage.error(errorMessage)
    }
  }
}

// 提交表单
async function handleSubmit() {
  if (!channelFormRef.value) return
  
  await channelFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      submitLoading.value = true
      try {
        // 过滤空字符串，避免后端验证失败
        const submitData = Object.fromEntries(
          Object.entries(channelForm).map(([key, value]) => [
            key,
            value === '' ? undefined : value
          ])
        )
        
        if (isEdit.value) {
          await updateChannel(currentChannelId.value, submitData)
          ElMessage.success('更新成功')
        } else {
          await createChannel(submitData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadChannels()
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
  Object.assign(channelForm, {
    channel_name: '',
    country: '',
    region: undefined,
    contact_person: undefined,
    contact_phone: undefined,
    contact_email: undefined,
    cooperation_level: 'B',
    cooperation_status: '活跃',
    cooperation_start_date: undefined,
  })
}

// 点击行跳转详情
function handleRowClick(row: Channel) {
  router.push(`/channels/${row.id}`)
}

// 格式化货币
function formatCurrency(amount: number | undefined) {
  if (!amount) return '-'
  return `USD ${amount.toLocaleString()}`
}

// 格式化日期
function formatDate(dateStr: string | undefined) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadChannels()
})
</script>

<style scoped>
.channel-list-container {
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

/* ============ 表格容器 ============ */

.table-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px;
}

.channel-name {
  font-weight: 500;
  color: var(--text-secondary);
}

.stat-value {
  font-weight: 600;
  color: var(--text-secondary);
}

.amount {
  font-weight: 600;
  color: var(--success-color);
}

.rate {
  font-weight: 600;
  color: var(--accent-color);
}

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

/* ============ 对话框样式 ============ */

.channel-dialog :deep(.el-dialog) {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

.channel-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid var(--border-color);
}

.channel-dialog :deep(.el-dialog__title) {
  color: var(--text-secondary);
}

.channel-form :deep(.el-form-item__label) {
  color: var(--text-muted);
}
</style>
