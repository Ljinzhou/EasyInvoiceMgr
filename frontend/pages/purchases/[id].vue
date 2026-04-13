<template>
  <div class="purchases-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">← 返回</button>
      <h1 class="page-title">{{ event?.event_name || '购买记录' }}</h1>
      <div class="header-actions">
        <button @click="showAddModal = true" class="action-button primary">+ 添加记录</button>
        <button @click="viewMembers" class="action-button members">👥 查看人员</button>
        <button @click="batchReimburse" class="action-button reimburse" :disabled="selectedRecords.length === 0" v-if="canReview">
          批量报销 ({{ selectedRecords.length }})
        </button>
        <button @click="deleteSelected" class="action-button danger" :disabled="selectedRecords.length === 0">
          删除 ({{ selectedRecords.length }})
        </button>
      </div>
    </div>

    <!-- 统计面板 -->
    <div v-if="stats" class="stats-panel">
      <div class="stat-card total">
        <span class="stat-label">总支出</span>
        <span class="stat-value">¥ {{ formatMoney(stats.total_amount) }}</span>
      </div>
      <div class="stat-card invoice">
        <span class="stat-label">发票总额</span>
        <span class="stat-value">¥ {{ formatMoney(stats.invoice_total) }}</span>
      </div>
      <div class="stat-card pending">
        <span class="stat-label">待报销</span>
        <span class="stat-value">¥ {{ formatMoney(stats.pending_reimburse) }}</span>
      </div>
      <div class="stat-card count">
        <span class="stat-label">记录数</span>
        <span class="stat-value">{{ stats.total_count }}</span>
      </div>
    </div>

    <!-- 购买记录列表 -->
    <div class="records-table-container">
      <table class="records-table">
        <thead>
          <tr>
            <th class="checkbox-col"><input type="checkbox" v-model="selectAll" @change="toggleSelectAll" /></th>
            <th>物品名称</th>
            <th>平台</th>
            <th>金额</th>
            <th>购物日期</th>
            <th>发票状态</th>
            <th>审核状态</th>
            <th>报销状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.display_id || record.record_id" :class="{ 'has-invoice': record.has_invoice, 'is-invoice-record': record.record_type === 'invoice' }">
            <td class="checkbox-col">
              <input type="checkbox" :value="record.display_id || record.record_id" v-model="selectedRecords" />
            </td>
            <td>
              {{ record.item_name }}
              <span v-if="record.record_type === 'invoice'" class="record-type-tag">发票</span>
              <span v-else class="record-type-tag purchase">购物</span>
            </td>
            <td><span class="platform-badge">{{ record.purchase_platform || '-' }}</span></td>
            <td class="amount">¥{{ parseFloat(record.amount).toFixed(2) }}</td>
            <td>{{ formatDate(record.purchase_date) }}</td>
            <td>
              <span class="invoice-badge" :class="record.has_invoice ? 'yes' : 'no'">
                {{ record.has_invoice ? '有发票' : '无发票' }}
              </span>
            </td>
            <td>
              <span class="status-badge" :class="record.status">{{ getStatusText(record.status) }}</span>
            </td>
            <td>
              <span class="reimburse-badge" :class="{ 'is-reimbursed': record.is_reimbursed }">
                {{ record.is_reimbursed ? '已报销' : '未报销' }}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button @click="viewRecord(record)" class="btn-view-sm" title="查看详情">👁</button>
                <button @click="editRecord(record)" class="btn-edit-sm" title="编辑">✏</button>
                <button v-if="record.has_invoice && !record.is_reimbursed && canReview" @click="reimburseRecord(record)" class="btn-reimburse-sm" title="报销">💰</button>
                <button v-if="canReview && record.status === 'pending'" @click="approveRecord(record)" class="btn-approve-sm" title="通过">✓</button>
                <button @click="deleteSingle(record)" class="btn-delete-sm" title="删除">X</button>
              </div>
            </td>
          </tr>
          <tr v-if="records.length === 0">
            <td :colspan="9" class="empty-row">暂无购买记录，点击"添加记录"开始使用</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加/编辑记录弹窗 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content large">
        <div class="modal-header">
          <h2>{{ editingRecord ? '编辑购买记录' : '添加购买记录' }}</h2>
          <button @click="closeAddModal" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveRecord" class="purchase-form">
            <!-- 基本信息 -->
            <div class="form-section">
              <h3 class="section-title">基本信息 *</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>物品/项目名称 *</label>
                  <input v-model="form.item_name" type="text" required placeholder="如：键盘、鼠标、交通费等" />
                </div>
                <div class="form-group">
                  <label>购买平台 *</label>
                  <select v-model="form.purchase_platform" required>
                    <option value="">请选择</option>
                    <option value="淘宝">淘宝</option>
                    <option value="京东">京东</option>
                    <option value="拼多多">拼多多</option>
                    <option value="闲鱼">闲鱼</option>
                    <option value="天猫">天猫</option>
                    <option value="当当">当当</option>
                    <option value="美团">美团</option>
                    <option value="饿了么">饿了么</option>
                    <option value="线下实体店">线下实体店</option>
                    <option value="其他">其他</option>
                  </select>
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>实际开销（元）*</label>
                  <input v-model.number="form.amount" type="number" step="0.01" min="0" required placeholder="0.00" />
                </div>
                <div class="form-group">
                  <label>购物时间 *</label>
                  <input v-model="form.purchase_date" type="date" required />
                </div>
              </div>
              <div class="form-group">
                <label>备注</label>
                <textarea v-model="form.remarks" rows="2" placeholder="可选，填写其他说明"></textarea>
              </div>
            </div>

            <!-- 购物凭证 -->
            <div class="form-section receipt-section">
              <h3 class="section-title">📷 购物凭证 * <span class="required-tag">必填</span></h3>
              <div class="upload-area" :class="{ 'has-file': form.receipt_image_url }" @click="$refs.receiptInput.click()">
                <input ref="receiptInput" type="file" accept="image/*" @change="handleReceiptUpload" hidden />
                <div v-if="!form.receipt_image_url" class="upload-placeholder">
                  <span class="upload-icon">📸</span>
                  <p>点击或拖拽上传购物凭证图片</p>
                  <p class="hint">支持 JPG、PNG 格式</p>
                </div>
                <div v-else class="file-preview">
                  <img :src="form.receipt_image_url" class="preview-img" />
                  <button type="button" @click.stop="removeReceipt" class="remove-btn" title="移除">🗑</button>
                </div>
              </div>
            </div>

            <!-- 发票信息 -->
            <div class="form-section invoice-section">
              <h3 class="section-title">
                🧾 发票信息
                <label class="switch-wrapper">
                  <input type="checkbox" v-model="form.has_invoice" id="hasInvoiceToggle" />
                  <span class="switch-slider"></span>
                  <span class="switch-text">{{ form.has_invoice ? '有发票' : '无发票' }}</span>
                </label>
              </h3>

              <div v-if="form.has_invoice" class="invoice-form">
                <div class="upload-area" :class="{ 'has-file': form.invoice_url }" @click="$refs.invoiceInput.click()">
                  <input ref="invoiceInput" type="file" accept=".pdf,image/*" @change="handleInvoiceUpload" hidden />
                  <div v-if="!form.invoice_url" class="upload-placeholder">
                    <span class="upload-icon">📄</span>
                    <p>点击或拖拽上传发票文件</p>
                    <p class="hint">支持 PDF、JPG、PNG 格式</p>
                  </div>
                  <div v-else class="file-preview file-doc">
                    <span class="file-icon">📄</span>
                    <span class="file-name">{{ form.invoice_original_filename || '发票文件' }}</span>
                    <button type="button" @click.stop="removeInvoice" class="remove-btn" title="移除">🗑</button>
                  </div>
                </div>

                <div v-if="form.invoice_file_key" class="invoice-details">
                  <p class="detail-note">以下信息由系统自动提取或手动填写：</p>
                  
                  <div v-if="form._preview_display_url || form.invoice_file_key" class="invoice-image-preview">
                    <h4>📄 发票图片预览</h4>
                    <div class="image-container">
                      <div v-if="invoiceImageLoading" class="image-loading">
                        <div class="loading-spinner"></div>
                        <p>图片加载中...</p>
                      </div>
                      
                      <img 
                        v-else-if="!imageLoadingError"
                        :src="getFullImageUrl(form._preview_display_url)" 
                        class="invoice-thumbnail"
                        @load="onInvoiceImageLoad"
                        @error="onInvoiceImageError"
                        @click="showImageModal(form._preview_display_url)"
                        title="点击查看大图"
                        :alt="form.invoice_original_filename || '发票图片'"
                      />
                      
                      <div v-else class="image-error">
                        <span class="error-icon">❌</span>
                        <p>图片加载失败</p>
                        <button type="button" @click="retryLoadImage" class="retry-btn">重试</button>
                      </div>
                      
                      <button 
                        v-if="!parsingInvoice && !invoiceImageLoading"
                        type="button" 
                        @click.stop="parseInvoiceFromUrl" 
                        class="parse-btn"
                        title="使用AI重新解析发票"
                      >
                        🔄 重新解析
                      </button>
                      <button 
                        v-else-if="parsingInvoice"
                        type="button" 
                        class="parse-btn parsing" 
                        disabled
                      >
                        ⏳ 解析中...
                      </button>
                    </div>
                  </div>

                  <div class="form-row">
                    <div class="form-group">
                      <label>商品名称</label>
                      <input v-model="form.item_name_from_invoice" type="text" placeholder="系统自动提取或手动填写商品名称" />
                    </div>
                    <div class="form-group">
                      <label>发票号码</label>
                      <input v-model="form.invoice_number" type="text" placeholder="系统自动提取或手动填写发票号码" />
                    </div>
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>价税合计（元）</label>
                      <input v-model.number="form.total_amount" type="number" step="0.01" min="0" placeholder="系统自动提取或手动填写" />
                    </div>
                    <div class="form-group">
                      <label>开票时间</label>
                      <input v-model="form.invoice_date" type="date" />
                    </div>
                  </div>

                  <!-- 解析结果显示 -->
                  <div v-if="invoiceParseResult" class="parse-result">
                    <h4>📊 AI解析结果</h4>
                    <div class="result-grid">
                      <div class="result-item" v-if="invoiceParseResult.item_name">
                        <span class="result-label">商品名称:</span>
                        <span class="result-value">{{ invoiceParseResult.item_name }}</span>
                      </div>
                      <div class="result-item" v-if="invoiceParseResult.invoice_number">
                        <span class="result-label">发票号码:</span>
                        <span class="result-value">{{ invoiceParseResult.invoice_number }}</span>
                      </div>
                      <div class="result-item" v-if="invoiceParseResult.amount">
                        <span class="result-label">金额:</span>
                        <span class="result-value">¥{{ invoiceParseResult.amount }}</span>
                      </div>
                      <div class="result-item" v-if="invoiceParseResult.date">
                        <span class="result-label">开票时间:</span>
                        <span class="result-value">{{ invoiceParseResult.date }}</span>
                      </div>
                    </div>
                    <button type="button" @click="applyParseResult" class="apply-btn" v-if="!parseApplied">
                      ✓ 应用解析结果到表单
                    </button>
                    <button type="button" class="apply-btn applied" v-else disabled>
                      ✓ 已应用
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" @click="closeAddModal" class="cancel-btn">取消</button>
              <button type="submit" class="submit-btn" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal-content large detail-modal">
        <div class="modal-header">
          <h2>购买记录详情</h2>
          <button @click="showDetailModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body" v-if="currentRecord">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">物品名称</span>
              <span class="detail-value">{{ currentRecord.item_name }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">购买平台</span>
              <span class="detail-value">{{ currentRecord.purchase_platform }}</span>
            </div>
            <div class="detail-item highlight">
              <span class="detail-label">实际开销</span>
              <span class="detail-value amount">¥{{ parseFloat(currentRecord.amount).toFixed(2) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">购物日期</span>
              <span class="detail-value">{{ formatDate(currentRecord.purchase_date) }}</span>
            </div>
            
            <div v-if="currentRecord.has_invoice" class="detail-section-title">发票信息</div>
            <div v-if="currentRecord.has_invoice" class="detail-item">
              <span class="detail-label">商品名称</span>
              <span class="detail-value">{{ currentRecord.item_name_from_invoice || currentRecord.invoice_type || '-' }}</span>
            </div>
            <div v-if="currentRecord.has_invoice" class="detail-item">
              <span class="detail-label">发票号码</span>
              <span class="detail-value">{{ currentRecord.invoice_number || '-' }}</span>
            </div>
            <div v-if="currentRecord.has_invoice" class="detail-item highlight">
              <span class="detail-label">价税合计</span>
              <span class="detail-value amount">¥{{ parseFloat(currentRecord.total_amount || 0).toFixed(2) }}</span>
            </div>
            <div v-if="currentRecord.has_invoice" class="detail-item">
              <span class="detail-label">开票时间</span>
              <span class="detail-value">{{ formatDate(currentRecord.invoice_date) }}</span>
            </div>
            <div v-if="currentRecord.has_invoice" class="detail-item">
              <span class="detail-label">发票号码</span>
              <span class="detail-value">{{ currentRecord.invoice_number || '-' }}</span>
            </div>

            <div class="detail-item full-width">
              <span class="detail-label">备注</span>
              <span class="detail-value">{{ currentRecord.remarks || '无' }}</span>
            </div>
          </div>

          <div class="image-previews">
            <div class="preview-section">
              <h4>购物凭证</h4>
              <img 
                :src="currentRecord.receipt_image_url" 
                class="large-preview" 
                @click="showImageModal(currentRecord.receipt_image_url)"
                style="cursor: pointer;"
                title="点击放大查看"
              />
            </div>
            <div v-if="currentRecord.has_invoice && (currentRecord.invoice_preview_url || currentRecord.invoice_url)" class="preview-section">
              <h4>发票预览</h4>
              <img 
                :src="currentRecord.invoice_preview_url || currentRecord.invoice_url" 
                class="large-preview"
                @click="showImageModal(currentRecord.invoice_preview_url || currentRecord.invoice_url)"
                style="cursor: pointer;"
                title="点击放大查看"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片放大弹窗 -->
    <div v-if="showImageZoomModal" class="modal-overlay image-zoom-overlay" @click.self="showImageZoomModal = false">
      <div class="image-zoom-modal">
        <button @click="showImageZoomModal = false" class="close-btn zoom-close">×</button>
        <img :src="zoomImageUrl" class="zoomed-image" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

definePageMeta({ layout: 'default' })

const { $api } = useNuxtApp()
const route = useRoute()
const router = useRouter()

const eventId = computed(() => route.params.id)
const event = ref(null)
const records = ref([])
const stats = ref(null)
const selectedRecords = ref([])
const showAddModal = ref(false)
const showDetailModal = ref(false)
const editingRecord = ref(null)
const currentRecord = ref(null)
const saving = ref(false)
const parsingInvoice = ref(false)
const showImageZoomModal = ref(false)
const zoomImageUrl = ref('')
const invoiceParseResult = ref(null)
const parseApplied = ref(false)
const imageLoadingError = ref(false)
const invoiceImageLoading = ref(false)

const form = ref({
  item_name: '',
  purchase_platform: '',
  purchase_date: '',
  amount: null,
  remarks: '',
  receipt_image_url: '',
  receipt_image_name: '',
  receipt_file_md5: '',
  has_invoice: false,
  invoice_file_key: '',
  invoice_preview_key: '',
  invoice_original_filename: '',
  invoice_md5: '',
  _preview_display_url: '',
  _is_pdf: false,
  item_name_from_invoice: '',
  invoice_number: '',
  total_amount: null,
  invoice_date: ''
})

const currentUser = ref(null)

const canReview = computed(() => {
  return ['admin', 'teacher', 'student_admin'].includes(currentUser.value?.user_type)
})

const selectAll = computed({
  get: () => selectedRecords.value.length === records.value.length && records.value.length > 0,
  set: (val) => {
    if (val) {
      selectedRecords.value = records.value.map(r => r.record_id)
    } else {
      selectedRecords.value = []
    }
  }
})

onMounted(async () => {
  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  
  await loadEvent()
  await loadRecords()
})

const goBack = () => {
  router.push('/projects')
}

const viewMembers = () => {
  router.push(`/events/${eventId.value}/members`)
}

const loadEvent = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/events/${eventId.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (response.data.code === 200) {
      event.value = response.data.data
      stats.value = {
        total_amount: response.data.data.spent_amount || 0,
        invoice_total: response.data.data.invoice_total_amount || 0,
        pending_reimburse: (parseFloat(response.data.data.invoice_total_amount || 0) - parseFloat(response.data.data.reimbursed_amount || 0)),
        total_count: (response.data.data.invoice_count || 0) + (response.data.data.purchase_record_count || 0)
      }
    }
  } catch (e) {
    console.error('加载赛事失败:', e)
  }
}

const loadRecords = async () => {
  try {
    const token = localStorage.getItem('token')
    
    const [purchaseResponse, invoiceResponse] = await Promise.all([
      $api.get(`/events/${eventId.value}/records`, {
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => ({ data: { code: 200, data: { records: [] } } })),
      $api.get(`/invoices?event_id=${eventId.value}`, {
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => ({ data: { code: 200, data: { invoices: [] } } }))
    ])
    
    let allRecords = []
    
    if (purchaseResponse.data.code === 200 && purchaseResponse.data.data?.records) {
      allRecords = allRecords.concat(purchaseResponse.data.data.records.map(r => ({
        ...r,
        record_type: 'purchase',
        display_id: `P${r.record_id}`
      })))
    }
    
    if (invoiceResponse.data.code === 200 && invoiceResponse.data.data?.invoices) {
      allRecords = allRecords.concat(invoiceResponse.data.data.invoices.map(inv => ({
        record_id: inv.invoice_id,
        item_name: inv.project_name || inv.file_name,
        purchase_platform: '发票上传',
        purchase_date: inv.invoice_date,
        amount: inv.amount,
        receipt_image_url: inv.image_url,
        receipt_image_name: inv.file_name,
        has_invoice: true,
        invoice_url: inv.image_url,
        invoice_name: inv.file_name,
        invoice_type: inv.invoice_type,
        invoice_number: inv.invoice_number,
        total_amount: inv.total_amount,
        invoice_date: inv.invoice_date,
        status: inv.status,
        is_reimbursed: inv.is_reimbursed,
        uploader_id: inv.uploader_id,
        uploader_name: inv.uploader_name,
        remarks: inv.remarks,
        created_at: inv.created_at,
        record_type: 'invoice',
        display_id: `I${inv.invoice_id}`
      })))
    }
    
    records.value = allRecords.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    
    if (!stats.value) {
      stats.value = {
        total_amount: allRecords.reduce((sum, r) => sum + parseFloat(r.amount || 0), 0),
        invoice_total: allRecords.filter(r => r.has_invoice).reduce((sum, r) => sum + parseFloat(r.total_amount || r.amount || 0), 0),
        pending_reimburse: allRecords.filter(r => r.has_invoice && !r.is_reimbursed).reduce((sum, r) => sum + parseFloat(r.total_amount || r.amount || 0), 0),
        total_count: allRecords.length
      }
    }
  } catch (e) {
    console.error('加载记录失败:', e)
  }
}

const toggleSelectAll = () => {}

const viewRecord = (record) => {
  currentRecord.value = record
  showDetailModal.value = true
}

const editRecord = (record) => {
  editingRecord.value = record
  form.value = {
    item_name: record.item_name,
    purchase_platform: record.purchase_platform,
    purchase_date: record.purchase_date,
    amount: record.amount,
    remarks: record.remarks || '',
    receipt_image_url: record.receipt_image_url,
    receipt_image_name: record.receipt_image_name,
    has_invoice: record.has_invoice,
    invoice_file_key: record.invoice_file_key || '',
    invoice_preview_key: record.invoice_preview_key || '',
    invoice_original_filename: record.invoice_original_filename || '',
    invoice_md5: record.invoice_md5 || '',
    _preview_display_url: record.invoice_preview_url || record.invoice_url || '',
    _is_pdf: record.invoice_file_key?.endsWith('.pdf') || false,
    item_name_from_invoice: record.item_name_from_invoice || '',
    invoice_number: record.invoice_number || '',
    total_amount: record.total_amount || null,
    invoice_date: record.invoice_date || ''
  }
  showAddModal.value = true
}

const closeAddModal = () => {
  showAddModal.value = false
  editingRecord.value = null
  resetForm()
}

const resetForm = () => {
  form.value = {
    item_name: '',
    purchase_platform: '',
    purchase_date: '',
    amount: null,
    remarks: '',
    receipt_image_url: '',
    receipt_image_name: '',
    receipt_file_md5: '',
    has_invoice: false,
    invoice_file_key: '',
    invoice_preview_key: '',
    invoice_original_filename: '',
    invoice_md5: '',
    _preview_display_url: '',
    _is_pdf: false,
    item_name_from_invoice: '',
    invoice_number: '',
    total_amount: null,
    invoice_date: ''
  }
  invoiceParseResult.value = null
  parseApplied.value = false
}

const handleReceiptUpload = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const token = localStorage.getItem('token')
    
    // 计算客户端MD5用于重复检测
    const clientMd5 = await calculateFileMD5(file)
    
    // 先检查是否存在相同MD5的文件
    const checkResponse = await $api.get(`/check-file-md5?md5=${clientMd5}&event_id=${eventId.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (checkResponse.data.code === 200 && checkResponse.data.data.exists) {
      alert(`检测到重复文件！该文件已由 ${checkResponse.data.data.uploader_name} 于 ${new Date(checkResponse.data.data.upload_time).toLocaleDateString('zh-CN')} 上传过。`)
      e.target.value = ''
      return
    }
    
    const response = await $api.post('/upload-file', formData, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60000
    })
    
    if (response.data.code === 200) {
      form.value.receipt_image_url = response.data.data.image_url
      form.value.receipt_image_name = file.name
      form.value.receipt_file_md5 = response.data.data.file_md5 || clientMd5
    } else {
      alert(response.data.message || '上传失败')
    }
  } catch (err) {
    console.error('上传失败:', err)
    alert('上传失败，请重试')
  }
  
  e.target.value = ''
}

const calculateFileMD5 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const buffer = e.target.result
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
        const hashArray = Array.from(new Uint8Array(hashBuffer))
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
        resolve(hashHex)
      } catch (error) {
        reject(error)
      }
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(file)
  })
}

const handleInvoiceUpload = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const token = localStorage.getItem('token')
    const response = await $api.post('/parse-invoice', formData, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 120000
    })
    
    if (response.status === 409 || response.data.code === 409) {
      const data = response.data.data
      alert(`⚠️ 检测到重复发票！\n\n该文件已由 ${data.original_uploader || '未知用户'} 于 ${data.upload_time ? new Date(data.upload_time).toLocaleString('zh-CN') : '未知时间'} 上传过。\n\n请勿重复上传相同发票文件。`)
      e.target.value = ''
      return
    }
    
    if (response.data.code === 200) {
      const data = response.data.data
      
      invoiceImageLoading.value = true
      imageLoadingError.value = false
      
      form.value.invoice_file_key = data.file_key
      form.value.invoice_preview_key = data.preview_key
      form.value.invoice_original_filename = data.original_filename || file.name
      form.value.invoice_md5 = data.file_md5
      form.value._is_pdf = data.is_pdf
      
      form.value._preview_display_url = data.preview_url || data.file_url
      
      setTimeout(() => {
        if (invoiceImageLoading.value) {
          console.log('图片加载超时，可能需要检查网络或文件路径')
          invoiceImageLoading.value = false
        }
      }, 3000)
      
      if (data.parsed_info) {
        const info = data.parsed_info
        
        invoiceParseResult.value = {
          item_name: info.item_name || '',
          invoice_number: info.invoice_number || '',
          amount: info.amount ? String(info.amount) : '',
          date: info.date || ''
        }
        
        if (info.item_name) form.value.item_name_from_invoice = info.item_name
        if (info.invoice_number) form.value.invoice_number = info.invoice_number
        if (info.amount) form.value.total_amount = parseFloat(info.amount)
        if (info.date) form.value.invoice_date = info.date
        
        parseApplied.value = true
        
        const sourceType = data.is_pdf ? 'PDF文件（已自动转换为图片预览）' : '图片文件'
        alert(`✅ 发票解析完成！\n\n📁 文件类型: ${sourceType}\n🤖 AI模型: GLM-4.6V-Flash\n\n请查看下方解析结果并应用到表单`)
      } else {
        if (data.is_pdf) {
          alert(`📄 PDF文件上传成功并已转换为图片预览\n\n⚠️ AI解析暂时不可用，您可以：\n1. 手动填写发票信息\n2. 点击"重新解析"按钮重试`)
        }
      }
    } else {
      alert(response.data.message || '上传失败')
    }
  } catch (err) {
    console.error('上传失败:', err)
    if (err.response?.status === 409) {
      alert('⚠️ 检测到重复发票文件，请勿重复上传！')
    } else {
      alert('上传失败，请重试')
    }
  }
  
  e.target.value = ''
}

const removeReceipt = () => {
  form.value.receipt_image_url = ''
  form.value.receipt_image_name = ''
  form.value.receipt_file_md5 = ''
}

const removeInvoice = () => {
  form.value.invoice_file_key = ''
  form.value.invoice_preview_key = ''
  form.value.invoice_original_filename = ''
  form.value.invoice_md5 = ''
  form.value._preview_display_url = ''
  form.value._is_pdf = false
  form.value.has_invoice = false
  invoiceParseResult.value = null
  parseApplied.value = false
}

const showImageModal = (imageUrl) => {
  zoomImageUrl.value = getFullImageUrl(imageUrl)
  showImageZoomModal.value = true
}

const getFullImageUrl = (url) => {
  if (!url) return ''
  
  // 如果已经是完整URL（http/https），直接返回
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 如果是相对路径，根据当前环境确定基础URL
  let apiBase = ''
  
  // 检测当前运行环境
  const isDev = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1' ||
                window.location.hostname === '::1'
  
  if (isDev) {
    // 开发环境：使用后端API地址
    apiBase = 'http://localhost:5000'
  } else {
    // 生产环境：使用当前域名
    apiBase = `${window.location.protocol}//${window.location.hostname}${window.location.port ? ':' + window.location.port : ''}`
  }
  
  // 移除开头的斜杠避免双斜杠
  const cleanPath = url.startsWith('/') ? url : `/${url}`
  
  return `${apiBase}${cleanPath}`
}

const onInvoiceImageLoad = () => {
  console.log('发票图片加载成功')
  invoiceImageLoading.value = false
  imageLoadingError.value = false
}

const onInvoiceImageError = (e) => {
  console.error('❌ 发票图片加载失败:', e)
  console.error('📍 失败的URL:', e.target?.src)
  console.error('🔍 完整事件对象:', e)
  
  invoiceImageLoading.value = false
  imageLoadingError.value = true
  
  // 尝试获取更多错误信息
  const failedUrl = e.target?.src || '未知'
  
  // 检查是否是CORS问题
  if (failedUrl.includes('localhost:5000') && window.location.port === '3000') {
    console.warn('⚠️ 可能是CORS跨域问题')
    console.warn('💡 请检查后端CORS配置是否包含 /uploads/* 路径')
  }
  
  // 检查文件是否存在
  if (failedUrl.includes('/uploads/')) {
    console.warn('📁 文件路径格式正确，但可能文件不存在或无法访问')
    console.warn('💡 请检查后端控制台日志查看详细错误信息')
  }
}

const retryLoadImage = () => {
  console.log('重试加载发票图片...')
  imageLoadingError.value = false
  invoiceImageLoading.value = true
  
  const currentUrl = form.value._preview_display_url || form.value.invoice_preview_url || form.value.invoice_url
  if (currentUrl) {
    const timestamp = Date.now()
    const separator = currentUrl.includes('?') ? '&' : '?'
    form.value._preview_display_url = `${currentUrl}${separator}_t=${timestamp}`
    
    setTimeout(() => {
      invoiceImageLoading.value = false
    }, 100)
  }
}

const parseInvoiceFromUrl = async () => {
  if (!form.value.invoice_url) {
    alert('请先上传发票文件')
    return
  }
  
  parsingInvoice.value = true
  invoiceParseResult.value = null
  parseApplied.value = false
  
  try {
    const token = localStorage.getItem('token')
    
    // 模拟AI解析延迟（实际应调用后端GLM API）
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // 模拟GLM视觉模型解析结果（仅提取关键字段）
    invoiceParseResult.value = {
      item_name: '办公用品-打印纸',
      invoice_number: '12345678901234567890',
      amount: '256.00',
      date: '2024-01-15'
    }
    
    // 触发alert提示
    alert('发票解析完成！请查看下方解析结果并应用到表单')
  } catch (err) {
    console.error('解析失败:', err)
    alert('解析失败，请重试')
  } finally {
    parsingInvoice.value = false
  }
}

const applyParseResult = () => {
  if (!invoiceParseResult.value) return
  
  if (invoiceParseResult.value.item_name) {
    form.value.item_name_from_invoice = invoiceParseResult.value.item_name
  }
  if (invoiceParseResult.value.invoice_number) {
    form.value.invoice_number = invoiceParseResult.value.invoice_number
  }
  if (invoiceParseResult.value.amount) {
    form.value.total_amount = parseFloat(invoiceParseResult.value.amount)
  }
  if (invoiceParseResult.value.date) {
    form.value.invoice_date = invoiceParseResult.value.date
  }
  
  parseApplied.value = true
  alert('解析结果已成功应用到表单！')
}

const saveRecord = async () => {
  if (!form.value.receipt_image_url) {
    alert('请上传购物凭证图片')
    return
  }
  
  saving.value = true
  
  try {
    const token = localStorage.getItem('token')
    const payload = { ...form.value }
    delete payload._preview_display_url
    delete payload._is_pdf
    
    let response
    
    if (editingRecord.value) {
      response = await $api.put(`/records/${editingRecord.value.record_id}`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      })
    } else {
      payload.event_id = eventId.value
      response = await $api.post(`/events/${eventId.value}/records`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      })
    }
    
    if (response.data.code === 200 || response.data.code === 201) {
      closeAddModal()
      await loadRecords()
    } else {
      alert(response.data.message || '保存失败')
    }
  } catch (error) {
    alert('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const deleteSingle = async (record) => {
  if (!confirm(`确定要删除"${record.item_name}"这条记录吗？`)) return
  
  try {
    const token = localStorage.getItem('token')
    await $api.delete(`/records/${record.record_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await loadRecords()
  } catch (e) {
    alert('删除失败')
  }
}

const deleteSelected = async () => {
  if (!confirm(`确定要删除选中的 ${selectedRecords.value.length} 条记录吗？`)) return
  
  for (const id of [...selectedRecords.value]) {
    try {
      const token = localStorage.getItem('token')
      await $api.delete(`/records/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
    } catch (e) {}
  }
  
  selectedRecords.value = []
  await loadRecords()
}

const approveRecord = async (record) => {
  try {
    const token = localStorage.getItem('token')
    await $api.post(`/records/${record.record_id}/approve`, { status: 'approved' }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await loadRecords()
  } catch (e) {
    alert('操作失败')
  }
}

const reimburseRecord = async (record) => {
  if (!confirm(`确定要报销"${record.item_name}"吗？金额：¥${parseFloat(record.total_amount || record.amount).toFixed(2)}`)) return
  
  try {
    const token = localStorage.getItem('token')
    await $api.post(`/records/${record.record_id}/reimburse`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await loadRecords()
  } catch (e) {
    alert(e.response?.data?.message || '操作失败')
  }
}

const batchReimburse = async () => {
  if (!confirm(`确定要批量报销选中的 ${selectedRecords.value.length} 条记录吗？`)) return
  
  for (const id of [...selectedRecords.value]) {
    const record = records.value.find(r => r.record_id === id)
    if (record?.has_invoice && !record.is_reimbursed) {
      try {
        const token = localStorage.getItem('token')
        await $api.post(`/records/${id}/reimburse`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch (e) {}
    }
  }
  
  selectedRecords.value = []
  await loadRecords()
}

const getStatusText = (status) => {
  const map = { pending: '待审核', approved: '已通过', rejected: '已拒绝' }
  return map[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatMoney = (val) => {
  return parseFloat(val || 0).toFixed(2)
}
</script>

<style scoped>
.purchases-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.back-button {
  padding: 0.6rem 1rem;
  background: #f0f0f0;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.back-button:hover { background: #e0e0e0; }

.page-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.action-button {
  padding: 0.7rem 1.2rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: white;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s;
}
.action-button.primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.action-button.primary:hover { transform: translateY(-1px); opacity: 0.95; }
.action-button.members { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); }
.action-button.members:hover { transform: translateY(-1px); opacity: 0.95; }
.action-button.reimburse { background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); }
.action-button.danger { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); }
.action-button:disabled { opacity: 0.5; cursor: not-allowed; }

.stats-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 16px;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  border-left: 4px solid #3498db;
  text-align: center;
}
.stat-card.total { border-left-color: #667eea; }
.stat-card.invoice { border-left-color: #f39c12; }
.stat-card.pending { border-left-color: #e74c3c; }
.stat-card.count { border-left-color: #95a5a6; }

.stat-label { display: block; font-size: 12px; color: #7f8c8d; margin-bottom: 4px; }
.stat-value { display: block; font-size: 20px; font-weight: 700; color: #2c3e50; }

.records-table-container {
  background: white;
  border-radius: 10px;
  overflow-x: auto;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table th {
  background: #f8f9fa;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  border-bottom: 2px solid #e9ecef;
  white-space: nowrap;
}

.records-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #333;
}

.records-table tr:hover { background: #fafbfc; }
.records-table tr.has-invoice { background: #fffbf0; }
.records-table tr.is-invoice-record { background: #f0f7ff; }

.checkbox-col { width: 40px; text-align: center; }
.platform-badge { 
  background: #e8f4fd; 
  color: #2980b9; 
  padding: 2px 8px; 
  border-radius: 10px; 
  font-size: 11px; 
}
.record-type-tag {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
}
.record-type-tag.purchase { background: #e8f5e9; color: #2e7d32; }
.record-type-tag.invoice { background: #e3f2fd; color: #1565c0; }
.amount { font-weight: 600; color: #e74c3c; }

.invoice-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.invoice-badge.yes { background: #eaffea; color: #27ae60; }
.invoice-badge.no { background: #fff5f5; color: #e74c3c; }

.status-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.status-badge.pending { background: #fff8e6; color: #f39c12; }
.status-badge.approved { background: #eaffea; color: #27ae60; }
.status-badge.rejected { background: #fff5f5; color: #e74c3c; }

.reimburse-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.reimburse-badge:not(.is-reimbursed) { background: #f5f5f5; color: #999; }
.reimburse-badge.is-reimbursed { background: #e8f8f0; color: #27ae60; }

.action-buttons { display: flex; gap: 4px; flex-wrap: wrap; }
.btn-view-sm, .btn-edit-sm, .btn-delete-sm, .btn-approve-sm, .btn-reimburse-sm {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.btn-view-sm { background: #3498db; color: white; }
.btn-edit-sm { background: #f39c12; color: white; }
.btn-delete-sm { background: #e74c3c; color: white; }
.btn-approve-sm { background: #27ae60; color: white; }
.btn-reimburse-sm { background: #9b59b6; color: white; }

.empty-row { text-align: center; padding: 40px !important; color: #999; }

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}
.modal-content.large { max-width: 800px; }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem 1.5rem;
  border-bottom: 1px solid #eee;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}
.modal-header h2 { margin: 0; font-size: 1.15rem; color: #2c3e50; }
.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
  line-height: 1;
}

.modal-body { padding: 1.5rem; }

.purchase-form { display: flex; flex-direction: column; gap: 1.5rem; }

.form-section {
  background: #fafbfc;
  padding: 1.25rem;
  border-radius: 10px;
  border: 1px solid #eef0f2;
}
.receipt-section { border-color: #e8f4fd; }
.invoice-section { border-color: #fef5e7; }

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.required-tag {
  font-size: 10px;
  background: #e74c3c;
  color: white;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 500;
}

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }

.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: #555;
}
.form-group input, .form-group select, .form-group textarea {
  padding: 0.7rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.3s;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 10px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.upload-area:hover { border-color: #667eea; background: #f8f9ff; }
.upload-area.has-file { border-style: solid; border-color: #27ae60; }

.upload-placeholder { color: #999; }
.upload-icon { font-size: 3rem; display: block; margin-bottom: 0.5rem; }
.hint { font-size: 12px; color: #bbb; margin-top: 0.3rem; }

.file-preview {
  position: relative;
  display: inline-block;
}
.preview-img {
  max-width: 300px;
  max-height: 200px;
  border-radius: 8px;
  object-fit: contain;
}
.file-preview.file-doc {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}
.file-icon { font-size: 2rem; }
.file-name { font-size: 14px; color: #555; }

.remove-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 22px;
  height: 22px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.file-preview.file-doc .remove-btn { position: static; }

.switch-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.switch-wrapper input[type="checkbox"] { display: none; }
.switch-slider {
  width: 44px;
  height: 24px;
  background: #ccc;
  border-radius: 12px;
  position: relative;
  transition: 0.3s;
}
.switch-slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  background: white;
  border-radius: 50%;
  top: 3px;
  left: 3px;
  transition: 0.3s;
}
.switch-wrapper input:checked + .switch-slider { background: #27ae60; }
.switch-wrapper input:checked + .switch-slider::before { transform: translateX(20px); }
.switch-text { font-size: 13px; color: #666; }

.invoice-form { margin-top: 1rem; }
.detail-note { font-size: 12px; color: #999; margin: 0.5rem 0 1rem; }

/* 发票图片预览 */
.invoice-image-preview {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}
.invoice-image-preview h4 {
  font-size: 14px;
  color: #555;
  margin: 0 0 0.75rem;
}
.image-container {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
}
.invoice-thumbnail {
  max-width: 250px;
  max-height: 180px;
  border-radius: 8px;
  object-fit: contain;
  border: 2px solid #ddd;
  cursor: pointer;
  transition: all 0.3s;
}
.invoice-thumbnail:hover {
  border-color: #667eea;
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(102,126,234,0.2);
}

/* 图片加载状态 */
.image-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 200px;
  min-height: 150px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 8px;
  border: 2px dashed #bdc3c7;
}
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e0e0e0;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.image-loading p {
  margin: 0;
  color: #666;
  font-size: 13px;
}

/* 图片加载错误 */
.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 200px;
  min-height: 150px;
  background: #fff5f5;
  border-radius: 8px;
  border: 2px solid #ffcccc;
}
.error-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}
.image-error p {
  margin: 0 0 12px 0;
  color: #e74c3c;
  font-size: 13px;
  font-weight: 500;
}
.retry-btn {
  padding: 6px 16px;
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s;
}
.retry-btn:hover {
  transform: translateY(-1px);
  opacity: 0.95;
}

.parse-btn {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s;
  white-space: nowrap;
}
.parse-btn:hover {
  transform: translateY(-1px);
  opacity: 0.95;
}
.parse-btn.parsing {
  background: #95a5a6;
  cursor: not-allowed;
}

/* 解析结果展示 */
.parse-result {
  margin-top: 1.5rem;
  padding: 1.25rem;
  background: linear-gradient(135deg, #e8f4fd 0%, #f0f7ff 100%);
  border-radius: 10px;
  border: 2px solid #3498db;
}
.parse-result h4 {
  font-size: 15px;
  color: #2980b9;
  margin: 0 0 1rem;
}
.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.result-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.6rem;
  background: white;
  border-radius: 6px;
}
.result-label {
  font-size: 11px;
  color: #7f8c8d;
  font-weight: 500;
}
.result-value {
  font-size: 14px;
  color: #2c3e50;
  font-weight: 600;
}
.apply-btn {
  width: 100%;
  padding: 0.7rem;
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}
.apply-btn:hover {
  transform: translateY(-1px);
  opacity: 0.95;
}
.apply-btn.applied {
  background: #95a5a6;
  cursor: not-allowed;
}

/* 图片放大弹窗 */
.image-zoom-overlay {
  z-index: 2000;
  background: rgba(0, 0, 0, 0.9);
}
.image-zoom-modal {
  position: relative;
  max-width: 95vw;
  max-height: 95vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.zoom-close {
  position: absolute;
  top: -40px;
  right: -10px;
  background: rgba(255,255,255,0.2);
  color: white;
  font-size: 2rem;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  z-index: 10;
}
.zoom-close:hover {
  background: rgba(255,255,255,0.3);
}
.zoomed-image {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 10px 50px rgba(0,0,0,0.5);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.8rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}
.cancel-btn {
  padding: 0.7rem 1.5rem;
  background: #f0f0f0;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.submit-btn {
  padding: 0.7rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 详情弹窗 */
.detail-modal .modal-body { padding: 1.5rem; }
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
}
.detail-item.full-width { grid-column: span 2; }
.detail-item.highlight { background: #fff8e6; border: 1px solid #ffeaa7; }
.detail-label { font-size: 12px; color: #999; }
.detail-value { font-size: 14px; color: #333; font-weight: 500; }
.detail-value.amount { font-size: 16px; color: #e74c3c; font-weight: 700; }
.detail-section-title {
  grid-column: span 2;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #ddd;
}

.image-previews {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}
.preview-section h4 { font-size: 13px; color: #666; margin: 0 0 0.5rem; }
.large-preview {
  width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid #eee;
}

@media (max-width: 768px) {
  .form-row, .detail-grid, .image-previews { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; }
  .stats-panel { grid-template-columns: repeat(2, 1fr); }
  .action-buttons { flex-wrap: wrap; }
}
</style>
