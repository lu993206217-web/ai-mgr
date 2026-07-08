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
          <div class="stat-trend" :class="stat.trend >= 0 ? 'up' : 'down'">
            {{ stat.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(stat.trend) }}%
          </div>
        </div>
      </div>

      <!-- 反直觉指标 -->
      <div class="counter-intuitive-cards">
        <div class="counter-card zombie">
          <div class="counter-icon">🧟</div>
          <div class="counter-value">{{ counterIntuitive.zombieProjects }}</div>
          <div class="counter-label">僵尸项目（30天无活动）</div>
        </div>
        <div class="counter-card fake">
          <div class="counter-icon">🎭</div>
          <div class="counter-value">{{ counterIntuitive.fakeProgress }}</div>
          <div class="counter-label">假性推进项目</div>
        </div>
        <div class="counter-card sunk">
          <div class="counter-icon">📉</div>
          <div class="counter-value">{{ counterIntuitive.sunkChannels }}</div>
          <div class="counter-label">沉没渠道（一年无成交）</div>
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
            <h3>渠道贡献 TOP10</h3>
          </div>
          <div ref="channelChartRef" class="chart-body"></div>
        </div>
        
        <div class="chart-card">
          <div class="chart-header">
            <h3>风险项目 TOP10</h3>
          </div>
          <div class="chart-body">
            <div class="risk-list">
              <div class="risk-item" v-for="(project, idx) in riskTop10" :key="project.id">
                <div class="risk-rank">{{ idx + 1 }}</div>
                <div class="risk-info">
                  <div class="risk-name">{{ project.project_name }}</div>
                  <div class="risk-meta">
                    <span>{{ project.country }}</span>
                    <span>卡点：{{ project.blocker }}</span>
                  </div>
                </div>
                <div class="risk-days">{{ project.days_stuck }}天</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 战术层：总监/PMO 视角 -->
    <div v-if="currentLayer === 'tactical'" class="layer-content">
      <div class="tactical-grid">
        <div class="tactical-card">
          <div class="tactical-header">
            <h3>📊 项目阶段漏斗</h3>
          </div>
          <div ref="funnelChartRef" class="tactical-body"></div>
        </div>
        
        <div class="tactical-card">
          <div class="tactical-header">
            <h3>⚠️ 验收超时项目</h3>
          </div>
          <div class="tactical-body">
            <el-table :data="overdueProjects" style="width: 100%">
              <el-table-column prop="project_name" label="项目名称" />
              <el-table-column prop="current_stage" label="当前阶段" />
              <el-table-column prop="days_overdue" label="超时天数" />
              <el-table-column prop="owner_name" label="负责人" />
            </el-table>
          </div>
        </div>
        
        <div class="tactical-card">
          <div class="tactical-header">
            <h3>🔍 渠道沉没预警</h3>
          </div>
          <div class="tactical-body">
            <el-table :data="sunkChannels" style="width: 100%">
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
            <div class="project-item" v-for="project in todayFollowups" :key="project.id">
              <div class="project-priority" :class="project.priority"></div>
              <div class="project-info">
                <div class="project-name">{{ project.project_name }}</div>
                <div class="project-next-action">{{ project.next_action }}</div>
              </div>
              <el-button size="small" type="primary" @click="goToProject(project.id)">
                查看
              </el-button>
            </div>
          </div>
        </div>
        
        <div class="execution-card">
          <div class="execution-header">
            <h3>⏰ 等待客户反馈超时</h3>
          </div>
          <div class="execution-body">
            <el-table :data="waitingTooLong" style="width: 100%">
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
                    <span>{{ activity.owner_name }}</span>
                    <span>{{ formatDate(activity.occurred_at) }}</span>
                  </div>
                </div>
              </div>
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
import { getDashboardSummary, getStageDistribution, getRiskTop10, getCountryDistribution, getChannelContribution, getRecentActivities, getOverdueProjects, getSunkChannels, getTodayFollowups, getWaitingTooLong } from '@/api/dashboard'
import type { Project } from '@/types/auth'

