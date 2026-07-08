<template>
  <div class="config-container fade-in">
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">⚙️ 系统设置</h2>
        <p class="page-subtitle">系统外观、主题、阈值等系统级配置</p>
      </div>
      <div class="header-actions">
        <el-button @click="handleReset">
          <el-icon><RefreshLeft /></el-icon>
          恢复默认
        </el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          <el-icon><Check /></el-icon>
          保存配置
        </el-button>
      </div>
    </div>

    <div class="config-content" v-loading="loading">
      <!-- 主题外观设置 -->
      <div class="config-section">
        <div class="section-header">
          <div class="section-icon theme">🎨</div>
          <div>
            <h3 class="section-title">主题外观</h3>
            <p class="section-desc">切换系统主题模式（深色 / 浅色）</p>
          </div>
        </div>

        <div class="theme-options">
          <div
            class="theme-card"
            :class="{ active: themeStore.isDark }"
            @click="themeStore.setTheme('dark')"
          >
            <div class="theme-preview dark-preview">
              <div class="preview-sidebar"></div>
              <div class="preview-content">
                <div class="preview-bar"></div>
                <div class="preview-block"></div>
                <div class="preview-block"></div>
              </div>
            </div>
            <div class="theme-info">
              <el-icon class="theme-icon"><Moon /></el-icon>
              <div class="theme-name">深色模式</div>
              <div class="theme-desc">适合长时间使用，护眼省电</div>
            </div>
            <el-icon v-if="themeStore.isDark" class="theme-check"><CircleCheckFilled /></el-icon>
          </div>

          <div
            class="theme-card"
            :class="{ active: !themeStore.isDark }"
            @click="themeStore.setTheme('light')"
          >
            <div class="theme-preview light-preview">
              <div class="preview-sidebar"></div>
              <div class="preview-content">
                <div class="preview-bar"></div>
                <div class="preview-block"></div>
                <div class="preview-block"></div>
              </div>
            </div>
            <div class="theme-info">
              <el-icon class="theme-icon"><Sunny /></el-icon>
              <div class="theme-name">浅色模式</div>
              <div class="theme-desc">明亮清晰，适合白天办公</div>
            </div>
            <el-icon v-if="!themeStore.isDark" class="theme-check"><CircleCheckFilled /></el-icon>
          </div>
        </div>

        <div class="theme-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>主题设置会保存到本地，刷新页面后依然生效</span>
        </div>
      </div>

      <!-- 战略层阈值 -->
      <div class="config-section">
        <div class="section-header">
          <div class="section-icon strategic">🎯</div>
          <div>
            <h3 class="section-title">战略层阈值</h3>
            <p class="section-desc">控制驾驶舱反直觉指标（僵尸项目、假性推进、沉没渠道）的判定标准</p>
          </div>
        </div>
        <div class="config-grid">
          <div class="config-item">
            <label class="config-label">
              僵尸项目天数
              <el-tooltip content="项目超过多少天没有任何活动则判定为僵尸项目" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.zombie_project_days" :min="1" :max="365" />
            <span class="config-unit">天</span>
            <p class="config-tip">用于统计「无活动项目数」指标</p>
          </div>

          <div class="config-item">
            <label class="config-label">
              假性推进连续次数
              <el-tooltip content="最近N次活动均为「等待客户反馈」则判定为假性推进" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.fake_progress_count" :min="2" :max="10" />
            <span class="config-unit">次</span>
            <p class="config-tip">连续等待客户反馈多少次后触发预警</p>
          </div>

          <div class="config-item">
            <label class="config-label">
              沉没渠道天数
              <el-tooltip content="渠道超过多少天无任何活动则判定为沉没渠道" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.sunk_channel_days" :min="1" :max="365" />
            <span class="config-unit">天</span>
            <p class="config-tip">影响统计中的「沉没渠道」指标</p>
          </div>
        </div>
      </div>

      <!-- 战术层阈值 -->
      <div class="config-section">
        <div class="section-header">
          <div class="section-icon tactical">⚔️</div>
          <div>
            <h3 class="section-title">战术层阈值</h3>
            <p class="section-desc">控制战术层关注事项（验收超时、渠道沉没）的判定</p>
          </div>
        </div>
        <div class="config-grid">
          <div class="config-item">
            <label class="config-label">
              战术层渠道沉没预警天数
              <el-tooltip content="战术层关注的渠道无联系天数阈值（建议大于战略层）" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.sunk_channel_warning_days" :min="1" :max="365" />
            <span class="config-unit">天</span>
            <p class="config-tip">影响「渠道沉没预警」列表</p>
          </div>
        </div>
      </div>

      <!-- 执行层阈值 -->
      <div class="config-section">
        <div class="section-header">
          <div class="section-icon execution">🎬</div>
          <div>
            <h3 class="section-title">执行层阈值</h3>
            <p class="section-desc">控制执行层关注事项（今日跟进、等待反馈）的展示</p>
          </div>
        </div>
        <div class="config-grid">
          <div class="config-item">
            <label class="config-label">
              今日跟进项目数限制
              <el-tooltip content="执行层显示的最大跟进项目数" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.today_followup_limit" :min="1" :max="50" />
            <span class="config-unit">个</span>
            <p class="config-tip">避免列表过长影响阅读</p>
          </div>
        </div>
      </div>

      <!-- 预警规则阈值 -->
      <div class="config-section">
        <div class="section-header">
          <div class="section-icon warning">⚠️</div>
          <div>
            <h3 class="section-title">预警规则阈值</h3>
            <p class="section-desc">控制预警中心各规则（R001-R007）的触发条件</p>
          </div>
        </div>
        <div class="config-grid">
          <div class="config-item">
            <label class="config-label">
              R001 无跟进预警
              <el-tooltip content="R001: 项目超过此天数无活动触发预警" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.no_activity_warning_days" :min="1" :max="90" />
            <span class="config-unit">天</span>
            <p class="config-tip">R001规则的天数阈值</p>
          </div>

          <div class="config-item">
            <label class="config-label">
              R003 POC超时
              <el-tooltip content="R003: 项目在POC阶段停留超过此天数触发预警" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.poc_overdue_days" :min="1" :max="365" />
            <span class="config-unit">天</span>
            <p class="config-tip">R003规则的天数阈值</p>
          </div>

          <div class="config-item">
            <label class="config-label">
              R002 验收超时
              <el-tooltip content="R002: 项目在验收阶段停留超过此天数触发预警" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.acceptance_overdue_days" :min="1" :max="365" />
            <span class="config-unit">天</span>
            <p class="config-tip">R002规则的天数阈值</p>
          </div>

          <div class="config-item">
            <label class="config-label">
              R007 长期未验收
              <el-tooltip content="R007: 项目计划验收时间已过期超过此天数仍未验收" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.acceptance_plan_overdue_days" :min="1" :max="730" />
            <span class="config-unit">天</span>
            <p class="config-tip">R007规则的天数阈值</p>
          </div>

          <div class="config-item">
            <label class="config-label">
              R004 报价无进展
              <el-tooltip content="R004: 报价后超过此天数未形成项目触发预警" placement="top">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </label>
            <el-input-number v-model="form.quote_no_progress_days" :min="1" :max="365" />
            <span class="config-unit">天</span>
            <p class="config-tip">R004规则的天数阈值</p>
          </div>
        </div>
      </div>

      <!-- 判断逻辑说明 -->
      <div class="config-section">
        <div class="section-header">
          <div class="section-icon logic">📋</div>
          <div>
            <h3 class="section-title">判断逻辑说明</h3>
            <p class="section-desc">系统当前各指标的判断逻辑</p>
          </div>
        </div>

        <el-collapse v-model="activeNames">
          <el-collapse-item title="🎯 战略层逻辑" name="strategic">
            <ul class="logic-list">
              <li><strong>总项目数</strong>：数据库中所有项目数量（不限状态）</li>
              <li><strong>进行中项目数</strong>：状态为「进行中」的项目数量</li>
              <li><strong>风险项目数</strong>：风险等级为「高」或「严重风险」的项目数量</li>
              <li><strong>月新增/验收项目数</strong>：当月新增/验收的项目数量</li>
              <li><strong>僵尸项目数</strong>：超过 {{ form.zombie_project_days }} 天无任何活动的进行中项目</li>
              <li><strong>假性推进项目数</strong>：最近 {{ form.fake_progress_count }} 次活动均为「等待客户反馈」的项目</li>
              <li><strong>沉没渠道数</strong>：超过 {{ form.sunk_channel_days }} 天无联系的活跃渠道</li>
            </ul>
          </el-collapse-item>

          <el-collapse-item title="⚔️ 战术层逻辑" name="tactical">
            <ul class="logic-list">
              <li><strong>验收超时项目</strong>：项目计划验收日期已过且未验收，按超期天数倒序</li>
              <li><strong>渠道沉没预警</strong>：超过 {{ form.sunk_channel_warning_days }} 天无联系的渠道，按失联天数倒序</li>
            </ul>
          </el-collapse-item>

          <el-collapse-item title="🎬 执行层逻辑" name="execution">
            <ul class="logic-list">
              <li><strong>今日需跟进项目</strong>：项目活动日志中存在「下一步动作」且项目仍在进行中，按风险等级排序，最多展示 {{ form.today_followup_limit }} 个</li>
              <li><strong>等待客户反馈超时</strong>：项目活动的「下一步动作截止日期」已超期，按等待天数倒序</li>
            </ul>
          </el-collapse-item>

          <el-collapse-item title="⚠️ 预警中心逻辑" name="warning">
            <ul class="logic-list">
              <li><strong>R001 无跟进预警</strong>：进行中项目超过 {{ form.no_activity_warning_days }} 天无活动</li>
              <li><strong>R002 验收阶段超时</strong>：在「验收」阶段停留超过 {{ form.acceptance_overdue_days }} 天</li>
              <li><strong>R003 POC阶段超时</strong>：在「POC」阶段停留超过 {{ form.poc_overdue_days }} 天</li>
              <li><strong>R004 报价无进展</strong>：报价后超过 {{ form.quote_no_progress_days }} 天未形成项目</li>
              <li><strong>R005 渠道沉没</strong>：活跃渠道无联系超过 {{ form.sunk_channel_warning_days }} 天</li>
              <li><strong>R006 假性推进</strong>：最近 {{ form.fake_progress_count }} 次活动均为「等待客户反馈」</li>
              <li><strong>R007 长期未验收</strong>：计划验收时间已过期超过 {{ form.acceptance_plan_overdue_days }} 天仍未验收</li>
            </ul>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, RefreshLeft, QuestionFilled, Moon, Sunny, CircleCheckFilled, InfoFilled } from '@element-plus/icons-vue'
