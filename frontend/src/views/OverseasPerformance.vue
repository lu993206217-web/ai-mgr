<template>
  <div class="performance-page fade-in" v-loading="loading">
    <div class="page-header">
      <div>
        <div class="title-row">
          <h2>海外绩效汇报</h2>
          <el-tag effect="plain">个人汇报工作台</el-tag>
        </div>
        <p>按考核条款自动汇总项目、邮件、活动和文件，并明确指出证据缺口</p>
      </div>
      <el-button type="primary" :loading="generating" @click="handleGenerate">
        <el-icon><Refresh /></el-icon>
        立即汇总
      </el-button>
    </div>

    <section class="period-panel">
      <div class="period-presets">
        <span class="control-label">汇报周期</span>
        <el-radio-group v-model="periodType" @change="applyPeriodPreset">
          <el-radio-button label="current_month">本月</el-radio-button>
          <el-radio-button label="previous_month">上月</el-radio-button>
          <el-radio-button label="current_quarter">本季度</el-radio-button>
          <el-radio-button label="previous_quarter">上季度</el-radio-button>
          <el-radio-button label="custom">自定义</el-radio-button>
        </el-radio-group>
      </div>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        :clearable="false"
        @change="periodType = 'custom'"
      />
      <el-select v-model="scope" class="scope-select">
        <el-option label="全部海外项目" value="all_projects" />
        <el-option label="仅我负责的项目" value="owned_projects" />
      </el-select>
    </section>

    <el-tabs v-model="activeTab" class="main-tabs">
      <el-tab-pane label="汇报总览" name="summary">
        <template v-if="currentReport?.summary?.criteria?.length">
          <div class="report-head">
            <div>
              <h3>{{ currentReport.period_label }}</h3>
              <p>
                {{ currentReport.start_date }} 至 {{ currentReport.end_date }} ·
                {{ currentReport.scope === 'owned_projects' ? '仅我负责的项目' : '全部海外项目' }} ·
                {{ currentReport.trigger_type === 'scheduled' ? '定时生成' : '手动生成' }}
              </p>
            </div>
            <span>生成于 {{ formatDateTime(currentReport.generated_at) }}</span>
          </div>

          <div class="source-cards">
            <div class="source-card blue"><el-icon><FolderOpened /></el-icon><div><strong>{{ currentReport.summary.source_summary.projects }}</strong><span>涉及项目</span></div></div>
            <div class="source-card purple"><el-icon><List /></el-icon><div><strong>{{ currentReport.summary.source_summary.activities }}</strong><span>活动记录</span></div></div>
            <div class="source-card green"><el-icon><Message /></el-icon><div><strong>{{ currentReport.summary.source_summary.emails }}</strong><span>项目邮件</span></div></div>
            <div class="source-card orange"><el-icon><Document /></el-icon><div><strong>{{ currentReport.summary.source_summary.files }}</strong><span>项目文件</span></div></div>
          </div>

          <el-alert :title="currentReport.summary.notice" type="info" :closable="false" show-icon class="data-notice" />

          <div class="criteria-list">
            <article v-for="criterion in currentReport.summary.criteria" :key="criterion.code" class="criterion-card">
              <div class="criterion-head">
                <div class="criterion-index">{{ criterion.code.toUpperCase() }}</div>
                <div class="criterion-title">
                  <div>
                    <h4>{{ criterion.title }}</h4>
                    <el-tag v-if="criterion.required" size="small" type="danger" effect="plain">必达</el-tag>
                  </div>
                  <p>{{ criterion.requirement }}</p>
                </div>
                <el-tag :type="statusTagType(criterion.status)" effect="dark" round>{{ criterion.status }}</el-tag>
              </div>

              <div class="metric-row">
                <div v-for="metric in criterion.metrics" :key="metric.label" class="metric-item">
                  <span>{{ metric.label }}</span>
                  <strong>{{ metric.value }}<small>{{ metric.unit }}</small></strong>
                </div>
              </div>

              <div class="criterion-conclusion">{{ criterion.conclusion }}</div>
              <div class="evidence-grid">
                <div>
                  <h5><el-icon><CircleCheck /></el-icon>系统已找到</h5>
                  <ul><li v-for="item in criterion.evidence" :key="item">{{ item }}</li></ul>
                </div>
                <div class="gap-box">
                  <h5><el-icon><Warning /></el-icon>提交前要补</h5>
                  <ul><li v-for="item in criterion.gaps" :key="item">{{ item }}</li></ul>
                </div>
              </div>
              <div class="criterion-actions">
                <span>考核要求证据：{{ criterion.evidence_requirements.join('、') }}</span>
                <el-button link type="primary" @click="openDetails(criterion)">查看汇总明细</el-button>
              </div>
            </article>
          </div>
        </template>

        <el-empty v-else description="选择汇报时间后点击“立即汇总”，系统会按7条考核要求整理现有证据" />
      </el-tab-pane>

      <el-tab-pane label="定时与考核配置" name="settings">
        <section class="settings-card">
          <div class="section-heading">
            <div><h3>定时汇总</h3><p>到期后自动汇总上一个完整月份或季度，并保存到历史记录</p></div>
            <el-switch v-model="config.enabled" inline-prompt active-text="开" inactive-text="关" />
          </div>
          <div class="schedule-grid">
            <div class="setting-field"><label>汇报范围</label><el-select v-model="config.scope"><el-option label="全部海外项目" value="all_projects" /><el-option label="仅我负责的项目" value="owned_projects" /></el-select></div>
            <div class="setting-field"><label>生成频率</label><el-select v-model="config.schedule_frequency"><el-option label="每月生成" value="monthly" /><el-option label="每季度生成" value="quarterly" /></el-select></div>
            <div class="setting-field"><label>生成日期</label><el-input-number v-model="config.schedule_day" :min="1" :max="28" controls-position="right" /><small>每月第几天；季度汇报在1、4、7、10月执行</small></div>
            <div class="setting-field"><label>生成时间</label><el-time-picker v-model="scheduleTime" format="HH:mm" value-format="HH:mm" :clearable="false" /></div>
          </div>
        </section>

        <section class="settings-card">
          <div class="section-heading"><div><h3>考核条款</h3><p>已按当前岗位考核要求预置，可调整量化阈值</p></div></div>
          <div class="criterion-settings">
            <div v-for="criterion in config.criteria" :key="criterion.code" class="criterion-setting">
              <el-switch v-model="criterion.enabled" />
              <div class="setting-copy">
                <div><strong>{{ criterion.code.toUpperCase() }} · {{ criterion.title }}</strong><el-tag v-if="criterion.required" size="small" type="danger" effect="plain">必达</el-tag></div>
                <p>{{ criterion.requirement }}</p>
              </div>
              <div class="thresholds">
                <div v-for="definition in thresholdDefinitions[criterion.code]" :key="definition.key" class="threshold-field">
                  <span>{{ definition.label }}</span>
                  <el-input-number v-model="criterion.thresholds[definition.key]" :min="definition.min" :max="definition.max" controls-position="right" />
                  <small>{{ definition.unit }}</small>
                </div>
              </div>
            </div>
          </div>
          <div class="save-row"><el-button type="primary" :loading="savingConfig" @click="handleSaveConfig"><el-icon><Check /></el-icon>保存定时与考核配置</el-button></div>
        </section>
      </el-tab-pane>

      <el-tab-pane name="history">
        <template #label>历史汇总 <el-badge v-if="history.length" :value="history.length" /></template>
        <section class="history-card">
          <el-table :data="history" stripe>
            <el-table-column prop="period_label" label="汇报周期" min-width="220" />
            <el-table-column label="时间范围" min-width="210"><template #default="{ row }">{{ row.start_date }} 至 {{ row.end_date }}</template></el-table-column>
            <el-table-column label="范围" width="130"><template #default="{ row }">{{ row.scope === 'owned_projects' ? '我的项目' : '全部项目' }}</template></el-table-column>
            <el-table-column label="生成方式" width="110"><template #default="{ row }"><el-tag size="small" effect="plain">{{ row.trigger_type === 'scheduled' ? '定时' : '手动' }}</el-tag></template></el-table-column>
            <el-table-column label="生成时间" width="170"><template #default="{ row }">{{ formatDateTime(row.generated_at) }}</template></el-table-column>
            <el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="loadReport(row.id)">查看</el-button></template></el-table-column>
          </el-table>
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="detailsVisible" :title="detailCriterion ? `${detailCriterion.code.toUpperCase()} · ${detailCriterion.title}` : '汇总明细'" width="88%" top="5vh">
      <el-table :data="detailRows" max-height="620" stripe>
        <el-table-column v-for="column in detailColumns" :key="column.key" :prop="column.key" :label="column.label" :min-width="column.width || 120" show-overflow-tooltip>
          <template #default="{ row }">{{ formatCell(row[column.key], column.key) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!detailRows.length" description="当前没有可展示的明细记录" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { Check, CircleCheck, Document, FolderOpened, List, Message, Refresh, Warning } from '@element-plus/icons-vue'
