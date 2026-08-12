<template>
  <div class="workflow-page fade-in">
    <div class="page-header">
      <div>
        <h2 class="page-title">🔄 流程中心</h2>
        <p class="page-subtitle">邮件和日报形成证据，AI持续推进事项，人工只处理不确定和关键节点</p>
      </div>
      <div class="header-actions">
        <el-button @click="refreshAll"><el-icon><Refresh /></el-icon>刷新</el-button>
        <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新建事项</el-button>
      </div>
    </div>

    <div class="summary-grid">
      <div v-for="card in summaryCards" :key="card.key" class="summary-card" :class="card.tone">
        <span class="summary-label">{{ card.label }}</span>
        <strong class="summary-value">{{ card.value }}</strong>
        <span class="summary-hint">{{ card.hint }}</span>
      </div>
    </div>

    <section class="automation-panel">
      <div class="section-heading">
        <div>
          <h3>🤖 自动推进任务</h3>
          <p>定时采集 → AI分析与匹配 → 生成推进证据 → 更新事项 → 重算告警</p>
        </div>
        <el-button @click="openRunHistory">运行记录</el-button>
      </div>
      <div class="automation-grid" v-loading="automationLoading">
        <article v-for="task in automationTasks" :key="task.id" class="automation-card">
          <div class="automation-title">
            <div><strong>{{ task.task_name }}</strong><el-tag :type="task.source_ready ? 'success' : 'warning'" effect="plain">{{ task.source_ready ? '数据源就绪' : '待配置' }}</el-tag></div>
            <el-switch v-model="task.enabled" inline-prompt active-text="开" inactive-text="关" @change="toggleTask(task)" />
          </div>
          <p>{{ task.description }}</p>
          <div class="automation-meta"><span>执行周期</span><b>{{ formatSchedule(task) }}</b></div>
          <div class="automation-meta"><span>下次执行</span><b>{{ task.enabled ? formatDateTime(task.next_run_at) : '已停用' }}</b></div>
          <div class="automation-result">
            <el-tag :type="jobStatusType(task.last_status)" size="small">{{ task.last_status || '尚未执行' }}</el-tag>
            <span>{{ task.last_result || task.source_message || '等待首次执行' }}</span>
          </div>
          <div v-if="task.last_error" class="automation-error">{{ task.last_error }}</div>
          <div class="automation-actions">
            <el-button size="small" @click="openTaskConfig(task)">配置</el-button>
            <el-button size="small" type="primary" plain :loading="runningTaskId === task.id" :disabled="!task.source_ready && task.task_code !== 'warning_evaluation'" @click="runTask(task)">立即执行</el-button>
          </div>
        </article>
      </div>
    </section>

    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索事项内容" clearable class="keyword" @keyup.enter="search">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filters.status" placeholder="事项状态" clearable @change="search">
        <el-option v-for="item in statuses" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.responsibility_party" placeholder="当前责任方" clearable @change="search">
        <el-option label="我方" value="我方" />
        <el-option label="客户" value="客户" />
        <el-option label="渠道" value="渠道" />
        <el-option label="第三方" value="第三方" />
      </el-select>
      <el-checkbox v-model="filters.mine" @change="search">只看我的</el-checkbox>
      <el-button type="primary" plain @click="search">查询</el-button>
    </div>

    <div class="table-shell">
      <el-table :data="items" v-loading="loading" @row-click="openDetail" class="workflow-table">
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="优先级" width="90">
          <template #default="{ row }"><el-tag :type="row.priority === '高' ? 'danger' : 'info'" effect="plain">{{ row.priority }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" min-width="170" />
        <el-table-column label="事项" min-width="320">
          <template #default="{ row }">
            <div class="item-title">{{ row.title }}</div>
            <div class="item-meta">{{ row.source_type }} · {{ row.evidence_count }}条证据</div>
          </template>
        </el-table-column>
        <el-table-column prop="responsibility_party" label="责任方" width="100" />
        <el-table-column prop="owner_name" label="负责人" width="110" />
        <el-table-column label="截止日期" width="125">
          <template #default="{ row }"><span :class="{ overdue: isOverdue(row) }">{{ row.due_date || '-' }}</span></template>
        </el-table-column>
        <el-table-column label="最后推进" width="165">
          <template #default="{ row }">{{ formatDateTime(row.last_progress_at) }}</template>
        </el-table-column>
        <el-table-column label="告警" width="90">
          <template #default="{ row }"><el-tag v-if="row.alert_level" :type="alertType(row.alert_level)">{{ row.alert_level }}</el-tag><span v-else>-</span></template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }"><el-button link type="primary" @click.stop="openDetail(row)">办理</el-button></template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.page_size" :total="pagination.total" layout="total, sizes, prev, pager, next" @current-change="loadItems" @size-change="loadItems" />
      </div>
    </div>

    <el-drawer v-model="detailVisible" title="事项办理" size="660px">
      <div v-if="selected" class="detail-content">
        <div class="detail-heading">
          <div><el-tag :type="statusType(selected.status)">{{ selected.status }}</el-tag><el-tag type="info" effect="plain">{{ selected.responsibility_party }}</el-tag></div>
          <h3>{{ selected.title }}</h3>
          <p>{{ selected.project_name }} · 负责人：{{ selected.owner_name || '未分配' }}</p>
        </div>

        <div class="action-bar">
          <el-button v-if="selected.status === '待接收' || selected.status === 'AI待确认'" type="primary" @click="changeStatus('处理中')">接收并处理</el-button>
          <el-button v-if="!closed(selected.status)" @click="changeStatus('等待外部')">等待外部</el-button>
          <el-button v-if="selected.status === '疑似完成' || selected.status === '处理中' || selected.status === '等待外部'" type="success" @click="changeStatus('已完成')">确认完成</el-button>
          <el-button v-if="closed(selected.status)" @click="changeStatus('处理中')">重新打开</el-button>
          <el-select v-model="assignOwnerId" placeholder="转交负责人" filterable class="owner-select" @change="assignOwner">
            <el-option v-for="user in users" :key="user.id" :label="user.full_name || user.username" :value="user.id" />
          </el-select>
        </div>

        <section class="detail-section">
          <h4>事项说明</h4>
          <p class="preserve">{{ selected.description || '暂无说明' }}</p>
          <div v-if="selected.ai_reason" class="ai-note">AI判断：{{ selected.ai_reason }}<span v-if="selected.ai_confidence">（{{ Math.round(selected.ai_confidence * 100) }}%）</span></div>
        </section>

        <section class="detail-section">
          <h4>推进证据</h4>
          <el-timeline v-if="selected.evidences?.length">
            <el-timeline-item v-for="evidence in selected.evidences" :key="evidence.id" :timestamp="formatDateTime(evidence.evidence_at)" placement="top">
              <div class="timeline-card"><b>{{ evidence.source_type }} · {{ evidence.decision }}</b><p class="preserve">{{ evidence.summary }}</p><small v-if="evidence.reason">{{ evidence.reason }}</small></div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无推进证据" :image-size="60" />
        </section>

        <section class="detail-section">
          <h4>状态历史</h4>
          <div v-for="event in selected.state_events" :key="event.id" class="state-event">
            <span>{{ event.from_status || '创建' }} → {{ event.to_status }}</span>
            <span>{{ formatDateTime(event.occurred_at) }}</span>
            <small>{{ event.reason }}</small>
          </div>
        </section>
      </div>
    </el-drawer>

    <el-dialog v-model="createVisible" title="新建流程事项" width="560px">
      <el-form label-position="top">
        <el-form-item label="项目"><el-select v-model="createForm.project_id" filterable style="width:100%"><el-option v-for="project in projects" :key="project.id" :label="project.project_name" :value="project.id" /></el-select></el-form-item>
        <el-form-item label="事项标题"><el-input v-model="createForm.title" maxlength="300" /></el-form-item>
        <el-form-item label="事项说明"><el-input v-model="createForm.description" type="textarea" :rows="4" /></el-form-item>
        <div class="form-row">
          <el-form-item label="责任方"><el-select v-model="createForm.responsibility_party"><el-option label="我方" value="我方" /><el-option label="客户" value="客户" /><el-option label="渠道" value="渠道" /><el-option label="第三方" value="第三方" /></el-select></el-form-item>
          <el-form-item label="优先级"><el-select v-model="createForm.priority"><el-option label="普通" value="普通" /><el-option label="高" value="高" /></el-select></el-form-item>
          <el-form-item label="截止日期"><el-date-picker v-model="createForm.due_date" type="date" value-format="YYYY-MM-DD" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="createVisible = false">取消</el-button><el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="taskConfigVisible" title="自动任务配置" width="520px">
      <el-form v-if="taskConfigForm.id" label-position="top">
        <el-form-item label="任务"><el-input v-model="taskConfigForm.task_name" disabled /></el-form-item>
        <el-form-item label="是否启用"><el-switch v-model="taskConfigForm.enabled" active-text="启用自动执行" /></el-form-item>
        <el-form-item label="执行方式">
          <el-radio-group v-model="taskConfigForm.schedule_type"><el-radio-button value="interval">按间隔</el-radio-button><el-radio-button value="daily">每天定时</el-radio-button></el-radio-group>
        </el-form-item>
        <el-form-item v-if="taskConfigForm.schedule_type === 'interval'" label="执行间隔（分钟）"><el-input-number v-model="taskConfigForm.interval_minutes" :min="1" :max="1440" /></el-form-item>
        <div v-else class="time-row">
          <el-form-item label="小时"><el-input-number v-model="taskConfigForm.schedule_hour" :min="0" :max="23" /></el-form-item>
          <el-form-item label="分钟"><el-input-number v-model="taskConfigForm.schedule_minute" :min="0" :max="59" /></el-form-item>
        </div>
        <el-form-item v-if="taskConfigForm.task_code === 'daily_report_sync'" label="每次回看天数"><el-input-number v-model="taskConfigForm.lookback_days" :min="1" :max="31" /><span class="field-tip">重复日报会自动跳过</span></el-form-item>
      </el-form>
      <template #footer><el-button @click="taskConfigVisible = false">取消</el-button><el-button type="primary" :loading="savingTask" @click="saveTaskConfig">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="runHistoryVisible" title="自动推进运行记录" size="760px">
      <el-table :data="automationRuns" v-loading="runHistoryLoading">
        <el-table-column prop="task_name" label="任务" min-width="180" />
        <el-table-column label="触发" width="85"><template #default="{ row }">{{ row.trigger_type === 'scheduled' ? '定时' : '手动' }}</template></el-table-column>
        <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="jobStatusType(row.status)">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column label="开始时间" width="175"><template #default="{ row }">{{ formatDateTime(row.started_at || row.created_at) }}</template></el-table-column>
        <el-table-column label="结果" min-width="240"><template #default="{ row }"><span :class="{ 'run-error': row.error_message }">{{ row.error_message || summarizeRun(row) }}</span></template></el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { getProjects } from '@/api/project'