const router = useRouter()

// 当前层级
const currentLayer = ref('strategic')

// 统计数据
const statistics = ref([
  { title: '项目总数', value: 0, icon: '📊', gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', trend: 12 },
  { title: '进行中项目', value: 0, icon: '🚀', gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', trend: 8 },
  { title: '风险项目', value: 0, icon: '⚠️', gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', trend: -5 },
  { title: '本月验收项目', value: 0, icon: '✅', gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', trend: 15 },
  { title: '本月新增项目', value: 0, icon: '🆕', gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', trend: 20 },
])

// 反直觉指标
const counterIntuitive = ref({
  zombieProjects: 0,
  fakeProgress: 0,
  sunkChannels: 0,
})

// 风险 TOP10
const riskTop10 = ref<Project[]>([])

// 图表引用
const stageChartRef = ref<HTMLElement>()
const countryChartRef = ref<HTMLElement>()
const channelChartRef = ref<HTMLElement>()
const funnelChartRef = ref<HTMLElement>()

// 战术层数据
const overdueProjects = ref([])
const sunkChannels = ref([])

// 执行层数据
const todayFollowups = ref([])
const waitingTooLong = ref([])
const recentActivities = ref([])

// 加载数据
async function loadData() {
  try {
    // 加载概览数据
    const summaryRes = await getDashboardSummary()
    const summary = summaryRes.data
    
    // 后端返回 snake_case 格式字段名
    statistics.value[0].value = summary.total_projects ?? 0
    statistics.value[1].value = summary.in_progress_projects ?? 0
    statistics.value[2].value = summary.risk_projects ?? 0
    statistics.value[3].value = summary.monthly_acceptance_projects ?? 0
    statistics.value[4].value = summary.monthly_new_projects ?? 0
    
    counterIntuitive.value.zombieProjects = summary.zombie_projects ?? 0
    counterIntuitive.value.fakeProgress = summary.fake_progress_projects ?? 0
    counterIntuitive.value.sunkChannels = summary.inactive_channels ?? 0
    
    // 加载风险 TOP10
    const riskRes = await getRiskTop10()
    riskTop10.value = riskRes.data
    
    // 加载近期活动
    const activitiesRes = await getRecentActivities(10)
    recentActivities.value = activitiesRes.data
    
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
      const chart = echarts.init(stageChartRef.value)
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
      const chart = echarts.init(countryChartRef.value)
      const countryData = await getCountryDistribution()
      
      chart.setOption({
        tooltip: { trigger: 'axis' },
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
        series: [{
          type: 'bar',
          data: countryData.data.map((item: any) => item.project_count),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#2563eb' },
            ]),
            borderRadius: [8, 8, 0, 0],
          },
        }],
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

// 加载战术层数据
async function loadTacticalData() {
  try {
    const [overdueRes, sunkRes] = await Promise.all([
      getOverdueProjects(),
      getSunkChannels(),
    ])
    overdueProjects.value = overdueRes.data || []
    sunkChannels.value = sunkRes.data || []
  } catch (error) {
    console.error('加载战术层数据失败', error)
  }
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
      max: 100,
      minSize: '0%',
      maxSize: '100%',
      sort: 'descending',
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
    const [todayRes, waitingRes] = await Promise.all([
      getTodayFollowups(),
      getWaitingTooLong(),
    ])
    todayFollowups.value = todayRes.data || []
    waitingTooLong.value = waitingRes.data || []
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

/* ============ 统计卡片 ============ */

.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
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
  width: 56px;
  height: 56px;
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
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-title {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.stat-trend {
  position: absolute;
  top: 16px;
  right: 16px;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
}

.stat-trend.up {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.stat-trend.down {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
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
  grid-template-columns: repeat(3, 1fr);
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
}

.activity-meta {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  gap: 16px;
}
</style>