import {
  generatePerformanceReport,
  getPerformanceConfig,
  getPerformanceReport,
  getPerformanceReports,
  updatePerformanceConfig,
  type CriterionResult,
  type PerformanceConfig,
  type PerformanceReport,
} from '@/api/overseasPerformance'

const loading = ref(false)
const generating = ref(false)
const savingConfig = ref(false)
const activeTab = ref('summary')
const periodType = ref('current_quarter')
const dateRange = ref<[string, string]>(['', ''])
const scope = ref<'all_projects' | 'owned_projects'>('all_projects')
const currentReport = ref<PerformanceReport | null>(null)
const history = ref<Array<Omit<PerformanceReport, 'summary'>>>([])
const scheduleTime = ref('09:00')
const detailsVisible = ref(false)
const detailCriterion = ref<CriterionResult | null>(null)
const detailRows = ref<any[]>([])
const detailColumns = ref<Array<{ key: string; label: string; width?: number }>>([])

const config = reactive<PerformanceConfig>({
  enabled: false,
  scope: 'all_projects',
  schedule_frequency: 'quarterly',
  schedule_day: 1,
  schedule_hour: 9,
  schedule_minute: 0,
  criteria: [],
  last_run_at: null,
})

const thresholdDefinitions: Record<string, Array<{ key: string; label: string; unit: string; min: number; max: number }>> = {
  c1: [{ key: 'on_time_rate', label: '按时交付率', unit: '%', min: 0, max: 100 }],
  c2: [
    { key: 'normal_response_minutes', label: '普通问题响应', unit: '分钟', min: 1, max: 1440 },
    { key: 'emergency_response_minutes', label: '紧急问题响应', unit: '分钟', min: 1, max: 240 },
  ],
  c3: [{ key: 'assignment_frequency_months', label: '任务分配频率', unit: '月/次', min: 1, max: 12 }],
  c4: [{ key: 'satisfaction_score', label: '满意度目标', unit: '分', min: 0, max: 100 }],
  c5: [{ key: 'retrospective_rate', label: '项目复盘覆盖率', unit: '%', min: 0, max: 100 }],
  c6: [{ key: 'quarterly_training_count', label: '季度培训次数', unit: '次', min: 0, max: 20 }],
  c7: [{ key: 'quarterly_material_count', label: '季度资料数量', unit: '份', min: 0, max: 100 }],
}

