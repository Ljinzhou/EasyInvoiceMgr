<template>
  <div class="projects-page">
    <div class="page-header">
      <h1 class="page-title">项目管理</h1>
      <button @click="goToCreate" class="create-button">创建比赛</button>
    </div>

    <div class="projects-list">
      <div v-for="event in events" :key="event.event_id" class="project-card">
        <div class="project-header">
          <div class="project-title-section">
            <h3 class="project-title">{{ event.event_name }}</h3>
            <span class="project-status" :class="event.status">
              {{ event.status === 'ongoing' ? '进行中' : '已结束' }}
            </span>
          </div>
          <div class="action-buttons">
            <button @click="editEvent(event)" class="edit-button">编辑</button>
            <button @click="confirmDelete(event)" class="delete-button">删除</button>
          </div>
        </div>
        
        <div class="project-body">
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">类别</span>
              <span class="info-value">{{ event.category || '未分类' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">地点</span>
              <span class="info-value">{{ event.location || '未设置' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">开始时间</span>
              <span class="info-value">{{ formatDateTime(event.event_start_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">结束时间</span>
              <span class="info-value">{{ formatDateTime(event.event_end_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">上传开始</span>
              <span class="info-value">{{ formatDateTime(event.upload_start_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">上传结束</span>
              <span class="info-value">{{ formatDateTime(event.upload_end_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">总预算</span>
              <span class="info-value budget">¥{{ parseFloat(event.total_budget).toFixed(2) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">已报销</span>
              <span class="info-value">¥{{ parseFloat(event.reimbursed_amount).toFixed(2) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">剩余预算</span>
              <span class="info-value remaining">¥{{ parseFloat(event.remaining_budget).toFixed(2) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">发票数量</span>
              <span class="info-value">{{ event.invoice_count || 0 }} 张</span>
            </div>
          </div>
          <div class="description-section" v-if="event.description">
            <span class="info-label">描述</span>
            <p class="description-text">{{ event.description }}</p>
          </div>
        </div>
      </div>

      <div v-if="events.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-text">暂无比赛数据</div>
        <button @click="goToCreate" class="create-button">创建第一个比赛</button>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>编辑比赛</h2>
          <button @click="showEditModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="updateEvent" class="modal-body">
          <div class="form-group">
            <label>比赛名称 *</label>
            <input v-model="editForm.event_name" type="text" required />
          </div>
          <div class="form-group">
            <label>比赛描述</label>
            <textarea v-model="editForm.description" rows="3"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>比赛类别</label>
              <input v-model="editForm.category" type="text" />
            </div>
            <div class="form-group">
              <label>比赛地点</label>
              <input v-model="editForm.location" type="text" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>开始时间 *</label>
              <input v-model="editForm.event_start_time" type="datetime-local" required />
            </div>
            <div class="form-group">
              <label>结束时间 *</label>
              <input v-model="editForm.event_end_time" type="datetime-local" required />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>上传开始时间</label>
              <input v-model="editForm.upload_start_time" type="datetime-local" />
            </div>
            <div class="form-group">
              <label>上传结束时间</label>
              <input v-model="editForm.upload_end_time" type="datetime-local" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>总预算 (元)</label>
              <input v-model.number="editForm.total_budget" type="number" step="0.01" min="0" />
            </div>
            <div class="form-group">
              <label>负责人</label>
              <div class="autocomplete-wrapper">
                <input
                  v-model="leaderSearch"
                  type="text"
                  placeholder="搜索负责人"
                  @input="searchUsers"
                  @focus="showLeaderDropdown = true"
                />
                <div v-if="showLeaderDropdown && filteredUsers.length > 0" class="dropdown">
                  <div
                    v-for="user in filteredUsers"
                    :key="user.user_id"
                    class="dropdown-item"
                    @click="selectLeader(user)"
                  >
                    {{ user.real_name }} ({{ user.user_type === 'admin' ? '管理员' : '教师' }})
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" @click="showEditModal = false" class="cancel-button">取消</button>
            <button type="submit" class="submit-button" :disabled="updating">
              {{ updating ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-content delete-modal">
        <div class="modal-header">
          <h2>确认删除</h2>
          <button @click="showDeleteModal = false" class="close-button">×</button>
        </div>
        <div class="modal-body">
          <div class="delete-warning">
            <div class="warning-icon">⚠️</div>
            <p class="warning-text">确定要删除项目 <strong>"{{ deletingEvent?.event_name }}"</strong> 吗？</p>
            <p class="warning-hint">此操作不可撤销，删除后数据将无法恢复。</p>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" @click="showDeleteModal = false" class="cancel-button">取消</button>
          <button type="button" @click="deleteEvent" class="delete-confirm-button" :disabled="deleting">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useCacheStore } from '~/stores/cache'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const cacheStore = useCacheStore()

const events = ref([])
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const updating = ref(false)
const deleting = ref(false)
const editingEventId = ref(null)
const deletingEvent = ref(null)

const editForm = ref({
  event_name: '',
  description: '',
  category: '',
  location: '',
  event_start_time: '',
  event_end_time: '',
  upload_start_time: '',
  upload_end_time: '',
  total_budget: 0,
  leader_id: null
})

const leaderSearch = ref('')
const filteredUsers = ref([])
const showLeaderDropdown = ref(false)

onMounted(async () => {
  console.log('=== 项目管理：页面加载 ===')
  const token = localStorage.getItem('token')
  console.log('检查token:', token ? '已登录' : '未登录')
  
  if (!token) {
    console.log('用户未登录，跳转到登录页面')
    navigateTo('/login')
    return
  }
  
  cacheStore.restoreFromLocalStorage()
  
  await loadEvents()
})

onUnmounted(() => {
  cacheStore.persistToLocalStorage()
})

const loadEvents = async (forceRefresh = false) => {
  const startTime = performance.now()
  console.log('=== 项目管理：开始加载比赛列表 ===')
  
  try {
    const token = localStorage.getItem('token')
    const cacheKey = cacheStore.generateKey('/events', { page: 1, page_size: 100 })
    
    const response = await cacheStore.fetchWithCache(
      cacheKey,
      async () => {
        console.log('发送请求: GET /api/events')
        return await $api.get('/events', {
          headers: { Authorization: `Bearer ${token}` }
        })
      },
      { forceRefresh, expiry: 3 * 60 * 1000 }
    )
    
    if (response.data.code === 200) {
      events.value = response.data.data.data
      console.log('成功加载比赛列表，数量:', events.value.length)
    }
  } catch (error) {
    console.error('加载比赛列表失败:', error)
  } finally {
    const loadTime = performance.now() - startTime
    console.log(`=== 项目管理：比赛列表加载完成，耗时: ${loadTime.toFixed(2)}ms ===`)
    console.log('缓存统计:', cacheStore.getStats)
  }
}

const goToCreate = () => {
  navigateTo('/events/create')
}

const editEvent = (event) => {
  editingEventId.value = event.event_id
  editForm.value = {
    event_name: event.event_name,
    description: event.description || '',
    category: event.category || '',
    location: event.location || '',
    event_start_time: formatDateTimeLocal(event.event_start_time),
    event_end_time: formatDateTimeLocal(event.event_end_time),
    upload_start_time: formatDateTimeLocal(event.upload_start_time),
    upload_end_time: formatDateTimeLocal(event.upload_end_time),
    total_budget: parseFloat(event.total_budget),
    leader_id: event.leader_id
  }
  leaderSearch.value = ''
  showEditModal.value = true
}

const formatDateTimeLocal = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toISOString().slice(0, 16)
}

const updateEvent = async () => {
  updating.value = true
  console.log('=== 项目管理：更新比赛 ===')
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/events/${editingEventId.value}`, editForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      console.log('比赛更新成功')
      cacheStore.invalidateEventCache(editingEventId.value)
      showEditModal.value = false
      await loadEvents(true)
    }
  } catch (error) {
    console.error('更新比赛失败:', error)
    alert('更新比赛失败，请稍后重试')
  } finally {
    updating.value = false
  }
}

const searchUsers = async () => {
  if (!leaderSearch.value) {
    filteredUsers.value = []
    return
  }
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/users?search=${leaderSearch.value}&user_type=admin,teacher`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      filteredUsers.value = response.data.data
    }
  } catch (error) {
    console.error('搜索用户失败:', error)
  }
}

const selectLeader = (user) => {
  editForm.value.leader_id = user.user_id
  leaderSearch.value = user.real_name
  showLeaderDropdown.value = false
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '未设置'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const confirmDelete = (event) => {
  deletingEvent.value = event
  showDeleteModal.value = true
}

const deleteEvent = async () => {
  if (!deletingEvent.value) return
  
  deleting.value = true
  console.log('=== 项目管理：删除项目 ===')
  console.log('项目ID:', deletingEvent.value.event_id)
  console.log('项目名称:', deletingEvent.value.event_name)
  
  try {
    const token = localStorage.getItem('token')
    console.log('发送删除请求: DELETE /api/events/' + deletingEvent.value.event_id)
    
    const response = await $api.delete(`/events/${deletingEvent.value.event_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    console.log('删除响应:', response.data)
    
    if (response.data.code === 200) {
      console.log('删除成功')
      cacheStore.invalidateEventCache(deletingEvent.value.event_id)
      showDeleteModal.value = false
      deletingEvent.value = null
      await loadEvents(true)
      alert('项目删除成功')
    } else {
      console.error('删除失败:', response.data.message)
      alert(response.data.message || '删除失败，请稍后重试')
    }
  } catch (error) {
    console.error('=== 项目管理：删除项目异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    console.error('错误响应数据:', error.response?.data)
    
    const message = error.response?.data?.message || '删除失败，请稍后重试'
    alert(message)
  } finally {
    deleting.value = false
    console.log('=== 项目管理：删除流程结束 ===')
  }
}
</script>

<style scoped>
.projects-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.create-button {
  padding: 0.8rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.3s ease;
}

.create-button:hover {
  opacity: 0.9;
}

.projects-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.project-card {
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.project-header {
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-title-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.project-title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
}

.project-status {
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.2);
}

.project-status.ongoing {
  background: #27ae60;
}

.project-status.finished {
  background: #e74c3c;
}

.edit-button {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.edit-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

.delete-button {
  padding: 0.5rem 1rem;
  background: rgba(231, 76, 60, 0.8);
  border: 1px solid rgba(231, 76, 60, 0.9);
  color: white;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.delete-button:hover {
  background: rgba(231, 76, 60, 1);
}

.project-body {
  padding: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.info-label {
  font-size: 0.85rem;
  color: #7f8c8d;
}

.info-value {
  font-size: 0.95rem;
  color: #2c3e50;
  font-weight: 500;
}

.info-value.budget {
  color: #27ae60;
}

.info-value.remaining {
  color: #3498db;
}

.description-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #ecf0f1;
}

.description-text {
  margin: 0.5rem 0 0 0;
  color: #2c3e50;
  line-height: 1.6;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-text {
  color: #7f8c8d;
  font-size: 1.1rem;
  margin-bottom: 1.5rem;
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
  max-width: 700px;
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

.autocomplete-wrapper {
  position: relative;
}

.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 5px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.dropdown-item {
  padding: 0.7rem;
  cursor: pointer;
  transition: background 0.3s ease;
}

.dropdown-item:hover {
  background: #f8f9fa;
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

.delete-modal {
  max-width: 500px;
}

.delete-warning {
  text-align: center;
  padding: 1rem 0;
}

.warning-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.warning-text {
  font-size: 1.1rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.warning-hint {
  color: #7f8c8d;
  font-size: 0.9rem;
}

.delete-confirm-button {
  padding: 0.7rem 1.5rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.3s ease;
}

.delete-confirm-button:hover:not(:disabled) {
  background: #c0392b;
}

.delete-confirm-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .info-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
