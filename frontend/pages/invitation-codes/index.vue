<template>
  <div class="invitation-codes-page">
    <div class="page-header">
      <h1 class="page-title">🎫 邀请码管理</h1>
      <button @click="showCreateModal = true" class="action-button primary">
        ➕ 生成邀请码
      </button>
    </div>

    <div class="stats-panel">
      <div class="stat-card">
        <span class="stat-value">{{ totalCodes }}</span>
        <span class="stat-label">总数</span>
      </div>
      <div class="stat-card active">
        <span class="stat-value">{{ activeCodes }}</span>
        <span class="stat-label">有效</span>
      </div>
      <div class="stat-card expired">
        <span class="stat-value">{{ expiredCodes }}</span>
        <span class="stat-label">已过期</span>
      </div>
      <div class="stat-card used">
        <span class="stat-value">{{ usedCodes }}</span>
        <span class="stat-label">已用完</span>
      </div>
    </div>

    <div class="filter-bar">
      <select v-model="filterStatus" @change="loadCodes" class="status-filter">
        <option value="">全部状态</option>
        <option value="active">有效</option>
        <option value="expired">已过期</option>
        <option value="used_out">已用完</option>
        <option value="disabled">已禁用</option>
      </select>
      <select v-model="filterType" @change="loadCodes" class="type-filter">
        <option value="">全部类型</option>
        <option value="teacher">老师</option>
        <option value="student_admin">学生管理员</option>
        <option value="student">学生</option>
      </select>
    </div>

    <div class="codes-table-container">
      <table class="codes-table">
        <thead>
          <tr>
            <th>邀请码</th>
            <th>目标类型</th>
            <th>有效期</th>
            <th>使用情况</th>
            <th>状态</th>
            <th>创建人</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="code in codes" :key="code.id">
            <td>
              <code class="code-text">{{ code.code }}</code>
              <button @click="copyCode(code.code)" class="btn-copy-sm" title="复制">📋</button>
            </td>
            <td>
              <span class="type-badge" :class="code.target_user_type">
                {{ code.target_user_type_text }}
              </span>
            </td>
            <td>{{ formatDateTime(code.expires_at) }}</td>
            <td>{{ code.used_count }}{{ code.max_uses > 0 ? ` / ${code.max_uses}` : ' / ∞' }}</td>
            <td>
              <span class="status-badge" :class="code.status">
                {{ getStatusText(code.status) }}
              </span>
            </td>
            <td>{{ code.creator_name || '-' }}</td>
            <td>{{ formatDateTime(code.created_at) }}</td>
            <td>
              <div class="row-actions">
                <button 
                  @click="toggleCodeStatus(code)" 
                  :class="code.is_active ? 'btn-disable-sm' : 'btn-enable-sm'"
                  :title="code.is_active ? '禁用' : '启用'"
                >{{ code.is_active ? '🔒' : '🔓' }}</button>
                <button 
                  v-if="canDelete"
                  @click="confirmDeleteCode(code)" 
                  class="btn-delete-sm"
                  title="删除"
                >🗑</button>
              </div>
            </td>
          </tr>
          <tr v-if="codes.length === 0">
            <td colspan="8" class="empty-row">暂无邀请码数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button 
        :disabled="currentPage === 1" 
        @click="changePage(currentPage - 1)"
        class="page-btn"
      >上一页</button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button 
        :disabled="currentPage === totalPages" 
        @click="changePage(currentPage + 1)"
        class="page-btn"
      >下一页</button>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>🎫 生成邀请码</h2>
          <button @click="showCreateModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="createCodes" class="modal-body">
          <div class="form-group">
            <label>目标用户类型 *</label>
            <select v-model="createForm.target_user_type" required>
              <option value="student">学生</option>
              <option value="student_admin">学生管理员</option>
              <option value="teacher">老师</option>
              <option v-if="currentUser?.user_type === 'admin'" value="admin">管理员（谨慎使用）</option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>有效期 (天) *</label>
              <input v-model.number="createForm.expires_days" type="number" min="1" max="365" required />
            </div>
            <div class="form-group">
              <label>生成数量 *</label>
              <input v-model.number="createForm.quantity" type="number" min="1" max="20" required />
            </div>
          </div>
          <div class="form-group">
            <label>最大使用次数</label>
            <input v-model.number="createForm.max_uses" type="number" min="-1" placeholder="-1表示无限次" />
            <div class="field-hint">-1 表示无限次使用</div>
          </div>
          <div class="modal-footer">
            <button type="button" @click="showCreateModal = false" class="cancel-button">取消</button>
            <button type="submit" class="submit-button" :disabled="creating">{{ creating ? '生成中...' : '生成' }}</button>
          </div>
        </form>

        <div v-if="createdCodes.length > 0" class="created-codes-result">
          <h3>✅ 已生成 {{ createdCodes.length }} 个邀请码</h3>
          <div class="codes-list">
            <div v-for="code in createdCodes" :key="code.code" class="code-item">
              <code>{{ code.code }}</code>
              <span class="code-type">{{ getTypeText(code.target_user_type) }}</span>
            </div>
          </div>
          <button @click="copyAllCodes" class="copy-all-btn">📋 复制全部</button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-content delete-modal">
        <div class="modal-header">
          <h2>确认删除</h2>
          <button @click="showDeleteModal = false" class="close-button">×</button>
        </div>
        <div class="modal-body">
          <p>确定要删除该邀请码吗？</p>
          <p class="warning-text">此操作不可撤销！</p>
        </div>
        <div class="modal-footer">
          <button @click="showDeleteModal = false" class="cancel-button">取消</button>
          <button @click="deleteCode" class="delete-btn" :disabled="deleting">{{ deleting ? '删除中...' : '确认删除' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

definePageMeta({ 
  layout: 'default',
  middleware: [
    function(to, from) {
      if (import.meta.client) {
        const userStr = localStorage.getItem('user')
        if (userStr) {
          const user = JSON.parse(userStr)
          if (!['admin', 'teacher', 'student_admin'].includes(user.user_type)) {
            return navigateTo('/dashboard')
          }
        } else {
          return navigateTo('/login')
        }
      }
    }
  ]
})

const { $api } = useNuxtApp()

const codes = ref([])
const currentPage = ref(1)
const totalPages = ref(1)
const totalCodes = ref(0)
const filterStatus = ref('')
const filterType = ref('')
const showCreateModal = ref(false)
const showDeleteModal = ref(false)
const creating = ref(false)
const deleting = ref(false)
const deletingCode = ref(null)
const createdCodes = ref([])

const createForm = ref({
  target_user_type: 'student',
  expires_days: 30,
  quantity: 1,
  max_uses: -1
})

const currentUser = ref(null)

const canDelete = computed(() => currentUser.value?.user_type === 'admin')

const activeCodes = computed(() => codes.value.filter(c => c.status === 'active').length)
const expiredCodes = computed(() => codes.value.filter(c => c.status === 'expired').length)
const usedCodes = computed(() => codes.value.filter(c => c.status === 'used_out').length)

onMounted(async () => {
  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  
  await loadCodes()
})

const loadCodes = async () => {
  try {
    const token = localStorage.getItem('token')
    const params = new URLSearchParams()
    params.append('page', currentPage.value)
    params.append('page_size', 20)
    
    const response = await $api.get(`/invitation-codes?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      let data = response.data.data.data || []
      
      if (filterStatus.value) {
        data = data.filter(c => c.status === filterStatus.value)
      }
      if (filterType.value) {
        data = data.filter(c => c.target_user_type === filterType.value)
      }
      
      codes.value = data
      totalCodes.value = response.data.data.total
      totalPages.value = response.data.data.total_pages
    }
  } catch (error) {
    console.error('加载邀请码失败:', error)
  }
}

const createCodes = async () => {
  creating.value = true
  createdCodes.value = []
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post('/invitation-codes', createForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      createdCodes.value = response.data.data.codes
      await loadCodes()
    } else {
      alert(response.data.message || '生成失败')
    }
  } catch (error) {
    alert('生成失败，请稍后重试')
  } finally {
    creating.value = false
  }
}

const toggleCodeStatus = async (code) => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post(`/invitation-codes/${code.id}/toggle`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      await loadCodes()
    } else {
      alert(response.data.message || '操作失败')
    }
  } catch (error) {
    alert('操作失败，请稍后重试')
  }
}

const confirmDeleteCode = (code) => {
  deletingCode.value = code
  showDeleteModal.value = true
}

const deleteCode = async () => {
  if (!deletingCode.value) return
  deleting.value = true
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.delete(`/invitation-codes/${deletingCode.value.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      showDeleteModal.value = false
      deletingCode.value = null
      await loadCodes()
    } else {
      alert(response.data.message || '删除失败')
    }
  } catch (error) {
    alert('删除失败，请稍后重试')
  } finally {
    deleting.value = false
  }
}

const copyToClipboard = (text, label) => {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      alert(label + '已复制到剪贴板！')
    }).catch(() => {
      prompt('复制以下' + label + ':', text)
    })
  } else {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      alert(label + '已复制到剪贴板！')
    } catch (_) {
      prompt('复制以下' + label + ':', text)
    }
    document.body.removeChild(textarea)
  }
}

