<template>
  <div class="dashboard-container fade-in">
    <!-- 层级切换 Tabs -->
    <div class="layer-tabs">
      <el-radio-group v-model="currentLayer" size="large">
        <el-radio-button label="strategic">🎯 战略层</el-radio-button>
        <el-radio-button label="tactical">⚡ 战术层</el-radio-button>
        <el-radio-button label="execution">📋 执行层</el-radio-button>
      </el-radio-group>
    </div>

    <div class="data-trust-panel">
      <div class="data-trust-item">
        <span>业务数据截止</span>
        <strong>{{ formatDateTime(dataQuality.latestActivityAt) }}</strong>
      </div>
      <div class="data-trust-item">
        <span>最近入库时间</span>
        <strong>{{ formatDateTime(dataQuality.latestIngestionAt) }}</strong>
      </div>
      <div class="data-trust-item">
        <span>项目活动覆盖</span>
        <strong>{{ dataQuality.coveredProjects }}/{{ dataQuality.totalProjects }}（{{ dataQuality.coveragePercentage }}%）</strong>
      </div>
      <div class="data-trust-item">
        <span>日报进入时间轴</span>
        <strong>{{ dataQuality.importedReports }}/{{ dataQuality.rawReports }}</strong>
      </div>
      <div class="data-trust-item warning">
        <span>待人工匹配</span>
        <strong>{{ dataQuality.pendingReports }}</strong>
      </div>
      <div class="data-trust-item">
        <span>邮件情报</span>
        <strong>{{ dataQuality.emailMessages }}</strong>
      </div>
      <div class="data-trust-item">
        <span>日报同步</span>
        <strong>{{ dataQuality.latestSyncStatus || '暂无记录' }} · {{ formatDateTime(dataQuality.latestSyncAt) }}</strong>
      </div>
    </div>
    <el-alert
      v-if="dataQuality.rawReports > 0 && dataQuality.coveragePercentage < 80"
      class="coverage-alert"
      type="warning"
      :closable="false"
      show-icon
      :title="`当前仅 ${dataQuality.coveragePercentage}% 的项目有活动数据；另有 ${dataQuality.pendingReports} 条日报待匹配，驾驶舱结论仅代表已确认数据。`"
    />

    <!-- 战略层：CEO/VP 视角 -->
    <div v-if="currentLayer === 'strategic'" class="layer-content">
      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card" v-for="stat in statistics" :key="stat.title">
          <div class="stat-icon" :style="{ background: stat.gradient }">
            {{ stat.icon }}
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-title">{{ stat.title }}</div>
          </div>
        </div>
      </div>

      <!-- 反直觉指标 -->
      <div class="counter-intuitive-cards">
        <div class="counter-card zombie">
          <div class="counter-icon">🧟</div>
          <div class="counter-value">{{ counterIntuitive.zombieProjects }}</div>
          <div class="counter-label">僵尸项目（{{ thresholds.zombie_project_days }}天无活动）</div>
        </div>
        <div class="counter-card fake">
          <div class="counter-icon">🎭</div>
          <div class="counter-value">{{ counterIntuitive.fakeProgress }}</div>
          <div class="counter-label">假性推进项目</div>
        </div>
        <div class="counter-card sunk">
          <div class="counter-icon">📉</div>
          <div class="counter-value">{{ counterIntuitive.sunkChannels }}</div>
          <div class="counter-label">沉没渠道（{{ thresholds.sunk_channel_days }}天无有效联系）</div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <div class="chart-card">
          <div class="chart-header">
            <h3>项目阶段分布</h3>
          </div>
          <div ref="stageChartRef" class="chart-body"></div>
        </div>
        
        <div class="chart-card">
          <div class="chart-header">
            <h3>国家分布</h3>
          </div>
          <div ref="countryChartRef" class="chart-body"></div>
        </div>
        
        <div class="chart-card">
          <div class="chart-header">
            <h3>渠道关联项目 TOP10（金额数据未维护）</h3>
          </div>
          <div ref="channelChartRef" class="chart-body"></div>
        </div>
        
        <div class="chart-card">
          <div class="chart-header">
            <h3>风险项目 TOP10</h3>
          </div>
          <div class="chart-body">
            <div class="risk-list">
              <div class="risk-item" v-for="(project, idx) in riskTop10" :key="project.project_id" @click="goToProject(project.project_id)">
                <div class="risk-rank">{{ idx + 1 }}</div>
                <div class="risk-info">
                  <div class="risk-name">{{ project.project_name }}</div>
                  <div class="risk-meta">
                    <span>{{ project.country }}</span>
                    <span>卡点：{{ project.blocker }}</span>
                  </div>
                </div>
                <div class="risk-days">阶段{{ project.days_stuck }}天</div>
              </div>
              <el-empty v-if="riskTop10.length === 0" description="暂无按活动时效计算的风险项目" :image-size="72" />
            </div>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <h3>30天项目情报趋势（从P2启用日起积累）</h3>
          </div>
          <div ref="trendChartRef" class="chart-body"></div>
        </div>

        <div class="chart-card management-insight-card">
          <div class="chart-header">
            <h3>管理建议（每条均附数据依据）</h3>
          </div>
          <div class="chart-body insight-list">
            <div
              v-for="insight in managementInsights"
              :key="insight.insight_id"
              class="insight-item"
              :class="insight.priority"
              @click="openInsight(insight)"
            >
              <div class="insight-priority">{{ insightPriorityLabel(insight.priority) }}</div>
              <div class="insight-main">
                <strong>{{ insight.title }}</strong>
                <p>{{ insight.reason }}</p>
                <span>建议：{{ insight.recommendation }}</span>
                <small>依据：{{ insight.evidence_source }} · {{ formatDateTime(insight.evidence_at) }}</small>
              </div>
            </div>
            <el-empty v-if="managementInsights.length === 0" description="暂无管理建议" :image-size="72" />
          </div>
        </div>
      </div>
    </div>

    <!-- 战术层：总监/PMO 视角 -->
    <div v-if="currentLayer === 'tactical'" class="layer-content">
      <div class="tactical-grid">
        <div class="tactical-card">
          <div class="tactical-header">
            <h3>📊 项目阶段分布（按业务顺序，非转化率）</h3>
          </div>
          <div ref="funnelChartRef" class="tactical-body"></div>
        </div>

        <div class="tactical-card">
          <div class="tactical-header">
            <h3>🎯 项目关注矩阵（按风险与无活动天数排序）</h3>
          </div>
          <div class="tactical-body attention-table-wrap">
            <el-table :data="attentionProjects" style="width: 100%" empty-text="暂无需要管理介入的项目" @row-click="openAttentionProject">
              <el-table-column prop="project_name" label="项目" min-width="180" show-overflow-tooltip />
              <el-table-column label="健康度" width="100">
                <template #default="scope">
                  <el-tag :type="healthTagType(scope.row.health_status)" effect="dark">{{ scope.row.health_status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="current_stage" label="阶段" width="90" />
              <el-table-column prop="stage_days" label="阶段天数" width="90" />
              <el-table-column prop="inactivity_days" label="无活动" width="90">
                <template #default="scope">{{ scope.row.inactivity_days }}天</template>
              </el-table-column>
              <el-table-column prop="attention_reason" label="关注依据" min-width="220" show-overflow-tooltip />
              <el-table-column prop="next_action" label="下一步" min-width="130">
                <template #default="scope">{{ scope.row.next_action || '尚未提取' }}</template>
              </el-table-column>
              <el-table-column prop="owner_name" label="负责人" width="110" />
            </el-table>
          </div>
        </div>
        
        <div class="tactical-card">
          <div class="tactical-header">
            <h3>⚠️ 验收超时项目（基于计划验收日期）</h3>
          </div>
          <div class="tactical-body">
            <el-table :data="overdueProjects" style="width: 100%" empty-text="暂无数据：项目尚未维护计划验收日期，无法判断是否超时">
              <el-table-column prop="project_name" label="项目名称" />
              <el-table-column prop="current_stage" label="当前阶段" />
              <el-table-column prop="days_overdue" label="超时天数" />
              <el-table-column prop="owner_name" label="负责人" />
            </el-table>
          </div>
        </div>
        
        <div class="tactical-card">
          <div class="tactical-header">
            <h3>🔍 渠道沉没预警（超过{{ thresholds.sunk_channel_warning_days }}天无有效联系）</h3>
          </div>
          <div class="tactical-body">
            <el-table :data="sunkChannels" style="width: 100%" empty-text="暂无达到阈值的沉没渠道">
              <el-table-column prop="channel_name" label="渠道名称" />
              <el-table-column prop="country" label="国家" />
              <el-table-column prop="days_since_last_contact" label="失联天数" />
              <el-table-column prop="total_projects" label="历史项目数" />
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <!-- 执行层：项目经理视角 -->
    <div v-if="currentLayer === 'execution'" class="layer-content">
      <div class="execution-grid">
        <div class="execution-card">
          <div class="execution-header">
            <h3>📅 今日需跟进项目</h3>
          </div>
          <div class="execution-body">
            <div class="project-item" v-for="project in todayFollowups" :key="project.project_id">
              <div class="project-priority" :class="project.priority"></div>
              <div class="project-info">
                <div class="project-name">{{ project.project_name }}</div>
                <div class="project-next-action">{{ project.next_action }}</div>
              </div>
              <el-button size="small" type="primary" @click="goToProject(project.project_id)">
                查看
              </el-button>
            </div>
            <el-empty v-if="todayFollowups.length === 0" description="暂无数据：当前活动尚未提取下一步动作" :image-size="72" />
          </div>
        </div>

        <div class="execution-card">
          <div class="execution-header">
            <h3>✉️ 客户邮件等待回复</h3>
          </div>
          <div class="execution-body">
            <el-table :data="waitingEmailThreads" style="width: 100%" empty-text="暂无数据：邮箱未配置或没有达到等待阈值的外发线程" @row-click="openWaitingEmailProject">
              <el-table-column prop="project_name" label="项目" min-width="130" show-overflow-tooltip />
              <el-table-column prop="subject" label="邮件主题" min-width="180" show-overflow-tooltip />
              <el-table-column prop="waiting_days" label="等待" width="80">
                <template #default="scope">{{ scope.row.waiting_days }}天</template>
              </el-table-column>
            </el-table>
          </div>
        </div>
        
        <div class="execution-card">
          <div class="execution-header">
            <h3>⏰ 等待客户反馈超时</h3>
          </div>
          <div class="execution-body">
            <el-table :data="waitingTooLong" style="width: 100%" empty-text="暂无数据：当前活动尚未提取截止日期">
              <el-table-column prop="project_name" label="项目名称" />
              <el-table-column prop="next_action" label="等待事项" />
              <el-table-column prop="days_waiting" label="等待天数" />
            </el-table>
          </div>
        </div>
        
        <div class="execution-card">
          <div class="execution-header">
            <h3>📝 近期活动流</h3>
          </div>
          <div class="execution-body">
            <div class="activity-timeline">
              <div class="activity-item" v-for="activity in recentActivities" :key="activity.id">
                <div class="activity-dot" :class="activity.activity_type"></div>
                <div class="activity-content">
                  <div class="activity-text">{{ activity.activity_content }}</div>
                  <div class="activity-meta">
                    <span class="activity-project">{{ activity.project_name || '未关联项目' }}</span>
                    <span class="activity-source">{{ activity.source || '未知来源' }}</span>
                    <span>{{ activity.owner_name }}</span>
                    <span>{{ formatDate(activity.occurred_at) }}</span>
                  </div>
                </div>
              </div>
              <el-empty v-if="recentActivities.length === 0" description="暂无已确认的项目活动" :image-size="72" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getDashboardSummary, getStageDistribution, getRiskTop10, getCountryDistribution, getChannelContribution, getRecentActivities, getOverdueProjects, getSunkChannels, getAttentionProjects, getTodayFollowups, getWaitingTooLong, getIntelligenceTrends, getWaitingEmailThreads, getManagementInsights } from '@/api/dashboard'
import { getThresholds, type DashboardThresholds } from '@/api/config'

const router = useRouter()

// 当前层级
const currentLayer = ref('strategic')

interface RiskProject {
  project_id: string
  project_name: string
  country?: string
  blocker: string
  days_stuck: number
  risk_level: string
}

const thresholds = ref<DashboardThresholds>({
  zombie_project_days: 30,
  fake_progress_count: 3,
  sunk_channel_days: 60,
  overdue_acceptance_days: 0,
  sunk_channel_warning_days: 90,
  waiting_too_long_days: 0,
  email_waiting_reply_days: 3,
  today_followup_limit: 10,
  poc_overdue_days: 60,
  acceptance_overdue_days: 30,
  acceptance_plan_overdue_days: 180,
  no_activity_warning_days: 7,
  quote_no_progress_days: 90,
})

const dataQuality = ref({
  latestActivityAt: '',
  latestIngestionAt: '',
  latestSyncAt: '',
  latestSyncStatus: '',
  coveredProjects: 0,
  totalProjects: 0,
  coveragePercentage: 0,
  rawReports: 0,
  importedReports: 0,
  pendingReports: 0,
  emailMessages: 0,
})

// 统计数据
const statistics = ref([
  { title: '项目总数', value: 0, icon: '📊', gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { title: '进行中项目', value: 0, icon: '🚀', gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { title: '风险项目', value: 0, icon: '⚠️', gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
  { title: '本月验收项目', value: 0, icon: '✅', gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' },
  { title: '本月新增项目', value: 0, icon: '🆕', gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' },
])

// 反直觉指标
const counterIntuitive = ref({
  zombieProjects: 0,
  fakeProgress: 0,
  sunkChannels: 0,
})

// 风险 TOP10
const riskTop10 = ref<RiskProject[]>([])

// 图表引用
const stageChartRef = ref<HTMLElement>()
const countryChartRef = ref<HTMLElement>()
const channelChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const funnelChartRef = ref<HTMLElement>()

// 战术层数据
const overdueProjects = ref([])
const sunkChannels = ref([])
const attentionProjects = ref([])

// 执行层数据
const todayFollowups = ref([])
const waitingTooLong = ref([])
const waitingEmailThreads = ref([])
const recentActivities = ref([])
const managementInsights = ref<any[]>([])

// 加载数据
async function loadData() {
  try {
    const [summaryRes, riskRes, activitiesRes, thresholdsRes, insightRes] = await Promise.all([
      getDashboardSummary(),
      getRiskTop10(),
      getRecentActivities(10),
      getThresholds(),
      getManagementInsights(),
    ])
    const summary = summaryRes.data
    thresholds.value = thresholdsRes.data || thresholds.value
    
    // 后端返回 snake_case 格式字段名
    statistics.value[0].value = summary.total_projects ?? 0
    statistics.value[1].value = summary.in_progress_projects ?? 0
    statistics.value[2].value = summary.risk_projects ?? 0
    statistics.value[3].value = summary.monthly_acceptance_projects ?? 0
    statistics.value[4].value = summary.monthly_new_projects ?? 0
    
    counterIntuitive.value.zombieProjects = summary.zombie_projects ?? 0
    counterIntuitive.value.fakeProgress = summary.fake_progress_projects ?? 0
    counterIntuitive.value.sunkChannels = summary.inactive_channels ?? 0

    dataQuality.value = {
      latestActivityAt: summary.latest_activity_at || '',
      latestIngestionAt: summary.latest_ingestion_at || '',
      latestSyncAt: summary.latest_daily_sync_at || '',
      latestSyncStatus: summary.latest_daily_sync_status || '',
      coveredProjects: summary.activity_covered_projects ?? 0,
      totalProjects: summary.total_projects ?? 0,
      coveragePercentage: summary.activity_coverage_percentage ?? 0,
      rawReports: summary.daily_report_raw_count ?? 0,
      importedReports: summary.daily_report_imported_count ?? 0,
      pendingReports: summary.daily_report_pending_match_count ?? 0,
      emailMessages: summary.email_message_count ?? 0,
    }
    riskTop10.value = riskRes.data || []
    recentActivities.value = activitiesRes.data || []
    managementInsights.value = insightRes.data || []
    
  } catch (error) {
    console.error('加载驾驶舱数据失败', error)
  }
}

// 初始化图表
async function initCharts() {
  await nextTick()
  
  if (currentLayer.value === 'strategic') {
    // 阶段分布图
    if (stageChartRef.value) {
      const chart = echarts.getInstanceByDom(stageChartRef.value) || echarts.init(stageChartRef.value)
      const stageData = await getStageDistribution()
      // 后端返回的 data 包含 items 字段，需要提取并转换格式
      const pieData = (stageData.data?.items || []).map((item: any) => ({
        name: item.stage,
        value: item.count,
      }))
      
      chart.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, textStyle: { color: '#9ca3af' } },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          data: pieData,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#1e2128',
            borderWidth: 2,
          },
        }],
        color: ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1'],
      })
    }
    
    // 国家分布图
    if (countryChartRef.value) {
      const chart = echarts.getInstanceByDom(countryChartRef.value) || echarts.init(countryChartRef.value)
      const countryData = await getCountryDistribution()
      
      chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0, textStyle: { color: '#9ca3af' } },
        xAxis: {
          type: 'category',
          data: countryData.data.map((item: any) => item.country),
          axisLabel: { color: '#9ca3af' },
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#9ca3af' },
          splitLine: { lineStyle: { color: '#363b47' } },
        },
        series: [
          {
            name: '项目数',
            type: 'bar',
            data: countryData.data.map((item: any) => item.project_count),
            itemStyle: { color: '#3b82f6', borderRadius: [6, 6, 0, 0] },
          },
          {
            name: '风险项目',
            type: 'bar',
            data: countryData.data.map((item: any) => item.risk_count),
            itemStyle: { color: '#ef4444', borderRadius: [6, 6, 0, 0] },
          },
        ],
      })
    }

    // 渠道贡献图：当前金额和中标率数据尚未维护，先用真实关联项目数展示。
    if (channelChartRef.value) {
      const chart = echarts.getInstanceByDom(channelChartRef.value) || echarts.init(channelChartRef.value)
      const channelData = await getChannelContribution()
      const items = channelData.data || []
      chart.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 24, right: 24, top: 12, bottom: 24, containLabel: true },
        xAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: '#9ca3af' },
          splitLine: { lineStyle: { color: '#363b47' } },
        },
        yAxis: {
          type: 'category',
          inverse: true,
          data: items.map((item: any) => item.channel_name),
          axisLabel: { color: '#9ca3af' },
        },
        series: [{
          name: '关联项目数',
          type: 'bar',
          data: items.map((item: any) => item.project_count),
          itemStyle: { color: '#8b5cf6', borderRadius: [0, 6, 6, 0] },
          label: { show: true, position: 'right', color: '#d1d5db' },
        }],
        graphic: items.length === 0 ? [{
          type: 'text', left: 'center', top: 'middle',
          style: { text: '暂无渠道关联数据', fill: '#9ca3af', fontSize: 14 },
        }] : [],
      })
    }

    if (trendChartRef.value) {
      const chart = echarts.getInstanceByDom(trendChartRef.value) || echarts.init(trendChartRef.value)
      const trendRes = await getIntelligenceTrends(30)
      const items = trendRes.data || []
      chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0, textStyle: { color: '#9ca3af' } },
        grid: { left: 42, right: 24, top: 30, bottom: 50 },
        xAxis: {
          type: 'category',
          data: items.map((item: any) => item.snapshot_date.slice(5)),
          axisLabel: { color: '#9ca3af' },
        },
        yAxis: {
          type: 'value', minInterval: 1,
          axisLabel: { color: '#9ca3af' },
          splitLine: { lineStyle: { color: '#363b47' } },
        },
        series: [
          { name: '风险项目', type: 'line', smooth: true, data: items.map((item: any) => item.risk_project_count), itemStyle: { color: '#ef4444' } },
          { name: '有活动覆盖', type: 'line', smooth: true, data: items.map((item: any) => item.covered_project_count), itemStyle: { color: '#10b981' } },
          { name: '活跃预警', type: 'line', smooth: true, data: items.map((item: any) => item.active_warning_count), itemStyle: { color: '#f59e0b' } },
        ],
        graphic: items.length <= 1 ? [{
          type: 'text', right: 18, top: 10,
          style: { text: items.length ? '已建立首日基线，趋势将按日积累' : '尚未生成项目情报快照', fill: '#9ca3af', fontSize: 12 },
        }] : [],
      })
    }
  }
}