import { getUsers } from '@/api/user'
import { assignWorkflowItem, createWorkflowItem, getWorkflowAutomationRuns, getWorkflowAutomationTasks, getWorkflowItem, getWorkflowItems, getWorkflowSummary, runWorkflowAutomationTask, transitionWorkflowItem, updateWorkflowAutomationTask } from '@/api/workflow'
import type { WorkflowAutomationRun, WorkflowAutomationTask, WorkflowItem, WorkflowSummary } from '@/types/workflow'

const statuses = ['AI待确认', '待接收', '处理中', '等待外部', '疑似完成', '已完成', '已取消']
const route = useRoute()
const emptySummary: WorkflowSummary = { total_open: 0, ai_pending: 0, mine_pending: 0, waiting_external: 0, due_today: 0, overdue: 0, suspected_complete: 0, active_alerts: 0 }
const summary = ref<WorkflowSummary>({ ...emptySummary })
const items = ref<WorkflowItem[]>([])
const selected = ref<WorkflowItem | null>(null)
const loading = ref(false)
const detailVisible = ref(false)
const createVisible = ref(false)
const creating = ref(false)
const automationLoading = ref(false)
const runHistoryLoading = ref(false)
const savingTask = ref(false)
const runningTaskId = ref('')
const taskConfigVisible = ref(false)
const runHistoryVisible = ref(false)
const automationTasks = ref<WorkflowAutomationTask[]>([])
const automationRuns = ref<WorkflowAutomationRun[]>([])
const users = ref<any[]>([])
const projects = ref<any[]>([])
const assignOwnerId = ref('')
const filters = reactive({ keyword: '', status: '', responsibility_party: '', mine: false })
const pagination = reactive({ page: 1, page_size: 20, total: 0 })
const createForm = reactive({ project_id: '', title: '', description: '', responsibility_party: '我方', priority: '普通', due_date: '' })
const taskConfigForm = reactive<any>({ id: '', task_code: '', task_name: '', enabled: true, schedule_type: 'interval', interval_minutes: 5, schedule_hour: 9, schedule_minute: 45, lookback_days: 3 })