import { getThresholds, updateThresholds, resetThresholds, DashboardThresholds } from '@/api/config'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

const loading = ref(false)
const saving = ref(false)
const activeNames = ref(['strategic', 'tactical', 'execution', 'warning'])

const form = reactive<DashboardThresholds>({
  zombie_project_days: 30,
  fake_progress_count: 3,
  sunk_channel_days: 60,
  overdue_acceptance_days: 0,
  sunk_channel_warning_days: 90,
  waiting_too_long_days: 0,
  today_followup_limit: 10,
  poc_overdue_days: 60,
  acceptance_overdue_days: 30,
  acceptance_plan_overdue_days: 180,
  no_activity_warning_days: 7,
  quote_no_progress_days: 90,
})

async function loadThresholds() {
  loading.value = true
  try {
    const res = await getThresholds()
    Object.assign(form, res.data)
  } catch (error: any) {
    ElMessage.error(error.message || '加载配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const res = await updateThresholds(form)
    Object.assign(form, res.data)
    ElMessage.success('配置保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleReset() {
  try {
    await ElMessageBox.confirm('确定要恢复所有阈值为默认值吗？', '确认重置', {
      type: 'warning',
    })
    const res = await resetThresholds()
    Object.assign(form, res.data)
    ElMessage.success('已恢复默认配置')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '重置失败')
    }
  }
}

onMounted(() => {
  loadThresholds()
})
</script>

<style scoped>
.config-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  height: calc(100vh - 80px);
  overflow-y: auto;
  background: var(--bg-primary);
  color: var(--text-primary);
}

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
  color: var(--text-muted);
  font-size: 14px;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  transition: all 0.3s;
}

