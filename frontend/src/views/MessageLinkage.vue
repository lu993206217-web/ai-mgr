<template>
  <div class="message-linkage-page fade-in" v-loading="loading">
    <div class="page-header">
      <div>
        <div class="title-line">
          <h2>消息联动</h2>
          <el-tag :type="form.enabled ? 'success' : 'info'" effect="light" round>
            {{ form.enabled ? '总开关已启用' : '当前未启用' }}
          </el-tag>
        </div>
        <p>把项目、售前、实施、商务和任务事件统一交给 Message Center 路由与推送</p>
      </div>
      <div class="header-actions">
        <el-button :loading="testing" @click="handleHealthTest">
          <el-icon><Connection /></el-icon>
          测试连接
        </el-button>
        <el-button type="primary" :loading="saving" @click="handleSave(true)">
          <el-icon><Check /></el-icon>
          保存配置
        </el-button>
      </div>
    </div>
    <div class="architecture-tip">
      <el-icon><InfoFilled /></el-icon>
      <div>
        <strong>职责边界</strong>
        <span>本系统只提交标准消息和业务上下文；接收人识别、钉钉 Token、卡片样式及最终投递由 Message Center 统一管理。</span>
      </div>
    </div>

    <section class="panel connection-panel">
      <div class="panel-heading">
        <div class="section-icon connection-icon"><el-icon><Link /></el-icon></div>
        <div>
          <h3>连接配置</h3>
          <p>配置 Message Center 的服务地址、系统身份和调用 Token</p>
        </div>
        <el-switch
          v-model="form.enabled"
          class="master-switch"
          inline-prompt
          active-text="启用"
          inactive-text="停用"
        />
      </div>

      <div class="connection-grid">
        <div class="field field-wide">
          <label>Message Center 地址</label>
          <el-input v-model="form.base_url" placeholder="http://message.srun.local:8001">
            <template #prefix><el-icon><Link /></el-icon></template>
          </el-input>
          <small>连接测试访问此地址的 /health 接口</small>
        </div>

        <div class="field">
          <label>来源系统标识</label>
          <el-input v-model="form.source_system" placeholder="ai_project_intelligence" />
          <small>必须与 Message Center 注册的 source_system 一致</small>
        </div>

        <div class="field">
          <label>请求超时</label>
          <el-input-number v-model="form.timeout_seconds" :min="3" :max="30" controls-position="right" />
          <small>3–30 秒；消息发送失败不会自动重试</small>
        </div>

        <div class="field field-wide">
          <label>
            X-API-Key
            <el-tag v-if="apiKeyConfigured" size="small" type="success" effect="plain">已安全保存</el-tag>
            <el-tag v-else size="small" type="warning" effect="plain">尚未配置</el-tag>
          </label>
          <el-input
            v-model="apiKeyInput"
            type="password"
            show-password
            autocomplete="new-password"
            :disabled="clearApiKey"
            :placeholder="apiKeyConfigured ? '留空则保持现有 Token 不变' : '请输入 Message Center Token'"
          >
            <template #prefix><el-icon><Key /></el-icon></template>
          </el-input>
          <div class="secret-foot">
            <small>Token 只保存在后端本机的受限文件中，页面和接口都不会回显。</small>
            <el-checkbox v-if="apiKeyConfigured" v-model="clearApiKey">清除已保存 Token</el-checkbox>
          </div>
        </div>
      </div>

      <div v-if="healthResult" class="health-result" :class="healthResult.success ? 'is-success' : 'is-error'">
        <el-icon><CircleCheckFilled v-if="healthResult.success" /><CircleCloseFilled v-else /></el-icon>
        <div>
          <strong>{{ healthResult.message }}</strong>
          <span>
            {{ healthResult.base_url }}
            <template v-if="healthResult.response_time_ms != null"> · {{ healthResult.response_time_ms }} ms</template>
            <template v-if="healthResult.remote_status"> · 状态 {{ healthResult.remote_status }}</template>
          </span>
        </div>
      </div>
    </section>

    <section class="panel rules-panel">
      <div class="panel-heading rules-heading">
        <div class="section-icon rules-icon"><el-icon><Operation /></el-icon></div>
        <div>
          <h3>业务联动场景</h3>
          <p>先定义哪些业务事件需要推送，以及交给 AI 路由还是指定接收目标</p>
        </div>
        <div class="enabled-count">已开启 {{ enabledRuleCount }} / {{ form.linkage_rules.length }}</div>
      </div>

      <div class="rule-list">
        <article v-for="rule in form.linkage_rules" :key="rule.scene_key" class="rule-card" :class="{ enabled: rule.enabled }">
          <div class="rule-summary">
            <el-switch v-model="rule.enabled" :disabled="rule.rollout_status !== '基础已就绪'" />
            <div class="rule-name">
              <div>
                <strong>{{ rule.scene_name }}</strong>
                <el-tag size="small" effect="plain">{{ rule.business_domain }}</el-tag>
                <el-tag
                  size="small"
                  :type="rule.rollout_status === '基础已就绪' ? 'success' : 'info'"
                  effect="plain"
                >
                  {{ rule.rollout_status }}
                </el-tag>
              </div>
              <p>{{ rule.description }}</p>
            </div>
          </div>

          <div class="rule-config">
            <div class="field compact">
              <label>消息分类</label>
              <el-select v-model="rule.category">
                <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </div>
            <div class="field compact">
              <label>来源子类</label>
              <el-input v-model="rule.source_category" />
            </div>
            <div class="field compact">
              <label>优先级</label>
              <el-select v-model="rule.priority">
                <el-option v-for="item in priorityOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </div>
            <div class="field compact">
              <label>接收方式</label>
              <el-select v-model="rule.route_mode">
                <el-option label="AI 智能路由" value="ai" />
                <el-option label="指定钉钉用户" value="user" />
                <el-option label="指定员工集合" value="employee_group" />
              </el-select>
            </div>
            <div v-if="rule.route_mode !== 'ai'" class="field compact target-field">
              <label>{{ rule.route_mode === 'user' ? '钉钉用户 ID' : '员工集合 ID' }}</label>
              <el-input v-model="rule.target_id" placeholder="必填" />
            </div>
            <div v-if="rule.route_mode !== 'ai'" class="field compact target-field">
              <label>目标名称</label>
              <el-input v-model="rule.target_name" placeholder="便于识别，可选" />
            </div>
          </div>

          <div v-if="rule.rollout_status !== '基础已就绪'" class="future-note">
            <el-icon><Clock /></el-icon>
            已预留标准配置，待“{{ rule.business_domain }}”业务流程上线后即可开启事件推送。
          </div>
        </article>
      </div>
    </section>

    <section class="panel flow-panel">
      <div class="panel-heading">
        <div class="section-icon flow-icon"><el-icon><Promotion /></el-icon></div>
        <div>
          <h3>联动流程</h3>
          <p>后续各业务模块都按同一条消息链路接入</p>
        </div>
      </div>
      <div class="flow-steps">
        <div class="flow-step"><b>1</b><span><strong>业务事件发生</strong><small>项目、售前、实施、商务、任务</small></span></div>
        <el-icon class="flow-arrow"><Right /></el-icon>
        <div class="flow-step"><b>2</b><span><strong>控制塔标准化</strong><small>补充来源、优先级和业务上下文</small></span></div>
        <el-icon class="flow-arrow"><Right /></el-icon>
        <div class="flow-step"><b>3</b><span><strong>Message Center</strong><small>AI 判断接收人并执行渠道投递</small></span></div>
        <el-icon class="flow-arrow"><Right /></el-icon>
        <div class="flow-step"><b>4</b><span><strong>其他 App 办理</strong><small>消息触达、事件办理与后续流转</small></span></div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Check,
  CircleCheckFilled,
  CircleCloseFilled,
  Clock,
  Connection,
  InfoFilled,
  Key,
  Link,
  Operation,
  Promotion,
  Right,
} from '@element-plus/icons-vue'
import {
  getMessageLinkageConfig,
  testMessageCenterHealth,
  updateMessageLinkageConfig,
  type MessageCenterHealthResult,
  type MessageLinkageConfig,
  type MessageLinkageRule,
} from '@/api/messageLinkage'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const apiKeyInput = ref('')
const apiKeyConfigured = ref(false)
const clearApiKey = ref(false)
const healthResult = ref<MessageCenterHealthResult | null>(null)

