<template>
  <div class="quote-list-container fade-in">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="page-title-section">
        <h2 class="page-title">💰 报价管理</h2>
        <p class="page-subtitle">软件报价单 - 授权明细 + 实施服务</p>
      </div>
      <el-button type="primary" size="large" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建报价单
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索报价标题/编号..."
        class="filter-input"
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select v-model="filters.status" placeholder="状态" clearable class="filter-select" @change="handleSearch">
        <el-option label="草稿" value="草稿" />
        <el-option label="已发送" value="已发送" />
        <el-option label="已接受" value="已接受" />
        <el-option label="已拒绝" value="已拒绝" />
        <el-option label="已过期" value="已过期" />
      </el-select>

      <el-button @click="handleSearch"><el-icon><Search /></el-icon>搜索</el-button>
      <el-button @click="handleReset"><el-icon><Refresh /></el-icon>重置</el-button>
    </div>

    <!-- 报价列表 -->
    <div class="table-container">
      <el-table :data="quoteList" v-loading="loading" class="data-table" @row-click="handleRowClick">
        <el-table-column prop="quote_no" label="报价单号" width="160">
          <template #default="{ row }">
            <span class="quote-no">{{ row.quote_no }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="quote_title" label="报价主题" min-width="200">
          <template #default="{ row }">
            <span class="quote-title">{{ row.quote_title }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="customer_name" label="客户" width="150" />

        <el-table-column prop="grand_total" label="总价" width="150">
          <template #default="{ row }">
            <span class="amount">{{ formatCurrency(row.grand_total, row.currency) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="quote_date" label="报价日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.quote_date) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </div>

    <!-- 创建/编辑对话框 - 软件报价单 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="960px"
      class="quote-dialog"
      :close-on-click-modal="false"
    >
      <el-form ref="quoteFormRef" :model="quoteForm" :rules="quoteRules" label-width="100px" class="quote-form">

        <!-- 基础信息 -->
        <div class="section-title">📋 基础信息</div>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="报价主题" prop="quote_title">
              <el-input v-model="quoteForm.quote_title" placeholder="如：XX银行数字化转型项目软件报价" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="客户" prop="customer_id">
              <el-select v-model="quoteForm.customer_id" placeholder="选择客户" filterable>
                <el-option v-for="c in customerOptions" :key="c.id" :label="c.customer_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="报价日期" prop="quote_date">
              <el-date-picker v-model="quoteForm.quote_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="有效期至">
              <el-date-picker v-model="quoteForm.valid_until" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="币种">
              <el-select v-model="quoteForm.currency" style="width:100%">
                <el-option label="USD 美元" value="USD" />
                <el-option label="CNY 人民币" value="CNY" />
                <el-option label="EUR 欧元" value="EUR" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 软件授权明细 -->
        <div class="section-title">📦 软件授权明细</div>
        <div class="items-section">
          <table class="item-table">
            <thead>
              <tr>
                <th style="width:25%">产品名称</th>
                <th style="width:12%">版本</th>
                <th style="width:18%">授权类型</th>
                <th style="width:8%">数量</th>
                <th style="width:14%">单价</th>
                <th style="width:14%">小计</th>
                <th style="width:40px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in quoteForm.license_items" :key="'lic-' + idx">
                <td><el-input v-model="item.product_name" size="small" placeholder="产品名称" /></td>
                <td><el-input v-model="item.version" size="small" placeholder="版本" /></td>
                <td>
                  <el-select v-model="item.license_type" size="small" style="width:100%">
                    <el-option label="永久授权" value="perpetual" />
                    <el-option label="年度订阅" value="annual_subscription" />
                    <el-option label="并发用户" value="concurrent" />
                    <el-option label="命名用户" value="named" />
                  </el-select>
                </td>
                <td><el-input-number v-model="item.qty" size="small" :min="1" style="width:100%"
                    @change="calcLicenseSubtotal(idx)" /></td>
                <td>
                  <el-input-number v-model="item.unit_price" size="small" :min="0" :precision="2" style="width:100%"
                    @change="calcLicenseSubtotal(idx)" />
                </td>
                <td class="subtotal-cell">{{ formatCurrency(item.subtotal, quoteForm.currency) }}</td>
                <td><el-button link type="danger" size="small" @click="removeLicenseItem(idx)" :disabled="quoteForm.license_items.length <= 1">×</el-button></td>
              </tr>
            </tbody>
          </table>
          <el-button type="primary" plain size="small" @click="addLicenseItem" class="add-btn">+ 添加授权项</el-button>
        </div>

        <!-- 实施服务明细 -->
        <div class="section-title">🔧 实施服务明细</div>
        <div class="items-section">
          <table class="item-table">
            <thead>
              <tr>
                <th style="width:20%">服务类型</th>
                <th style="width:30%">描述</th>
                <th style="width:10%">天数</th>
                <th style="width:15%">人天费率</th>
                <th style="width:15%">小计</th>
                <th style="width:40px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in quoteForm.service_items" :key="'svc-' + idx">
                <td>
                  <el-select v-model="item.service_type" size="small" style="width:100%">
                    <el-option label="实施服务" value="implementation" />
                    <el-option label="培训服务" value="training" />
                    <el-option label="定制开发" value="customization" />
                    <el-option label="数据迁移" value="data_migration" />
                    <el-option label="系统集成" value="integration" />
                    <el-option label="技术支持" value="support" />
                  </el-select>
                </td>
                <td><el-input v-model="item.description" size="small" placeholder="服务说明" /></td>
                <td><el-input-number v-model="item.quantity" size="small" :min="0" style="width:100%"
                    @change="calcServiceSubtotal(idx)" /></td>
                <td>
                  <el-input-number v-model="item.daily_rate" size="small" :min="0" :precision="2" style="width:100%"
                    @change="calcServiceSubtotal(idx)" />
                </td>
                <td class="subtotal-cell">{{ formatCurrency(item.subtotal, quoteForm.currency) }}</td>
                <td><el-button link type="danger" size="small" @click="removeServiceItem(idx)" :disabled="quoteForm.service_items.length <= 1">×</el-button></td>
              </tr>
            </tbody>
          </table>
          <el-button type="success" plain size="small" @click="addServiceItem" class="add-btn">+ 添加服务项</el-button>
        </div>

        <!-- 汇总信息 -->
        <div class="summary-section">
          <div class="section-title">🧾 费用汇总</div>
          <div class="summary-grid">
            <div class="summary-line">
              <span class="summary-label">授权费小计:</span>
              <span class="summary-value">{{ formatCurrency(licenseSubtotal, quoteForm.currency) }}</span>
            </div>
            <div class="summary-line">
              <span class="summary-label">服务费小计:</span>
              <span class="summary-value">{{ formatCurrency(serviceSubtotal, quoteForm.currency) }}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-line">
              <span class="summary-label">折扣率 (%):</span>
              <el-input-number v-model="quoteForm.discount_rate" size="small" :min="0" :max="100" :precision="1"
                style="width:100px" @change="recalcTotal" /> %
            </div>
            <div class="summary-line discount-line">
              <span class="summary-label">折扣金额:</span>
              <span class="summary-value discount">{{ formatCurrency(discountAmount, quoteForm.currency) }}</span>
            </div>
            <div class="summary-line">
              <span class="summary-label">税率 (%):</span>
              <el-input-number v-model="quoteForm.tax_rate" size="small" :min="0" :max="30" :precision="1"
                style="width:100px" @change="recalcTotal" /> %
            </div>
            <div class="summary-line tax-line">
              <span class="summary-label">税额:</span>
              <span class="summary-value tax">{{ formatCurrency(taxAmount, quoteForm.currency) }}</span>
            </div>
            <div class="summary-total">
              <span class="summary-label grand-total-label">总计 (Grand Total):</span>
              <span class="grand-total-amount">{{ formatCurrency(grandTotal, quoteForm.currency) }}</span>
            </div>
          </div>
        </div>

        <!-- 备注 -->
        <el-form-item label="内部备注">
          <el-input v-model="quoteForm.internal_notes" type="textarea" :rows="2" placeholder="仅内部可见的备注" />
        </el-form-item>
        <el-form-item label="客户说明">
          <el-input v-model="quoteForm.customer_notes" type="textarea" :rows="2" placeholder="将显示在报价单上的说明文字" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">保存报价单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getQuotes, createQuote, updateQuote, deleteQuote } from '@/api/quote'
import { getCustomers } from '@/api/customer'
import type { Quote, CreateQuoteRequest, LicenseItem, ServiceItem } from '@/types/quote'

// 数据列表
const quoteList = ref<Quote[]>([])
const loading = ref(false)

// 筛选条件
const filters = reactive({
  keyword: '',
  status: undefined as string | undefined,
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('新建报价单')
const isEdit = ref(false)
const submitLoading = ref(false)
const quoteFormRef = ref()
const currentQuoteId = ref('')

// 默认授权项
function defaultLicenseItem(): LicenseItem {
  return {
    product_name: '',
    version: '',
    license_type: 'perpetual',
    qty: 1,
    unit_price: 0,
    subtotal: 0,
  }
}

// 默认服务项
function defaultServiceItem(): ServiceItem {
  return {
    service_type: 'implementation',
    description: '',
    quantity: 1,
    daily_rate: 800,
    subtotal: 800,
  }
}

// 报价表单
const quoteForm = reactive<CreateQuoteRequest & {
  license_items: LicenseItem[]
  service_items: ServiceItem[]
}>({
  customer_id: '',
  project_id: undefined,
  quote_title: '',
  quote_date: new Date().toISOString().split('T')[0],
  valid_until: undefined,
  currency: 'USD',
  license_items: [defaultLicenseItem()],
  license_subtotal: 0,
  service_items: [defaultServiceItem()],
  service_subtotal: 0,
  discount_rate: 0,
  discount_amount: 0,
  tax_rate: 0,
  tax_amount: 0,
  grand_total: 0,
  internal_notes: '',
  customer_notes: '',
})

// 校验规则
const quoteRules = {
  customer_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
  quote_title: [{ required: true, message: '请输入报价主题', trigger: 'blur' }],
  quote_date: [{ required: true, message: '请选择报价日期', trigger: 'change' }],
}

// 计算属性：授权费小计
const licenseSubtotal = computed(() => {
  return quoteForm.license_items.reduce((sum, item) => sum + (Number(item.unit_price) * Number(item.qty)), 0)
})

// 计算属性：服务费小计
const serviceSubtotal = computed(() => {
  return quoteForm.service_items.reduce((sum, item) => sum + (Number(item.daily_rate) * Number(item.quantity)), 0)
})

// 折扣金额
const discountAmount = computed(() => {
  const base = licenseSubtotal.value + serviceSubtotal.value
  return Math.round(base * Number(quoteForm.discount_rate) / 100 * 100) / 100
})

// 税额
const taxAmount = computed(() => {
  const afterDiscount = licenseSubtotal.value + serviceSubtotal.value - discountAmount.value
  return Math.round(afterDiscount * Number(quoteForm.tax_rate) / 100 * 100) / 100
})

// 总计
const grandTotal = computed(() => {
  const base = licenseSubtotal.value + serviceSubtotal.value
  return Math.round((base - discountAmount.value + taxAmount.value) * 100) / 100
})

// 自动重新计算总计
function recalcTotal() {
  // 计算每项小计
  quoteForm.license_items.forEach(item => {
    item.subtotal = Number(item.unit_price) * Number(item.qty)
  })
  quoteForm.service_items.forEach(item => {
    item.subtotal = Number(item.daily_rate) * Number(item.quantity)
  })
  // 汇总
  quoteForm.license_subtotal = licenseSubtotal.value as any
  quoteForm.service_subtotal = serviceSubtotal.value as any
  quoteForm.discount_amount = discountAmount.value as any
  quoteForm.tax_amount = taxAmount.value as any
  quoteForm.grand_total = grandTotal.value as any
}

// 单项计算
function calcLicenseSubtotal(_idx: number) {
  recalcTotal()
}
function calcServiceSubtotal(_idx: number) {
  recalcTotal()
}

function addLicenseItem() {
  quoteForm.license_items.push(defaultLicenseItem())
}
function removeLicenseItem(idx: number) {
  quoteForm.license_items.splice(idx, 1)
  recalcTotal()
}
function addServiceItem() {
  quoteForm.service_items.push(defaultServiceItem())
}
function removeServiceItem(idx: number) {
  quoteForm.service_items.splice(idx, 1)
  recalcTotal()
}

// 选项
const customerOptions = ref<any[]>([])

async function loadCustomers() {
  try {
    const res = await getCustomers({ page: 1, page_size: 1000 })
    customerOptions.value = res.data.items
  } catch (e) {
    console.error('加载客户失败', e)
  }
}

// 加载列表
async function loadQuotes() {
  loading.value = true
  try {
    const res = await getQuotes({
      page: pagination.page,
      page_size: pagination.page_size,
    })
    quoteList.value = res.data.items
    pagination.total = res.data.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() { pagination.page = 1; loadQuotes() }
function handleReset() {
  filters.keyword = ''; filters.status = undefined; pagination.page = 1; loadQuotes()
}

function handleCreate() {
  dialogTitle.value = '新建报价单'
  isEdit.value = false
  currentQuoteId.value = ''
  resetForm()
  loadCustomers()
  dialogVisible.value = true
}

function handleEdit(row: Quote) {
  dialogTitle.value = '编辑报价单'
  isEdit.value = true
  currentQuoteId.value = row.id
  Object.assign(quoteForm, {
    customer_id: row.customer_id,
    project_id: row.project_id,
    quote_title: row.quote_title,
    quote_date: row.quote_date.split('T')[0],
    valid_until: row.valid_until?.split('T')[0],
    currency: row.currency,
    license_items: row.license_items?.length ? [...row.license_items] : [defaultLicenseItem()],
    service_items: row.service_items?.length ? [...row.service_items] : [defaultServiceItem()],
    discount_rate: row.discount_rate ?? 0,
    tax_rate: row.tax_rate ?? 0,
    internal_notes: row.internal_notes || '',
    customer_notes: row.customer_notes || '',
  })
  recalcTotal()
  loadCustomers()
  dialogVisible.value = true
}

async function handleDelete(row: Quote) {
  try {
    await ElMessageBox.confirm(`确定要删除报价单「${row.quote_title}」吗？`, '确认删除', { type: 'warning' })
    await deleteQuote(row.id)
    ElMessage.success('删除成功')
    loadQuotes()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
  }
}

async function handleSubmit() {
  if (!quoteFormRef.value) return
  await quoteFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    submitLoading.value = true
    try {
      // 最终计算
      recalcTotal()
      const submitData = {
        ...quoteForm,
        license_subtotal: licenseSubtotal.value,
        service_subtotal: serviceSubtotal.value,
        discount_amount: discountAmount.value,
        tax_amount: taxAmount.value,
        grand_total: grandTotal.value,
      }

      if (isEdit.value) {
        await updateQuote(currentQuoteId.value, submitData)
        ElMessage.success('更新成功')
      } else {
        await createQuote(submitData as CreateQuoteRequest)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      loadQuotes()
    } catch (error: any) {
      ElMessage.error(error.message || '操作失败')
    } finally {
      submitLoading.value = false
    }
  })
}

function resetForm() {
  Object.assign(quoteForm, {
    customer_id: '',
    project_id: undefined,
    quote_title: '',
    quote_date: new Date().toISOString().split('T')[0],
    valid_until: undefined,
    currency: 'USD',
    license_items: [defaultLicenseItem()],
    service_items: [defaultServiceItem()],
    discount_rate: 0,
    discount_amount: 0,
    tax_rate: 0,
    tax_amount: 0,
    grand_total: 0,
    internal_notes: '',
    customer_notes: '',
  })
  recalcTotal()
}

function handleRowClick(_row: Quote) {
  // TODO: 跳转到详情页
}

function getStatusType(status: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    '草稿': 'info', '已发送': 'warning', '已接受': 'success', '已拒绝': 'danger', '已过期': 'info',
  }
  return map[status] || 'info'
}

function formatCurrency(amount: number | undefined, currency: string = 'USD'): string {
  if (amount == null) return '-'
  return `${currency} ${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
}
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return dateStr.split('T')[0]
}

onMounted(() => { loadQuotes() })
</script>

<style scoped>
.quote-list-container { max-width: 1400px; margin: 0 auto; }

.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: var(--text-muted); margin: 0; }

.filter-bar { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.filter-input { width: 280px; }
.filter-select { width: 150px; }

.table-container { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 16px; padding: 20px; }

.data-table :deep(.el-table__header th) { background: var(--bg-tertiary) !important; color: var(--text-muted) !important; }
.data-table :deep(.el-table__row td) { border-bottom: 1px solid var(--border-color); color: var(--text-secondary); cursor: pointer; }
.data-table :deep(.el-table__row:hover) { background: var(--bg-tertiary) !important; }

.quote-no { font-family: monospace; font-size: 13px; color: var(--accent-color); }
.quote-title { font-weight: 500; color: var(--text-secondary); }
.amount { font-weight: 700; color: var(--success-color); font-size: 14px; }

.pagination-container { display: flex; justify-content: flex-end; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border-color); }

/* ===== 对话框样式 ===== */
.quote-dialog :deep(.el-dialog) { background: var(--bg-secondary); border: 1px solid var(--border-color); }
.quote-dialog :deep(.el-dialog__title) { color: var(--text-secondary); font-size: 18px; font-weight: 600; }
.quote-dialog :deep(.el-dialog__header) { border-bottom: 1px solid var(--border-color); padding-bottom: 16px; }
.quote-form :deep(.el-form-item__label) { color: var(--text-muted); }
.quote-form :deep(.el-input__wrapper) { background: var(--bg-tertiary); box-shadow: 0 0 0 1px var(--border-color) inset; }
.quote-form :deep(.el-input__inner) { color: var(--text-secondary); }

.section-title {
  font-size: 15px; font-weight: 600; color: var(--accent-color);
  margin: 20px 0 12px 0; padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.items-section { margin-bottom: 8px; }
.item-table {
  width: 100%; border-collapse: collapse; margin-bottom: 8px;
  background: var(--bg-tertiary); border-radius: 8px; overflow: hidden;
}
.item-table th {
  text-align: left; padding: 8px 10px; font-size: 13px; font-weight: 500;
  color: var(--text-muted); background: var(--bg-primary); border-bottom: 1px solid var(--border-color);
}
.item-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-color); vertical-align: middle; }
.item-table :deep(.el-input__wrapper) { background: var(--bg-secondary) !important; box-shadow: 0 0 0 1px var(--border-color) inset !important; }
.item-table :deep(.el-input__inner) { color: var(--text-secondary) !important; height: 32px !important; font-size: 13px; }
.subtotal-cell { text-align: right; color: var(--success-color); font-weight: 500; font-size: 13px; white-space: nowrap; }
.add-btn { margin-top: 8px; }

/* ===== 汇总区域 ===== */
.summary-section {
  background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px 20px; margin: 16px 0;
}
.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 32px; }
.summary-line { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
.summary-label { color: var(--text-muted); font-size: 13px; }
.summary-value { color: var(--text-secondary); font-weight: 500; text-align: right; }
.summary-divider { grid-column: 1 / -1; border-top: 1px dashed var(--border-color); margin: 8px 0; }
.discount-line .summary-value { color: var(--warning-color); }
.tax-line .summary-value { color: var(--info-color); }
.summary-total {
  grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center;
  padding-top: 12px; margin-top: 8px; border-top: 2px solid var(--border-color);
}
.grand-total-label { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.grand-total-amount { font-size: 22px; font-weight: 700; color: var(--success-color); }
</style>
