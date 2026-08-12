import request from '@/utils/request'

// 获取驾驶舱概览数据
export function getDashboardSummary() {
  return request.get(`/dashboard/summary`)
}

// 获取项目阶段分布
export function getStageDistribution() {
  return request.get(`/dashboard/stage-distribution`)
}

// 获取风险项目 TOP10
export function getRiskTop10() {
  return request.get(`/dashboard/risk-top10`)
}

// 获取国家分布
export function getCountryDistribution() {
  return request.get(`/dashboard/country-distribution`)
}

// 获取渠道贡献分析
export function getChannelContribution() {
  return request.get(`/dashboard/channel-contribution`)
}

// 获取项目健康度分布
export function getHealthDistribution() {
  return request.get(`/dashboard/health-distribution`)
}

// 获取近期活动流
export function getRecentActivities(limit: number = 10) {
  return request.get(`/dashboard/recent-activities`, { params: { limit } })
}

// 战术层 - 验收超时项目
export function getOverdueProjects() {
  return request.get(`/dashboard/overdue-projects`)
}

// 战术层 - 渠道沉没预警
export function getSunkChannels() {
  return request.get(`/dashboard/sunk-channels`)
}

// 战术层 - 需要管理介入的项目矩阵
export function getAttentionProjects() {
  return request.get(`/dashboard/attention-projects`)
}

// 执行层 - 今日需跟进项目
export function getTodayFollowups() {
  return request.get(`/dashboard/today-followups`)
}

// 执行层 - 等待客户反馈超时
export function getWaitingTooLong() {
  return request.get(`/dashboard/waiting-too-long`)
}

export function getIntelligenceTrends(days: number = 30) {
  return request.get(`/dashboard/intelligence-trends`, { params: { days } })
}

export function getWaitingEmailThreads() {
  return request.get(`/dashboard/waiting-email-threads`)
}

export function getManagementInsights() {
  return request.get(`/dashboard/management-insights`)
}
