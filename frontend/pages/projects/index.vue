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
            <button @click="goToInvoiceManage(event)" class="action-btn invoice-btn">📄 发票</button>
            <button @click="toggleEventStatus(event)" v-if="event.status === 'ongoing'" class="action-btn end-btn">⏹ 结束</button>
            <button @click="openAddMemberModal(event)" class="action-btn member-btn">👥 添加人员</button>
            <button @click="viewMembers(event)" class="action-btn view-btn">📋 查看人员</button>
            <button @click="editEvent(event)" class="edit-button">编辑</button>
            <button @click="confirmDelete(event)" class="delete-button">删除</button>
          </div>
        </div>
        
        <div class="project-body">
          <!-- 预算信息面板 -->
          <div class="budget-overview">
            <div class="budget-item total">
              <span class="b-label">总预算</span>
              <span class="b-value">¥ {{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="budget-item spent">
              <span class="b-label">已用金额</span>
              <span class="b-value">¥ {{ formatMoney(event.spent_amount) }}</span>
              <div class="mini-progress">
                <div class="mini-fill spent-fill" :style="{ width: getBudgetUsagePercent(event) + '%' }"></div>
              </div>
            </div>
            <div class="budget-item invoice">
              <span class="b-label">发票总额</span>
              <span class="b-value">¥ {{ formatMoney(event.invoice_total_amount) }}</span>
            </div>
            <div class="budget-item reimbursed">
              <span class="b-label">已报销</span>
              <span class="b-value">¥ {{ formatMoney(event.reimbursed_amount) }}</span>
            </div>
            <div class="budget-item remaining" :class="{ 'low': getRemainingPercent(event) < 20 }">
              <span class="b-label">剩余预算</span>
              <span class="b-value">¥ {{ formatMoney(getRemainingBudget(event)) }}</span>
              <div class="mini-progress">
                <div class="mini-fill" :style="{ width: getRemainingPercent(event) + '%' }"></div>
              </div>
            </div>
            <div class="budget-item count">
              <span class="b-label">记录数</span>
              <span class="b-value">{{ event.voucher_count || 0 }} 条</span>
            </div>
          </div>

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
              <span class="info-value budget">¥{{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">已用金额</span>
              <span class="info-value spent">¥{{ formatMoney(event.spent_amount) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">已报销</span>
              <span class="info-value">¥{{ formatMoney(event.reimbursed_amount) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">剩余预算</span>
              <span class="info-value remaining">¥{{ formatMoney(event.remaining_budget) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">记录数量</span>
              <span class="info-value">{{ event.voucher_count || 0 }} 条</span>
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
          <div class="form-group">
            <label>是否需要审核发票</label>
            <div class="checkbox-group">
              <input type="checkbox" id="need_invoice_review" v-model="editForm.need_invoice_review" />
              <label for="need_invoice_review">需要审核发票</label>
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

    <!-- 添加人员弹窗 -->
    <div v-if="showAddMemberModal" class="modal-overlay" @click.self="showAddMemberModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>添加成员 - {{ currentEvent?.event_name }}</h2>
          <button @click="showAddMemberModal = false" class="close-button">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>搜索用户</label>
            <div class="autocomplete-wrapper">
              <input
                v-model="memberSearch"
                type="text"
                placeholder="输入用户名或真实姓名"
                @input="searchUsersForMember"
                @focus="showMemberDropdown = true"
              />
              <div v-if="showMemberDropdown && filteredMembers.length > 0" class="dropdown">
                <div
                  v-for="user in filteredMembers"
                  :key="user.user_id"
                  class="dropdown-item"
                  @click="selectMember(user)"
                >
                  {{ user.real_name }} ({{ user.username }}) - {{ getUserTypeText(user.user_type) }}
                </div>
              </div>
            </div>
          </div>
          <div v-if="selectedMember" class="selected-member">
            <div class="member-info">
              <img :src="selectedMember.avatar_url || '/default-avatar.png'" class="avatar-sm" />
              <div>
                <strong>{{ selectedMember.real_name }}</strong>
                <span class="user-type">{{ getUserTypeText(selectedMember.user_type) }}</span>
              </div>
            </div>
            <button @click="selectedMember = null" class="remove-button">移除</button>
          </div>
          <div class="form-group">
            <label>角色</label>
            <select v-model="memberRole">
              <option value="member">成员</option>
              <option value="admin">管理员</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" @click="showAddMemberModal = false" class="cancel-button">取消</button>
          <button type="button" @click="addMember" class="submit-button" :disabled="!selectedMember || addingMember">
            {{ addingMember ? '添加中...' : '添加' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useEventStore } from '~/stores/eventStore'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const eventStore = useEventStore()

// Events from the unified store (reactive)
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
  leader_id: null,
  need_invoice_review: true
})

const leaderSearch = ref('')
const filteredUsers = ref([])
const showLeaderDropdown = ref(false)

// 添加人员相关变量
const showAddMemberModal = ref(false)
const currentEvent = ref(null)
const memberSearch = ref('')
const filteredMembers = ref([])
const showMemberDropdown = ref(false)
const selectedMember = ref(null)
const memberRole = ref('member')
const addingMember = ref(false)

onMounted(async () => {
  console.log('=== 项目管理：页面加载 ===')
  const token = localStorage.getItem('token')

  if (!token) {
    navigateTo('/login')
    return
  }

  await eventStore.ensureLoaded()
  syncFromStore()
})

// Keep local events in sync with store (reactive binding)
const syncFromStore = () => {
  events.value = [...eventStore.events]
}

// Watch store data version to sync when data changes
watch(() => eventStore.dataVersion, () => {
  syncFromStore()
})

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
    leader_id: event.leader_id,
    need_invoice_review: event.need_invoice_review !== undefined ? event.need_invoice_review : true
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
      showEditModal.value = false
      const eventId = editingEventId.value
      if (eventId) {
        await eventStore.invalidateAndRefresh({ eventId })
      }
      syncFromStore()
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
    const response = await $api.get(`/auth/users?search=${leaderSearch.value}&user_type=admin,teacher`, {
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

const goToInvoiceManage = (event) => {
  navigateTo(`/purchases/${event.event_id}`)
}

const toggleEventStatus = async (event) => {
  if (!confirm(`确定要将比赛 "${event.event_name}" 结束吗？`)) return

  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/events/${event.event_id}`, { status: 'finished' }, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      alert('比赛已结束')
      await eventStore.invalidateAndRefresh({ eventId: event.event_id })
      syncFromStore()
    }
  } catch (error) {
    alert('操作失败，请稍后重试')
  }
}

const viewMembers = (event) => {
  navigateTo(`/events/${event.event_id}/members`)
}

const openAddMemberModal = (event) => {
  currentEvent.value = event
  memberSearch.value = ''
  filteredMembers.value = []
  selectedMember.value = null
  memberRole.value = 'member'
  showAddMemberModal.value = true
}

const searchUsersForMember = async () => {
  if (!memberSearch.value) {
    filteredMembers.value = []
    return
  }
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/auth/users?search=${memberSearch.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      filteredMembers.value = response.data.data
    }
  } catch (error) {
    console.error('搜索用户失败:', error)
  }
}

const selectMember = (user) => {
  selectedMember.value = user
  memberSearch.value = user.real_name
  showMemberDropdown.value = false
}

const addMember = async () => {
  if (!selectedMember.value || !currentEvent.value) return

  addingMember.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post(`/events/${currentEvent.value.event_id}/members`, {
      user_id: selectedMember.value.user_id,
      role_in_event: memberRole.value
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      alert('添加成员成功')
      showAddMemberModal.value = false
      await eventStore.invalidateAndRefresh({ eventId: currentEvent.value.event_id })
      syncFromStore()
    }
  } catch (error) {
    console.error('添加成员失败:', error)
    alert('添加成员失败，请稍后重试')
  } finally {
    addingMember.value = false
  }
}

const getUserTypeText = (type) => {
  const map = { admin: '管理员', teacher: '老师', student_admin: '学生管理员', student: '学生' }
  return map[type] || type
}

const formatMoney = (value) => {
  if (!value && value !== 0) return '0.00'
  return Number(value).toFixed(2)
}

const getRemainingBudget = (event) => {
  if (!event) return 0
  return Number(event.total_budget || 0) - Number(event.reimbursed_amount || 0)
}

const getRemainingPercent = (event) => {
  const total = Number(event.total_budget || 0)
  if (total === 0) return 100
  return Math.max(0, Math.min(100, (getRemainingBudget(event) / total) * 100))
}

const getBudgetUsagePercent = (event) => {
  const budget = Number(event.total_budget || 0)
  const spent = Number(event.spent_amount || 0)
  if (budget <= 0) return 0
  return Math.min(100, (spent / budget) * 100)
}

const deleteEvent = async () => {
  if (!deletingEvent.value) return

  deleting.value = true
  console.log('=== 项目管理：删除项目 ===')

  try {
    const token = localStorage.getItem('token')
    const response = await $api.delete(`/events/${deletingEvent.value.event_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      console.log('删除成功')
      showDeleteModal.value = false
      deletingEvent.value = null
      await eventStore.invalidateAndRefresh({ eventId: deletingEvent.value?.event_id })
      syncFromStore()
      alert('项目删除成功')
    } else {
      alert(response.data.message || '删除失败，请稍后重试')
    }
  } catch (error) {
    console.error('=== 项目管理：删除项目异常 ===')
    const message = error.response?.data?.message || '删除失败，请稍后重试'
    alert(message)
  } finally {
    deleting.value = false
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

.info-value.spent {
  color: #e74c3c;
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

/* 操作按钮样式 */
.action-btn {
  padding: 0.4rem 0.8rem;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: white;
}

.invoice-btn { background: #3498db; }
.invoice-btn:hover { background: #2980b9; }

.end-btn { background: #e67e22; }
.end-btn:hover { background: #d35400; }

.member-btn { background: #9b59b6; }
.member-btn:hover { background: #8e44ad; }

.view-btn { background: #1abc9c; }
.view-btn:hover { background: #16a085; }

/* 预算概览面板 */
.budget-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 1.2rem;
  padding: 14px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 10px;
  border: 1px solid #dee2e6;
}

.budget-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.b-label {
  font-size: 11px;
  color: #7f8c8d;
  margin-bottom: 4px;
}

.b-value {
  font-size: 16px;
  font-weight: 700;
  color: #2c3e50;
}

.budget-item.total .b-value { color: #3498db; }
.budget-item.spent .b-value { color: #e74c3c; }
.budget-item.invoice .b-value { color: #f39c12; }
.budget-item.reimbursed .b-value { color: #27ae60; }
.budget-item.remaining .b-value { color: #9b59b6; }
.budget-item.remaining.low .b-value { color: #e74c3c; }
.budget-item.count .b-value { color: #1abc9c; }

.mini-progress {
  width: 100%;
  height: 3px;
  background: #ecf0f1;
  border-radius: 2px;
  margin-top: 5px;
  overflow: hidden;
}

.mini-fill {
  height: 100%;
  background: linear-gradient(90deg, #9b59b6, #8e44ad);
  border-radius: 2px;
  transition: width 0.4s ease;
}

.mini-fill.spent-fill {
  background: linear-gradient(90deg, #e74c3c, #f39c12);
}

/* 添加成员相关样式 */
.selected-member {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  margin: 1rem 0;
  border: 1px solid #e9ecef;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
}

.user-type {
  font-size: 12px;
  color: #6c757d;
  margin-left: 8px;
}

.remove-button {
  padding: 6px 12px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.remove-button:hover {
  background: #c82333;
}

/* Checkbox group styles */
.checkbox-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.checkbox-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-group label {
  margin: 0;
  cursor: pointer;
  font-weight: normal;
}
</style>