const summaryCards = computed(() => [
  { key: 'mine', label: '我的待办', value: summary.value.mine_pending, hint: '需要我持续推进', tone: 'blue' },
  { key: 'ai', label: 'AI待确认', value: summary.value.ai_pending, hint: '不确定内容由人工把关', tone: 'purple' },
  { key: 'external', label: '等待外部', value: summary.value.waiting_external, hint: '客户、渠道或第三方', tone: 'cyan' },
  { key: 'overdue', label: '已逾期', value: summary.value.overdue, hint: '超过明确截止日期', tone: 'red' },
  { key: 'complete', label: '疑似完成', value: summary.value.suspected_complete, hint: '等待人工确认关闭', tone: 'green' },
  { key: 'alerts', label: '活跃告警', value: summary.value.active_alerts, hint: '已按延长阈值计算', tone: 'orange' },
])

async function loadSummary() { const res = await getWorkflowSummary(); summary.value = res.data }
async function loadAutomationTasks() {
  automationLoading.value = true
  try { const res = await getWorkflowAutomationTasks(); automationTasks.value = res.data }
  catch (e: any) { ElMessage.error(e.message || '自动任务加载失败') }
  finally { automationLoading.value = false }
}
async function loadItems() {
  loading.value = true
  try {
    const res = await getWorkflowItems({ page: pagination.page, page_size: pagination.page_size, keyword: filters.keyword || undefined, status: filters.status || undefined, responsibility_party: filters.responsibility_party || undefined, mine: filters.mine || undefined })
    items.value = res.data.items; pagination.total = res.data.total
  } catch (e: any) { ElMessage.error(e.message || '流程事项加载失败') } finally { loading.value = false }
}
async function refreshAll() { await Promise.all([loadSummary(), loadItems(), loadAutomationTasks()]) }
function search() { pagination.page = 1; loadItems() }
async function openDetail(row: WorkflowItem) { const res = await getWorkflowItem(row.id); selected.value = res.data; assignOwnerId.value = row.owner_id || ''; detailVisible.value = true }
async function changeStatus(status: string) {
  if (!selected.value) return
  const { value } = await ElMessageBox.prompt('填写本次处理说明（可选）', `更新为“${status}”`, { inputPlaceholder: '例如：已回复客户并提供测试计划', inputValue: '' }).catch(() => ({ value: undefined }))
  if (value === undefined) return
  await transitionWorkflowItem(selected.value.id, status, value)
  ElMessage.success('事项状态已更新'); await openDetail(selected.value); await refreshAll()
}
async function assignOwner(value: string) { if (!selected.value || !value || value === selected.value.owner_id) return; await assignWorkflowItem(selected.value.id, value); ElMessage.success('事项已转交'); await openDetail(selected.value); await refreshAll() }
function openCreate() { createVisible.value = true }
async function submitCreate() {
  if (!createForm.project_id || !createForm.title.trim()) return ElMessage.warning('请选择项目并填写事项标题')
  creating.value = true
  try { await createWorkflowItem({ ...createForm, due_date: createForm.due_date || null }); createVisible.value = false; Object.assign(createForm, { project_id: '', title: '', description: '', responsibility_party: '我方', priority: '普通', due_date: '' }); ElMessage.success('事项已创建'); await refreshAll() } finally { creating.value = false }
}
function taskPayload(task: WorkflowAutomationTask | typeof taskConfigForm) {
  return {
    enabled: task.enabled,
    schedule_type: task.schedule_type,
    interval_minutes: task.schedule_type === 'interval' ? Number(task.interval_minutes || 5) : null,
    schedule_hour: task.schedule_type === 'daily' ? Number(task.schedule_hour ?? 9) : null,
    schedule_minute: task.schedule_type === 'daily' ? Number(task.schedule_minute ?? 0) : null,
    lookback_days: task.task_code === 'daily_report_sync' ? Number(task.lookback_days || 3) : null,
  }
}
async function toggleTask(task: WorkflowAutomationTask) {
  try { await updateWorkflowAutomationTask(task.id, taskPayload(task)); ElMessage.success(task.enabled ? '自动任务已启用' : '自动任务已停用'); await loadAutomationTasks() }
  catch (e: any) { task.enabled = !task.enabled; ElMessage.error(e.message || '自动任务更新失败') }
}
function openTaskConfig(task: WorkflowAutomationTask) {
  Object.assign(taskConfigForm, { ...task, interval_minutes: task.interval_minutes || 5, schedule_hour: task.schedule_hour ?? 9, schedule_minute: task.schedule_minute ?? 0, lookback_days: task.lookback_days || 3 })
  taskConfigVisible.value = true
}
async function saveTaskConfig() {
  savingTask.value = true
  try { await updateWorkflowAutomationTask(taskConfigForm.id, taskPayload(taskConfigForm)); taskConfigVisible.value = false; ElMessage.success('执行计划已保存'); await loadAutomationTasks() }
  catch (e: any) { ElMessage.error(e.message || '保存失败') }
  finally { savingTask.value = false }
}
async function runTask(task: WorkflowAutomationTask) {
  runningTaskId.value = task.id
  try {
    const res = await runWorkflowAutomationTask(task.id)
    ElMessage.success(res.data.status === '排队中' ? '任务已提交到后台执行' : '任务正在执行')
    window.setTimeout(() => { loadAutomationTasks(); if (runHistoryVisible.value) loadAutomationRuns() }, 1500)
  } catch (e: any) { ElMessage.error(e.message || '任务提交失败') }
  finally { runningTaskId.value = '' }
}
async function loadAutomationRuns() {
  runHistoryLoading.value = true
  try { const res = await getWorkflowAutomationRuns({ page: 1, page_size: 50 }); automationRuns.value = res.data.items }
  finally { runHistoryLoading.value = false }
}
async function openRunHistory() { runHistoryVisible.value = true; await loadAutomationRuns() }
function formatSchedule(task: WorkflowAutomationTask) { return task.schedule_type === 'interval' ? `每${task.interval_minutes || 1}分钟` : `每天 ${String(task.schedule_hour ?? 0).padStart(2, '0')}:${String(task.schedule_minute ?? 0).padStart(2, '0')}${task.task_code === 'daily_report_sync' ? ` · 回看${task.lookback_days || 3}天` : ''}` }
function jobStatusType(status?: string) { return status === '成功' ? 'success' : status === '部分成功' || status === '已跳过' ? 'warning' : status === '失败' ? 'danger' : status === '运行中' || status === '排队中' ? 'primary' : 'info' }
function summarizeRun(run: WorkflowAutomationRun) { const value = run.result_json || {}; if (value.reason) return value.reason; if ('imported_count' in value) return `新增${value.imported_count || 0}封，生成活动${value.activity_count || 0}条`; if ('imported_activity_count' in value) return `导入活动${value.imported_activity_count || 0}条，未匹配${value.unmatched_count || 0}条`; if ('new_alert_count' in value) return `新增告警${value.new_alert_count || 0}条`; return '执行完成' }
function statusType(status: string) { return ({ 'AI待确认': 'warning', '待接收': 'info', '处理中': 'primary', '等待外部': 'warning', '疑似完成': 'success', '已完成': 'success', '已取消': 'info' } as any)[status] || 'info' }
function alertType(level: string) { return level === '严重' ? 'danger' : level === '告警' ? 'warning' : 'info' }
function closed(status: string) { return ['已完成', '已取消'].includes(status) }
function isOverdue(item: WorkflowItem) { return Boolean(item.due_date && !closed(item.status) && item.due_date < new Date().toISOString().slice(0, 10)) }
function formatDateTime(value?: string) { return value ? new Date(value).toLocaleString('zh-CN') : '-' }