.config-section:hover {
  border-color: var(--border-color-hover);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.section-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.section-icon.strategic {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

.section-icon.tactical {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.section-icon.execution {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
}

.section-icon.warning {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.section-icon.logic {
  background: linear-gradient(135deg, #10b981, #059669);
}

.section-icon.theme {
  background: linear-gradient(135deg, #ec4899, #d946ef);
}

.section-title {
  font-size: 18px;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.section-desc {
  color: var(--text-tertiary);
  font-size: 13px;
  margin: 0;
}

/* ============ 主题切换样式 ============ */

.theme-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.theme-card {
  position: relative;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-card:hover {
  border-color: var(--accent-color);
  transform: translateY(-2px);
}

.theme-card.active {
  border-color: var(--accent-color);
  background: rgba(59, 130, 246, 0.08);
}

.theme-preview {
  display: flex;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
  border: 1px solid var(--border-color);
}

.dark-preview .preview-sidebar {
  width: 25%;
  background: #1e2128;
}

.dark-preview .preview-content {
  flex: 1;
  background: #1a1d23;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dark-preview .preview-bar {
  height: 8px;
  background: #2a2d35;
  border-radius: 2px;
}

.dark-preview .preview-block {
  flex: 1;
  background: #2a2d35;
  border-radius: 4px;
}

.light-preview .preview-sidebar {
  width: 25%;
  background: #f3f4f6;
}

.light-preview .preview-content {
  flex: 1;
  background: #ffffff;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.light-preview .preview-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 2px;
}

.light-preview .preview-block {
  flex: 1;
  background: #f9fafb;
  border-radius: 4px;
}

.theme-info {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.theme-icon {
  font-size: 20px;
  color: var(--accent-color);
  flex-shrink: 0;
  margin-top: 2px;
}

.theme-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.theme-desc {
  font-size: 12px;
  color: var(--text-tertiary);
}

.theme-check {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 20px;
  color: var(--accent-color);
}

.theme-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.theme-tip .el-icon {
  color: var(--accent-color);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.config-item {
  background: var(--bg-tertiary);
  border-radius: 8px;
  padding: 16px;
}

.config-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 12px;
  font-weight: 500;
}

.help-icon {
  color: var(--text-muted);
  cursor: help;
}

.config-unit {
  margin-left: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.config-tip {
  margin: 8px 0 0 0;
  color: var(--text-muted);
  font-size: 12px;
}

.logic-list {
  list-style: none;
  padding: 0;
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 2;
}

.logic-list li {
  padding: 4px 0;
}

.logic-list strong {
  color: var(--accent-color);
  margin-right: 4px;
}

/* 折叠面板主题适配 */
:deep(.el-collapse) {
  --el-collapse-border-color: var(--border-color);
  background: transparent;
  border: none;
}

:deep(.el-collapse-item) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

:deep(.el-collapse-item__header) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 500;
  border-bottom: 1px solid transparent;
  padding: 0 16px;
  height: 48px;
  line-height: 48px;
}

:deep(.el-collapse-item__header:hover) {
  background: var(--bg-hover);
}

:deep(.el-collapse-item__arrow) {
  color: var(--text-tertiary);
}

:deep(.el-collapse-item__wrap) {
  background: var(--bg-tertiary);
  border: none;
}

:deep(.el-collapse-item__content) {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  padding: 8px 16px 16px;
}

:deep(.el-collapse-item.is-active > .el-collapse-item__header) {
  border-bottom-color: var(--border-color);
  background: var(--bg-hover);
}

:deep(.el-input-number) {
  width: 160px;
}

:deep(.el-input-number .el-input__wrapper) {
  background: var(--bg-secondary);
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

:deep(.el-input-number .el-input__inner) {
  color: var(--text-primary);
}
</style>