const form = reactive<{
  enabled: boolean
  base_url: string
  source_system: string
  timeout_seconds: number
  linkage_rules: MessageLinkageRule[]
}>({
  enabled: false,
  base_url: 'http://message.srun.local:8001',
  source_system: 'ai_project_intelligence',
  timeout_seconds: 10,
  linkage_rules: [],
})

const categoryOptions = [
  { label: '销售', value: 'sales' },
  { label: '需求', value: 'requirement' },
  { label: '支持', value: 'support' },
  { label: '故障', value: 'bug' },
  { label: '通用', value: 'general' },
]

const priorityOptions = [
  { label: '低', value: 'low' },
  { label: '普通', value: 'normal' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'urgent' },
]

const enabledRuleCount = computed(() => form.linkage_rules.filter((item) => item.enabled).length)

function applyConfig(config: MessageLinkageConfig) {
  form.enabled = config.enabled
  form.base_url = config.base_url
  form.source_system = config.source_system
  form.timeout_seconds = config.timeout_seconds
  form.linkage_rules = config.linkage_rules.map((item) => ({ ...item }))
  apiKeyConfigured.value = config.api_key_configured
  apiKeyInput.value = ''
  clearApiKey.value = false
}

function validateForm() {
  if (!/^https?:\/\//i.test(form.base_url.trim())) {
    ElMessage.warning('请填写以 http:// 或 https:// 开头的 Message Center 地址')
    return false
  }
  if (!/^[A-Za-z0-9_-]+$/.test(form.source_system.trim())) {
    ElMessage.warning('来源系统标识只能包含字母、数字、下划线和短横线')
    return false
  }
  if (form.enabled && !apiKeyConfigured.value && !apiKeyInput.value.trim()) {
    ElMessage.warning('启用消息联动前，请填写 Message Center Token')
    return false
  }
  const missingTarget = form.linkage_rules.find(
    (rule) => rule.enabled && rule.route_mode !== 'ai' && !rule.target_id?.trim(),
  )
  if (missingTarget) {
    ElMessage.warning(`${missingTarget.scene_name}采用指定接收方式时，需要填写目标 ID`)
    return false
  }
  return true
}

