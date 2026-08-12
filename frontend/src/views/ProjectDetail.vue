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

    <!-- 阶段与状态事实记录 -->
    <div class="state-history-section">
      <div class="section-header state-history-header">
        <div>
          <h3 class="section-title">阶段与状态历史</h3>
          <p class="section-description">只记录系统掌握的事实；“首次基线”不代表历史变更。</p>
        </div>
      </div>
      <div class="state-history-list" v-loading="stateEventsLoading">
        <div v-for="event in stateEvents" :key="event.id" class="state-history-item">
          <div class="state-history-dot" :class="event.event_type.includes('stage') ? 'stage' : 'status'"></div>
          <div class="state-history-content">
            <div class="state-history-main">
              <el-tag size="small" :type="event.event_type.includes('stage') ? 'primary' : 'info'">
                {{ getStateEventLabel(event.event_type) }}
              </el-tag>
              <span v-if="event.from_value" class="state-history-value">
                {{ event.from_value }} → {{ event.to_value }}
              </span>
              <span v-else class="state-history-value">{{ event.to_value }}</span>
              <span class="state-history-time">{{ formatDateTime(event.occurred_at) }}</span>
            </div>
            <div v-if="event.note" class="state-history-note">{{ event.note }}</div>
          </div>
        </div>
        <el-empty v-if="!stateEventsLoading && stateEvents.length === 0" description="暂无阶段或状态记录" />
      </div>
    </div>

    <!-- 活动日志区域 -->
    <div class="activity-section">
      <div class="section-header">
        <h3 class="section-title">活动日志 <span v-if="total" class="section-count">共 {{ total }} 条</span></h3>
        <el-button type="primary" size="small" @click="handleAddActivity">
          <el-icon><Plus /></el-icon>
          添加活动
        </el-button>
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
              <div class="activity-title-row">
                <span
                  v-if="activity.email_detail"
                  class="communication-title"
                  :class="getCommunicationClass(activity.email_detail.communication_type)"
                >
                  {{ activity.display_title || activity.email_detail.communication_type }}
                </span>
                <span v-else class="activity-type">{{ getActivityTypeLabel(activity.activity_type) }}</span>
                <el-tag size="small" :type="activity.source === '日报' || activity.source === 'DAILY_REPORT' ? 'success' : 'info'">
                  {{ getActivitySourceLabel(activity.source) }}
                </el-tag>
              </div>
              <span class="activity-time">{{ formatDateTime(activity.occurred_at) }}</span>
            </div>
            <div class="activity-text">
              <div v-if="activity.email_detail" class="email-activity-preview">
                <div class="email-activity-subject">{{ activity.email_detail.subject }}</div>
                <div class="activity-text-preview">{{ activity.display_summary || activity.email_detail.summary || '暂无摘要' }}</div>
                <div v-if="activity.email_detail.action_items.length" class="email-key-action">
                  <span>关键行动</span>
                  {{ activity.email_detail.action_items[0] }}
                </div>
              </div>
              <div v-else class="activity-text-preview">{{ activity.display_summary || activity.activity_content || '暂无活动内容' }}</div>
              <el-button
                v-if="activity.activity_content"
                link
                type="primary"
                class="activity-detail-btn"
                @click="openActivityDetail(activity)"
              >
                查看详情
              </el-button>
            </div>
            <div class="activity-meta" v-if="activity.next_action">
              <el-tag size="small" type="warning">下一步：{{ getNextActionLabel(activity.next_action) }}</el-tag>
              <span class="activity-owner">负责人：{{ activity.owner_name }}</span>
            </div>
            <div class="activity-meta" v-else>
              <span class="activity-owner">负责人：{{ activity.owner_name || '-' }}</span>
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

    <!-- 项目文件区域 -->
    <div class="file-section">
      <div class="section-header">
        <h3 class="section-title">项目文件</h3>
        <el-button type="primary" size="small" @click="handleAddFile">
          <el-icon><Plus /></el-icon>
          添加文件
        </el-button>
      </div>

      <div class="file-filters">
        <el-select v-model="fileFilterForm.file_category" placeholder="文件分类" clearable>
          <el-option label="全部" value="" />
          <el-option label="售前交流" value="售前交流" />
          <el-option label="商务资料" value="商务资料" />
          <el-option label="技术方案" value="技术方案" />
          <el-option label="合同/订单" value="合同/订单" />
          <el-option label="交付验收" value="交付验收" />
          <el-option label="其他" value="其他" />
        </el-select>
        <el-input v-model="fileFilterForm.keyword" placeholder="搜索文件名" clearable />
        <el-button size="small" @click="handleFileFilter">筛选</el-button>
        <el-button size="small" @click="handleFileResetFilter">重置</el-button>
      </div>

      <div class="file-list" v-loading="filesLoading">
        <el-table :data="files" style="width: 100%">
          <el-table-column prop="file_name" label="文件名称" min-width="220">
            <template #default="{ row }">
              <div class="file-name-cell">
                <el-icon><Document /></el-icon>
                <span>{{ row.file_name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="file_category" label="分类" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.file_category }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="owner_party" label="归属方" width="100" />
          <el-table-column prop="file_source" label="来源" width="120" />
          <el-table-column prop="description" label="备注" min-width="180" show-overflow-tooltip />
          <el-table-column prop="created_by_name" label="登记人" width="120" />
          <el-table-column prop="created_at" label="登记时间" width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.file_url"
                link
                type="primary"
                @click="openFile(row.file_url)"
              >
                打开
              </el-button>
              <el-button link type="danger" @click="handleDeleteFile(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="timeline-pagination" v-if="fileTotal > 0 && files && files.length > 0">
          <el-pagination
            :current-page="filePagination.page"
            :page-size="filePagination.page_size"
            :total="fileTotal"
            @current-change="handleFilePageChange"
            layout="prev, pager, next"
            :small="true"
          />
          <span class="pagination-info">共 {{ fileTotal }} 个文件</span>
        </div>

        <div class="empty-activity" v-if="!filesLoading && files && files.length === 0">
          <el-empty description="暂无项目文件" />
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

    <el-dialog
      v-model="activityDetailVisible"
      :title="selectedActivity?.email_detail ? '邮件活动详情' : '活动详情'"
      width="720px"
      class="activity-detail-dialog"
    >
      <div v-if="selectedActivity" class="activity-detail">
        <div class="activity-detail-header">
          <span
            v-if="selectedActivity.email_detail"
            class="communication-title"
            :class="getCommunicationClass(selectedActivity.email_detail.communication_type)"
          >
            {{ selectedActivity.display_title || selectedActivity.email_detail.communication_type }}
          </span>
          <el-tag v-else>{{ getActivityTypeLabel(selectedActivity.activity_type) }}</el-tag>
          <el-tag type="success" v-if="selectedActivity.source === '日报' || selectedActivity.source === 'DAILY_REPORT'">
            {{ getActivitySourceLabel(selectedActivity.source) }}
          </el-tag>
          <el-tag type="info" v-else>{{ getActivitySourceLabel(selectedActivity.source) }}</el-tag>
          <span>{{ formatDateTime(selectedActivity.occurred_at) }}</span>
        </div>
        <div class="activity-detail-scroll">
          <div v-if="selectedActivity.email_detail" class="email-detail-content">
            <section class="email-detail-hero">
              <div class="email-detail-subject">{{ selectedActivity.email_detail.subject }}</div>
              <div class="email-detail-summary">{{ selectedActivity.email_detail.summary || selectedActivity.display_summary || '-' }}</div>
            </section>

            <section v-if="selectedActivity.next_action" class="email-responsibility">
              <span>下一步责任</span>
              <strong>{{ getNextActionLabel(selectedActivity.next_action) }}</strong>
              <small v-if="selectedActivity.next_action_deadline">
                截止：{{ formatDate(selectedActivity.next_action_deadline) }}
              </small>
            </section>

            <section v-if="selectedActivity.email_detail.customer_request" class="email-detail-section">
              <h4>客户诉求</h4>
              <p>{{ selectedActivity.email_detail.customer_request }}</p>
            </section>

            <section v-if="selectedActivity.email_detail.action_items.length" class="email-detail-section">
              <h4>行动项</h4>
              <ol class="email-detail-list">
                <li v-for="item in selectedActivity.email_detail.action_items" :key="item">{{ item }}</li>
              </ol>
            </section>

            <section v-if="selectedActivity.email_detail.risks.length" class="email-detail-section risk-section">
              <h4>风险提示（待确认）</h4>
              <ul class="email-detail-list">
                <li v-for="item in selectedActivity.email_detail.risks" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="email-detail-section email-meta-section">
              <h4>邮件信息</h4>
              <dl>
                <div><dt>发件人</dt><dd>{{ selectedActivity.email_detail.sender }}</dd></div>
                <div><dt>收件人</dt><dd>{{ selectedActivity.email_detail.recipients.join('、') || '-' }}</dd></div>
                <div v-if="selectedActivity.email_detail.cc.length"><dt>抄送</dt><dd>{{ selectedActivity.email_detail.cc.join('、') }}</dd></div>
                <div><dt>客户态度</dt><dd>{{ selectedActivity.email_detail.customer_attitude || '未知' }}</dd></div>
                <div v-if="selectedActivity.email_detail.attachment_names.length">
                  <dt>附件</dt><dd>{{ selectedActivity.email_detail.attachment_names.join('、') }}</dd>
                </div>
              </dl>
            </section>

            <details v-if="selectedActivity.email_detail.body_excerpt" class="email-original-detail">
              <summary>查看原邮件正文节选</summary>
              <div>{{ selectedActivity.email_detail.body_excerpt }}</div>
            </details>
          </div>
          <div v-else class="activity-detail-content">{{ selectedActivity.activity_content }}</div>
        </div>
        <div class="activity-detail-footer">
          负责人：{{ selectedActivity.owner_name || '-' }}
        </div>
      </div>
    </el-dialog>

    <!-- 添加文件对话框 -->
    <el-dialog
      v-model="fileDialogVisible"
      title="添加项目文件"
      width="640px"
    >
      <el-form
        ref="fileFormRef"
        :model="fileForm"
        :rules="fileRules"
        label-width="100px"
      >
        <el-form-item label="文件名称" prop="file_name">
          <el-input v-model="fileForm.file_name" placeholder="例如：客户售前交流纪要-20260708" />
        </el-form-item>
        <el-form-item label="文件分类" prop="file_category">
          <el-select v-model="fileForm.file_category" placeholder="请选择文件分类">
            <el-option label="售前交流" value="售前交流" />
            <el-option label="商务资料" value="商务资料" />
            <el-option label="技术方案" value="技术方案" />
            <el-option label="合同/订单" value="合同/订单" />
            <el-option label="交付验收" value="交付验收" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="链接/路径">
          <el-input v-model="fileForm.file_url" placeholder="可填写网盘、飞书、钉钉链接或本地归档路径" />
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="fileForm.file_source" placeholder="例如：客户邮件、销售上传、会议纪要" />
        </el-form-item>
        <el-form-item label="归属方">
          <el-select v-model="fileForm.owner_party" placeholder="请选择归属方" clearable>
            <el-option label="客户" value="客户" />
            <el-option label="渠道" value="渠道" />
            <el-option label="我方" value="我方" />
            <el-option label="第三方" value="第三方" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="fileForm.description" type="textarea" :rows="3" placeholder="补充说明文件用途、版本或关键内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fileDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleFileSubmit" :loading="fileSubmitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Edit, Plus, Document } from '@element-plus/icons-vue'
import { getProject, getProjectStateEvents, getActivities, createActivity, getProjectFiles, createProjectFile, deleteProjectFile } from '@/api/project'
import type { Project, ProjectStateEvent, ActivityLog, ProjectFile } from '@/types/project'

const route = useRoute()
const router = useRouter()

const project = ref<Project | null>(null)
const stateEvents = ref<ProjectStateEvent[]>([])
const stateEventsLoading = ref(false)
const activities = ref<ActivityLog[]>([])
const activitiesLoading = ref(false)
const total = ref(0)
const files = ref<ProjectFile[]>([])
const filesLoading = ref(false)
const fileTotal = ref(0)

const pagination = ref({
  page: 1,
  page_size: 20,
})

const filterForm = ref({
  activity_type: '',
  start_date: '',
  end_date: '',
})

const filePagination = ref({
  page: 1,
  page_size: 10,
})

const fileFilterForm = ref({
  file_category: '',
  keyword: '',
})

const activityDialogVisible = ref(false)
const activitySubmitLoading = ref(false)
const activityFormRef = ref()
const activityDetailVisible = ref(false)
const selectedActivity = ref<ActivityLog | null>(null)
const fileDialogVisible = ref(false)
const fileSubmitLoading = ref(false)
const fileFormRef = ref()

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

const fileForm = ref({
  file_name: '',
  file_category: '售前交流',
  file_url: '',
  file_source: '',
  owner_party: '',
  description: '',
})

const fileRules = {
  file_name: [
    { required: true, message: '请输入文件名称', trigger: 'blur' },
  ],
  file_category: [
    { required: true, message: '请选择文件分类', trigger: 'change' },
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

const loadStateEvents = async () => {
  const id = route.params.id as string
  stateEventsLoading.value = true
  try {
    const res = await getProjectStateEvents(id)
    stateEvents.value = res.data
  } catch (error) {
    ElMessage.error('获取阶段与状态历史失败')
    console.error(error)
  } finally {
    stateEventsLoading.value = false
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

// 加载项目文件
const loadFiles = async () => {
  const id = route.params.id as string
  filesLoading.value = true
  try {
    const params: any = {
      page: filePagination.value.page,
      page_size: filePagination.value.page_size,
    }
    if (fileFilterForm.value.file_category) {
      params.file_category = fileFilterForm.value.file_category
    }
    if (fileFilterForm.value.keyword) {
      params.keyword = fileFilterForm.value.keyword
    }
    const res = await getProjectFiles(id, params)
    files.value = res.data.items
    fileTotal.value = res.data.total
  } catch (error) {
    ElMessage.error('获取项目文件失败')
    console.error(error)
  } finally {
    filesLoading.value = false
  }
}

// 页面加载时初始化
onMounted(() => {
  loadProject()
  loadStateEvents()
  loadActivities()
  loadFiles()
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

const openActivityDetail = (activity: ActivityLog) => {
  selectedActivity.value = activity
  activityDetailVisible.value = true
}

// 打开添加文件对话框
const handleAddFile = () => {
  fileDialogVisible.value = true
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

// 提交文件记录
const handleFileSubmit = async () => {
  if (!fileFormRef.value) return
  const valid = await fileFormRef.value.validate()
  if (!valid) return

  fileSubmitLoading.value = true
  const id = route.params.id as string
  try {
    await createProjectFile(id, {
      file_name: fileForm.value.file_name,
      file_category: fileForm.value.file_category,
      file_url: fileForm.value.file_url || undefined,
      file_source: fileForm.value.file_source || undefined,
      owner_party: fileForm.value.owner_party || undefined,
      description: fileForm.value.description || undefined,
    })
    ElMessage.success('项目文件添加成功')
    fileDialogVisible.value = false
    fileForm.value = {
      file_name: '',
      file_category: '售前交流',
      file_url: '',
      file_source: '',
      owner_party: '',
      description: '',
    }
    loadFiles()
  } catch (error) {
    ElMessage.error('添加项目文件失败')
    console.error(error)
  } finally {
    fileSubmitLoading.value = false
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

// 文件分页和筛选
const handleFilePageChange = (page: number) => {
  filePagination.value.page = page
  loadFiles()
}

const handleFileFilter = () => {
  filePagination.value.page = 1
  loadFiles()
}

const handleFileResetFilter = () => {
  fileFilterForm.value = {
    file_category: '',
    keyword: '',
  }
  filePagination.value.page = 1
  loadFiles()
}

const openFile = (url: string) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

const handleDeleteFile = async (fileId: string) => {
  try {
    await ElMessageBox.confirm('确认删除这条项目文件记录吗？', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const id = route.params.id as string
  try {
    await deleteProjectFile(id, fileId)
    ElMessage.success('项目文件已删除')
    loadFiles()
  } catch (error) {
    ElMessage.error('删除项目文件失败')
    console.error(error)
  }
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

const getStateEventLabel = (eventType: string) => {
  const map: Record<string, string> = {
    stage_baseline: '阶段首次基线',
    status_baseline: '状态首次基线',
    stage_change: '阶段变更',
    status_change: '状态变更',
  }
  return map[eventType] || eventType
}

// 获取活动类型标签
const getActivityTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    '进展更新': '进展更新',
    'PROGRESS_UPDATE': '进展更新',
    '风险上报': '风险上报',
    'RISK_REPORT': '风险上报',
    '里程碑完成': '里程碑完成',
    'MILESTONE_COMPLETE': '里程碑完成',
    '阻塞等待': '阻塞等待',
    'BLOCKER_WAITING': '阻塞等待',
  }
  return map[type] || type
}

const getActivitySourceLabel = (source: string) => {
  const map: Record<string, string> = {
    'MANUAL': '手工',
    '手工': '手工',
    'DAILY_REPORT': '日报',
    '日报': '日报',
    'DINGTALK': '钉钉',
    'EMAIL': '邮件',
    '邮件': '邮件',
  }
  return map[source] || source || '-'
}

const getCommunicationClass = (type: string) => {
  const map: Record<string, string> = {
    '客户发起': 'customer-start',
    '客户回复': 'customer-reply',
    '我方发起': 'our-start',
    '我方回复': 'our-reply',
    '内部协同': 'internal',
  }
  return map[type] || 'internal'
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
    '我方处理': '我方处理（Srun）',
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

.state-history-section {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.state-history-header {
  align-items: flex-start;
}

.section-description {
  margin: 6px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}

.state-history-list {
  display: grid;
  gap: 12px;
}

.state-history-item {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.state-history-dot {
  flex: 0 0 9px;
  width: 9px;
  height: 9px;
  margin-top: 7px;
  border-radius: 50%;
  background: #64748b;
}

.state-history-dot.stage {
  background: #3b82f6;
}

.state-history-content {
  min-width: 0;
  flex: 1;
}

.state-history-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.state-history-value {
  color: var(--text-primary);
  font-weight: 600;
}

.state-history-time {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 12px;
}

.state-history-note {
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 12px;
}

.activity-section {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.file-section {
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

.section-count {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
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

.file-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.file-filters .el-select {
  width: 160px;
}

.file-filters .el-input {
  width: 220px;
}

.file-list {
  min-height: 160px;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

/* ============ 活动时间轴 ============ */

.activity-timeline {
  overflow: visible;
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
  min-width: 0;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 8px;
}

.activity-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.activity-type {
  font-size: 14px;
  font-weight: 500;
  color: #3b82f6;
}

.activity-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.activity-text {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  margin: 8px 0 10px;
  padding: 12px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.activity-text-preview {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  white-space: normal;
  word-break: break-word;
}

.communication-title {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.communication-title.customer-start,
.communication-title.customer-reply {
  color: var(--communication-customer-text);
  background: var(--communication-customer-bg);
  border: 1px solid var(--communication-customer-border);
}

.communication-title.our-start,
.communication-title.our-reply {
  color: var(--communication-our-text);
  background: var(--communication-our-bg);
  border: 1px solid var(--communication-our-border);
}

.communication-title.internal {
  color: var(--communication-internal-text);
  background: var(--communication-internal-bg);
  border: 1px solid var(--communication-internal-border);
}

.email-activity-preview {
  display: grid;
  gap: 8px;
}

.email-activity-subject {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.email-key-action {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 12px;
}

.email-key-action span {
  margin-right: 8px;
  color: var(--warning-text-strong);
  font-weight: 600;
}

.activity-detail-scroll::-webkit-scrollbar {
  width: 12px;
}

.activity-detail-scroll::-webkit-scrollbar-track {
  background: var(--bg-tertiary);
  border-radius: 999px;
}

.activity-detail-scroll::-webkit-scrollbar-thumb {
  background: #60a5fa;
  border-radius: 999px;
  border: 3px solid var(--bg-tertiary);
}

.activity-detail-scroll::-webkit-scrollbar-thumb:hover {
  background: #93c5fd;
}

.activity-detail-btn {
  margin-top: 6px;
  padding: 0;
}

.activity-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.activity-owner {
  font-size: 12px;
  color: var(--text-tertiary);
}

.activity-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.activity-detail-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--text-muted);
  font-size: 13px;
}

.activity-detail-content {
  min-height: 420px;
  padding: 16px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.email-detail-content {
  display: grid;
  gap: 14px;
  padding: 2px 14px 16px 2px;
}

.email-detail-hero,
.email-detail-section,
.email-original-detail {
  padding: 14px 16px;
  border-radius: 9px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
}

.email-detail-subject {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.5;
}

.email-detail-summary {
  margin-top: 10px;
  color: var(--text-secondary);
  line-height: 1.75;
}

.email-responsibility {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 8px;
  color: var(--text-secondary);
  background: var(--communication-our-bg);
  border: 1px solid var(--communication-our-border);
}

.email-responsibility span {
  color: var(--text-tertiary);
  font-size: 12px;
}

.email-responsibility strong {
  color: var(--communication-our-text);
}

.email-responsibility small {
  margin-left: auto;
  color: var(--text-tertiary);
}

.email-detail-section h4 {
  margin: 0 0 10px;
  color: var(--accent-color);
  font-size: 13px;
}

.email-detail-section p,
.email-detail-list {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.75;
}

.email-detail-list {
  padding-left: 22px;
}

.email-detail-list li + li {
  margin-top: 7px;
}

.risk-section {
  border-color: rgba(245, 158, 11, 0.3);
}

.risk-section h4 {
  color: var(--warning-text-strong);
}

.email-meta-section dl {
  display: grid;
  gap: 8px;
  margin: 0;
}

.email-meta-section dl div {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
}

.email-meta-section dt {
  color: var(--text-muted);
}

.email-meta-section dd {
  margin: 0;
  color: var(--text-secondary);
  word-break: break-word;
}

.email-original-detail summary {
  cursor: pointer;
  color: var(--accent-color);
  font-weight: 600;
}

.email-original-detail div {
  margin-top: 12px;
  color: var(--text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.activity-detail-scroll {
  max-height: min(64vh, 580px);
  overflow-y: auto;
  border-radius: 8px;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: var(--accent-color) var(--bg-tertiary);
}

.activity-detail-footer {
  font-size: 13px;
  color: var(--text-muted);
}

:deep(.activity-detail-dialog .el-dialog) {
  max-height: 82vh;
  display: flex;
  flex-direction: column;
}

:deep(.activity-detail-dialog .el-dialog__body) {
  overflow: hidden;
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
