<template>
  <div class="warning-page fade-in">
    <div class="page-header">
      <div>
        <h2 class="page-title">⚠️ 告警中心</h2>
        <p class="page-subtitle">按事项推进证据分级判断；条件消失后自动解除</p>
      </div>
      <el-button type="primary" :loading="checking" @click="runCheck">
        <el-icon><Refresh /></el-icon>重新计算告警
      </el-button>
    </div>

    <div class="policy-note">
      <b>新告警策略：</b>无推进14天提醒、30天告警、45天严重；等待外部7天提醒、14天告警、30天严重。明确截止日期超期3天告警、7天严重。
    </div>

    <el-tabs v-model="activeTab" class="warning-tabs" @tab-change="loadCurrent">
      <el-tab-pane label="流程事项告警" name="workflow">
        <div class="filter-bar">
          <el-select v-model="workflowFilters.status" placeholder="状态" clearable @change="loadWorkflowAlerts">
            <el-option label="活跃" value="活跃" /><el-option label="已解除" value="已解除" /><el-option label="已忽略" value="已忽略" />
          </el-select>
          <el-select v-model="workflowFilters.level" placeholder="级别" clearable @change="loadWorkflowAlerts">
            <el-option label="严重" value="严重" /><el-option label="告警" value="告警" /><el-option label="提醒" value="提醒" />
          </el-select>
          <el-button @click="resetWorkflow">重置</el-button>
        </div>
        <div class="table-shell">
          <el-table :data="workflowAlerts" v-loading="workflowLoading">
            <el-table-column label="级别" width="90"><template #default="{ row }"><el-tag :type="levelType(row.level)">{{ row.level }}</el-tag></template></el-table-column>
            <el-table-column prop="alert_type" label="告警类型" width="120" />
            <el-table-column prop="message" label="告警内容" min-width="340" />
            <el-table-column prop="project_name" label="关联项目" min-width="160" />
            <el-table-column label="办理事项" min-width="180"><template #default="{ row }"><el-button v-if="row.workflow_item_id" link type="primary" @click="openWorkflow(row)">{{ row.item_title || '查看事项' }}</el-button><span v-else>-</span></template></el-table-column>
            <el-table-column label="持续时间" width="100"><template #default="{ row }">{{ row.elapsed_days }}天</template></el-table-column>
            <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.status === '活跃' ? 'danger' : 'success'" effect="plain">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column label="最后计算" width="170"><template #default="{ row }">{{ formatDateTime(row.last_evaluated_at) }}</template></el-table-column>
            <el-table-column label="操作" width="130" fixed="right"><template #default="{ row }"><el-button v-if="row.status === '活跃'" link type="success" @click="resolveWorkflow(row)">解除</el-button><el-button link @click="viewProject(row.project_id)">项目</el-button></template></el-table-column>
          </el-table>
          <div class="pagination"><el-pagination v-model:current-page="workflowPage.page" v-model:page-size="workflowPage.page_size" :total="workflowPage.total" layout="total, sizes, prev, pager, next" @current-change="loadWorkflowAlerts" @size-change="loadWorkflowAlerts" /></div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="历史规则预警" name="legacy">
        <div class="filter-bar">
          <el-select v-model="legacyFilters.status" placeholder="状态" clearable @change="loadLegacy"><el-option label="活跃" value="活跃" /><el-option label="已处理" value="已处理" /></el-select>
          <el-select v-model="legacyFilters.severity" placeholder="级别" clearable @change="loadLegacy"><el-option label="严重" value="严重" /><el-option label="警告" value="警告" /><el-option label="关注" value="关注" /><el-option label="提示" value="提示" /></el-select>
          <el-button @click="resetLegacy">重置</el-button>
        </div>
        <div class="table-shell">
          <el-table :data="legacyAlerts" v-loading="legacyLoading">
            <el-table-column label="级别" width="90"><template #default="{ row }"><el-tag :type="levelType(row.severity)">{{ row.severity }}</el-tag></template></el-table-column>
            <el-table-column prop="rule_name" label="规则" width="170" />
            <el-table-column prop="message" label="预警内容" min-width="340" />
            <el-table-column prop="project_name" label="项目" min-width="170" />
            <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.status === '活跃' ? 'danger' : 'success'" effect="plain">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
            <el-table-column label="操作" width="140" fixed="right"><template #default="{ row }"><el-button v-if="row.status === '活跃'" link type="success" @click="resolveLegacy(row)">标记已处理</el-button><el-button v-if="row.project_id" link @click="viewProject(row.project_id)">项目</el-button></template></el-table-column>
          </el-table>
          <div class="pagination"><el-pagination v-model:current-page="legacyPage.page" v-model:page-size="legacyPage.page_size" :total="legacyPage.total" layout="total, sizes, prev, pager, next" @current-change="loadLegacy" @size-change="loadLegacy" /></div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getWarningInstances, resolveWarningInstance, triggerWarningCheck } from '@/api/warning'
