<template>
  <div class="export-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">&larr; 返回</button>
      <h1 class="page-title">导出数据</h1>
      <span class="event-name" v-if="event">{{ event.event_name }}</span>
    </div>

    <!-- Column Selection -->
    <div class="export-section">
      <h3 class="section-title">选择导出列</h3>
      <p class="section-desc">勾选需要导出的数据列，至少选择一项</p>
      <div class="columns-grid">
        <div
          v-for="col in columns"
          :key="col.key"
          class="column-card"
          :class="{ selected: selectedColumns.includes(col.key) }"
          @click="toggleColumn(col.key)"
        >
          <div class="column-checkbox">
            <input type="checkbox" :checked="selectedColumns.includes(col.key)" @click.stop />
          </div>
          <span class="column-icon">{{ col.icon }}</span>
          <span class="column-label">{{ col.label }}</span>
          <span class="column-desc">{{ col.desc }}</span>
        </div>
      </div>
    </div>

    <!-- Export Options -->
    <div class="export-section">
      <h3 class="section-title">导出选项</h3>
      <div class="options-list">
        <label class="option-item">
          <input type="checkbox" v-model="options.mergedPdf" />
          <div class="option-content">
            <span class="option-label">合并发票PDF</span>
            <span class="option-desc">将所有发票文件按数据顺序合并为一个PDF文件</span>
          </div>
        </label>
        <label class="option-item">
          <input type="checkbox" v-model="options.individualInvoices" />
          <div class="option-content">
            <span class="option-label">单独发票文件</span>
            <span class="option-desc">每个发票作为单独文件保存，文件名以发票税号命名</span>
          </div>
        </label>
        <label class="option-item">
          <input type="checkbox" v-model="options.receiptImages" />
          <div class="option-content">
            <span class="option-label">购物凭证图片</span>
            <span class="option-desc">导出所有购物凭证截图到独立文件夹</span>
          </div>
        </label>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="export-actions">
      <button
        @click="startExport"
        :disabled="!canExport || exporting"
        class="btn-export"
      >
        <span v-if="exporting" class="spinner"></span>
        {{ exporting ? '导出中...' : '确认导出' }}
      </button>
      <button @click="goBack" class="btn-cancel">取消</button>
    </div>

    <!-- Progress Display -->
    <div v-if="taskId && (exportStatus === 'processing' || exportStatus === 'pending')" class="progress-section">
      <div class="progress-info">
        <span class="progress-label">{{ progressMessage || '准备中...' }}</span>
        <span class="progress-percent">{{ progress }}%</span>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar" :style="{ width: progress + '%' }"></div>
      </div>
    </div>

    <!-- Download Section -->
    <div v-if="exportStatus === 'completed'" class="download-section">
      <div class="download-icon">&#10003;</div>
      <h3>导出完成</h3>
      <p class="download-info">共 {{ recordCount }} 条记录 &middot; {{ formatFileSize(fileSize) }}</p>
      <button @click="downloadFile" class="btn-download">下载ZIP文件</button>
      <p class="download-hint">文件将在30分钟后自动删除</p>
    </div>

    <!-- Error Display -->
    <div v-if="exportStatus === 'failed'" class="error-section">
      <div class="error-icon">&#10007;</div>
      <h3>导出失败</h3>
      <p class="error-message">{{ errorMessage }}</p>
      <button @click="resetExport" class="btn-retry">重试</button>
    </div>
  </div>
</template>

<script setup>
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const { $api } = useNuxtApp()

const eventId = computed(() => route.params.id)
const event = ref(null)

const columns = [
  { key: 'item_name', label: '名称', icon: '📦', desc: '物品或项目名称' },
  { key: 'purchase_platform', label: '购买平台', icon: '🏪', desc: '购买渠道平台' },
  { key: 'amount', label: '金额', icon: '💰', desc: '购买金额' },
  { key: 'purchase_date', label: '购物日期', icon: '📅', desc: '购买日期' },
  { key: 'invoice_date', label: '开票日期', icon: '🗓', desc: '发票开票日期' },
  { key: 'uploader', label: '上传人', icon: '👤', desc: '记录上传者姓名' },
  { key: 'invoice_tax_number', label: '发票税号', icon: '🔢', desc: '发票上的纳税人识别号' },
  { key: 'receipt_image', label: '购物图片', icon: '🖼', desc: '购物凭证截图' },
  { key: 'invoice_image', label: '发票图片', icon: '📄', desc: '发票文件' },
]

