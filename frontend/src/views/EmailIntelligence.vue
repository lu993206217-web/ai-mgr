<template>
  <div class="email-page">
    <div class="page-heading">
      <div>
        <h2>AI 邮件情报中心</h2>
        <p>原始邮件永久保留，可靠匹配才进入项目时间轴，低置信度邮件由人工确认。</p>
      </div>
      <el-button type="primary" @click="ingestVisible = true">导入测试邮件</el-button>
    </div>

    <div class="provider-grid">
      <el-card v-for="provider in connections" :key="provider.provider" shadow="never" class="provider-card">
        <div class="provider-card-head">
          <div>
            <strong>{{ provider.provider === 'dingtalk_mail' ? '钉钉企业邮箱' : 'Gmail' }}</strong>
            <p>{{ provider.account_email || '尚未配置账号' }}</p>
          </div>
          <el-tag :type="provider.connected ? 'success' : provider.configured ? 'warning' : 'info'">
            {{ provider.connected ? '连接正常' : provider.configured ? '待测试' : '未配置' }}
          </el-tag>
        </div>
        <p class="provider-message">{{ provider.message }}</p>
        <div v-if="provider.provider === 'dingtalk_mail'" class="server-info">
          <span>收件：{{ provider.receive_host }}:{{ provider.receive_port }} SSL</span>
          <span>发件：{{ provider.send_host }}:{{ provider.send_port }} SSL</span>
        </div>
        <div v-if="provider.provider === 'dingtalk_mail' && canManageEmail" class="provider-actions">
          <el-button @click="openDingTalkConfig">配置邮箱</el-button>
          <el-button :loading="testingDingTalk" :disabled="!provider.configured" @click="handleTestDingTalk">
            测试连接
          </el-button>
          <el-button type="primary" :loading="syncingDingTalk" :disabled="!provider.configured" @click="handleSyncDingTalk">
            同步邮件
          </el-button>
        </div>
      </el-card>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <span>邮件总量</span>
        <strong>{{ total }}</strong>
      </div>
      <div class="stat-card attention">
        <span>当前筛选</span>
        <strong>{{ emails.length }}</strong>
      </div>
      <div class="stat-card">
        <span>接入方式</span>
        <strong class="provider">{{ activeProviderText }}</strong>
      </div>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索主题或发件人"
          clearable
          style="width: 280px"
          @keyup.enter="loadEmails"
          @clear="loadEmails"
        />
        <el-select v-model="statusFilter" placeholder="归属状态" clearable style="width: 160px" @change="loadEmails">
          <el-option label="待确认" value="待确认" />
          <el-option label="已自动关联" value="已自动关联" />
          <el-option label="人工确认" value="人工确认" />
        </el-select>
        <el-button @click="loadEmails">查询</el-button>
      </div>

      <el-table :data="emails" v-loading="loading" row-key="id">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="email-detail">
              <h4>AI / 规则摘要</h4>
              <p>{{ row.summary || '待分析' }}</p>
              <h4 v-if="row.customer_request">客户诉求</h4>
              <p v-if="row.customer_request">{{ row.customer_request }}</p>
              <h4>原始正文</h4>
              <pre>{{ row.body_text || '（空正文）' }}</pre>
              <div v-if="row.risks.length" class="risk-line">
                <el-tag v-for="risk in row.risks" :key="risk" type="danger">{{ risk }}</el-tag>
              </div>
              <small>原始数据与分析结果分开保存；修正分析不会改动邮件原文。</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="received_at" label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.received_at) }}</template>
        </el-table-column>
        <el-table-column prop="provider" label="来源" width="110">
          <template #default="{ row }">
            <el-tag effect="plain">{{ providerLabel(row.provider) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="主题" min-width="260" show-overflow-tooltip />
        <el-table-column prop="sender" label="发件人" min-width="210" show-overflow-tooltip />
        <el-table-column prop="project_name" label="所属项目" min-width="180">
          <template #default="{ row }">{{ row.project_name || '待确认' }}</template>
        </el-table-column>
        <el-table-column prop="match_status" label="归属状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.match_status === '待确认' ? 'warning' : 'success'">
              {{ row.match_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="analysis_status" label="分析状态" width="110" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canManageEmail" link type="primary" @click="openBind(row)">
              {{ row.match_status === '待确认' ? '确认项目' : '调整项目' }}
            </el-button>
            <span v-else class="timeline-state">{{ row.activity_id ? '已入时间轴' : '仅查看' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, total"
          @current-change="loadEmails"
        />
      </div>
    </el-card>

    <el-dialog v-model="ingestVisible" title="导入测试邮件" width="620px">
      <el-form :model="ingestForm" label-width="90px">
        <el-form-item label="主题">
          <el-input v-model="ingestForm.subject" placeholder="主题中写入本地项目名可验证自动关联" />
        </el-form-item>
        <el-form-item label="发件人">
          <el-input v-model="ingestForm.sender" />
        </el-form-item>
        <el-form-item label="收件时间">
          <el-date-picker v-model="ingestForm.received_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ" />
        </el-form-item>
        <el-form-item label="邮件正文">
          <el-input v-model="ingestForm.body_text" type="textarea" :rows="7" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ingestVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitIngest">保存并分析</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="mailConfigVisible" title="配置钉钉企业邮箱" width="620px">
      <el-alert
        title="请填写邮箱客户端使用的第三方安全密码/授权码，不是网页登录密码。密码只保存在本机后端且不会回显。"
        type="warning"
        :closable="false"
        show-icon
        class="mail-config-alert"
      />
      <el-form :model="mailConfigForm" label-width="130px" class="mail-config-form">
        <el-form-item label="启用自动同步">
          <el-switch v-model="mailConfigForm.enabled" />
        </el-form-item>
        <el-form-item label="企业邮箱账号" required>
          <el-input v-model="mailConfigForm.account_email" placeholder="name@company.com" autocomplete="off" />
        </el-form-item>
        <el-form-item label="第三方安全密码" :required="!mailPasswordConfigured">
          <el-input
            v-model="mailConfigForm.app_password"
            type="password"
            show-password
            autocomplete="new-password"
            :placeholder="mailPasswordConfigured ? '已经配置；留空表示不修改' : '请输入邮箱生成的客户端专用密码/授权码'"
          />
        </el-form-item>
        <el-form-item label="已发送目录">
          <el-input v-model="mailConfigForm.sent_folder" placeholder="留空自动识别 IMAP Sent 目录" />
        </el-form-item>
        <el-form-item label="固定服务器">
          <div class="fixed-server-info">
            <span>IMAP：{{ mailConfigMeta.imap_host }}:{{ mailConfigMeta.imap_port }}（SSL）</span>
            <span>SMTP：{{ mailConfigMeta.smtp_host }}:{{ mailConfigMeta.smtp_port }}（SSL）</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mailConfigVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingMailConfig" @click="saveMailConfig">保存配置</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="bindVisible" title="确认邮件所属项目" width="520px">
      <el-select
        v-model="selectedProjectId"
        filterable
        remote
        reserve-keyword
        placeholder="输入项目名称搜索"
        :remote-method="searchProjects"
        :loading="projectLoading"
        style="width: 100%"
      >
        <el-option v-for="project in projects" :key="project.id" :label="project.project_name" :value="project.id" />
      </el-select>
      <el-input
        v-model="bindReason"
        type="textarea"
        :rows="3"
        placeholder="可选：填写调整原因，便于后续审计"
        class="reason-input"
      />
      <p class="bind-tip">确认后会生成一条“邮件”来源的项目活动，并进入项目时间轴。</p>
      <template #footer>
        <el-button @click="bindVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedProjectId" :loading="binding" @click="confirmBind">确认关联</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  bindEmailToProject,
  getEmailConnections,
  getDingTalkMailConfig,
  getIntelligenceEmails,
  manualIngestEmail,
  syncDingTalkMail,
  testDingTalkMailConnection,
  updateDingTalkMailConfig,
} from '@/api/emailIntelligence'
import { getProjects } from '@/api/project'
import { useAuthStore } from '@/stores/auth'
import type { IntelligenceEmail, EmailConnectionStatus, DingTalkMailConfig } from '@/types/emailIntelligence'
import type { Project } from '@/types/project'

const connections = ref<EmailConnectionStatus[]>([])
const testingDingTalk = ref(false)
const syncingDingTalk = ref(false)
const mailConfigVisible = ref(false)
const savingMailConfig = ref(false)
const mailPasswordConfigured = ref(false)
const mailConfigMeta = reactive({
  imap_host: 'imap.qiye.aliyun.com',
  imap_port: 993,
  smtp_host: 'smtp.qiye.aliyun.com',
  smtp_port: 465,
})
const mailConfigForm = reactive({
  enabled: true,
  account_email: '',
  app_password: '',
  sent_folder: '',
})
const authStore = useAuthStore()
const canManageEmail = ['管理员', '项目经理'].includes(String(authStore.user?.role || ''))
const emails = ref<IntelligenceEmail[]>([])
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const ingestVisible = ref(false)
const submitting = ref(false)
const ingestForm = reactive({
  subject: '',
  sender: 'customer@example.com',
  received_at: new Date().toISOString(),
  body_text: '',
})

const bindVisible = ref(false)
const binding = ref(false)
const selectedEmail = ref<IntelligenceEmail>()
const selectedProjectId = ref('')
const bindReason = ref('')
const projects = ref<Project[]>([])
const projectLoading = ref(false)
const activeProviderText = computed(() => {
  const active = connections.value.filter((item) => item.configured).map((item) => item.provider === 'dingtalk_mail' ? '钉钉邮箱' : 'Gmail')
  return active.length ? active.join(' + ') : '测试导入'
})

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function providerLabel(provider: string) {
  if (provider === 'dingtalk_mail') return '钉钉邮箱'
  if (provider === 'gmail') return 'Gmail'
  return '手工导入'
}

async function loadConnection() {
  const response = await getEmailConnections()
  connections.value = response.data.providers
}

async function handleTestDingTalk() {
  testingDingTalk.value = true
  try {
    const response = await testDingTalkMailConnection()
    ElMessage.success(response.data.message)
    await loadConnection()
    const target = connections.value.find((item) => item.provider === 'dingtalk_mail')
    if (target) target.connected = response.data.connected
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '邮箱连接测试失败')
  } finally {
    testingDingTalk.value = false
  }
}

async function openDingTalkConfig() {
  const response = await getDingTalkMailConfig()
  const config: DingTalkMailConfig = response.data
  mailConfigForm.enabled = config.enabled
  mailConfigForm.account_email = config.account_email || ''
  mailConfigForm.app_password = ''
  mailConfigForm.sent_folder = config.sent_folder || ''
  mailPasswordConfigured.value = config.password_configured
  mailConfigMeta.imap_host = config.imap_host
  mailConfigMeta.imap_port = config.imap_port
  mailConfigMeta.smtp_host = config.smtp_host
  mailConfigMeta.smtp_port = config.smtp_port
  mailConfigVisible.value = true
}

async function saveMailConfig() {
  if (!mailConfigForm.account_email.trim()) {
    ElMessage.warning('请填写企业邮箱账号')
    return
  }
  if (!mailPasswordConfigured.value && !mailConfigForm.app_password) {
    ElMessage.warning('请填写第三方安全密码/授权码')
    return
  }
  savingMailConfig.value = true
  try {
    const response = await updateDingTalkMailConfig({
      enabled: mailConfigForm.enabled,
      account_email: mailConfigForm.account_email.trim(),
      app_password: mailConfigForm.app_password || undefined,
      sent_folder: mailConfigForm.sent_folder.trim() || undefined,
    })
    ElMessage.success(response.message || '企业邮箱配置已保存')
    mailConfigVisible.value = false
    await loadConnection()
  } finally {
    savingMailConfig.value = false
  }
}

async function handleSyncDingTalk() {
  syncingDingTalk.value = true
  try {
    const response = await syncDingTalkMail(50, false)
    const result = response.data
    const folders = result.folders?.length ? `；目录 ${result.folders.join('、')}` : ''
    ElMessage.success(`同步完成：新增 ${result.imported_count} 封，重复 ${result.duplicate_count} 封，关联项目 ${result.matched_count} 封${folders}`)
    page.value = 1
    await loadEmails()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '邮箱同步失败')
  } finally {
    syncingDingTalk.value = false
  }
}

async function loadEmails() {
  loading.value = true
  try {
    const response = await getIntelligenceEmails({
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value || undefined,
      match_status: statusFilter.value || undefined,
    })
    emails.value = response.data.items
    total.value = response.data.total
  } finally {
    loading.value = false
  }
}

async function submitIngest() {
  if (!ingestForm.subject || !ingestForm.sender) {
    ElMessage.warning('请填写主题和发件人')
    return
  }
  submitting.value = true
  try {
    const response = await manualIngestEmail({
      ...ingestForm,
      recipients: [],
      cc: [],
    })
    ElMessage.success(response.message || '邮件已保存')
    ingestVisible.value = false
    ingestForm.subject = ''
    ingestForm.body_text = ''
    ingestForm.received_at = new Date().toISOString()
    page.value = 1
    await loadEmails()
  } finally {
    submitting.value = false
  }
}

function openBind(email: IntelligenceEmail) {
  selectedEmail.value = email
  selectedProjectId.value = email.project_id || ''
  bindReason.value = ''
  projects.value = []
  bindVisible.value = true
}

async function searchProjects(query: string) {
  if (!query.trim()) return
  projectLoading.value = true
  try {
    const response: any = await getProjects({ page: 1, page_size: 20, project_name: query })
    projects.value = response.data?.items || []
  } finally {
    projectLoading.value = false
  }
}

async function confirmBind() {
  if (!selectedEmail.value || !selectedProjectId.value) return
  binding.value = true
  try {
    await bindEmailToProject(selectedEmail.value.id, selectedProjectId.value, bindReason.value || undefined)
    ElMessage.success('项目归属已确认，活动已进入时间轴')
    bindVisible.value = false
    await loadEmails()
  } finally {
    binding.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadConnection(), loadEmails()])
})
</script>

<style scoped>
.email-page { display: flex; flex-direction: column; gap: 18px; }
.page-heading { display: flex; align-items: center; justify-content: space-between; }
.page-heading h2 { margin: 0 0 8px; font-size: 24px; }
.page-heading p { margin: 0; color: var(--el-text-color-secondary); }
.connection-alert { border-radius: 10px; }
.provider-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.provider-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.provider-card-head strong { font-size: 18px; }
.provider-card-head p, .provider-message { margin: 6px 0 0; color: var(--el-text-color-secondary); }
.server-info { display: flex; flex-direction: column; gap: 5px; margin-top: 12px; font-size: 13px; color: var(--el-text-color-regular); }
.provider-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
.mail-config-alert { margin-bottom: 18px; }
.mail-config-form { padding-top: 4px; }
.fixed-server-info { display: flex; flex-direction: column; gap: 4px; color: var(--el-text-color-secondary); font-size: 13px; }
.stat-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.stat-card { padding: 18px 20px; border: 1px solid var(--el-border-color-light); border-radius: 12px; background: var(--el-bg-color); }
.stat-card span { display: block; color: var(--el-text-color-secondary); margin-bottom: 8px; }
.stat-card strong { font-size: 28px; }
.stat-card .provider { font-size: 20px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.email-detail { padding: 6px 32px 18px; max-width: 980px; }
.email-detail h4 { margin: 14px 0 6px; }
.email-detail p { margin: 0; line-height: 1.7; }
.email-detail pre { white-space: pre-wrap; font-family: inherit; line-height: 1.65; padding: 12px; border-radius: 8px; background: var(--el-fill-color-light); }
.email-detail small { color: var(--el-text-color-secondary); }
.risk-line { display: flex; gap: 8px; margin: 12px 0; }
.timeline-state { color: var(--el-text-color-secondary); font-size: 13px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 18px; }
.bind-tip { color: var(--el-text-color-secondary); font-size: 13px; margin-top: 12px; }
.reason-input { margin-top: 14px; }
@media (max-width: 900px) {
  .stat-grid { grid-template-columns: 1fr; }
  .provider-grid { grid-template-columns: 1fr; }
  .page-heading { align-items: flex-start; gap: 16px; }
}
</style>