// 跳转项目详情
function goToProject(id: string) {
  router.push(`/projects/${id}`)
}

// 格式化日期
function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function formatDateTime(dateStr?: string) {
  if (!dateStr) return '暂无数据'
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 加载战术层数据
async function loadTacticalData() {
  try {
    const [overdueRes, sunkRes, attentionRes] = await Promise.all([
      getOverdueProjects(),
      getSunkChannels(),
      getAttentionProjects(),
    ])
    overdueProjects.value = overdueRes.data || []
    sunkChannels.value = sunkRes.data || []
    attentionProjects.value = attentionRes.data || []
  } catch (error) {
    console.error('加载战术层数据失败', error)
  }
}

function openAttentionProject(row: any) {
  if (row?.project_id) goToProject(row.project_id)
}

function healthTagType(healthStatus: string) {
  if (healthStatus === '严重风险') return 'danger'
  if (healthStatus === '风险') return 'warning'
  if (healthStatus === '关注') return 'info'
  return 'success'
}

function openInsight(insight: any) {
  if (insight?.project_id) goToProject(insight.project_id)
}

function insightPriorityLabel(priority: string) {
  if (priority === 'high') return '高优先'
  if (priority === 'medium') return '需关注'
  return '提示'
}

function openWaitingEmailProject(row: any) {
  if (row?.project_id) goToProject(row.project_id)
}

// 漏斗图实例
let funnelChartInstance: any = null

// 初始化漏斗图
async function initFunnelChart() {
  await nextTick()
  
  if (!funnelChartRef.value) return
  
  // 先获取数据
  const stageData = await getStageDistribution()
  // 将阶段分布数据转换为漏斗图格式，过滤掉 count 为 0 的阶段
  const funnelData = (stageData.data?.items || [])
    .filter((item: any) => item.count > 0)
    .map((item: any) => ({
      name: item.stage,
      value: item.count,
    }))
  
  // 销毁旧实例
  if (funnelChartInstance) {
    funnelChartInstance.dispose()
    funnelChartInstance = null
  }
  
  funnelChartInstance = echarts.init(funnelChartRef.value)
  
  funnelChartInstance.setOption({
    tooltip: { 
      trigger: 'item',
      formatter: '{b}: {c}个项目 ({d}%)'
    },
    legend: { 
      bottom: 0, 
      textStyle: { color: '#9ca3af' },
      orient: 'horizontal'
    },
    series: [{
      type: 'funnel',
      left: '10%',
      top: '10%',
      bottom: '15%',
      width: '80%',
      min: 0,
      max: Math.max(...funnelData.map((item: any) => item.value), 1),
      minSize: '0%',
      maxSize: '100%',
      sort: 'none',
      gap: 2,
      label: {
        show: true,
        position: 'inside',
        color: '#fff',
        fontSize: 12,
        formatter: '{b}\n{c}个'
      },
      labelLine: {
        length: 10,
        lineStyle: {
          width: 1,
          type: 'solid'
        }
      },
      data: funnelData,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#1e2128',
        borderWidth: 2,
      },
    }],
    color: ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1'],
  })

  // 响应式调整
  window.addEventListener('resize', resizeFunnelChart)
}