function quarterRange(base: dayjs.Dayjs, offset: number) {
  const shifted = base.add(offset * 3, 'month')
  const startMonth = Math.floor(shifted.month() / 3) * 3
  const start = shifted.month(startMonth).startOf('month')
  return [start.format('YYYY-MM-DD'), start.add(2, 'month').endOf('month').format('YYYY-MM-DD')] as [string, string]
}

function applyPeriodPreset() {
  const now = dayjs()
  if (periodType.value === 'current_month') dateRange.value = [now.startOf('month').format('YYYY-MM-DD'), now.format('YYYY-MM-DD')]
  else if (periodType.value === 'previous_month') {
    const previous = now.subtract(1, 'month')
    dateRange.value = [previous.startOf('month').format('YYYY-MM-DD'), previous.endOf('month').format('YYYY-MM-DD')]
  } else if (periodType.value === 'current_quarter') dateRange.value = [quarterRange(now, 0)[0], now.format('YYYY-MM-DD')]
  else if (periodType.value === 'previous_quarter') dateRange.value = quarterRange(now, -1)
}

function periodLabel() {
  const start = dayjs(dateRange.value[0])
  if (periodType.value.includes('month')) return `${start.year()}年${start.month() + 1}月海外绩效汇报`
  if (periodType.value.includes('quarter')) return `${start.year()}年第${Math.floor(start.month() / 3) + 1}季度海外绩效汇报`
  return `${dateRange.value[0]}至${dateRange.value[1]}海外绩效汇报`
}