const copyCode = (code) => {
  copyToClipboard(code, '邀请码')
}

const copyAllCodes = () => {
  const text = createdCodes.value.map(c => c.code).join('\n')
  copyToClipboard(text, '所有邀请码')
}

const changePage = (page) => {
  currentPage.value = page
  loadCodes()
}

const getTypeText = (type) => {
  const map = { admin: '管理员', teacher: '老师', student_admin: '学生管理员', student: '学生' }
  return map[type] || type
}

const getStatusText = (status) => {
  const map = { active: '有效', expired: '已过期', used_out: '已用完', disabled: '已禁用' }
  return map[status] || status
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<style scoped>
.invitation-codes-page {
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

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.action-button {
  padding: 0.7rem 1.2rem;
  border: none;
  border-radius: 5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  color: white;
  font-size: 14px;
}

.action-button.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.action-button.primary:hover { transform: translateY(-1px); }

.stats-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 16px;
  border-radius: 10px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  border-left: 4px solid #3498db;
}

.stat-card.active { border-left-color: #27ae60; }
.stat-card.expired { border-left-color: #e74c3c; }
.stat-card.used { border-left-color: #f39c12; }

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

.stat-label {
  font-size: 12px;
  color: #7f8c8d;
  margin-top: 4px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 1.2rem;
}

.status-filter, .type-filter {
  padding: 0.7rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.codes-table-container {
  background: white;
  border-radius: 10px;
  overflow-x: auto;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.codes-table {
  width: 100%;
  border-collapse: collapse;
}

.codes-table th {
  background: #f8f9fa;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  border-bottom: 2px solid #e9ecef;
  white-space: nowrap;
}

.codes-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #333;
}

.codes-table tr:hover { background: #fafbfc; }

.code-text {
  font-family: monospace;
  font-size: 12px;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 4px;
}

.btn-copy-sm {
  background: none;
  border: none;
  cursor: pointer;
  margin-left: 8px;
  opacity: 0.6;
}

.btn-copy-sm:hover { opacity: 1; }

.type-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.type-badge.teacher { background: #eef7ff; color: #2980b9; }
.type-badge.student_admin { background: #f4ecff; color: #8e44ad; }
.type-badge.student { background: #eaffea; color: #27ae60; }
.type-badge.admin { background: #fee; color: #c0392b; }

.status-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.active { background: #eaffea; color: #27ae60; }
.status-badge.expired { background: #fff5f5; color: #e74c3c; }
.status-badge.used_out { background: #fff8e6; color: #f39c12; }
.status-badge.disabled { background: #eee; color: #95a5a6; }

.row-actions {
  display: flex;
  gap: 4px;
}

.btn-disable-sm, .btn-enable-sm, .btn-delete-sm {
  padding: 3px 7px;
  font-size: 12px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-disable-sm { background: #95a5a6; color: white; }
.btn-enable-sm { background: #27ae60; color: white; }
.btn-delete-sm { background: #e74c3c; color: white; }

.empty-row {
  text-align: center;
  padding: 40px !important;
  color: #999;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

.page-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: 5px;
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: #666;
}

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
  border-radius: 10px;
  width: 90%;
  max-width: 550px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}

.modal-header {
  padding: 1.2rem 1.5rem;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 { margin: 0; font-size: 1.2rem; }

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-body { padding: 1.5rem; }

.form-group { margin-bottom: 1rem; }
.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 500;
  font-size: 13px;
  color: #555;
}
.form-group input, .form-group select {
  width: 100%;
  padding: 0.65rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
  box-sizing: border-box;
}

.field-hint {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
}

.cancel-button {
  padding: 0.6rem 1.2rem;
  background: #f0f0f0;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}

.submit-button {
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.submit-button:disabled { opacity: 0.6; cursor: not-allowed; }

.delete-modal { max-width: 420px; }
.warning-text { color: #e74c3c; font-size: 13px; margin-top: 0.5rem; }
.delete-btn {
  padding: 0.6rem 1.2rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}

.created-codes-result {
  margin: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.created-codes-result h3 {
  margin: 0 0 1rem;
  font-size: 14px;
  color: #27ae60;
}

.codes-list {
  max-height: 150px;
  overflow-y: auto;
}

.code-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: white;
  margin-bottom: 4px;
  border-radius: 4px;
}

.copy-all-btn {
  width: 100%;
  margin-top: 1rem;
  padding: 0.6rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

@media (max-width: 768px) {
  .form-row { grid-template-columns: 1fr; }
  .filter-bar { flex-direction: column; }
  .status-filter, .type-filter { min-height: 44px; }
  .action-button { min-height: 44px; }
  .page-header { flex-direction: column; align-items: flex-start; }
  .modal-content { width: 95%; max-height: 85vh; }
  .modal-footer { flex-direction: column; }
  .cancel-button, .submit-button, .delete-btn { width: 100%; min-height: 44px; }
  .page-btn { min-height: 44px; min-width: 80px; }
}

@media (max-width: 480px) {
  .page-title { font-size: 1.5rem; }
  .stats-panel { grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat-card { padding: 12px; }
  .stat-value { font-size: 20px; }
  .codes-table th, .codes-table td { padding: 10px 12px; font-size: 12px; }
  .codes-table-container { border-radius: 8px; }
  .btn-disable-sm, .btn-enable-sm, .btn-delete-sm {
    min-width: 32px; min-height: 32px; padding: 4px 8px;
  }
  .row-actions { gap: 6px; }
  .pagination { gap: 0.5rem; }
  .page-info { font-size: 12px; }
  .modal-body { padding: 1rem; }
  .modal-header { padding: 1rem; }
  .form-group input, .form-group select { min-height: 44px; }
  .copy-all-btn { min-height: 44px; }
}
</style>