function resizeFunnelChart() {
  if (funnelChartInstance) {
    funnelChartInstance.resize()
  }
}

// 加载执行层数据
async function loadExecutionData() {
  try {
    const [todayRes, waitingRes, emailWaitingRes] = await Promise.all([
      getTodayFollowups(),
      getWaitingTooLong(),
      getWaitingEmailThreads(),
    ])
    todayFollowups.value = todayRes.data || []
    waitingTooLong.value = waitingRes.data || []
    waitingEmailThreads.value = emailWaitingRes.data || []
  } catch (error) {
    console.error('加载执行层数据失败', error)
  }
}

// 监听层级切换
watch(currentLayer, (newLayer) => {
  if (newLayer === 'strategic') {
    initCharts()
  } else if (newLayer === 'tactical') {
    loadTacticalData()
    initFunnelChart()
  } else if (newLayer === 'execution') {
    loadExecutionData()
  }
})

onMounted(() => {
  loadData()
  initCharts()
})
</script>

<style scoped>
.dashboard-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  height: calc(100vh - 80px);
  overflow-y: auto;
}

.dashboard-container::-webkit-scrollbar {
  width: 6px;
}

.dashboard-container::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

.dashboard-container::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.dashboard-container::-webkit-scrollbar-thumb:hover {
  background: var(--border-color-hover);
}