function applyConfig(data: PerformanceConfig) {
  Object.assign(config, data)
  config.criteria = data.criteria.map((item) => ({ ...item, thresholds: { ...item.thresholds } }))
  scheduleTime.value = `${String(data.schedule_hour).padStart(2, '0')}:${String(data.schedule_minute).padStart(2, '0')}`
  scope.value = data.scope
}

async function loadPage() {
  loading.value = true
  try {
    const [configResponse, historyResponse] = await Promise.all([getPerformanceConfig(), getPerformanceReports()])
    applyConfig(configResponse.data)
    history.value = historyResponse.data.items
    if (history.value.length) await loadReport(history.value[0].id, false)
  } catch (error) {
    console.error(error)
    ElMessage.error('海外绩效汇报页面加载失败')
  } finally {
    loading.value = false
  }
}

async function handleGenerate() {
  if (!dateRange.value[0] || !dateRange.value[1]) return ElMessage.warning('请选择汇报时间范围')
  generating.value = true
  try {
    const response = await generatePerformanceReport({
      period_type: periodType.value,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      period_label: periodLabel(),
      scope: scope.value,
    })
    currentReport.value = response.data
    activeTab.value = 'summary'
    ElMessage.success('已按考核条款完成汇总')
    const historyResponse = await getPerformanceReports()
    history.value = historyResponse.data.items
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '汇报生成失败')
  } finally {
    generating.value = false
  }
}

async function handleSaveConfig() {
  const [hour, minute] = scheduleTime.value.split(':').map(Number)
  config.schedule_hour = hour
  config.schedule_minute = minute
  savingConfig.value = true
  try {
    const response = await updatePerformanceConfig(config)
    applyConfig(response.data)
    ElMessage.success('定时与考核配置已保存')
  } catch (error) {
    console.error(error)
    ElMessage.error('配置保存失败')
  } finally {
    savingConfig.value = false
  }
}

async function loadReport(id: string, switchTab = true) {
  try {
    const response = await getPerformanceReport(id)
    currentReport.value = response.data
    if (switchTab) activeTab.value = 'summary'
  } catch (error) {
    console.error(error)
    ElMessage.error('历史汇报加载失败')
  }
}

function statusTagType(status: string) {
  if (status === '达标') return 'success'
  if (status === '未达标') return 'danger'
  if (status === '部分达标' || status === '证据不足') return 'warning'
  return 'info'
}

const columnsByCode: Record<string, Array<{ key: string; label: string; width?: number }>> = {
  c1: [
    { key: 'project_name', label: '项目', width: 190 }, { key: 'owner', label: '负责人' },
    { key: 'stage', label: '阶段' }, { key: 'status', label: '状态' },
    { key: 'planned_date', label: '计划完成' }, { key: 'actual_date', label: '实际完成' },
    { key: 'on_time', label: '是否按时' }, { key: 'document_count', label: '文件数' },
  ],
  c2: [
    { key: 'subject', label: '邮件主题', width: 260 }, { key: 'received_at', label: '客户来信时间', width: 170 },
    { key: 'reply_at', label: '我方回复时间', width: 170 }, { key: 'response_minutes', label: '响应分钟' },
    { key: 'emergency', label: '紧急问题' }, { key: 'sla_minutes', label: '考核阈值' }, { key: 'met', label: '是否达标' },
  ],
  c3: [{ key: 'month', label: '月份' }, { key: 'owner', label: '成员' }, { key: 'project_count', label: '涉及项目' }, { key: 'activity_count', label: '活动记录' }],
  c4: [{ key: 'record_type', label: '候选类型' }, { key: 'subject', label: '邮件主题', width: 320 }, { key: 'received_at', label: '邮件时间', width: 180 }],
  c5: [{ key: 'project_name', label: '结束项目', width: 260 }, { key: 'status', label: '状态' }, { key: 'has_review_file', label: '存在复盘文件' }],
  c6: [{ key: 'file_name', label: '培训材料候选', width: 320 }, { key: 'category', label: '文件分类' }, { key: 'project_id', label: '项目ID', width: 260 }],
  c7: [{ key: 'name', label: '资料名称', width: 360 }, { key: 'source', label: '来源' }, { key: 'project_id', label: '项目ID', width: 260 }],
}

