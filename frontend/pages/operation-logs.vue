<template>
  <div class="operation-logs-page">
    <div class="page-header">
      <h1>操作日志</h1>
      <p class="subtitle">追踪所有用户操作行为</p>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <label>操作类型</label>
        <select v-model="filters.action_type" @change="page = 1; fetchLogs()">
          <option value="">全部操作</option>
          <option v-for="type in actionTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>目标类型</label>
        <select v-model="filters.target_type" @change="page = 1; fetchLogs()">
          <option value="">全部类型</option>
          <option value="event">项目</option>
          <option value="invoice">发票</option>
          <option value="voucher">凭证</option>
          <option value="purchase_record">购买记录</option>
          <option value="user">用户</option>
          <option value="invitation_code">邀请码</option>
          <option value="system">系统</option>
        </select>
      </div>
      <div class="filter-group">
        <label>开始日期</label>
        <input type="date" v-model="filters.start_date" @change="page = 1; fetchLogs()" />
      </div>
      <div class="filter-group">
        <label>结束日期</label>
        <input type="date" v-model="filters.end_date" @change="page = 1; fetchLogs()" />
      </div>
      <button class="reset-btn" @click="resetFilters">重置筛选</button>
    </div>

    <!-- 批量操作栏 -->
    <div class="batch-actions" v-if="selectedLogs.length > 0">
      <span>已选择 {{ selectedLogs.length }} 条</span>
      <button class="delete-btn" @click="batchDelete">删除选中</button>
      <button class="cancel-btn" @click="selectedLogs = []">取消选择</button>
    </div>

    <!-- 日志列表 -->
    <div class="logs-table">
      <table>
        <thead>
          <tr>
            <th class="checkbox-col">
              <input type="checkbox" @change="toggleSelectAll" :checked="isAllSelected" />
            </th>
            <th>时间</th>
            <th>操作人</th>
            <th>操作类型</th>
            <th>操作描述</th>
            <th>关联项目</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.log_id">
            <td class="checkbox-col">
              <input type="checkbox" :value="log.log_id" v-model="selectedLogs" />
            </td>
            <td class="time-col">{{ formatTime(log.created_at) }}</td>
            <td>{{ log.username }}</td>
            <td>
              <span class="action-tag" :class="getActionClass(log.action_type)">
                {{ getActionLabel(log.action_type) }}
              </span>
            </td>
            <td class="desc-col">
              <a
                v-if="log.target_type && log.target_id"
                href="javascript:void(0)"
                class="log-link"
                @click="navigateToDetail(log)"
                :title="log.action_description"
              >
                {{ log.action_description }}
              </a>
              <span v-else :title="log.action_description">{{ log.action_description }}</span>
            </td>
            <td>
              <a
                v-if="log.event_id"
                href="javascript:void(0)"
                class="event-link"
                @click="navigateTo(`/projects/${log.event_id}`)"
                :title="log.event_name"
              >
                {{ log.event_name }}
              </a>
              <span v-else>-</span>
            </td>
            <td class="action-col">
              <button class="delete-single-btn" @click="deleteLog(log.log_id)" title="删除">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                </svg>
              </button>
            </td>
          </tr>
          <tr v-if="logs.length === 0">
            <td colspan="7" class="empty-row">暂无操作日志</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button @click="page--; fetchLogs()" :disabled="page === 1">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页 (共 {{ total }} 条)</span>
      <button @click="page++; fetchLogs()" :disabled="page >= totalPages">下一页</button>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="confirm-modal">
        <h3>确认删除</h3>
        <p>确定要删除选中的 {{ deleteCount }} 条日志吗？此操作不可恢复。</p>
        <div class="modal-actions">
          <button @click="showDeleteConfirm = false">取消</button>
          <button class="delete-btn" @click="confirmDelete">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const { $api } = useNuxtApp()

const logs = ref<any[]>([])
const actionTypes = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const selectedLogs = ref<number[]>([])

const filters = ref({
  action_type: '',
  target_type: '',
  start_date: '',
  end_date: ''
})

const showDeleteConfirm = ref(false)
const deleteCount = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const isAllSelected = computed(() => logs.value.length > 0 && selectedLogs.value.length === logs.value.length)

onMounted(async () => {
  await fetchActionTypes()
  await fetchLogs()
})

async function fetchActionTypes() {
  try {
    const token = localStorage.getItem('token')
    const resp = await $api.get('/operation-logs/action-types', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (resp.data.code === 200) {
      actionTypes.value = resp.data.data
    }
  } catch (e: any) {
    if (e.response?.status === 403) {
      alert('需要管理员权限访问')
      navigateTo('/dashboard')
    }
  }
}

async function fetchLogs() {
  try {
    const token = localStorage.getItem('token')
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filters.value.action_type) params.action_type = filters.value.action_type
    if (filters.value.target_type) params.target_type = filters.value.target_type
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    
    const resp = await $api.get('/operation-logs', {
      params,
      headers: { Authorization: `Bearer ${token}` }
    })
    if (resp.data.code === 200) {
      logs.value = resp.data.data.logs
      total.value = resp.data.data.total
    }
  } catch (e: any) {
    if (e.response?.status === 403) {
      alert('需要管理员权限访问')
      navigateTo('/dashboard')
    }
  }
}