const selectedColumns = ref(['item_name', 'purchase_platform', 'amount', 'purchase_date', 'uploader'])
const options = ref({
  mergedPdf: true,
  individualInvoices: false,
  receiptImages: true,
})

const taskId = ref(null)
const exportStatus = ref(null)
const progress = ref(0)
const progressMessage = ref('')
const recordCount = ref(0)
const fileSize = ref(0)
const errorMessage = ref('')
const exporting = ref(false)
let pollTimer = null

const canExport = computed(() => selectedColumns.value.length > 0)

const toggleColumn = (key) => {
  const idx = selectedColumns.value.indexOf(key)
  if (idx >= 0) {
    selectedColumns.value.splice(idx, 1)
  } else {
    selectedColumns.value.push(key)
  }
}

const loadEvent = async () => {
  try {
    const response = await $api.get(`/events/${eventId.value}`)
    if (response.data.code === 200) {
      event.value = response.data.data
    }
  } catch (e) {
    console.error('加载赛事信息失败:', e)
  }
}

const startExport = async () => {
  if (!canExport.value || exporting.value) return

  exporting.value = true
  exportStatus.value = null
  errorMessage.value = ''
  progress.value = 0
  progressMessage.value = ''

  try {
    const response = await $api.post(`/events/${eventId.value}/export`, {
      columns: selectedColumns.value,
      options: options.value,
    })

    if (response.data.code === 200) {
      taskId.value = response.data.data.task_id
      exportStatus.value = response.data.data.status

      if (response.data.data.cached) {
        exportStatus.value = 'completed'
        await loadTaskStatus()
      } else {
        startPolling()
      }
    } else {
      exportStatus.value = 'failed'
      errorMessage.value = response.data.message || '导出请求失败'
    }
  } catch (e) {
    exportStatus.value = 'failed'
    errorMessage.value = e.response?.data?.message || '网络错误，请重试'
  } finally {
    exporting.value = false
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    await loadTaskStatus()
  }, 1500)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const loadTaskStatus = async () => {
  if (!taskId.value) return

  try {
    const response = await $api.get(`/events/${eventId.value}/export/status`, {
      params: { task_id: taskId.value }
    })

    if (response.data.code === 200) {
      const data = response.data.data
      exportStatus.value = data.status
      progress.value = data.progress_percent || 0
      progressMessage.value = data.progress_message || ''
      recordCount.value = data.record_count || 0
      fileSize.value = data.file_size || 0

      if (data.status === 'completed' || data.status === 'failed') {
        stopPolling()
        if (data.status === 'failed') {
          errorMessage.value = data.error_message || '导出失败'
        }
      }
    }
  } catch (e) {
    console.error('查询导出状态失败:', e)
  }
}