import { getWorkflowAlerts, handleWorkflowAlert } from '@/api/workflow'
import type { WarningInstance } from '@/types/warning'
import type { WorkflowAlert } from '@/types/workflow'

const router = useRouter()
const activeTab = ref('workflow')
const checking = ref(false)
const workflowLoading = ref(false)
const legacyLoading = ref(false)
const workflowAlerts = ref<WorkflowAlert[]>([])
const legacyAlerts = ref<WarningInstance[]>([])
const workflowFilters = reactive({ status: '活跃', level: '' })
const legacyFilters = reactive({ status: '活跃', severity: '' })
const workflowPage = reactive({ page: 1, page_size: 20, total: 0 })
const legacyPage = reactive({ page: 1, page_size: 20, total: 0 })

async function loadWorkflowAlerts() {
  workflowLoading.value = true
  try { const res = await getWorkflowAlerts({ page: workflowPage.page, page_size: workflowPage.page_size, status: workflowFilters.status || undefined, level: workflowFilters.level || undefined }); workflowAlerts.value = res.data.items; workflowPage.total = res.data.total } finally { workflowLoading.value = false }
}
async function loadLegacy() {
  legacyLoading.value = true
  try { const res = await getWarningInstances({ page: legacyPage.page, page_size: legacyPage.page_size, status: legacyFilters.status || undefined, severity: legacyFilters.severity || undefined }); legacyAlerts.value = res.data.items; legacyPage.total = res.data.total } finally { legacyLoading.value = false }
}
function loadCurrent() { activeTab.value === 'workflow' ? loadWorkflowAlerts() : loadLegacy() }
async function runCheck() { checking.value = true; try { await triggerWarningCheck(); ElMessage.success('告警已按最新证据和延长阈值重新计算'); await Promise.all([loadWorkflowAlerts(), loadLegacy()]) } catch (e: any) { ElMessage.error(e.message || '告警计算失败') } finally { checking.value = false } }
async function resolveWorkflow(row: WorkflowAlert) { const { value } = await ElMessageBox.prompt('填写解除说明（可选）', '解除流程告警', { inputValue: '' }).catch(() => ({ value: undefined })); if (value === undefined) return; await handleWorkflowAlert(row.id, '已解除', value); ElMessage.success('告警已解除'); loadWorkflowAlerts() }
async function resolveLegacy(row: WarningInstance) { await resolveWarningInstance(row.id); ElMessage.success('已标记处理'); loadLegacy() }
function resetWorkflow() { workflowFilters.status = '活跃'; workflowFilters.level = ''; workflowPage.page = 1; loadWorkflowAlerts() }
function resetLegacy() { legacyFilters.status = '活跃'; legacyFilters.severity = ''; legacyPage.page = 1; loadLegacy() }
function viewProject(id: string) { router.push(`/projects/${id}`) }
function openWorkflow(row: WorkflowAlert) { router.push({ path: '/workflow-center', query: { item: row.workflow_item_id } }) }
function levelType(level: string) { if (['严重'].includes(level)) return 'danger'; if (['告警', '警告', '关注'].includes(level)) return 'warning'; return 'info' }
function formatDateTime(value?: string) { return value ? new Date(value).toLocaleString('zh-CN') : '-' }
onMounted(() => Promise.all([loadWorkflowAlerts(), loadLegacy()]))
</script>

<style scoped>
.warning-page{max-width:1600px;margin:0 auto}.page-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.page-title{margin:0 0 7px;color:var(--text-primary);font-size:25px}.page-subtitle{margin:0;color:var(--text-tertiary)}.policy-note{padding:14px 18px;margin-bottom:16px;border:1px solid rgba(59,130,246,.28);border-radius:12px;background:rgba(59,130,246,.08);color:var(--text-secondary);line-height:1.7}.warning-tabs{padding:0 18px 18px;border:1px solid var(--border-color);border-radius:16px;background:var(--bg-secondary)}.filter-bar{display:flex;gap:12px;margin:12px 0 16px}.filter-bar .el-select{width:155px}.table-shell{padding:8px 0}.pagination{display:flex;justify-content:flex-end;padding-top:16px;border-top:1px solid var(--border-color)}
</style>