function resetFilters() {
  filters.value = { action_type: '', target_type: '', start_date: '', end_date: '' }
  page.value = 1
  fetchLogs()
}

function formatTime(isoString: string) {
  if (!isoString) return '-'
  const d = new Date(isoString)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function getActionLabel(actionType: string) {
  const type = actionTypes.value.find((t: any) => t.value === actionType)
  return type ? type.label : actionType
}

function getActionClass(actionType: string) {
  if (actionType.includes('create')) return 'create'
  if (actionType.includes('delete')) return 'delete'
  if (actionType.includes('update') || actionType.includes('edit')) return 'update'
  if (actionType.includes('reimburse') || actionType.includes('approve') || actionType.includes('login')) return 'approve'
  return 'default'
}

function navigateToDetail(log: any) {
  const { target_type, target_id, event_id } = log
  if (!target_type || !target_id) return

  switch (target_type) {
    case 'event':
      navigateTo(`/projects/${target_id}`)
      break
    case 'purchase_record':
      // 跳转到项目的购买记录页面，高亮目标记录
      if (event_id) {
        navigateTo(`/purchases/${event_id}?highlight=${target_id}`)
      }
      break
    case 'invoice':
      if (event_id) {
        navigateTo(`/purchases/${event_id}?highlight=${target_id}&tab=invoices`)
      }
      break
    case 'voucher':
      if (event_id) {
        navigateTo(`/purchases/${event_id}?highlight=${target_id}&tab=vouchers`)
      }
      break
    case 'user':
      navigateTo(`/users/${target_id}`)
      break
    case 'invitation_code':
      navigateTo('/settings?tab=invitation')
      break
    default:
      if (event_id) {
        navigateTo(`/projects/${event_id}`)
      }
  }
}

function toggleSelectAll(e: Event) {
  if ((e.target as HTMLInputElement).checked) {
    selectedLogs.value = logs.value.map(l => l.log_id)
  } else {
    selectedLogs.value = []
  }
}

function batchDelete() {
  deleteCount.value = selectedLogs.value.length
  showDeleteConfirm.value = true
}

function deleteLog(logId: number) {
  selectedLogs.value = [logId]
  deleteCount.value = 1
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  try {
    const token = localStorage.getItem('token')
    const resp = await $api.delete('/operation-logs', {
      data: { log_ids: selectedLogs.value },
      headers: { Authorization: `Bearer ${token}` }
    })
    if (resp.data.code === 200) {
      alert(`成功删除 ${resp.data.data.deleted} 条日志`)
      selectedLogs.value = []
      showDeleteConfirm.value = false
      await fetchLogs()
    } else {
      alert(resp.data.message || '删除失败')
    }
  } catch (e: any) {
    alert(e.response?.data?.message || '删除失败')
  }
}
</script>

<style scoped>
.operation-logs-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.8rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  font-size: 0.9rem;
}

.filter-bar {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  background: white;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.filter-group label {
  font-size: 0.8rem;
  color: #666;
  font-weight: 500;
}

.filter-group select,
.filter-group input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-height: 36px;
}

.reset-btn {
  padding: 0.5rem 1rem;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-end;
  min-height: 36px;
}

.reset-btn:hover {
  background: #e0e0e0;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: #fff3cd;
  padding: 0.8rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.delete-btn {
  background: #dc3545;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.delete-btn:hover {
  background: #c82333;
}

.cancel-btn {
  background: #6c757d;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.logs-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.8rem;
  text-align: left;
  border-bottom: 1px solid #eee;
  font-size: 0.9rem;
}

th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.checkbox-col {
  width: 40px;
  text-align: center;
}

.time-col {
  white-space: nowrap;
  color: #666;
  font-size: 0.85rem;
}

.desc-col {
  max-width: 300px;
}

.log-link {
  color: #667eea;
  text-decoration: none;
  cursor: pointer;
}

.log-link:hover {
  text-decoration: underline;
}

.event-link {
  color: #28a745;
  text-decoration: none;
  cursor: pointer;
}

.event-link:hover {
  text-decoration: underline;
}

.action-tag {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.action-tag.create { background: #d4edda; color: #155724; }
.action-tag.delete { background: #f8d7da; color: #721c24; }
.action-tag.update { background: #cce5ff; color: #004085; }
.action-tag.approve { background: #fff3cd; color: #856404; }
.action-tag.default { background: #e2e3e5; color: #383d41; }

.delete-single-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.3rem;
  opacity: 0.6;
  transition: opacity 0.2s;
  color: #dc3545;
}

.delete-single-btn:hover {
  opacity: 1;
}

.empty-row {
  text-align: center;
  color: #999;
  padding: 2rem !important;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.pagination button {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  min-height: 36px;
}

.pagination button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.confirm-modal {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  max-width: 400px;
}

.confirm-modal h3 {
  margin: 0 0 1rem;
}

.confirm-modal p {
  color: #666;
  margin-bottom: 1rem;
}

.modal-actions {
  display: flex;
  gap: 0.8rem;
  justify-content: flex-end;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.modal-actions button:first-child {
  background: #f0f0f0;
}

.modal-actions .delete-btn {
  background: #dc3545;
  color: white;
}
</style>