const downloadFile = async () => {
  if (!taskId.value) return

  try {
    const response = await $api.get(`/events/${eventId.value}/export/download`, {
      params: { task_id: taskId.value },
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${event.value?.event_name || '导出数据'}_${new Date().toISOString().split('T')[0]}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    if (e.response?.data) {
      try {
        const text = await e.response.data.text()
        const json = JSON.parse(text)
        alert(json.message || '下载失败')
      } catch {
        alert('下载失败，请重试')
      }
    } else {
      alert('下载失败，请重试')
    }
  }
}

const resetExport = () => {
  taskId.value = null
  exportStatus.value = null
  progress.value = 0
  progressMessage.value = ''
  recordCount.value = 0
  fileSize.value = 0
  errorMessage.value = ''
}

const goBack = () => {
  stopPolling()
  router.push(`/purchases/${eventId.value}`)
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

onMounted(() => {
  loadEvent()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.export-page {
  max-width: 900px;
  margin: 0 auto;
  padding-bottom: 2rem;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.back-button {
  padding: 0.6rem 1rem;
  background: #f0f0f0;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}
.back-button:hover { background: #e0e0e0; }

.page-title {
  font-size: 1.6rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.event-name {
  font-size: 0.9rem;
  color: #7f8c8d;
  background: #f8f9fa;
  padding: 0.3rem 0.8rem;
  border-radius: 20px;
}

.export-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 0.3rem 0;
}

.section-desc {
  font-size: 0.85rem;
  color: #95a5a6;
  margin: 0 0 1rem 0;
}

.columns-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.8rem;
}

.column-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  padding: 1rem 0.5rem;
  border: 2px solid #ecf0f1;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  position: relative;
}
.column-card:hover {
  border-color: #bdc3c7;
  background: #fafafa;
}
.column-card.selected {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
}

.column-checkbox {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
}
.column-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #667eea;
  cursor: pointer;
}

.column-icon {
  font-size: 1.5rem;
  margin-top: 0.3rem;
}

.column-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c3e50;
}

.column-desc {
  font-size: 0.75rem;
  color: #95a5a6;
  line-height: 1.3;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  padding: 0.8rem 1rem;
  border: 1px solid #ecf0f1;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.option-item:hover {
  background: #f8f9fa;
  border-color: #dcdfe6;
}
.option-item input[type="checkbox"] {
  margin-top: 0.2rem;
  width: 16px;
  height: 16px;
  accent-color: #667eea;
  cursor: pointer;
}

.option-content {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.option-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #2c3e50;
}

.option-desc {
  font-size: 0.8rem;
  color: #95a5a6;
}

.export-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 1.5rem;
}

.btn-export {
  padding: 0.8rem 2.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.btn-export:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}
.btn-export:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-cancel {
  padding: 0.8rem 2rem;
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-cancel:hover {
  background: #e0e0e0;
}

.progress-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.8rem;
}

.progress-label {
  font-size: 0.9rem;
  color: #2c3e50;
}

.progress-percent {
  font-size: 0.9rem;
  font-weight: 600;
  color: #667eea;
}

.progress-bar-container {
  height: 8px;
  background: #ecf0f1;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.download-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.download-icon {
  width: 60px;
  height: 60px;
  line-height: 60px;
  font-size: 1.8rem;
  color: white;
  background: linear-gradient(135deg, #27ae60, #2ecc71);
  border-radius: 50%;
  margin: 0 auto 1rem;
}

.download-section h3 {
  font-size: 1.2rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
}

.download-info {
  font-size: 0.9rem;
  color: #7f8c8d;
  margin: 0 0 1.5rem 0;
}

.btn-download {
  padding: 0.8rem 2.5rem;
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-download:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(39, 174, 96, 0.4);
}

.download-hint {
  font-size: 0.8rem;
  color: #bdc3c7;
  margin: 1rem 0 0 0;
}

.error-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.error-icon {
  width: 60px;
  height: 60px;
  line-height: 60px;
  font-size: 1.8rem;
  color: white;
  background: linear-gradient(135deg, #e74c3c, #c0392b);
  border-radius: 50%;
  margin: 0 auto 1rem;
}

.error-section h3 {
  font-size: 1.2rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
}

.error-message {
  font-size: 0.9rem;
  color: #e74c3c;
  margin: 0 0 1.5rem 0;
}

.btn-retry {
  padding: 0.8rem 2rem;
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-retry:hover {
  background: #e0e0e0;
}

@media (max-width: 768px) {
  .columns-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .page-header {
    gap: 0.5rem;
  }

  .page-title {
    font-size: 1.3rem;
  }
}

@media (max-width: 480px) {
  .columns-grid {
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }

  .column-card {
    padding: 0.7rem 0.4rem;
  }

  .export-actions {
    flex-direction: column;
  }

  .btn-export,
  .btn-cancel {
    width: 100%;
    justify-content: center;
  }
}
</style>