/* ============ 层级切换 Tabs ============ */

.layer-tabs {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.layer-tabs :deep(.el-radio-button__inner) {
  background: var(--bg-tertiary);
  border-color: var(--border-color);
  color: var(--text-tertiary);
  padding: 12px 24px;
  font-size: 14px;
}

.layer-tabs :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-color: #3b82f6;
  color: white;
}

.data-trust-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

.data-trust-item {
  min-width: 0;
  padding-right: 12px;
  border-right: 1px solid var(--border-color);
}

.data-trust-item:last-child {
  border-right: 0;
}

.data-trust-item span,
.data-trust-item strong {
  display: block;
}

.data-trust-item span {
  margin-bottom: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.data-trust-item strong {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-trust-item.warning strong {
  color: var(--warning-color);
}

.coverage-alert {
  margin-bottom: 20px;
}

/* ============ 统计卡片 ============ */

.stat-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(59, 130, 246, 0.15);
  border-color: var(--accent-color);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-title {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* ============ 反直觉指标卡片 ============ */

.counter-intuitive-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.counter-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  transition: all 0.3s ease;
}

.counter-card:hover {
  transform: translateY(-4px);
}

.counter-card.zombie:hover {
  border-color: #ef4444;
  box-shadow: 0 12px 40px rgba(239, 68, 68, 0.15);
}

.counter-card.fake:hover {
  border-color: #f59e0b;
  box-shadow: 0 12px 40px rgba(245, 158, 11, 0.15);
}

.counter-card.sunk:hover {
  border-color: #8b5cf6;
  box-shadow: 0 12px 40px rgba(139, 92, 246, 0.15);
}

.counter-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.counter-value {
  font-size: 48px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.counter-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 8px;
}

/* ============ 图表网格 ============ */

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
}

.chart-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.chart-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.chart-body {
  padding: 24px;
  height: 320px;
}

.management-insight-card {
  grid-column: span 1;
}

.insight-list {
  overflow-y: auto;
}

.insight-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: var(--bg-tertiary);
  border-left: 4px solid var(--border-color);
  border-radius: 8px;
  cursor: default;
}