onMounted(async () => {
  await refreshAll()
  const [userRes, projectRes] = await Promise.all([getUsers({ page: 1, page_size: 100 }), getProjects({ page: 1, page_size: 100 })])
  users.value = (userRes as any).data?.items || []
  projects.value = (projectRes as any).data?.items || []
  if (typeof route.query.item === 'string') {
    const row = items.value.find((item) => item.id === route.query.item) || { id: route.query.item } as WorkflowItem
    await openDetail(row)
  }
})
</script>

<style scoped>
.workflow-page{max-width:1600px;margin:0 auto}.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}.page-title{margin:0 0 7px;color:var(--text-primary);font-size:25px}.page-subtitle{margin:0;color:var(--text-tertiary)}.header-actions{display:flex;gap:10px}.summary-grid{display:grid;grid-template-columns:repeat(6,minmax(145px,1fr));gap:12px;margin-bottom:18px}.summary-card{display:flex;flex-direction:column;gap:5px;padding:17px;border:1px solid var(--border-color);border-radius:14px;background:var(--bg-secondary)}.summary-label{color:var(--text-secondary)}.summary-value{font-size:28px;color:var(--text-primary)}.summary-hint{font-size:12px;color:var(--text-tertiary)}.summary-card.red{border-color:rgba(239,68,68,.35)}.summary-card.orange{border-color:rgba(245,158,11,.35)}.automation-panel{padding:18px;margin-bottom:18px;border:1px solid var(--border-color);border-radius:16px;background:var(--bg-secondary)}.section-heading{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:14px}.section-heading h3{margin:0 0 6px;color:var(--text-primary);font-size:18px}.section-heading p{margin:0;color:var(--text-tertiary);font-size:13px}.automation-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.automation-card{padding:15px;border:1px solid var(--border-color);border-radius:13px;background:var(--bg-tertiary)}.automation-title{display:flex;justify-content:space-between;gap:12px}.automation-title>div{display:flex;align-items:center;gap:8px;color:var(--text-primary)}.automation-card>p{min-height:38px;margin:9px 0 12px;color:var(--text-tertiary);font-size:12px;line-height:1.6}.automation-meta{display:flex;justify-content:space-between;padding:5px 0;color:var(--text-tertiary);font-size:12px}.automation-meta b{color:var(--text-secondary);font-weight:500}.automation-result{display:flex;align-items:center;gap:8px;padding:9px;margin-top:8px;border-radius:8px;background:var(--bg-secondary);color:var(--text-secondary);font-size:12px}.automation-result span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.automation-error{margin-top:7px;color:#ef4444;font-size:12px;line-height:1.5}.automation-actions{display:flex;justify-content:flex-end;gap:7px;margin-top:12px}.time-row{display:grid;grid-template-columns:1fr 1fr;gap:18px}.field-tip{margin-left:10px;color:var(--text-tertiary);font-size:12px}.run-error{color:#ef4444}.filter-bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:16px}.filter-bar .keyword{width:260px}.filter-bar .el-select{width:150px}.table-shell{padding:18px;border:1px solid var(--border-color);border-radius:16px;background:var(--bg-secondary)}.workflow-table{cursor:pointer}.item-title{font-weight:600;color:var(--text-primary)}.item-meta{margin-top:5px;font-size:12px;color:var(--text-tertiary)}.overdue{color:#ef4444;font-weight:600}.pagination{display:flex;justify-content:flex-end;margin-top:16px}.detail-content{color:var(--text-primary)}.detail-heading{padding-bottom:16px;border-bottom:1px solid var(--border-color)}.detail-heading>div{display:flex;gap:8px}.detail-heading h3{font-size:20px;margin:14px 0 8px}.detail-heading p{color:var(--text-tertiary)}.action-bar{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:18px 0}.owner-select{width:165px}.detail-section{padding:17px 0;border-top:1px solid var(--border-color)}.detail-section h4{margin:0 0 12px}.preserve{white-space:pre-wrap;line-height:1.75;color:var(--text-secondary)}.ai-note,.timeline-card{padding:12px;border-radius:10px;background:var(--bg-tertiary);color:var(--text-secondary)}.timeline-card p{margin:8px 0}.timeline-card small{color:var(--text-tertiary)}.state-event{display:grid;grid-template-columns:1fr auto;gap:5px;padding:10px 0;border-bottom:1px dashed var(--border-color)}.state-event small{grid-column:1/-1;color:var(--text-tertiary)}.form-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}@media(max-width:1200px){.summary-grid{grid-template-columns:repeat(3,1fr)}.automation-grid{grid-template-columns:1fr}}
</style>