function openDetails(criterion: CriterionResult) {
  detailCriterion.value = criterion
  detailColumns.value = columnsByCode[criterion.code] || []
  if (criterion.code === 'c4' && !Array.isArray(criterion.records)) {
    detailRows.value = [
      ...(criterion.records?.positive_feedback || []).map((item: any) => ({ ...item, record_type: '正向反馈候选' })),
      ...(criterion.records?.complaints || []).map((item: any) => ({ ...item, record_type: '投诉关键词候选' })),
    ]
  } else {
    detailRows.value = Array.isArray(criterion.records) ? criterion.records : []
  }
  detailsVisible.value = true
}

function formatCell(value: any, key: string) {
  if (value === null || value === undefined || value === '') return '待补'
  if (typeof value === 'boolean') return value ? (key === 'emergency' ? '是' : '达标/已有') : (key === 'emergency' ? '否' : '未达标/缺失')
  if (Array.isArray(value)) return value.join('、') || '--'
  if (key.endsWith('_at')) return formatDateTime(value)
  return value
}

function formatDateTime(value?: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

onMounted(() => {
  applyPeriodPreset()
  loadPage()
})
</script>

<style scoped>
.performance-page { display: flex; flex-direction: column; gap: 18px; max-width: 1500px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
.title-row { display: flex; align-items: center; gap: 12px; }
.title-row h2 { margin: 0; color: var(--el-text-color-primary); font-size: 26px; }
.page-header p { margin: 8px 0 0; color: var(--el-text-color-secondary); }
.period-panel { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; padding: 16px 18px; border: 1px solid var(--el-border-color-light); border-radius: 12px; background: var(--el-bg-color); }
.period-presets { display: flex; align-items: center; gap: 12px; }
.control-label { color: var(--el-text-color-primary); font-weight: 600; }
.scope-select { width: 170px; }
.main-tabs { padding: 0 20px 20px; border: 1px solid var(--el-border-color-light); border-radius: 14px; background: var(--el-bg-color); }
.report-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; padding: 8px 0 16px; }
.report-head h3 { margin: 0; color: var(--el-text-color-primary); font-size: 20px; }
.report-head p, .report-head > span { margin: 5px 0 0; color: var(--el-text-color-secondary); font-size: 13px; }
.source-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.source-card { display: flex; align-items: center; gap: 14px; padding: 17px; border: 1px solid var(--el-border-color-light); border-radius: 12px; background: var(--el-fill-color-light); }
.source-card > .el-icon { font-size: 28px; }
.source-card div { display: flex; flex-direction: column; gap: 2px; }
.source-card strong { color: var(--el-text-color-primary); font-size: 24px; }
.source-card span { color: var(--el-text-color-secondary); font-size: 13px; }
.source-card.blue > .el-icon { color: #2563eb; } .source-card.purple > .el-icon { color: #7c3aed; } .source-card.green > .el-icon { color: #059669; } .source-card.orange > .el-icon { color: #ea580c; }
.data-notice { margin: 14px 0; }
.criteria-list { display: flex; flex-direction: column; gap: 14px; }
.criterion-card { overflow: hidden; border: 1px solid var(--el-border-color-light); border-radius: 13px; background: var(--el-fill-color-blank); }
.criterion-head { display: flex; align-items: flex-start; gap: 13px; padding: 17px 18px 13px; }
.criterion-index { display: grid; place-items: center; width: 42px; height: 42px; flex-shrink: 0; border-radius: 11px; background: color-mix(in srgb, var(--el-color-primary) 12%, var(--el-bg-color)); color: var(--el-color-primary); font-weight: 700; }
.criterion-title { flex: 1; min-width: 0; }
.criterion-title > div { display: flex; align-items: center; gap: 8px; }
.criterion-title h4 { margin: 0; color: var(--el-text-color-primary); font-size: 16px; }
.criterion-title p { margin: 5px 0 0; color: var(--el-text-color-secondary); font-size: 13px; }
.metric-row { display: grid; grid-template-columns: repeat(4, 1fr); margin: 0 18px; border: 1px solid var(--el-border-color-light); border-radius: 10px; background: var(--el-fill-color-light); }
.metric-item { display: flex; flex-direction: column; gap: 5px; padding: 12px 14px; border-right: 1px solid var(--el-border-color-light); }
.metric-item:last-child { border-right: 0; }
.metric-item span { color: var(--el-text-color-secondary); font-size: 12px; }
.metric-item strong { color: var(--el-text-color-primary); font-size: 20px; }
.metric-item small { margin-left: 3px; font-size: 12px; font-weight: 400; }
.criterion-conclusion { margin: 14px 18px 0; padding: 11px 13px; border-left: 3px solid var(--el-color-primary); border-radius: 6px; background: color-mix(in srgb, var(--el-color-primary) 6%, var(--el-bg-color)); color: var(--el-text-color-regular); line-height: 1.55; }
.evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 14px 18px; }
.evidence-grid > div { padding: 12px 14px; border: 1px solid color-mix(in srgb, var(--el-color-success) 25%, var(--el-border-color-light)); border-radius: 9px; background: color-mix(in srgb, var(--el-color-success) 5%, var(--el-bg-color)); }
.evidence-grid .gap-box { border-color: color-mix(in srgb, var(--el-color-warning) 30%, var(--el-border-color-light)); background: color-mix(in srgb, var(--el-color-warning) 6%, var(--el-bg-color)); }
.evidence-grid h5 { display: flex; align-items: center; gap: 6px; margin: 0 0 7px; color: var(--el-text-color-primary); }
.evidence-grid ul { margin: 0; padding-left: 20px; color: var(--el-text-color-regular); font-size: 13px; line-height: 1.75; }
.criterion-actions { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 10px 18px; border-top: 1px solid var(--el-border-color-light); color: var(--el-text-color-secondary); font-size: 12px; }
.settings-card, .history-card { margin-top: 8px; padding: 20px; border: 1px solid var(--el-border-color-light); border-radius: 12px; background: var(--el-fill-color-blank); }
.settings-card + .settings-card { margin-top: 15px; }
.section-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 18px; }
.section-heading h3 { margin: 0; color: var(--el-text-color-primary); }
.section-heading p { margin: 5px 0 0; color: var(--el-text-color-secondary); font-size: 13px; }
.schedule-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.setting-field label { display: block; margin-bottom: 7px; color: var(--el-text-color-primary); font-size: 13px; font-weight: 600; }
.setting-field :deep(.el-select), .setting-field :deep(.el-input-number), .setting-field :deep(.el-date-editor) { width: 100%; }
.setting-field small { display: block; margin-top: 5px; color: var(--el-text-color-secondary); line-height: 1.4; }
.criterion-settings { display: flex; flex-direction: column; gap: 10px; }
.criterion-setting { display: flex; align-items: flex-start; gap: 13px; padding: 14px; border: 1px solid var(--el-border-color-light); border-radius: 10px; background: var(--el-fill-color-light); }
.setting-copy { flex: 1; min-width: 0; }
.setting-copy > div { display: flex; align-items: center; gap: 8px; }
.setting-copy strong { color: var(--el-text-color-primary); }
.setting-copy p { margin: 5px 0 0; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
.thresholds { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 10px; }
.threshold-field { display: grid; grid-template-columns: auto 110px auto; align-items: center; gap: 7px; }
.threshold-field span, .threshold-field small { color: var(--el-text-color-secondary); font-size: 12px; }
.save-row { display: flex; justify-content: flex-end; margin-top: 18px; }

@media (max-width: 1100px) {
  .source-cards, .schedule-grid { grid-template-columns: repeat(2, 1fr); }
  .metric-row { grid-template-columns: repeat(2, 1fr); }
  .metric-item:nth-child(2) { border-right: 0; }
  .metric-item:nth-child(-n+2) { border-bottom: 1px solid var(--el-border-color-light); }
  .criterion-setting { flex-wrap: wrap; }
  .thresholds { width: 100%; justify-content: flex-start; padding-left: 47px; }
}
@media (max-width: 720px) {
  .page-header, .report-head { flex-direction: column; }
  .period-panel, .period-presets { align-items: stretch; flex-direction: column; }
  .scope-select, .period-panel :deep(.el-date-editor) { width: 100%; }
  .source-cards, .schedule-grid, .evidence-grid { grid-template-columns: 1fr; }
  .criterion-head { flex-wrap: wrap; }
  .criterion-title { min-width: calc(100% - 58px); }
  .criterion-actions { align-items: flex-start; flex-direction: column; }
  .thresholds { padding-left: 0; }
}
</style>