.insight-item:has(.insight-main) {
  cursor: pointer;
}

.insight-item.high { border-left-color: var(--danger-color); }
.insight-item.medium { border-left-color: var(--warning-color); }
.insight-item.low { border-left-color: var(--accent-color); }

.insight-priority {
  flex-shrink: 0;
  height: fit-content;
  padding: 3px 7px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: 5px;
  font-size: 11px;
}

.insight-main {
  min-width: 0;
}

.insight-main strong,
.insight-main p,
.insight-main span,
.insight-main small {
  display: block;
}

.insight-main strong { color: var(--text-primary); font-size: 14px; }
.insight-main p { margin: 5px 0; color: var(--text-secondary); font-size: 13px; }
.insight-main span { color: var(--text-muted); font-size: 12px; }
.insight-main small { margin-top: 5px; color: var(--text-muted); font-size: 11px; }

/* ============ 风险列表 ============ */

.risk-list {
  height: 100%;
  overflow-y: auto;
}

.risk-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
  gap: 16px;
  cursor: pointer;
}

.risk-rank {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--danger-color);
  font-size: 14px;
}

.risk-info {
  flex: 1;
}

.risk-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.risk-meta {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  gap: 16px;
}

.risk-days {
  font-size: 18px;
  font-weight: 700;
  color: var(--danger-color);
}

