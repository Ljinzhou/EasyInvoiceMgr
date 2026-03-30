<template>
  <div class="invoice-detail-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">← 返回</button>
      <h1 class="page-title">{{ event?.event_name || '发票管理' }}</h1>
      <div class="header-actions">
        <button @click="showAddModal = true" class="action-button primary">添加发票</button>
        <button @click="deleteSelected" class="action-button danger" :disabled="selectedInvoices.length === 0">
          删除发票 ({{ selectedInvoices.length }})
        </button>
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
            <th>上传时间</th>
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
            <td>{{ formatDateTime(invoice.created_at) }}</td>
          </tr>
          <tr v-if="invoices.length === 0">
            <td colspan="7" class="empty-row">暂无发票数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加发票弹窗 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>添加发票</h2>
          <button @click="showAddModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="addInvoice" class="modal-body">
          <div class="form-group">
            <label>发票图片 *</label>
            <input 
              type="file" 
              @change="handleFileUpload" 
              accept=".pdf,.png,.jpg,.jpeg"
              required
            />
            <div class="file-hint">支持格式：PDF、PNG、JPG、JPEG</div>
            <div v-if="fileError" class="file-error">{{ fileError }}</div>
          </div>
          <div class="form-group">
            <label>发票类型</label>
            <input v-model="newInvoice.invoice_type" type="text" required placeholder="如：餐饮、交通、住宿" />
          </div>
          <div class="form-group">
            <label>项目名称 *</label>
            <input v-model="newInvoice.project_name" type="text" required />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>金额 *</label>
              <input v-model.number="newInvoice.amount" type="number" step="0.01" min="0" required />
            </div>
            <div class="form-group">
              <label>开票日期 *</label>
              <input v-model="newInvoice.invoice_date" type="date" required />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>发票代码</label>
              <input v-model="newInvoice.invoice_code" type="text" />
            </div>
            <div class="form-group">
              <label>发票号码</label>
              <input v-model="newInvoice.invoice_number" type="text" />
            </div>
          </div>
          <div class="form-group">
            <label>税号</label>
            <input v-model="newInvoice.tax_number" type="text" />
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const route = useRoute()

const eventId = route.params.id
const event = ref(null)
const invoices = ref([])
const selectedInvoices = ref([])
const showAddModal = ref(false)
const uploading = ref(false)
const fileError = ref('')

const newInvoice = ref({
  invoice_type: '',
  project_name: '',
  amount: 0,
  invoice_date: '',
  invoice_code: '',
  invoice_number: '',
  tax_number: '',
  remarks: '',
  file: null
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
  
  await loadEvent()
  await loadInvoices()
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
      showAddModal.value = false
      resetForm()
      await loadInvoices()
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

const resetForm = () => {
  newInvoice.value = {
    invoice_type: '',
    project_name: '',
    amount: 0,
    invoice_date: '',
    invoice_code: '',
    invoice_number: '',
    tax_number: '',
    remarks: '',
    file: null
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
</style>
