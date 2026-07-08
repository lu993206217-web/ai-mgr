<template>
  <div class="project-detail-container fade-in" v-if="project">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="page-title-section">
        <el-button class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2 class="page-title">{{ project.project_name }}</h2>
        <el-tag :type="getStatusType(project.status)">{{ project.status }}</el-tag>
      </div>
      <div class="page-actions">
        <el-button @click="handleEdit">
          <el-icon><Edit /></el-icon>
          编辑
        </el-button>
        <el-button type="primary" @click="handleAddActivity">
          <el-icon><Plus /></el-icon>
          添加活动
        </el-button>
      </div>
    </div>

    <!-- 项目信息卡片 -->
    <div class="info-cards">
      <div class="info-card">
        <div class="info-card-header">
          <span class="info-card-title">基本信息</span>
        </div>
        <div class="info-card-body">
          <div class="info-item">
            <span class="info-label">国家</span>
            <span class="info-value">{{ project.country }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">客户</span>
            <span class="info-value">{{ project.customer_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">渠道</span>
            <span class="info-value">{{ project.channel_name || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">负责人</span>
            <span class="info-value">{{ project.owner_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">项目来源</span>
            <span class="info-value">{{ project.source_type }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">项目金额</span>
            <span class="info-value">{{ project.project_amount ? project.project_amount + ' ' + project.currency : '-' }}</span>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="info-card-header">
          <span class="info-card-title">进度信息</span>
        </div>
        <div class="info-card-body">
          <div class="info-item">
            <span class="info-label">当前阶段</span>
            <span class="info-value">{{ project.current_stage }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">阶段进入时间</span>
            <span class="info-value">{{ formatDate(project.stage_entered_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">计划上线</span>
            <span class="info-value">{{ formatDate(project.planned_go_live) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">计划验收</span>
            <span class="info-value">{{ formatDate(project.planned_acceptance) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">健康状态</span>
            <span class="info-value"><el-tag :type="getHealthType(project.health_status)">{{ project.health_status }}</el-tag></span>
          </div>
          <div class="info-item">
            <span class="info-label">风险等级</span>
            <span class="info-value"><el-tag :type="getRiskType(project.risk_level)">{{ project.risk_level }}</el-tag></span>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="info-card-header">
          <span class="info-card-title">时间信息</span>
        </div>
        <div class="info-card-body">
          <div class="info-item">
            <span class="info-label">最后活动时间</span>
            <span class="info-value">{{ formatDateTime(project.last_activity_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatDateTime(project.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">更新时间</span>
            <span class="info-value">{{ formatDateTime(project.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 活动日志区域 -->
    <div class="activity-section">
      <div class="section-header">
        <h3 class="section-title">活动日志</h3>
      </div>

      <!-- 筛选栏 -->
      <div class="activity-filters">
        <el-select v-model="filterForm.activity_type" placeholder="活动类型" clearable>
          <el-option label="全部" value="" />
          <el-option label="进展更新" value="进展更新" />
          <el-option label="风险上报" value="风险上报" />
          <el-option label="里程碑完成" value="里程碑完成" />
          <el-option label="阻塞等待" value="阻塞等待" />
        </el-select>
        <el-date-picker v-model="filterForm.start_date" type="date" placeholder="开始日期" />
        <el-date-picker v-model="filterForm.end_date" type="date" placeholder="结束日期" />
        <el-button size="small" @click="handleFilter">筛选</el-button>
        <el-button size="small" @click="handleResetFilter">重置</el-button>
      </div>

      <!-- 活动时间轴 -->
      <div class="activity-timeline" v-loading="activitiesLoading">
        <div class="activity-item" v-for="activity in activities" :key="activity.id">
          <div class="activity-dot" :class="activity.activity_type"></div>
          <div class="activity-content">
            <div class="activity-header">
              <span class="activity-type">{{ getActivityTypeLabel(activity.activity_type) }}</span>
              <span class="activity-time">{{ formatDateTime(activity.occurred_at) }}</span>
            </div>
            <div class="activity-text">{{ activity.activity_content }}</div>
            <div class="activity-meta" v-if="activity.next_action">
              <el-tag size="small" type="warning">下一步：{{ getNextActionLabel(activity.next_action) }}</el-tag>
              <span class="activity-owner">负责人：{{ activity.owner_name }}</span>
            </div>
          </div>
        </div>

        <!-- 分页组件 -->
        <div class="timeline-pagination" v-if="total > 0 && activities && activities.length > 0">
          <el-pagination
            :current-page="pagination.page"
            :page-size="pagination.page_size"
            :total="total"
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
            layout="prev, pager, next"
            :small="true"
          />
          <span class="pagination-info">共 {{ total }} 条</span>
        </div>

        <div class="empty-activity" v-if="!activitiesLoading && activities && activities.length === 0">
          <el-empty description="暂无活动记录" />
        </div>
      </div>
    </div>

    <!-- 添加活动对话框 -->
    <el-dialog
      v-model="activityDialogVisible"
      title="添加活动记录"
      width="600px"
    >
      <el-form
        ref="activityFormRef"
        :model="activityForm"
        :rules="activityRules"
        label-width="100px"
      >
        <el-form-item label="活动类型" prop="activity_type">
          <el-select v-model="activityForm.activity_type" placeholder="请选择活动类型">
            <el-option label="进展更新" value="进展更新" />
            <el-option label="风险上报" value="风险上报" />
            <el-option label="里程碑完成" value="里程碑完成" />
            <el-option label="阻塞等待" value="阻塞等待" />
          </el-select>
        </el-form-item>
        <el-form-item label="活动内容" prop="activity_content">
          <el-input v-model="activityForm.activity_content" type="textarea" :rows="4" placeholder="请输入活动内容" />
        </el-form-item>
        <el-form-item label="下一步行动">
          <el-select v-model="activityForm.next_action" placeholder="请选择下一步行动" clearable>
            <el-option label="等待客户反馈" value="等待客户反馈" />
            <el-option label="等待内部审批" value="等待内部审批" />
            <el-option label="技术方案设计" value="技术方案设计" />
            <el-option label="开发实施" value="开发实施" />
            <el-option label="测试验证" value="测试验证" />
            <el-option label="部署上线" value="部署上线" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否阻塞">
          <el-switch v-model="activityForm.blocker_flag" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="activityDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleActivitySubmit" :loading="activitySubmitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit, Plus } from '@element-plus/icons-vue'
import { getProject, getActivities, createActivity } from '@/api/project'
import type { Project, ActivityLog } from '@/types/project'

const route = useRoute()
const router = useRouter()

const project = ref<Project | null>(null)
const activities = ref<ActivityLog[]>([])
const activitiesLoading = ref(false)
const total = ref(0)

const pagination = ref({
  page: 1,
  page_size: 20,
})

const filterForm = ref({
  activity_type: '',
  start_date: '',
  end_date: '',
})

const activityDialogVisible = ref(false)
const activitySubmitLoading = ref(false)
const activityFormRef = ref()

const activityForm = ref({
  activity_type: '进展更新',
  activity_content: '',
  next_action: undefined as string | undefined,
  blocker_flag: false,
})

const activityRules = {
  activity_type: [
    { required: true, message: '请选择活动类型', trigger: 'change' },
  ],
  activity_content: [
    { required: true, message: '请输入活动内容', trigger: 'blur' },
  ],
}

// 加载项目详情
const loadProject = async () => {
  const id = route.params.id as string
  try {
    const res = await getProject(id)
    project.value = res.data
  } catch (error) {
    ElMessage.error('获取项目详情失败')
    console.error(error)
  }
}

// 加载活动日志
const loadActivities = async () => {
  const id = route.params.id as string
  activitiesLoading.value = true
  try {
    const params: any = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
    }
    if (filterForm.value.activity_type) {
      params.activity_type = filterForm.value.activity_type
    }
    if (filterForm.value.start_date) {
      // 将日期转换为 YYYY-MM-DD 格式
      const startDate = new Date(filterForm.value.start_date)
      params.start_date = startDate.toISOString().split('T')[0]
    }
    if (filterForm.value.end_date) {
      // 将日期转换为 YYYY-MM-DD 格式
      const endDate = new Date(filterForm.value.end_date)
      params.end_date = endDate.toISOString().split('T')[0]
    }
    const res = await getActivities(id, params)
    activities.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    ElMessage.error('获取活动日志失败')
    console.error(error)
  } finally {
    activitiesLoading.value = false
  }
}

// 页面加载时初始化
onMounted(() => {
  loadProject()
  loadActivities()
})

// 返回列表页
const goBack = () => {
  router.push('/projects')
}

// 编辑项目
const handleEdit = () => {
  ElMessage.info('编辑功能开发中')
}

// 打开添加活动对话框
const handleAddActivity = () => {
  activityDialogVisible.value = true
}

// 提交活动
const handleActivitySubmit = async () => {
  if (!activityFormRef.value) return
  const valid = await activityFormRef.value.validate()
  if (!valid) return
  
  activitySubmitLoading.value = true
  const id = route.params.id as string
  try {
    await createActivity(id, {
      activity_type: activityForm.value.activity_type,
      activity_content: activityForm.value.activity_content,
      next_action: activityForm.value.next_action,
      blocker_flag: activityForm.value.blocker_flag,
    })
    ElMessage.success('活动记录添加成功')
    activityDialogVisible.value = false
    activityForm.value = {
      activity_type: '进展更新',
      activity_content: '',
      next_action: undefined,
      blocker_flag: false,
    }
    loadActivities()
    loadProject()
  } catch (error) {
    ElMessage.error('添加活动记录失败')
    console.error(error)
  } finally {
    activitySubmitLoading.value = false
  }
}

// 分页处理
const handlePageChange = (page: number) => {
  pagination.value.page = page
  loadActivities()
}

const handlePageSizeChange = (size: number) => {
  pagination.value.page_size = size
  pagination.value.page = 1
  loadActivities()
}

// 筛选处理
const handleFilter = () => {
  pagination.value.page = 1
  loadActivities()
}

const handleResetFilter = () => {
  filterForm.value = {
    activity_type: '',
    start_date: '',
    end_date: '',
  }
  pagination.value.page = 1
  loadActivities()
}

// 格式化日期
const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

// 格式化日期时间
const formatDateTime = (dateStr?: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 获取状态类型
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    '进行中': 'success',
    '已完成': 'primary',
    '已关闭': 'info',
    '暂停': 'warning',
  }
  return map[status] || 'default'
}

// 获取健康状态类型
const getHealthType = (health: string) => {
  const map: Record<string, string> = {
    '健康': 'success',
    '一般': 'warning',
    '危险': 'danger',
  }
  return map[health] || 'default'
}

// 获取风险等级类型
const getRiskType = (risk: string) => {
  const map: Record<string, string> = {
    '低': 'success',
    '中': 'warning',
    '高': 'danger',
  }
  return map[risk] || 'default'
}

// 获取活动类型标签
const getActivityTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    '进展更新': '进展更新',
    '风险上报': '风险上报',
    '里程碑完成': '里程碑完成',
    '阻塞等待': '阻塞等待',
  }
  return map[type] || type
}

// 获取下一步行动标签
const getNextActionLabel = (action: string) => {
  const map: Record<string, string> = {
    '等待客户反馈': '等待客户反馈',
    '等待内部审批': '等待内部审批',
    '技术方案设计': '技术方案设计',
    '开发实施': '开发实施',
    '测试验证': '测试验证',
    '部署上线': '部署上线',
  }
  return map[action] || action
}
</script>

<style scoped>
.project-detail-container {
  padding: 24px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ============ 页面标题栏 ============ */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #363b47;
}

.page-title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  padding: 8px 12px;
  margin: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-actions {
  display: flex;
  gap: 12px;
}

/* ============ 信息卡片 ============ */

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.info-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  overflow: hidden;
}

.info-card-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.info-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
}

.info-card-body {
  padding: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 13px;
  color: var(--text-muted);
}

.info-value {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ============ 活动区域 ============ */

.activity-section {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

/* ============ 筛选栏 ============ */

.activity-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.activity-filters .el-select,
.activity-filters .el-date-picker {
  width: 160px;
}

.activity-filters .el-button {
  padding: 8px 16px;
}

/* ============ 活动时间轴 ============ */

.activity-timeline {
  max-height: 500px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.activity-dot.进展更新 {
  background: var(--success-color);
}

.activity-dot.风险上报 {
  background: var(--danger-color);
}

.activity-dot.里程碑完成 {
  background: var(--accent-color);
}

.activity-dot.阻塞等待 {
  background: var(--warning-color);
}

.activity-content {
  flex: 1;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.activity-type {
  font-size: 14px;
  font-weight: 500;
  color: #3b82f6;
}

.activity-time {
  font-size: 12px;
  color: #6b7280;
}

.activity-text {
  font-size: 14px;
  color: #d1d5db;
  line-height: 1.6;
  margin-bottom: 8px;
}

.activity-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.activity-owner {
  font-size: 12px;
  color: #6b7280;
}

/* ============ 空状态 ============ */

.empty-activity {
  padding: 40px 0;
}

/* ============ 时间轴内部分页 ============ */

.timeline-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px 0;
  border-top: 1px solid #363b47;
  margin-top: 8px;
}

.pagination-info {
  font-size: 12px;
  color: #6b7280;
}
</style>