/* ============ 战术层样式 ============ */

.tactical-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

.tactical-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
}

.tactical-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.tactical-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.tactical-body {
  padding: 24px;
  min-height: 300px;
}

.tactical-card:nth-child(1) .tactical-body {
  height: 400px;
}

/* ============ 执行层样式 ============ */

.execution-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.execution-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
}

.execution-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.execution-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.execution-body {
  padding: 24px;
}

.project-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
  gap: 12px;
}

.project-priority {
  width: 4px;
  height: 40px;
  border-radius: 2px;
}

.project-priority.high {
  background: var(--danger-color);
}

.project-priority.medium {
  background: var(--warning-color);
}

.project-priority.low {
  background: var(--success-color);
}

.project-info {
  flex: 1;
}

.project-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.project-next-action {
  font-size: 12px;
  color: var(--text-muted);
}

/* ============ 活动时间轴 ============ */

.activity-timeline {
  max-height: 400px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.activity-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.activity-dot.progress {
  background: var(--success-color);
}

.activity-dot.risk {
  background: var(--danger-color);
}

.activity-dot.milestone {
  background: var(--accent-color);
}

.activity-content {
  flex: 1;
}

.activity-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.activity-meta {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.activity-project {
  color: var(--accent-color);
}

.activity-source {
  padding: 1px 6px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border-radius: 4px;
}

@media (max-width: 1200px) {
  .stat-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .execution-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .stat-cards,
  .counter-intuitive-cards,
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
