<template>
  <div class="customer-list-container fade-in">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">👥 客户管理</h2>
        <p class="page-subtitle">管理海外客户信息</p>
      </div>
      <el-button type="primary" size="large" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        创建客户
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="filters.customer_name"
        placeholder="搜索客户名称..."
        class="filter-input"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-input
        v-model="filters.country"
        placeholder="国家"
        class="filter-input-sm"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      />

      <el-button @click="handleSearch">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>

      <el-button @click="handleReset">
        <el-icon><Refresh /></el-icon>
        重置
      </el-button>
    </div>

    <!-- 客户表格 -->
    <div class="table-container">
      <el-table
        :data="customerList"
        v-loading="loading"
        class="data-table"
        @row-click="handleRowClick"
      >
        <el-table-column prop="customer_name" label="客户名称" min-width="200">
          <template #default="{ row }">
            <span class="customer-name">{{ row.customer_name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="country" label="国家" width="120" />

        <el-table-column prop="industry" label="行业" width="150" />

        <el-table-column prop="contact_person" label="联系人" width="120" />

        <el-table-column prop="contact_email" label="联系邮箱" width="200">
          <template #default="{ row }">
            <span class="email-text">{{ row.contact_email || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="total_projects" label="项目数" width="100" align="center">
          <template #default="{ row }">
            <span class="stat-value">{{ row.total_projects }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="total_amount" label="成交金额" width="150">
          <template #default="{ row }">
            <span class="amount">{{ formatCurrency(row.total_amount) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="handleEdit(row)">
              编辑
            </el-button>
            <el-button link type="danger" @click.stop="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="800px"
      class="customer-dialog"
    >
      <el-form
        ref="customerFormRef"
        :model="customerForm"
        :rules="customerRules"
        label-width="120px"
        class="customer-form"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="客户名称" prop="customer_name">
              <el-input v-model="customerForm.customer_name" placeholder="请输入客户名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="国家" prop="country">
              <el-input v-model="customerForm.country" placeholder="请输入国家" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="行业">
              <el-input v-model="customerForm.industry" placeholder="请输入行业" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="客户类型">
              <el-select v-model="customerForm.customer_type" placeholder="请选择客户类型">
                <el-option label="企业" value="企业" />
                <el-option label="政府" value="政府" />
                <el-option label="教育" value="教育" />
                <el-option label="非营利组织" value="非营利组织" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="customerForm.contact_person" placeholder="请输入联系人" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="customerForm.contact_phone" placeholder="请输入联系电话" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="联系邮箱">
              <el-input v-model="customerForm.contact_email" placeholder="请输入联系邮箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="客户地址">
              <el-input v-model="customerForm.address" placeholder="请输入客户地址" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getCustomers, createCustomer, updateCustomer, deleteCustomer } from '@/api/customer'
import type { Customer, CreateCustomerRequest } from '@/types/customer'

const router = useRouter()

// 数据列表
const customerList = ref<Customer[]>([])
const loading = ref(false)

// 筛选条件
const filters = reactive({
  customer_name: '',
  country: '',
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('创建客户')
const isEdit = ref(false)
const submitLoading = ref(false)
const customerFormRef = ref()
const currentCustomerId = ref('')

// 客户表单
const customerForm = reactive<CreateCustomerRequest>({
  customer_name: '',
  country: '',
  industry: undefined,
  customer_type: '企业',
  contact_person: undefined,
  contact_phone: undefined,
  contact_email: undefined,
  address: undefined,
})

// 表单校验
const customerRules = {
  customer_name: [
    { required: true, message: '请输入客户名称', trigger: 'blur' },
  ],
  country: [
    { required: true, message: '请输入国家', trigger: 'blur' },
  ],
}

// 加载客户列表
async function loadCustomers() {
  loading.value = true
  try {
    const res = await getCustomers({
      page: pagination.page,
      page_size: pagination.page_size,
      customer_name: filters.customer_name || undefined,
      country: filters.country || undefined,
    })
    customerList.value = res.data.items
    pagination.total = res.data.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// 搜索
function handleSearch() {
  pagination.page = 1
  loadCustomers()
}

// 重置
function handleReset() {
  filters.customer_name = ''
  filters.country = ''
  pagination.page = 1
  loadCustomers()
}

// 创建客户
function handleCreate() {
  dialogTitle.value = '创建客户'
  isEdit.value = false
  currentCustomerId.value = ''
  resetForm()
  dialogVisible.value = true
}

// 编辑客户
function handleEdit(row: Customer) {
  dialogTitle.value = '编辑客户'
  isEdit.value = true
  currentCustomerId.value = row.id
  Object.assign(customerForm, {
    customer_name: row.customer_name,
    country: row.country,
    industry: row.industry || undefined,
    customer_type: row.customer_type || '企业',
    contact_person: row.contact_person || undefined,
    contact_phone: row.contact_phone || undefined,
    contact_email: row.contact_email || undefined,
    address: row.address || undefined,
  })
  dialogVisible.value = true
}

// 删除客户
async function handleDelete(row: Customer) {
  try {
    await ElMessageBox.confirm(
      `确定要删除客户「${row.customer_name}」吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await deleteCustomer(row.id)
    ElMessage.success('删除成功')
    loadCustomers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 提交表单
async function handleSubmit() {
  if (!customerFormRef.value) return
  
  await customerFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      submitLoading.value = true
      try {
        // 过滤空字符串，避免后端验证失败
        const submitData = Object.fromEntries(
          Object.entries(customerForm).map(([key, value]) => [
            key,
            value === '' ? undefined : value
          ])
        )
        
        if (isEdit.value) {
          await updateCustomer(currentCustomerId.value, submitData)
          ElMessage.success('更新成功')
        } else {
          await createCustomer(submitData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadCustomers()
      } catch (error: any) {
        ElMessage.error(error.message || '操作失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 重置表单
function resetForm() {
  Object.assign(customerForm, {
    customer_name: '',
    country: '',
    industry: undefined,
    customer_type: '企业',
    contact_person: undefined,
    contact_phone: undefined,
    contact_email: undefined,
    address: undefined,
  })
}

// 点击行跳转详情
function handleRowClick(row: Customer) {
  router.push(`/customers/${row.id}`)
}

// 格式化货币
function formatCurrency(amount: number | undefined) {
  if (!amount) return '-'
  return `USD ${amount.toLocaleString()}`
}

onMounted(() => {
  loadCustomers()
})
</script>

<style scoped>
.customer-list-container {
  max-width: 1600px;
  margin: 0 auto;
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
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

/* ============ 筛选栏 ============ */

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-input {
  width: 280px;
}

.filter-input-sm {
  width: 160px;
}

/* ============ 表格容器 ============ */

.table-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 20px;
}

.customer-name {
  font-weight: 500;
  color: var(--text-secondary);
}

.email-text {
  font-size: 13px;
  color: var(--text-muted);
}

.stat-value {
  font-weight: 600;
  color: var(--text-secondary);
}

.amount {
  font-weight: 600;
  color: var(--success-color);
}

/* ============ 分页容器 ============ */

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}
</style>
