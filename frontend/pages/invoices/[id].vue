<template>
  <div class="invoice-detail-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">← 返回</button>
      <h1 class="page-title">{{ event?.event_name || '发票管理' }}</h1>
      <div class="header-actions">
        <button @click="showAddModal = true" class="action-button primary">添加发票</button>
        <button @click="showVoucherModal = true" class="action-button voucher">添加凭证</button>
        <button @click="batchDownload" class="action-button warning" :disabled="selectedInvoices.length === 0">
          批量下载 ({{ selectedInvoices.length }})
        </button>
        <button @click="batchReimburse" class="action-button reimburse" :disabled="selectedInvoices.length === 0" v-if="canReviewInvoices">
          批量报销 ({{ selectedInvoices.length }})
        </button>
        <button @click="deleteSelected" class="action-button danger" :disabled="selectedInvoices.length === 0">
          删除 ({{ selectedInvoices.length }})
        </button>
      </div>
    </div>

    <!-- 预算信息面板 -->
    <div v-if="event" class="budget-panel">
      <div class="budget-card total-budget">
        <span class="budget-label">总预算</span>
        <span class="budget-value">¥ {{ formatMoney(event.total_budget) }}</span>
      </div>
      <div class="budget-card invoice-total">
        <span class="budget-label">发票总额</span>
        <span class="budget-value">¥ {{ formatMoney(event.invoice_total_amount) }}</span>
      </div>
      <div class="budget-card reimbursed">
        <span class="budget-label">已报销</span>
        <span class="budget-value">¥ {{ formatMoney(event.reimbursed_amount) }}</span>
      </div>
      <div class="budget-card remaining" :class="{ 'warning': remainingBudgetPercent < 20, 'danger': remainingBudgetPercent <= 5 }">
        <span class="budget-label">预算剩余</span>
        <span class="budget-value">¥ {{ formatMoney(remainingBudget) }}</span>
        <div class="progress-bar-container">
          <div class="progress-bar-fill" :style="{ width: remainingBudgetPercent + '%' }"></div>
        </div>
      </div>
    </div>

    <div class="invoices-table-container">
      <table class="invoices-table">
        <thead>
          <tr>
            <th class="checkbox-col">
              <input type="checkbox" v-model="selectAll" @change="toggleSelectAll" />
            </th>
            <th>发票类型</th>
            <th>项目名称</th>
            <th>金额</th>
            <th>开票日期</th>
            <th>状态</th>
            <th>报销</th>
            <th>上传时间</th>
            <th>上传人</th>
            <th>备注</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="invoice in invoices" :key="invoice.invoice_id">
            <td class="checkbox-col">
              <input type="checkbox" :value="invoice.invoice_id" v-model="selectedInvoices" />
            </td>
            <td>{{ invoice.invoice_type || '-' }}</td>
            <td>{{ invoice.project_name }}</td>
            <td class="amount">¥{{ parseFloat(invoice.amount).toFixed(2) }}</td>
            <td>{{ formatDate(invoice.invoice_date) }}</td>
            <td>
              <span class="status-badge" :class="invoice.status">
                {{ getStatusText(invoice.status) }}
              </span>
            </td>
            <td>
              <span class="reimburse-badge" :class="{ 'is-reimbursed': invoice.is_reimbursed }">
                {{ invoice.is_reimbursed ? '已报销' : '未报销' }}
              </span>
            </td>
            <td>{{ formatDateTime(invoice.created_at) }}</td>
            <td>{{ invoice.uploader_name || '-' }}</td>
            <td class="remarks-cell">{{ invoice.remarks || '无' }}</td>
            <td>
              <div class="action-buttons-vertical">
                <div class="action-row-top">
                  <template v-if="canReviewInvoices && invoice.status === 'pending'">
                    <button @click="approveInvoice(invoice)" class="btn-approve-sm" title="通过审核">✓ 通过</button>
                    <button @click="showRejectDialog(invoice)" class="btn-reject-sm" title="拒绝审核">✗ 拒绝</button>
                  </template>
                  <span v-if="!canReviewInvoices || invoice.status !== 'pending'" class="reviewed-info-sm">
                    {{ invoice.status === 'pending' ? '' : (invoice.reviewer_name ? `已审核` : '') }}
                  </span>
                </div>
                <div class="action-row-bottom">
                  <button @click="previewInvoice(invoice)" class="btn-preview-sm" title="预览发票">👁</button>
                  <button @click="editInvoice(invoice)" class="btn-edit-sm" title="编辑发票信息">✏</button>
                  <button @click="downloadInvoice(invoice)" class="btn-download-sm" title="下载原文件">⬇</button>
                  <button 
                    v-if="canReviewInvoices && invoice.status === 'approved' && !invoice.is_reimbursed" 
                    @click="reimburseInvoice(invoice)" 
                    class="btn-reimburse-sm"
                    title="标记为已报销"
                  >💰</button>
                </div>
              </div>
            </td>
          </tr>
          <tr v-if="invoices.length === 0">
              <td colspan="12" class="empty-row">暂无发票数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加发票弹窗 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h2>添加发票</h2>
          <button @click="showAddModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="addInvoice" class="modal-body">
          <div class="form-group">
            <label>发票图片 *</label>
            <div class="file-upload-section">
              <input 
                type="file" 
                @change="handleFileUpload" 
                accept=".pdf,.png,.jpg,.jpeg"
                required
                ref="fileInput"
              />
              <div class="file-hint">支持格式：PDF、PNG、JPG、JPEG</div>
              <div v-if="fileError" class="file-error">{{ fileError }}</div>
              <button 
                type="button" 
                @click="parseInvoice" 
                class="parse-button"
                :disabled="!newInvoice.file || parsing"
              >
                {{ parsing ? '解析中...' : '一键解析' }}
              </button>
            </div>
          </div>
          
          <div v-if="parseError" class="parse-error">
            <span class="error-icon">⚠️</span>
            {{ parseError }}
          </div>
          
          <div v-if="parseSuccess" class="parse-success">
            <span class="success-icon">✅</span>
            发票数据已自动填充，请核对后提交
            <div v-if="fieldPermissions.readonly.length > 0" class="field-notice">
              <strong>⚠️ 注意：</strong>以下字段为系统自动提取，不可手动修改：
              <span class="readonly-fields">{{ fieldPermissions.readonly.join('、') }}</span>
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label>发票类型 <span v-if="fieldPermissions.editable.includes('invoice_type')" class="editable-tag">可编辑</span></label>
              <input v-model="newInvoice.invoice_type" type="text" placeholder="如：餐饮、交通、住宿" />
            </div>
            <div class="form-group">
              <label>项目名称 * <span v-if="fieldPermissions.editable.includes('project_name')" class="editable-tag">可编辑</span></label>
              <input v-model="newInvoice.project_name" type="text" required />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>价税合计（不可编辑）<span class="readonly-tag">系统提取</span></label>
              <input 
                v-model.number="newInvoice.total_amount" 
                type="number" 
                step="0.01" 
                min="0" 
                disabled
                :class="{ 'readonly-field': fieldPermissions.readonly.includes('total_amount') }"
              />
            </div>
            <div class="form-group">
              <label>开票日期（不可编辑）<span class="readonly-tag">系统提取</span></label>
              <input 
                v-model="newInvoice.invoice_date" 
                type="date" 
                required
                disabled
                :class="{ 'readonly-field': fieldPermissions.readonly.includes('invoice_date') }"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>发票号码（不可编辑）<span class="readonly-tag">系统提取</span></label>
              <input 
                v-model="newInvoice.invoice_number" 
                type="text" 
                disabled
                :class="{ 'readonly-field': fieldPermissions.readonly.includes('invoice_number') }"
              />
            </div>
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="newInvoice.remarks" rows="3"></textarea>
          </div>
          <div class="modal-footer">
            <button type="button" @click="showAddModal = false" class="cancel-button">取消</button>
            <button type="submit" class="submit-button" :disabled="uploading">
              {{ uploading ? '上传中...' : '添加' }}
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <div v-if="showDuplicateAlert" class="duplicate-alert-overlay" @click.self="showDuplicateAlert = false">
      <div class="duplicate-alert-modal">
        <h3>⚠️ 重复上传检测</h3>
        <p class="duplicate-message">{{ duplicateMessage }}</p>
        <div v-if="duplicateData?.existing_invoice_id" class="duplicate-actions">
          <a :href="`/invoices/${eventId}`" class="view-existing-link">查看已存在的发票 →</a>
        </div>
        <button @click="showDuplicateAlert = false" class="duplicate-close-btn">我知道了</button>
      </div>
    </div>

    <div v-if="showRejectModal" class="reject-modal-overlay" @click.self="showRejectModal = false">
      <div class="reject-modal-content">
        <h3>✗ 拒绝发票审核</h3>
        <p class="reject-invoice-info">发票：{{ currentRejectInvoice?.project_name }}</p>
        <div class="form-group">
          <label>拒绝原因 *（必填）</label>
          <textarea
            v-model="rejectionReason"
            rows="4"
            placeholder="请输入拒绝原因，将通知上传人"
            required
          ></textarea>
        </div>
        <div class="reject-actions">
          <button @click="showRejectModal = false" class="btn-cancel">取消</button>
          <button @click="rejectInvoice" class="btn-confirm-reject" :disabled="reviewing">
            {{ reviewing ? '提交中...' : '确认拒绝' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showPreviewModal" class="preview-modal-overlay" @click.self="showPreviewModal = false">
      <div class="preview-modal-content">
        <div class="preview-header">
          <h3>📄 发票预览 - {{ currentPreviewInvoice?.project_name }}</h3>
          <button @click="showPreviewModal = false" class="close-button">×</button>
        </div>
        <div class="preview-body">
          <div v-if="previewLoading" class="loading-spinner">加载预览图...</div>
          <img 
            v-else-if="previewImageUrl" 
            :src="previewImageUrl" 
            alt="发票预览" 
            class="preview-image"
            @error="previewError = true"
          />
          <div v-else-if="previewError" class="preview-error">
            <p>⚠️ 预览图加载失败</p>
            <button @click="generatePreviewImage" class="retry-btn">重新生成</button>
          </div>
          <div v-else class="no-preview">
            <p>暂无预览图</p>
            <button @click="generatePreviewImage" class="retry-btn">生成预览图</button>
          </div>
        </div>
        <div class="preview-info">
          <div class="info-row"><strong>发票类型：</strong>{{ currentPreviewInvoice?.invoice_type || '-' }}</div>
          <div class="info-row"><strong>金额：</strong>¥{{ currentPreviewInvoice ? parseFloat(currentPreviewInvoice.amount).toFixed(2) : '0.00' }}</div>
          <div class="info-row"><strong>开票日期：</strong>{{ currentPreviewInvoice?.invoice_date || '-' }}</div>
          <div class="info-row"><strong>发票号码：</strong>{{ currentPreviewInvoice?.invoice_number || '-' }}</div>
        </div>
      </div>
    </div>

    <div v-if="showEditModal" class="edit-modal-overlay" @click.self="showEditModal = false">
      <div class="edit-modal-content">
        <div class="modal-header">
          <h2>✏ 编辑发票信息</h2>
          <button @click="showEditModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="updateInvoice" class="modal-body">
          <div class="form-group">
            <label>发票类型</label>
            <input v-model="editForm.invoice_type" type="text" placeholder="如：餐饮、交通、住宿" />
          </div>
          <div class="form-group">
            <label>项目名称 *</label>
            <input v-model="editForm.project_name" type="text" required />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>金额 *</label>
              <input v-model.number="editForm.amount" type="number" step="0.01" min="0" required />
            </div>
            <div class="form-group">
              <label>开票日期 *</label>
              <input v-model="editForm.invoice_date" type="date" required />
            </div>
          </div>
          <div class="form-group">
            <label>发票号码</label>
            <input v-model="editForm.invoice_number" type="text" />
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="editForm.remarks" rows="3"></textarea>
          </div>
          <div class="modal-footer">
            <button type="button" @click="showEditModal = false" class="cancel-button">取消</button>
            <button type="submit" class="submit-button" :disabled="editing">
              {{ editing ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 凭证上传弹窗 -->
    <div v-if="showVoucherModal" class="modal-overlay" @click.self="showVoucherModal = false">
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h2>📋 添加凭证</h2>
          <button @click="showVoucherModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="addVoucher" class="modal-body">
          <div class="form-group">
            <label>凭证文件 *</label>
            <input type="file" @change="handleVoucherFileUpload" accept=".pdf,.png,.jpg,.jpeg" required ref="voucherFileInput" />
            <div class="file-hint">支持格式：PDF、PNG、JPG、JPEG</div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>物品名称 *</label>
              <input v-model="voucherForm.item_name" type="text" required placeholder="如：办公用品、设备等" />
            </div>
            <div class="form-group">
              <label>类型</label>
              <input v-model="voucherForm.voucher_type" type="text" placeholder="如：办公耗材、电子设备等" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>购买渠道</label>
              <input v-model="voucherForm.purchase_channel" type="text" placeholder="如：京东、淘宝等" />
            </div>
            <div class="form-group">
              <label>购入日期</label>
              <input v-model="voucherForm.purchase_date" type="date" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>购入金额 * (元)</label>
              <input v-model.number="voucherForm.amount" type="number" step="0.01" min="0" required />
            </div>
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="voucherForm.remarks" rows="2"></textarea>
          </div>
          <div class="modal-footer">
            <button type="button" @click="showVoucherModal = false" class="cancel-button">取消</button>
            <button type="submit" class="submit-button voucher-submit" :disabled="uploadingVoucher">
              {{ uploadingVoucher ? '上传中...' : '上传凭证' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCacheStore } from '~/stores/cache'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const cacheStore = useCacheStore()
const route = useRoute()

const eventId = route.params.id
const event = ref(null)
const invoices = ref([])
const selectedInvoices = ref([])
const showAddModal = ref(false)
const uploading = ref(false)
const fileError = ref('')
const parsing = ref(false)
const parseError = ref('')
const parseSuccess = ref(false)
const fileInput = ref(null)
const showDuplicateAlert = ref(false)
const duplicateMessage = ref('')
const duplicateData = ref(null)
const needInvoiceReview = ref(true)
const canReviewInvoices = computed(() => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    try {
      const user = JSON.parse(userStr)
      return ['admin', 'teacher'].includes(user.user_type)
    } catch (e) {
      return false
    }
  }
  return false
})

const remainingBudget = computed(() => {
  if (!event.value) return 0
  return Number(event.value.total_budget) - Number(event.value.reimbursed_amount)
})

const remainingBudgetPercent = computed(() => {
  if (!event.value || !event.value.total_budget || event.value.total_budget == 0) return 100
  const remaining = remainingBudget.value
  const total = Number(event.value.total_budget)
  return Math.max(0, Math.min(100, (remaining / total) * 100))
})

const formatMoney = (value) => {
  if (!value && value !== 0) return '0.00'
  return Number(value).toFixed(2)
}
const showRejectModal = ref(false)
const currentRejectInvoice = ref(null)
const rejectionReason = ref('')
const reviewing = ref(false)

// 预览相关
const showPreviewModal = ref(false)
const currentPreviewInvoice = ref(null)
const previewImageUrl = ref('')
const previewLoading = ref(false)
const previewError = ref(false)

// 编辑相关
const showEditModal = ref(false)
const editing = ref(false)
const editForm = ref({
  invoice_type: '',
  project_name: '',
  amount: 0,
  invoice_date: '',
  invoice_number: '',
  remarks: ''
})
const currentEditInvoiceId = ref(null)

// 下载相关
const downloading = ref(false)

const showVoucherModal = ref(false)
const uploadingVoucher = ref(false)
const voucherForm = ref({
  item_name: '',
  voucher_type: '',
  purchase_channel: '',
  purchase_date: '',
  amount: 0,
  remarks: '',
  file: null
})
const voucherFileInput = ref(null)

const newInvoice = ref({
  invoice_type: '',
  project_name: '',
  amount: 0,
  total_amount: 0,
  invoice_date: '',
  invoice_number: '',
  remarks: '',
  file: null
})

const fieldPermissions = ref({
  readonly: [],
  editable: []
})

const selectAll = computed({
  get: () => selectedInvoices.value.length === invoices.value.length && invoices.value.length > 0,
  set: () => {}
})

onMounted(async () => {
  console.log('=== 发票详情：页面加载 ===')
  const token = localStorage.getItem('token')
  console.log('检查token:', token ? '已登录' : '未登录')
  
  if (!token) {
    console.log('用户未登录，跳转到登录页面')
    navigateTo('/login')
    return
  }
  
  cacheStore.restoreFromLocalStorage()
  
  await loadEvent()
  await loadInvoices()
})

onUnmounted(() => {
  cacheStore.persistToLocalStorage()
})

const loadEvent = async () => {
  console.log('=== 发票详情：开始加载比赛信息 ===')
  console.log('比赛ID:', eventId)
  try {
    const token = localStorage.getItem('token')
    console.log('获取token:', token ? '已获取' : '未获取')
    
    console.log(`发送请求: GET /api/events/${eventId}`)
    const response = await $api.get(`/events/${eventId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    console.log('响应状态:', response.status)
    console.log('响应数据:', response.data)
    
    if (response.data.code === 200) {
      console.log('成功获取比赛信息:', response.data.data)
      event.value = response.data.data
    } else {
      console.error('获取比赛信息失败，错误码:', response.data.code)
      console.error('错误信息:', response.data.message)
    }
  } catch (error) {
    console.error('=== 发票详情：加载比赛信息异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    console.error('错误响应数据:', error.response?.data)
    console.error('错误状态码:', error.response?.status)
    console.error('错误消息:', error.message)
  } finally {
    console.log('=== 发票详情：比赛信息加载结束 ===')
  }
}

const loadInvoices = async () => {
  console.log('=== 发票详情：开始加载发票列表 ===')
  try {
    const token = localStorage.getItem('token')
    console.log('获取token:', token ? '已获取' : '未获取')
    
    console.log(`发送请求: GET /api/invoices?event_id=${eventId}`)
    const response = await $api.get(`/invoices?event_id=${eventId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    console.log('响应状态:', response.status)
    console.log('响应数据:', response.data)
    
    if (response.data.code === 200) {
      console.log('成功获取发票列表，数量:', response.data.data.data.length)
      invoices.value = response.data.data.data
    } else {
      console.error('获取发票列表失败，错误码:', response.data.code)
      console.error('错误信息:', response.data.message)
    }
  } catch (error) {
    console.error('=== 发票详情：加载发票列表异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    console.error('错误响应数据:', error.response?.data)
    console.error('错误状态码:', error.response?.status)
    console.error('错误消息:', error.message)
  } finally {
    console.log('=== 发票详情：发票列表加载结束 ===')
  }
}

const toggleSelectAll = () => {
  if (selectedInvoices.value.length === invoices.value.length) {
    selectedInvoices.value = []
  } else {
    selectedInvoices.value = invoices.value.map(i => i.invoice_id)
  }
}

const handleFileUpload = (e) => {
  const file = e.target.files[0]
  fileError.value = ''
  parseError.value = ''
  parseSuccess.value = false
  
  if (!file) {
    return
  }
  
  const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']
  const fileExtension = file.name.split('.').pop().toLowerCase()
  const allowedExtensions = ['pdf', 'png', 'jpg', 'jpeg']
  
  if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
    fileError.value = '文件格式不支持，请上传 PDF、PNG、JPG 或 JPEG 格式的文件'
    e.target.value = ''
    newInvoice.value.file = null
    return
  }
  
  console.log('文件验证通过:', file.name, file.type)
  newInvoice.value.file = file
}

const parseInvoice = async () => {
  if (!newInvoice.value.file) {
    parseError.value = '请先上传发票文件'
    return
  }
  
  parsing.value = true
  parseError.value = ''
  parseSuccess.value = false
  
  console.log('=== 开始解析发票 ===')
  console.log('文件名:', newInvoice.value.file.name)
  
  try {
    const token = localStorage.getItem('token')
    const formData = new FormData()
    formData.append('file', newInvoice.value.file)
    
    console.log('发送解析请求: POST /api/parse-invoice')
    const response = await $api.post('/parse-invoice', formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    })
    
    console.log('解析响应:', response.data)
    
    if (response.data.code === 200) {
      const data = response.data.data
      console.log('解析数据:', data)
      
      if (data.invoice_number) {
        newInvoice.value.invoice_number = data.invoice_number
      }
      if (data.invoice_date) {
        newInvoice.value.invoice_date = data.invoice_date
      }
      if (data.total_amount && data.total_amount > 0) {
        newInvoice.value.total_amount = data.total_amount
        newInvoice.value.amount = data.amount || data.total_amount
      } else if (data.amount && data.amount > 0) {
        newInvoice.value.amount = data.amount
        newInvoice.value.total_amount = data.amount
      }
      if (data.project_name) {
        newInvoice.value.project_name = data.project_name
      }
      
      if (response.data.field_permissions) {
        fieldPermissions.value = response.data.field_permissions
        console.log('字段权限:', fieldPermissions.value)
      }
      
      parseSuccess.value = true
      console.log('发票解析成功，数据已填充')
    } else {
      parseError.value = response.data.message || '解析失败，请手动填写'
      console.error('解析失败:', response.data.message)
    }
  } catch (error) {
    console.error('=== 发票解析异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    
    const message = error.response?.data?.message || '解析服务暂时不可用，请手动填写'
    parseError.value = message
  } finally {
    parsing.value = false
    console.log('=== 发票解析流程结束 ===')
  }
}

const addInvoice = async () => {
  console.log('=== 发票详情：开始添加发票 ===')
  console.log('发票数据:', newInvoice.value)
  uploading.value = true
  try {
    const token = localStorage.getItem('token')
    console.log('获取token:', token ? '已获取' : '未获取')
    
    const formData = new FormData()
    
    Object.keys(newInvoice.value).forEach(key => {
      if (key === 'file' && newInvoice.value.file) {
        console.log('添加文件到FormData')
        formData.append('file', newInvoice.value.file)
      } else if (newInvoice.value[key]) {
        console.log(`添加字段 ${key}:`, newInvoice.value[key])
        formData.append(key, newInvoice.value[key])
      }
    })
    
    formData.append('event_id', eventId)
    console.log('添加 event_id:', eventId)
    
    console.log('发送请求: POST /api/invoices')
    const response = await $api.post('/invoices', formData, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    })
    
    console.log('响应状态:', response.status)
    console.log('响应数据:', response.data)
    
    if (response.data.code === 200) {
      console.log('发票添加成功')
      cacheStore.invalidateInvoiceCache(parseInt(eventId))
      cacheStore.invalidateEventCache(parseInt(eventId))
      showAddModal.value = false
      resetForm()
      await loadInvoices()
    } else if (response.data.code === 4001) {
      console.error('重复上传检测:', response.data.message)
      const existingTime = response.data.data?.upload_time 
        ? new Date(response.data.data.upload_time).toLocaleString('zh-CN') 
        : '未知时间'
      showDuplicateAlert.value = true
      duplicateMessage.value = `⚠️ 该发票文件已经存在，无法重复添加\n\n首次上传时间：${existingTime}`
      duplicateData.value = response.data.data
    } else {
      console.error('添加发票失败，错误码:', response.data.code)
      console.error('错误信息:', response.data.message)
      alert('添加发票失败：' + response.data.message)
    }
  } catch (error) {
    console.error('=== 发票详情：添加发票异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    console.error('错误响应数据:', error.response?.data)
    console.error('错误状态码:', error.response?.status)
    console.error('错误消息:', error.message)
    alert('添加发票失败，请稍后重试')
  } finally {
    uploading.value = false
    console.log('=== 发票详情：添加发票流程结束 ===')
  }
}

const deleteSelected = async () => {
  if (!confirm(`确定要删除选中的 ${selectedInvoices.value.length} 张发票吗？`)) {
    return
  }
  
  console.log('=== 发票详情：开始删除发票 ===')
  console.log('选中的发票ID:', selectedInvoices.value)
  
  try {
    const token = localStorage.getItem('token')
    console.log('获取token:', token ? '已获取' : '未获取')
    
    for (const invoiceId of selectedInvoices.value) {
      console.log(`删除发票 ID: ${invoiceId}`)
      await $api.delete(`/invoices/${invoiceId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
    }
    
    console.log('发票删除成功')
    cacheStore.invalidateInvoiceCache(parseInt(eventId))
    cacheStore.invalidateEventCache(parseInt(eventId))
    selectedInvoices.value = []
    await loadInvoices()
  } catch (error) {
    console.error('=== 发票详情：删除发票异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    console.error('错误响应数据:', error.response?.data)
    console.error('错误状态码:', error.response?.status)
    console.error('错误消息:', error.message)
    alert('删除发票失败，请稍后重试')
  } finally {
    console.log('=== 发票详情：删除发票流程结束 ===')
  }
}

// 预览发票
const previewInvoice = async (invoice) => {
  currentPreviewInvoice.value = invoice
  previewImageUrl.value = ''
  previewError.value = false
  previewLoading.value = true
  showPreviewModal.value = true
  
  try {
    // 先尝试获取预览图URL
    const token = localStorage.getItem('token')
    const response = await $api.get(`/invoices/${invoice.invoice_id}/preview`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200 && response.data.data?.preview_url) {
      previewImageUrl.value = response.data.data.preview_url
    } else {
      // 如果没有预览图，尝试生成
      await generatePreviewImage()
    }
  } catch (error) {
    console.error('获取预览图失败:', error)
    previewError.value = true
  } finally {
    previewLoading.value = false
  }
}

// 生成预览图
const generatePreviewImage = async () => {
  if (!currentPreviewInvoice.value) return
  
  previewLoading.value = true
  previewError.value = false
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post(`/invoices/${currentPreviewInvoice.value.invoice_id}/generate-preview`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200 && response.data.data?.preview_url) {
      previewImageUrl.value = response.data.data.preview_url
      previewError.value = false
    } else {
      previewError.value = true
    }
  } catch (error) {
    console.error('生成预览图失败:', error)
    previewError.value = true
  } finally {
    previewLoading.value = false
  }
}

// 编辑发票
const editInvoice = (invoice) => {
  currentEditInvoiceId.value = invoice.invoice_id
  editForm.value = {
    invoice_type: invoice.invoice_type || '',
    project_name: invoice.project_name || '',
    amount: parseFloat(invoice.amount) || 0,
    invoice_date: invoice.invoice_date ? invoice.invoice_date.split('T')[0] : '',
    invoice_number: invoice.invoice_number || '',
    remarks: invoice.remarks || ''
  }
  showEditModal.value = true
}

// 更新发票信息
const updateInvoice = async () => {
  editing.value = true
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/invoices/${currentEditInvoiceId.value}`, editForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      showEditModal.value = false
      alert('发票信息更新成功！')
      await loadInvoices()
    } else {
      alert('更新失败：' + response.data.message)
    }
  } catch (error) {
    console.error('更新发票失败:', error)
    alert('更新失败，请稍后重试')
  } finally {
    editing.value = false
  }
}

// 下载单个发票
const downloadInvoice = async (invoice) => {
  downloading.value = true
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/invoices/${invoice.invoice_id}/download`, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob'
    })
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = invoice.file_name || `invoice_${invoice.invoice_id}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载失败:', error)
    alert('下载失败，请稍后重试')
  } finally {
    downloading.value = false
  }
}

const handleVoucherFileUpload = (e) => {
  const file = e.target.files[0]
  if (file) {
    voucherForm.value.file = file
  }
}

const addVoucher = async () => {
  if (!voucherForm.value.item_name) {
    alert('请填写物品名称')
    return
  }
  if (!voucherForm.value.file) {
    alert('请上传凭证文件')
    return
  }
  
  uploadingVoucher.value = true
  
  try {
    const token = localStorage.getItem('token')
    const formData = new FormData()
    
    formData.append('file', voucherForm.value.file)
    formData.append('event_id', eventId)
    formData.append('item_name', voucherForm.value.item_name)
    formData.append('voucher_type', voucherForm.value.voucher_type || '')
    formData.append('purchase_channel', voucherForm.value.purchase_channel || '')
    formData.append('purchase_date', voucherForm.value.purchase_date || '')
    formData.append('amount', voucherForm.value.amount || 0)
    formData.append('remarks', voucherForm.value.remarks || '')
    
    const response = await $api.post('/vouchers', formData, {
      headers: { Authorization: `Bearer ${token}` },
      'Content-Type': 'multipart/form-data'
    })
    
    if (response.data.code === 200) {
      showVoucherModal.value = false
      resetVoucherForm()
      alert('凭证上传成功！')
      await loadInvoices()
    } else {
      alert('上传失败：' + response.data.message)
    }
  } catch (error) {
    console.error('上传凭证失败:', error)
    alert('上传失败，请稍后重试')
  } finally {
    uploadingVoucher.value = false
  }
}

const resetVoucherForm = () => {
  voucherForm.value = {
    item_name: '',
    voucher_type: '',
    purchase_channel: '',
    purchase_date: '',
    amount: 0,
    remarks: '',
    file: null
  }
  if (voucherFileInput.value) {
    voucherFileInput.value.value = ''
  }
}

const reimburseInvoice = async (invoice) => {
  if (!confirm(`确定要将发票 "${invoice.project_name}" 标记为已报销吗？`)) {
    return
  }
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post(`/invoices/${invoice.invoice_id}/reimburse`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      alert('发票已标记为已报销')
      await loadInvoices()
    } else {
      alert('操作失败：' + response.data.message)
    }
  } catch (error) {
    console.error('报销操作失败:', error)
    alert('操作失败，请稍后重试')
  }
}

const batchReimburse = async () => {
  if (selectedInvoices.value.length === 0) {
    alert('请先选择要报销的发票')
    return
  }
  
  if (!confirm(`确定要报销选中的 ${selectedInvoices.value.length} 张发票吗？（仅审核通过的发票可报销）`)) {
    return
  }
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post('/invoices/batch-reimburse', {
      invoice_ids: selectedInvoices.value
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      alert(response.data.message)
      selectedInvoices.value = []
      await loadInvoices()
    } else {
      alert('批量报销失败：' + response.data.message)
    }
  } catch (error) {
    console.error('批量报销失败:', error)
    alert('批量报销失败，请稍后重试')
  }
}

// 批量下载
const batchDownload = async () => {
  if (selectedInvoices.value.length === 0) {
    alert('请先选择要下载的发票')
    return
  }
  
  if (!confirm(`确定要下载选中的 ${selectedInvoices.value.length} 张发票吗？`)) {
    return
  }
  
  downloading.value = true
  
  try {
    const token = localStorage.getItem('token')
    
    for (const invoiceId of selectedInvoices.value) {
      const response = await $api.get(`/invoices/${invoiceId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `invoice_${invoiceId}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      // 避免浏览器阻止多次下载，添加小延迟
      await new Promise(resolve => setTimeout(resolve, 300))
    }
    
    alert(`成功下载 ${selectedInvoices.value.length} 张发票！`)
  } catch (error) {
    console.error('批量下载失败:', error)
    alert('批量下载失败，请稍后重试')
  } finally {
    downloading.value = false
  }
}

const approveInvoice = async (invoice) => {
  if (!confirm(`确定要通过发票 "${invoice.project_name}" 的审核吗？`)) {
    return
  }
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/invoices/${invoice.invoice_id}/review`, {
      status: 'approved'
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      alert(`发票审核通过！`)
      await loadInvoices()
    } else {
      alert('审核操作失败：' + response.data.message)
    }
  } catch (error) {
    console.error('审核通过失败:', error)
    alert('审核操作失败，请稍后重试')
  }
}

const showRejectDialog = (invoice) => {
  currentRejectInvoice.value = invoice
  rejectionReason.value = ''
  showRejectModal.value = true
}

const rejectInvoice = async () => {
  if (!currentRejectInvoice.value) return
  
  if (!rejectionReason.value.trim()) {
    alert('请填写拒绝原因')
    return
  }
  
  reviewing.value = true
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/invoices/${currentRejectInvoice.value.invoice_id}/review`, {
      status: 'rejected',
      rejection_reason: rejectionReason.value.trim()
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      showRejectModal.value = false
      alert(`发票已拒绝！`)
      await loadInvoices()
    } else {
      alert('拒绝操作失败：' + response.data.message)
    }
  } catch (error) {
    console.error('拒绝审核失败:', error)
    alert('拒绝操作失败，请稍后重试')
  } finally {
    reviewing.value = false
  }
}

const resetForm = () => {
  newInvoice.value = {
    invoice_type: '',
    project_name: '',
    amount: 0,
    total_amount: 0,
    invoice_date: '',
    invoice_number: '',
    remarks: '',
    file: null
  }
  fieldPermissions.value = {
    readonly: [],
    editable: []
  }
  fileError.value = ''
}

const goBack = () => {
  navigateTo('/invoices')
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getStatusText = (status) => {
  const statusMap = {
    approved: '已通过',
    pending: '待审核',
    rejected: '已拒绝'
  }
  return statusMap[status] || status
}
</script>

<style scoped>
.invoice-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.back-button {
  padding: 0.5rem 1rem;
  background: #ecf0f1;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.back-button:hover {
  background: #bdc3c7;
}

.page-title {
  flex: 1;
  font-size: 1.8rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.8rem;
}

.action-button {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 5px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.3s ease;
}

.action-button.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-button.danger {
  background: #e74c3c;
  color: white;
}

.action-button.danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.invoices-table-container {
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow-x: auto;
}

.invoices-table {
  width: 100%;
  border-collapse: collapse;
}

.invoices-table th,
.invoices-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #ecf0f1;
}

.invoices-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #2c3e50;
}

.invoices-table tbody tr:hover {
  background: #f8f9fa;
}

.checkbox-col {
  width: 40px;
  text-align: center;
}

.amount {
  font-weight: 600;
  color: #27ae60;
}

.status-badge {
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
}

.status-badge.approved {
  background: #d4edda;
  color: #155724;
}

.status-badge.pending {
  background: #fff3cd;
  color: #856404;
}

.status-badge.rejected {
  background: #f8d7da;
  color: #721c24;
}

.empty-row {
  text-align: center;
  color: #7f8c8d;
  padding: 2rem !important;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 10px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 800px;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #ecf0f1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.3rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #7f8c8d;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #2c3e50;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.7rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 0.95rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #ecf0f1;
}

.cancel-button,
.submit-button {
  padding: 0.7rem 1.5rem;
  border: none;
  border-radius: 5px;
  font-weight: 500;
  cursor: pointer;
}

.cancel-button {
  background: #ecf0f1;
  color: #2c3e50;
}

.submit-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.file-hint {
  font-size: 0.85rem;
  color: #7f8c8d;
  margin-top: 0.3rem;
}

.file-error {
  color: #e74c3c;
  font-size: 0.85rem;
  margin-top: 0.3rem;
}

.file-upload-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.parse-button {
  margin-top: 0.5rem;
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #3498db, #2ecc71);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.parse-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
}

.parse-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.parse-error {
  background: #fee;
  border: 1px solid #fcc;
  color: #c0392b;
  padding: 0.8rem 1rem;
  border-radius: 5px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.parse-success {
  background: #efe;
  border: 1px solid #afa;
  color: #27ae60;
  padding: 0.8rem 1rem;
  border-radius: 5px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error-icon, .success-icon {
  font-size: 1.2rem;
}

.editable-tag {
  background: #d4edda;
  color: #155724;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
  margin-left: 0.5rem;
  font-weight: normal;
}

.readonly-tag {
  background: #fff3cd;
  color: #856404;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
  margin-left: 0.5rem;
  font-weight: normal;
}

.readonly-field {
  background-color: #f8f9fa;
  cursor: not-allowed;
}

.field-notice {
  margin-top: 0.5rem;
  padding: 0.7rem;
  background: #e8f4f8;
  border-left: 4px solid #3498db;
  border-radius: 3px;
  font-size: 0.9rem;
}

.readonly-fields {
  color: #e74c3c;
  font-weight: 600;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
  }
  
  .action-button {
    flex: 1;
  }
}

.duplicate-alert-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.duplicate-alert-modal {
  background: white;
  padding: 2rem;
  border-radius: 10px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.duplicate-alert-modal h3 {
  color: #f39c12;
  margin-bottom: 1rem;
}

.duplicate-message {
  color: #555;
  line-height: 1.6;
  margin-bottom: 1.5rem;
  white-space: pre-line;
}

.duplicate-close-btn {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 5px;
  cursor: pointer;
  width: 100%;
  font-size: 1rem;
}

.duplicate-close-btn:hover {
  background: #5568d3;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-approve {
  background: #27ae60;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-approve:hover {
  background: #229954;
}

.btn-reject {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-reject:hover {
  background: #c0392b;
}

.reviewed-info {
  color: #7f8c8d;
  font-size: 0.85rem;
  font-style: italic;
}

.reject-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001;
}

.reject-modal-content {
  background: white;
  padding: 2rem;
  border-radius: 10px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.reject-modal-content h3 {
  color: #e74c3c;
  margin-bottom: 1rem;
}

.reject-invoice-info {
  color: #555;
  margin-bottom: 1rem;
  font-weight: 500;
}

.reject-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn-cancel {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: 5px;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #f5f5f5;
}

.btn-confirm-reject {
  flex: 1;
  padding: 0.75rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.btn-confirm-reject:hover:not(:disabled) {
  background: #c0392b;
}

.btn-confirm-reject:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.view-existing-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  display: inline-block;
  margin-top: 0.5rem;
}

.view-existing-link:hover {
  text-decoration: underline;
}

/* 操作按钮样式 */
.btn-preview {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.btn-preview:hover {
  background: #2980b9;
  transform: translateY(-1px);
}

.btn-edit {
  background: #f39c12;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.btn-edit:hover {
  background: #e67e22;
  transform: translateY(-1px);
}

.btn-download {
  background: #27ae60;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.btn-download:hover {
  background: #229954;
  transform: translateY(-1px);
}

.action-button.warning {
  background: linear-gradient(135deg, #f39c12, #e67e22);
  color: white;
}

.action-button.warning:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 备注列样式 */
.remarks-cell {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #7f8c8d;
  font-size: 0.9rem;
}

/* 预览模态框样式 */
.preview-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1002;
}

.preview-modal-content {
  background: white;
  border-radius: 12px;
  max-width: 900px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.preview-header {
  padding: 1.5rem;
  border-bottom: 1px solid #ecf0f1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.preview-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.preview-header .close-button {
  color: white;
  font-size: 1.8rem;
}

.preview-body {
  padding: 2rem;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background: #f8f9fa;
}

.preview-image {
  max-width: 100%;
  max-height: 600px;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.preview-info {
  padding: 1.5rem;
  background: #f8f9fa;
  border-top: 1px solid #ecf0f1;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.8rem;
}

.info-row {
  padding: 0.5rem;
  background: white;
  border-radius: 5px;
  border-left: 3px solid #667eea;
}

.loading-spinner {
  text-align: center;
  color: #667eea;
  font-size: 1.1rem;
  padding: 2rem;
}

.no-preview,
.preview-error {
  text-align: center;
  color: #7f8c8d;
  padding: 2rem;
}

.retry-btn {
  margin-top: 1rem;
  padding: 0.6rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.retry-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* 编辑模态框样式 */
.edit-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001;
}

.edit-modal-content {
  background: white;
  border-radius: 10px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

/* 两行操作按钮布局 */
.action-buttons-vertical {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.action-row-top,
.action-row-bottom {
  display: flex;
  gap: 2px;
  justify-content: center;
}

/* 小尺寸按钮 */
.btn-preview-sm,
.btn-edit-sm,
.btn-download-sm,
.btn-approve-sm,
.btn-reject-sm,
.btn-reimburse-sm {
  padding: 2px 6px;
  font-size: 11px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  color: white;
  line-height: 1.4;
}

.btn-preview-sm {
  background: #3498db;
}
.btn-preview-sm:hover { background: #2980b9; transform: scale(1.05); }

.btn-edit-sm {
  background: #f39c12;
}
.btn-edit-sm:hover { background: #e67e22; transform: scale(1.05); }

.btn-download-sm {
  background: #27ae60;
}
.btn-download-sm:hover { background: #229954; transform: scale(1.05); }

.btn-approve-sm {
  background: #27ae60;
}
.btn-approve-sm:hover { background: #229954; }

.btn-reject-sm {
  background: #e74c3c;
}
.btn-reject-sm:hover { background: #c0392b; }

.btn-reimburse-sm {
  background: #9b59b6;
}
.btn-reimburse-sm:hover { background: #8e44ad; transform: scale(1.05); }

.reviewed-info-sm {
  font-size: 11px;
  color: #7f8c8d;
  min-width: 40px;
  text-align: center;
}

/* 报销状态标识 */
.reimburse-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: #ecf0f1;
  color: #7f8c8d;
}

.reimburse-badge.is-reimbursed {
  background: linear-gradient(135deg, #27ae60, #229954);
  color: white;
}

/* 凭证按钮样式 */
.action-button.voucher {
  background: linear-gradient(135deg, #16a085, #1abc9c);
}
.action-button.voucher:hover { transform: translateY(-2px); }
.action-button.voucher:disabled { opacity: 0.5; cursor: not-allowed; }

.action-button.reimburse {
  background: linear-gradient(135deg, #9b59b6, #8e44ad);
}
.action-button.reimburse:hover { transform: translateY(-2px); }
.action-button.reimburse:disabled { opacity: 0.5; cursor: not-allowed; }

/* 凭证上传弹窗 */
.modal-large {
  max-width: 650px !important;
}

.voucher-submit {
  background: linear-gradient(135deg, #16a085, #1abc9c) !important;
}
.voucher-submit:hover { transform: translateY(-2px); }
.voucher-submit:disabled { opacity: 0.5; cursor: not-allowed; }

.file-hint {
  font-size: 12px;
  color: #7f8c8d;
  margin-top: 4px;
}

/* 预算信息面板 */
.budget-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
  padding: 18px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  border-radius: 12px;
  border: 1px solid #e0e6ed;
}

.budget-card {
  padding: 14px 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: all 0.3s ease;
}

.budget-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.budget-label {
  font-size: 13px;
  color: #7f8c8d;
  font-weight: 500;
  margin-bottom: 6px;
}

.budget-value {
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
}

.total-budget { background: white; box-shadow: 0 2px 8px rgba(52, 152, 219, 0.08); }
.total-budget .budget-value { color: #3498db; }

.invoice-total { background: white; box-shadow: 0 2px 8px rgba(243, 156, 18, 0.08); }
.invoice-total .budget-value { color: #f39c12; }

.reimbursed { background: white; box-shadow: 0 2px 8px rgba(46, 204, 113, 0.08); }
.reimbursed .budget-value { color: #27ae60; }

.remaining { 
  background: white; 
  box-shadow: 0 2px 8px rgba(155, 89, 182, 0.08);
}
.remaining .budget-value { color: #9b59b6; }
.remaining.warning { box-shadow: 0 2px 8px rgba(231, 76, 60, 0.15); }
.remaining.warning .budget-value { color: #e67e22; }
.remaining.danger { box-shadow: 0 2px 8px rgba(231, 76, 60, 0.25); }
.remaining.danger .budget-value { color: #e74c3c; }

.progress-bar-container {
  width: 100%;
  height: 4px;
  background: #ecf0f1;
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #9b59b6, #8e44ad);
  border-radius: 2px;
  transition: width 0.5s ease;
}
</style>
