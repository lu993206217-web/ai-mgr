<template>
  <div class="warning-center-container fade-in">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">⚠️ 预警中心</h2>
        <p class="page-subtitle">查看和处理项目风险预警</p>
      </div>
      <el-button type="primary" size="large" @click="handleTriggerCheck">
        <el-icon><Refresh /></el-icon>
        手动触发检查
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select
        v-model="filters.status"
        placeholder="处理状态"
        clearable
        class="filter-select"
        @change="handleSearch"
      >
        <el-option label="活跃" value="活跃" />
        <el-option label="已处理" value="已处理" />
      </el-select>

      <el-select
        v-model="filters.severity"
        placeholder="严重等级"
        clearable
        class="filter-select"
        @change="handleSearch"
      >
        <el-option label="严重" value="严重" />
        <el-option label="高" value="高" />
        <el-option label="中" value="中" />
        <el-option label="低" value="低" />
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

    <!-- 预警实例列表 -->
    <div class="table-container">
      <el-table
        :data="instanceList"
        v-loading="loading"
        class="data-table"
      >
        <el-table-column prop="severity" label="严重等级" width="120">
          <template #default="{ row }">
            <el-tag
              :type="getSeverityType(row.severity)"
              size="large"
            >
              {{ row.severity }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="rule_name" label="规则名称" min-width="150">
          <template #default="{ row }">
            <span class="rule-name">{{ row.rule_name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="message" label="预警信息" min-width="300">
          <template #default="{ row }">
            <span class="warning-message">{{ row.message }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="project_name" label="关联项目" width="200">
          <template #default="{ row }">
            <span class="project-name">{{ row.project_name || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag
              :type="row.status === '已处理' ? 'success' : 'danger'"
            >
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="date-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === '活跃'"
              link
              type="primary"
              @click="handleResolve(row)"
            >
              标记已处理
            </el-button>
            <el-button
              link
              type="primary"
              @click="handleViewProject(row)"
              v-if="row.project_id"
            >
              查看项目
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { getWarningInstances, resolveWarningInstance, triggerWarningCheck } from '@/api/warning'
import type { WarningInstance } from '@/types/warning'

const router = useRouter()

// 数据列表
const instanceList = ref<WarningInstance[]>([])
const loading = ref(false)

// 筛选条件
const filters = reactive({
  status: undefined as string | undefined,
  severity: undefined as string | undefined,
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 加载预警实例列表
async function loadInstances() {
  loading.value = true
  try {
    const res = await getWarningInstances({
      page: pagination.page,
      page_size: pagination.page_size,
      status: filters.status,
      severity: filters.severity,
    })
    instanceList.value = res.data.items
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
  loadInstances()
}

// 重置
function handleReset() {
  filters.status = undefined
  filters.severity = undefined
  pagination.page = 1
  loadInstances()
}

// 手动触发检查
async function handleTriggerCheck() {
  try {
    await triggerWarningCheck()
    ElMessage.success('预警检查已触发，请稍后刷新')
    setTimeout(() => {
      loadInstances()
    }, 3000)
  } catch (error: any) {
    ElMessage.error(error.message || '触发失败')
  }
}

// 标记已处理
async function handleResolve(row: WarningInstance) {
  try {
    await resolveWarningInstance(row.id)
    ElMessage.success('标记已处理成功')
    loadInstances()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

// 查看项目
function handleViewProject(row: WarningInstance) {
  if (row.project_id) {
    router.push(`/projects/${row.project_id}`)
  }
}

// 获取严重等级标签类型
function getSeverityType(severity: string) {
  const map: Record<string, string> = {
    '严重': 'danger',
    '高': 'warning',
    '中': 'warning',
    '低': 'success',
  }
  return map[severity] || 'info'
}

// 格式化日期时间
function formatDateTime(dateStr: string | undefined) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadInstances()
})
</script>

<style scoped>
.warning-center-container {
  max-width: 1600px;
  margin: 0 auto;
}

/* =========== 页面标题栏 =========== */

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
  color: var(--text-tertiary);
  margin: 0;
}

/* =========== 筛选栏 =========== */

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-select {
  width: 160px;
}

/* =========== 表格容器 =========== */

.table-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px;
}

.rule-name {
  font-weight: 500;
  color: var(--text-primary);
}

.warning-message {
  color: var(--text-secondary);
  line-height: 1.6;
}

.project-name {
  font-weight: 500;
  color: var(--text-primary);
}

.date-text {
  font-size: 13px;
  color: var(--text-tertiary);
}

/* =========== 分页容器 =========== */

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}
</style>
