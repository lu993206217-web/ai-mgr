<template>
  <div class="daily-report-container fade-in">
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">日报导入处理</h2>
        <p class="page-subtitle">先保存原始日志，再由 DeepSeek 分析项目归属和实际活动时间</p>
      </div>
      <el-button type="primary" size="large" :loading="syncLoading" @click="handleSync">
        <el-icon><Refresh /></el-icon>
        立即同步
      </el-button>
    </div>

    <div class="sync-panel">
      <el-form :inline="true" :model="syncForm">
        <el-form-item label="同步月份">
          <el-date-picker
            v-model="syncForm.month"
            type="month"
            format="YYYY-MM"
            value-format="YYYY-MM"
            placeholder="选择月份"
          />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="syncForm.date_range"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            range-separator="至"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="指定项目">
          <el-select
            v-model="syncForm.project_ids"
            multiple
            filterable
            remote
            reserve-keyword
            collapse-tags
            collapse-tags-tooltip
            placeholder="不选则同步全部已绑定项目"
            :remote-method="searchProjects"
            :loading="projectSearchLoading"
            class="project-sync-select"
          >
            <el-option
              v-for="project in projectOptions"
              :key="project.id"
              :label="project.project_name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="回看天数">
          <el-input-number v-model="syncForm.lookback_days" :min="1" :max="31" />
        </el-form-item>
        <el-form-item label="触发外部摄入">
          <el-switch v-model="syncForm.trigger_ingestion" />
        </el-form-item>
      </el-form>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <span class="summary-label">最近状态</span>
        <strong>{{ latestRun?.status || '-' }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">导入活动</span>
        <strong>{{ latestRun?.imported_activity_count ?? 0 }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">自动绑定</span>
        <strong>{{ latestRun?.auto_bound_count ?? 0 }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">未匹配</span>
        <strong>{{ latestRun?.unmatched_count ?? 0 }}</strong>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="content-tabs">
      <el-tab-pane label="原始日志与AI分析" name="raw">
        <div class="toolbar">
          <el-select v-model="rawFilters.analysis_status" placeholder="分析状态" clearable @change="loadRawEntries">
            <el-option label="待分析" value="待分析" />
            <el-option label="已导入" value="已导入" />
            <el-option label="已更新历史活动" value="已更新历史活动" />
            <el-option label="待人工匹配" value="待人工匹配" />
            <el-option label="分析失败" value="分析失败" />
            <el-option label="重复已跳过" value="重复已跳过" />
          </el-select>
          <el-button @click="loadRawEntries">
            <el-icon><Search /></el-icon>
            刷新
          </el-button>
        </div>
        <el-alert
          title="同步会先保存原始日志，再调用 DeepSeek 分析项目、摘要和实际活动时间；AI结果不会覆盖原文。"
          type="info"
          :closable="false"
          show-icon
          class="raw-tip"
        />
        <el-table :data="rawList" v-loading="rawLoading" class="data-table" row-key="id">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="raw-detail">
                <h4>原始日志</h4>
                <p>{{ row.original_summary || '（无摘要）' }}</p>
                <h4>DeepSeek 分析</h4>
                <p>{{ row.ai_summary || row.error_message || '等待分析' }}</p>
                <p v-if="row.ai_reason" class="muted">匹配依据：{{ row.ai_reason }}</p>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="source_date" label="拉取日期" width="110" />
          <el-table-column prop="external_project_name" label="外部项目" min-width="180" />
          <el-table-column prop="creator_name" label="提交人" width="120" />
          <el-table-column label="日志实际时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.source_occurred_at) }}</template>
          </el-table-column>
          <el-table-column prop="ai_project_name" label="AI匹配项目" min-width="170">
            <template #default="{ row }">{{ row.ai_project_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="置信度" width="100">
            <template #default="{ row }">{{ formatScore(row.ai_confidence) }}</template>
          </el-table-column>
          <el-table-column prop="ai_activity_type" label="活动类型" width="120" />
          <el-table-column label="写入活动时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.ai_occurred_at) }}</template>
          </el-table-column>
          <el-table-column prop="analysis_status" label="状态" width="120">
            <template #default="{ row }"><el-tag>{{ row.analysis_status }}</el-tag></template>
          </el-table-column>
        </el-table>
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="rawPagination.page"
            :page-size="rawPagination.page_size"
            :total="rawPagination.total"
            layout="total, prev, pager, next"
            @current-change="loadRawEntries"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="未匹配处理" name="unmatched">
        <el-alert
          title="默认只处理置信度达到 80% 的推荐；低于 80% 的数据单独隔离，不参与日常匹配判断。"
          type="warning"
          :closable="false"
          show-icon
          class="raw-tip"
        />
        <div class="toolbar">
          <el-date-picker
            v-model="unmatchedFilters.month"
            type="month"
            format="YYYY-MM"
            value-format="YYYY-MM"
            placeholder="月份"
            @change="loadUnmatched"
          />
          <el-select v-model="unmatchedFilters.status" placeholder="状态" clearable @change="loadUnmatched">
            <el-option label="待处理" value="待处理" />
            <el-option label="已绑定" value="已绑定" />
            <el-option label="已忽略" value="已忽略" />
          </el-select>
          <el-input
            v-if="unmatchedConfidenceTab === 'low'"
            v-model="unmatchedFilters.keyword"
            clearable
            class="unmatched-search"
            placeholder="搜索项目、提交人、日志内容或AI原因"
            @keyup.enter="handleUnmatchedSearch"
            @clear="handleUnmatchedSearch"
          />
          <el-button @click="loadUnmatched">
            <el-icon><Search /></el-icon>
            刷新
          </el-button>
        </div>

        <el-tabs v-model="unmatchedConfidenceTab" class="confidence-tabs" @tab-change="handleConfidenceTabChange">
          <el-tab-pane label="优先匹配（≥80%）" name="high" />
          <el-tab-pane label="低可信数据（<80%）" name="low" />
        </el-tabs>

        <el-table :data="unmatchedList" v-loading="unmatchedLoading" class="data-table">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="raw-detail unmatched-evidence">
                <h4>数据源样本</h4>
                <p>
                  {{ row.sample_source_date || '-' }} · {{ row.sample_creator_name || '未知提交人' }}
                </p>
                <p>{{ row.sample_original_summary || '没有可展示的原始日志内容' }}</p>
                <p v-if="row.source_project_names?.length > 1" class="source-warning">
                  同一 project_key 下的项目名称：{{ row.source_project_names.join('、') }}
                </p>
                <h4>AI未匹配原因</h4>
                <p>{{ row.sample_ai_reason || 'AI没有返回明确原因' }}</p>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="external_project_name" label="外部项目" min-width="220" />
          <el-table-column prop="project_key" label="project_key" min-width="210" show-overflow-tooltip />
          <el-table-column prop="month" label="月份" width="100" />
          <el-table-column label="条目" width="160">
            <template #default="{ row }">
              售前 {{ row.pre_sales_entry_count }} / 实施 {{ row.implementation_entry_count }} / 服务 {{ row.service_entry_count }}
            </template>
          </el-table-column>
          <el-table-column prop="last_active_date" label="最近活跃" width="120" />
          <el-table-column label="推荐项目" min-width="220">
            <template #default="{ row }">
              <div>{{ row.suggested_project_name || '-' }}</div>
              <span class="muted">匹配分 {{ formatScore(row.suggested_score) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="排查结论" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag :type="row.source_project_names?.length > 1 ? 'danger' : 'warning'" effect="plain">
                {{ row.diagnosis_hint || '展开查看数据源样本' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" :disabled="row.status !== '待处理'" @click="openBindDialog(row)">
                绑定
              </el-button>
              <el-button link type="success" :disabled="!row.suggested_project_id || row.status !== '待处理'" @click="bindSuggested(row)">
                采纳推荐
              </el-button>
              <el-button link type="danger" :disabled="row.status !== '待处理'" @click="ignoreItem(row.id)">
                忽略
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="unmatchedPagination.page"
            v-model:page-size="unmatchedPagination.page_size"
            :total="unmatchedPagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadUnmatched"
            @current-change="loadUnmatched"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="项目日报别名" name="bindings">
        <el-alert
          title="一个本地项目可以对应多个日报名称、简称和 project_key；每次人工确认都会沉淀为后续识别使用的项目别名。"
          type="success"
          :closable="false"
          show-icon
          class="raw-tip"
        />
        <el-table :data="bindingList" v-loading="bindingsLoading" class="data-table">
          <el-table-column prop="project_name" label="本地项目" min-width="220" />
          <el-table-column prop="external_project_name" label="日报名称/别名" min-width="220" />
          <el-table-column prop="project_key" label="日报入口 project_key" min-width="210" show-overflow-tooltip />
          <el-table-column prop="match_method" label="方式" width="100" />
          <el-table-column label="匹配分" width="100">
            <template #default="{ row }">{{ formatScore(row.match_score) }}</template>
          </el-table-column>
          <el-table-column prop="last_sync_month" label="最近月份" width="110" />
          <el-table-column label="最近同步" width="180">
            <template #default="{ row }">{{ formatDateTime(row.last_sync_at) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="同步记录" name="runs">
        <el-table :data="runList" v-loading="runsLoading" class="data-table">
          <el-table-column prop="month" label="月份" width="100" />
          <el-table-column prop="trigger_type" label="触发" width="100" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === '成功' ? 'success' : row.status === '失败' ? 'danger' : 'warning'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="options_count" label="外部项目" width="100" />
          <el-table-column prop="auto_bound_count" label="自动绑定" width="100" />
          <el-table-column prop="unmatched_count" label="未匹配" width="100" />
          <el-table-column prop="imported_activity_count" label="导入活动" width="100" />
          <el-table-column prop="skipped_duplicate_count" label="重复跳过" width="100" />
          <el-table-column label="开始时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误" min-width="220" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="bindDialogVisible" title="绑定日报项目" width="560px">
      <el-form label-width="100px">
        <el-form-item label="外部项目">
          <span>{{ currentUnmatched?.external_project_name }}</span>
        </el-form-item>
        <el-form-item label="本地项目">
          <el-select
            v-model="bindForm.project_id"
            filterable
            remote
            reserve-keyword
            placeholder="搜索项目名称"
            :remote-method="searchProjects"
            :loading="projectSearchLoading"
          >
            <el-option
              v-for="project in projectOptions"
              :key="project.id"
              :label="project.project_name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定后同步">
          <el-switch v-model="bindForm.sync_after_bind" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="bindLoading" @click="submitBind">确定绑定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import {
  bindDailyReportUnmatched,
  getDailyReportBindings,
  getDailyReportRuns,
  getDailyReportRawEntries,
  getDailyReportUnmatched,
  ignoreDailyReportUnmatched,
  syncDailyReports,
} from '@/api/dailyReport'
import { getProjects } from '@/api/project'
import type { DailyReportBinding, DailyReportRawEntry, DailyReportSyncRun, DailyReportUnmatchedProject } from '@/types/dailyReport'
import type { Project } from '@/types/project'

const currentMonth = new Date().toISOString().slice(0, 7)

const syncLoading = ref(false)
const syncForm = ref({
  month: currentMonth,
  date_range: [] as string[],
  project_ids: [] as string[],
  lookback_days: 3,
  trigger_ingestion: true,
})

const activeTab = ref('raw')
const runList = ref<DailyReportSyncRun[]>([])
const runsLoading = ref(false)
const unmatchedList = ref<DailyReportUnmatchedProject[]>([])
const unmatchedLoading = ref(false)
const unmatchedConfidenceTab = ref<'high' | 'low'>('high')
const bindingList = ref<DailyReportBinding[]>([])
const bindingsLoading = ref(false)
const rawList = ref<DailyReportRawEntry[]>([])
const rawLoading = ref(false)
const rawFilters = ref({ analysis_status: '' })
const rawPagination = ref({ page: 1, page_size: 20, total: 0 })

const unmatchedFilters = ref({
  month: currentMonth,
  status: '待处理',
  keyword: '',
})

const unmatchedPagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
})

const bindDialogVisible = ref(false)
const bindLoading = ref(false)
const currentUnmatched = ref<DailyReportUnmatchedProject | null>(null)
const bindForm = ref({
  project_id: '',
  sync_after_bind: true,
})
const projectOptions = ref<Project[]>([])
const projectSearchLoading = ref(false)

const latestRun = computed(() => runList.value[0])
let runPollingTimer: number | undefined

async function handleSync() {
  syncLoading.value = true
  try {
    const [startDate, endDate] = syncForm.value.date_range || []
    const res = await syncDailyReports({
      month: syncForm.value.month,
      start_date: startDate,
      end_date: endDate,
      project_ids: syncForm.value.project_ids.length ? syncForm.value.project_ids : undefined,
      lookback_days: syncForm.value.lookback_days,
      trigger_ingestion: syncForm.value.trigger_ingestion,
    })
    if (res.data.status === '运行中') {
      ElMessage.success('同步任务已提交，后端正在执行，可在同步记录查看进度')
      activeTab.value = 'runs'
    } else if (res.data.status === '成功') {
      ElMessage.success(`同步完成，导入 ${res.data.imported_activity_count} 条活动`)
    } else {
      ElMessage.error(res.data.error_message || '同步失败')
    }
    await loadRuns()
    startRunPolling()
  } catch (error) {
    const message = getRequestErrorMessage(error)
    ElMessage.error(message || '同步失败，请检查外部日报接口')
    console.error(error)
  } finally {
    syncLoading.value = false
  }
}

function hasRunningRun() {
  return runList.value.some((run) => run.status === '运行中')
}

function startRunPolling() {
  if (runPollingTimer !== undefined) return
  runPollingTimer = window.setInterval(async () => {
    await loadRuns()
    if (!hasRunningRun()) {
      stopRunPolling()
      await Promise.all([loadRawEntries(), loadUnmatched(), loadBindings()])
    }
  }, 5000)
}

function stopRunPolling() {
  if (runPollingTimer === undefined) return
  window.clearInterval(runPollingTimer)
  runPollingTimer = undefined
}

function getRequestErrorMessage(error: unknown) {
  if (!error || typeof error !== 'object') return ''
  const err = error as {
    code?: string
    message?: string
    response?: {
      data?: {
        message?: string
        detail?: string
        data?: {
          error_message?: string
        }
      }
    }
  }
  if (err.response?.data?.data?.error_message) return err.response.data.data.error_message
  if (err.response?.data?.message) return err.response.data.message
  if (err.response?.data?.detail) return err.response.data.detail
  if (err.code === 'ECONNABORTED') return '同步仍在执行但等待时间过长，请稍后刷新同步记录查看结果'
  return err.message || ''
}

async function loadRuns() {
  runsLoading.value = true
  try {
    const res = await getDailyReportRuns({ page: 1, page_size: 20 })
    runList.value = res.data.items
  } finally {
    runsLoading.value = false
  }
}

async function loadUnmatched() {
  unmatchedLoading.value = true
  try {
    const res = await getDailyReportUnmatched({
      month: unmatchedFilters.value.month,
      status: unmatchedFilters.value.status || undefined,
      confidence_level: unmatchedConfidenceTab.value,
      keyword: unmatchedConfidenceTab.value === 'low' ? unmatchedFilters.value.keyword.trim() || undefined : undefined,
      page: unmatchedPagination.value.page,
      page_size: unmatchedPagination.value.page_size,
    })
    unmatchedList.value = res.data.items
    unmatchedPagination.value.total = res.data.total
  } finally {
    unmatchedLoading.value = false
  }
}

function handleConfidenceTabChange() {
  unmatchedPagination.value.page = 1
  loadUnmatched()
}

function handleUnmatchedSearch() {
  unmatchedPagination.value.page = 1
  loadUnmatched()
}

async function loadBindings() {
  bindingsLoading.value = true
  try {
    const res = await getDailyReportBindings({ page: 1, page_size: 100 })
    bindingList.value = res.data.items
  } finally {
    bindingsLoading.value = false
  }
}

async function loadRawEntries() {
  rawLoading.value = true
  try {
    const res = await getDailyReportRawEntries({
      analysis_status: rawFilters.value.analysis_status || undefined,
      page: rawPagination.value.page,
      page_size: rawPagination.value.page_size,
    })
    rawList.value = res.data.items
    rawPagination.value.total = res.data.total
  } finally {
    rawLoading.value = false
  }
}

async function searchProjects(keyword: string) {
  projectSearchLoading.value = true
  try {
    const res = await getProjects({
      page: 1,
      page_size: 50,
      project_name: keyword,
    })
    projectOptions.value = res.data.items
  } finally {
    projectSearchLoading.value = false
  }
}

function openBindDialog(row: DailyReportUnmatchedProject) {
  currentUnmatched.value = row
  bindForm.value = {
    project_id: row.suggested_project_id || '',
    sync_after_bind: true,
  }
  projectOptions.value = []
  if (row.suggested_project_id && row.suggested_project_name) {
    projectOptions.value = [{ id: row.suggested_project_id, project_name: row.suggested_project_name } as Project]
  }
  bindDialogVisible.value = true
}

async function submitBind() {
  if (!currentUnmatched.value || !bindForm.value.project_id) {
    ElMessage.warning('请选择要绑定的本地项目')
    return
  }
  bindLoading.value = true
  try {
    const res = await bindDailyReportUnmatched(currentUnmatched.value.id, bindForm.value)
    const imported = res.data.imported_activity_count || 0
    ElMessage.success(bindForm.value.sync_after_bind ? `绑定成功，已导入 ${imported} 条活动` : '绑定成功')
    bindDialogVisible.value = false
    await Promise.all([loadUnmatched(), loadBindings(), loadRuns()])
  } finally {
    bindLoading.value = false
  }
}

async function bindSuggested(row: DailyReportUnmatchedProject) {
  if (!row.suggested_project_id) return
  const res = await bindDailyReportUnmatched(row.id, {
    project_id: row.suggested_project_id,
    sync_after_bind: true,
  })
  ElMessage.success(`已采纳推荐并绑定，导入 ${res.data.imported_activity_count || 0} 条活动`)
  await Promise.all([loadUnmatched(), loadBindings()])
}

async function ignoreItem(id: string) {
  try {
    await ElMessageBox.confirm('确认忽略这个外部日报项目吗？', '忽略确认', {
      type: 'warning',
      confirmButtonText: '忽略',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await ignoreDailyReportUnmatched(id)
  ElMessage.success('已忽略')
  loadUnmatched()
}

function formatScore(score?: number) {
  if (score === undefined || score === null) return '-'
  return `${Math.round(Number(score) * 100)}%`
}

function formatDateTime(value?: string) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

function getStatusType(status: string) {
  const map: Record<string, any> = {
    '待处理': 'warning',
    '已绑定': 'success',
    '已忽略': 'info',
  }
  return map[status] || 'info'
}

watch(activeTab, (tab) => {
  if (tab === 'raw') loadRawEntries()
  if (tab === 'unmatched') loadUnmatched()
  if (tab === 'bindings') loadBindings()
  if (tab === 'runs') loadRuns()
})

onMounted(async () => {
  await loadRuns()
  if (hasRunningRun()) startRunPolling()
  loadUnmatched()
  loadBindings()
  loadRawEntries()
})

onUnmounted(() => {
  stopRunPolling()
})
</script>

<style scoped>
.daily-report-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.sync-panel,
.content-tabs {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.summary-card {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-label,
.muted {
  color: var(--text-muted);
  font-size: 12px;
}

.summary-card strong {
  color: var(--text-primary);
  font-size: 24px;
}

.raw-tip { margin-bottom: 16px; }
.confidence-tabs { margin-bottom: 12px; }
.raw-detail { padding: 8px 28px 18px; max-width: 980px; }
.raw-detail h4 { margin: 12px 0 6px; }
.raw-detail p { margin: 0; line-height: 1.7; white-space: pre-wrap; }

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.project-sync-select {
  width: 280px;
}

.unmatched-search {
  width: 340px;
}

.unmatched-evidence p + p {
  margin-top: 8px;
}

.source-warning {
  color: var(--el-color-danger);
  font-weight: 600;
}

.data-table {
  width: 100%;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }
}
</style>