async function loadConfig() {
  loading.value = true
  try {
    const response = await getMessageLinkageConfig()
    applyConfig(response.data)
  } catch (error) {
    console.error(error)
    ElMessage.error('消息联动配置加载失败')
  } finally {
    loading.value = false
  }
}

async function handleSave(showSuccess: boolean) {
  if (!validateForm()) return false
  saving.value = true
  try {
    const response = await updateMessageLinkageConfig({
      enabled: form.enabled,
      base_url: form.base_url.trim(),
      api_key: apiKeyInput.value.trim() || undefined,
      clear_api_key: clearApiKey.value,
      source_system: form.source_system.trim(),
      timeout_seconds: form.timeout_seconds,
      linkage_rules: form.linkage_rules,
    })
    applyConfig(response.data)
    if (showSuccess) ElMessage.success('消息联动配置已保存')
    return true
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '保存失败，请检查配置')
    return false
  } finally {
    saving.value = false
  }
}

async function handleHealthTest() {
  const saved = await handleSave(false)
  if (!saved) return
  testing.value = true
  healthResult.value = null
  try {
    const response = await testMessageCenterHealth()
    healthResult.value = response.data
    if (response.data.success) ElMessage.success('Message Center 连接正常')
    else ElMessage.warning(response.data.message)
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '连接测试失败')
  } finally {
    testing.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.message-linkage-page { display: flex; flex-direction: column; gap: 18px; max-width: 1500px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }
.title-line { display: flex; align-items: center; gap: 12px; }
.title-line h2 { margin: 0; color: var(--el-text-color-primary); font-size: 26px; }
.page-header p { margin: 8px 0 0; color: var(--el-text-color-secondary); }
.header-actions { display: flex; gap: 10px; flex-shrink: 0; }
.architecture-tip { display: flex; gap: 12px; align-items: flex-start; padding: 14px 18px; border: 1px solid color-mix(in srgb, var(--el-color-primary) 32%, transparent); border-radius: 12px; background: color-mix(in srgb, var(--el-color-primary) 8%, var(--el-bg-color)); color: var(--el-text-color-regular); }
.architecture-tip > .el-icon { margin-top: 2px; color: var(--el-color-primary); font-size: 18px; }
.architecture-tip div { display: flex; flex-direction: column; gap: 4px; line-height: 1.55; }
.panel { padding: 22px; border: 1px solid var(--el-border-color-light); border-radius: 14px; background: var(--el-bg-color); box-shadow: 0 6px 22px rgba(15, 23, 42, .04); }
.panel-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 22px; }
.panel-heading h3 { margin: 0; color: var(--el-text-color-primary); font-size: 18px; }
.panel-heading p { margin: 5px 0 0; color: var(--el-text-color-secondary); font-size: 13px; }
.section-icon { display: grid; place-items: center; width: 40px; height: 40px; flex-shrink: 0; border-radius: 11px; font-size: 20px; }
.connection-icon { color: #2563eb; background: rgba(37, 99, 235, .12); }
.rules-icon { color: #7c3aed; background: rgba(124, 58, 237, .12); }
.flow-icon { color: #059669; background: rgba(5, 150, 105, .12); }
.master-switch, .enabled-count { margin-left: auto; }
.enabled-count { padding: 7px 12px; border-radius: 20px; background: var(--el-fill-color-light); color: var(--el-text-color-secondary); font-size: 13px; }
.connection-grid { display: grid; grid-template-columns: minmax(0, 2fr) minmax(180px, 1fr) 160px; gap: 18px; }
.field { min-width: 0; }
.field-wide { grid-column: span 1; }
.field label { display: flex; align-items: center; gap: 8px; min-height: 24px; margin-bottom: 7px; color: var(--el-text-color-primary); font-size: 14px; font-weight: 600; }
.field small { display: block; margin-top: 7px; color: var(--el-text-color-secondary); line-height: 1.45; }
.field :deep(.el-input-number) { width: 100%; }
.secret-foot { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.secret-foot small { flex: 1; }
.health-result { display: flex; align-items: flex-start; gap: 10px; margin-top: 18px; padding: 13px 15px; border-radius: 10px; }
.health-result > .el-icon { margin-top: 2px; font-size: 20px; }
.health-result div { display: flex; flex-direction: column; gap: 4px; }
.health-result span { font-size: 12px; opacity: .8; word-break: break-all; }
.health-result.is-success { color: var(--el-color-success); background: color-mix(in srgb, var(--el-color-success) 10%, var(--el-bg-color)); }
.health-result.is-error { color: var(--el-color-danger); background: color-mix(in srgb, var(--el-color-danger) 10%, var(--el-bg-color)); }
.rules-heading { margin-bottom: 16px; }
.rule-list { display: flex; flex-direction: column; gap: 12px; }
.rule-card { overflow: hidden; border: 1px solid var(--el-border-color-light); border-left: 4px solid var(--el-border-color); border-radius: 12px; background: var(--el-fill-color-blank); transition: border-color .2s, box-shadow .2s; }
.rule-card.enabled { border-left-color: var(--el-color-success); box-shadow: 0 4px 15px rgba(16, 185, 129, .07); }
.rule-summary { display: flex; align-items: flex-start; gap: 13px; padding: 16px 18px 12px; }
.rule-summary > .el-switch { margin-top: 1px; }
.rule-name { flex: 1; min-width: 0; }
.rule-name > div { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.rule-name strong { color: var(--el-text-color-primary); font-size: 15px; }
.rule-name p { margin: 5px 0 0; color: var(--el-text-color-secondary); font-size: 13px; }
.rule-config { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; padding: 0 18px 16px 53px; }
.field.compact label { margin-bottom: 5px; color: var(--el-text-color-secondary); font-size: 12px; font-weight: 500; }
.field.compact :deep(.el-select) { width: 100%; }
.target-field { grid-column: span 2; }
.future-note { display: flex; align-items: center; gap: 7px; padding: 10px 18px 10px 53px; border-top: 1px dashed var(--el-border-color-light); background: var(--el-fill-color-light); color: var(--el-text-color-secondary); font-size: 12px; }
.flow-steps { display: flex; align-items: stretch; gap: 12px; }
.flow-step { display: flex; align-items: center; gap: 11px; flex: 1; min-width: 0; padding: 14px; border: 1px solid var(--el-border-color-light); border-radius: 10px; background: var(--el-fill-color-light); }
.flow-step b { display: grid; place-items: center; width: 28px; height: 28px; flex-shrink: 0; border-radius: 50%; background: var(--el-color-primary); color: #fff; }
.flow-step span { display: flex; flex-direction: column; min-width: 0; gap: 3px; }
.flow-step strong { color: var(--el-text-color-primary); font-size: 13px; }
.flow-step small { color: var(--el-text-color-secondary); line-height: 1.35; }
.flow-arrow { align-self: center; flex-shrink: 0; color: var(--el-text-color-placeholder); }

@media (max-width: 1100px) {
  .connection-grid { grid-template-columns: 1fr 1fr; }
  .field-wide { grid-column: span 2; }
  .rule-config { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
  .flow-steps { display: grid; grid-template-columns: 1fr 1fr; }
  .flow-arrow { display: none; }
}

@media (max-width: 720px) {
  .page-header { flex-direction: column; }
  .header-actions { width: 100%; }
  .header-actions .el-button { flex: 1; }
  .panel { padding: 16px; }
  .connection-grid, .rule-config, .flow-steps { grid-template-columns: 1fr; }
  .field-wide, .target-field { grid-column: span 1; }
  .panel-heading { align-items: flex-start; }
  .master-switch, .enabled-count { margin-left: 0; }
  .rule-config { padding: 0 14px 14px; }
  .future-note { padding-left: 14px; }
  .secret-foot { flex-direction: column; gap: 4px; }
}
</style>
