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
    <transition name="modal-fade">
      <div v-if="showAddMemberModal" class="member-modal-mask" @click.self="showAddMemberModal = false">
        <div class="member-modal">
          <div class="member-modal__header">
            <div class="member-modal__title-row">
              <div class="member-modal__icon-box">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
              </div>
              <div>
                <h2>添加成员</h2>
                <p class="member-modal__subtitle">{{ currentEvent?.event_name }}</p>
              </div>
            </div>
            <button @click="showAddMemberModal = false" class="member-modal__close">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="member-modal__body">
            <!-- Search -->
            <div class="member-search" :class="{ 'has-results': showMemberDropdown && filteredMembers.length > 0 }">
              <div class="member-search__input-wrap">
                <svg class="member-search__icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input
                  v-model="memberSearch"
                  type="text"
                  placeholder="搜索用户姓名或用户名..."
                  class="member-search__input"
                  @input="searchUsersForMember"
                  @focus="showMemberDropdown = true"
                />
                <button v-if="memberSearch" @click="memberSearch = ''; filteredMembers = []" class="member-search__clear">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
              <transition name="drop-enter">
                <div v-if="showMemberDropdown && filteredMembers.length > 0" class="member-search__dropdown">
                  <div
                    v-for="user in filteredMembers"
                    :key="user.user_id"
                    class="member-search__item"
                    :class="{ 'is-selected': selectedMember?.user_id === user.user_id }"
                    @click="selectMember(user)"
                  >
                    <div class="member-search__avatar">
                      <img v-if="user.avatar_url" :src="user.avatar_url" alt="" />
                      <span v-else>{{ (user.real_name || user.username || '?').charAt(0) }}</span>
                    </div>
                    <div class="member-search__info">
                      <span class="member-search__name">{{ user.real_name }}</span>
                      <span class="member-search__meta">@{{ user.username }} · {{ getUserTypeText(user.user_type) }}</span>
                    </div>
                    <div v-if="selectedMember?.user_id === user.user_id" class="member-search__check">
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                    </div>
                  </div>
                </div>
              </transition>
            </div>

            <!-- Selected member card -->
            <transition name="card-rise">
              <div v-if="selectedMember" class="member-card">
                <div class="member-card__avatar">
                  <img v-if="selectedMember.avatar_url" :src="selectedMember.avatar_url" alt="" />
                  <span v-else class="member-card__initial">{{ (selectedMember.real_name || '?').charAt(0) }}</span>
                </div>
                <div class="member-card__body">
                  <div class="member-card__name">{{ selectedMember.real_name }}</div>
                  <div class="member-card__details">
                    <span>@{{ selectedMember.username }}</span>
                    <span class="member-card__dot">·</span>
                    <span class="member-card__role">{{ getUserTypeText(selectedMember.user_type) }}</span>
                  </div>
                </div>
                <button @click="selectedMember = null" class="member-card__remove" title="取消选择">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            </transition>
          </div>

          <div class="member-modal__footer">
            <button type="button" @click="showAddMemberModal = false" class="member-modal__btn member-modal__btn--cancel">取消</button>
            <button
              type="button"
              @click="addMember"
              class="member-modal__btn member-modal__btn--confirm"
              :disabled="!selectedMember || addingMember"
            >
              <svg v-if="addingMember" class="spin-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
              {{ addingMember ? '添加中...' : '确认添加' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
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
      role_in_event: 'member'
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
  return Number(event.total_budget || 0) - Number(event.spent_amount || 0)
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

  .project-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .project-title-section {
    flex-wrap: wrap;
  }

  .action-buttons {
    flex-wrap: wrap;
    width: 100%;
  }

  .action-btn {
    flex: 1;
    min-width: calc(50% - 0.5rem);
    min-height: 40px;
    justify-content: center;
    font-size: 13px;
    padding: 0.5rem 0.6rem;
  }

  .edit-button, .delete-button {
    min-height: 40px;
    padding: 0.5rem 1rem;
  }

  .budget-overview {
    grid-template-columns: repeat(2, 1fr);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .create-button {
    width: 100%;
    min-height: 48px;
    text-align: center;
    justify-content: center;
  }

  .modal-content {
    width: 95%;
    max-height: 85vh;
  }

  .member-modal {
    width: 95%;
    max-height: 85vh;
  }
}

@media (max-width: 480px) {
  .page-title { font-size: 1.5rem; }
  .project-title { font-size: 1.1rem; }
  .project-status { font-size: 0.75rem; padding: 0.2rem 0.6rem; }
  .info-grid { grid-template-columns: 1fr; }
  .budget-overview { grid-template-columns: 1fr 1fr; gap: 8px; padding: 10px; }
  .budget-item { padding: 8px 6px; }
  .b-value { font-size: 14px; }
  .action-btn { min-width: 100%; }
  .modal-body { padding: 1rem; }
  .modal-header { padding: 1rem; }
  .modal-footer { flex-direction: column; }
  .cancel-button, .submit-button { width: 100%; min-height: 44px; }
  .member-modal__body { padding: 1rem; }
  .member-modal__footer { flex-direction: column; }
  .member-modal__btn { width: 100%; justify-content: center; min-height: 44px; }
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

/* ===== MEMBER MODAL ===== */
.member-modal-mask {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.member-modal {
  background: #fff;
  border-radius: 18px;
  width: 90%; max-width: 480px;
  box-shadow: 0 25px 60px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05);
  overflow: hidden;
  transform-origin: center;
}

/* Header */
.member-modal__header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 1.5rem 1.5rem 0;
}
.member-modal__title-row { display: flex; align-items: center; gap: 12px; }
.member-modal__icon-box {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, #eef2ff, #f5f3ff);
  color: #6366f1;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.member-modal__header h2 { margin: 0; font-size: 1.15rem; font-weight: 700; color: #0f172a; letter-spacing: -0.01em; }
.member-modal__subtitle { margin: 3px 0 0; font-size: 0.8rem; color: #94a3b8; }
.member-modal__close {
  width: 34px; height: 34px; border-radius: 10px;
  border: none; background: #f8fafc; color: #94a3b8;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.2s;
  flex-shrink: 0; margin-top: 2px;
}
.member-modal__close:hover { background: #fee2e2; color: #ef4444; }

/* Body */
.member-modal__body { padding: 1.25rem 1.5rem; }

/* Search */
.member-search { position: relative; }
.member-search__input-wrap {
  display: flex; align-items: center; gap: 10px;
  padding: 0 14px; height: 48px;
  background: #f8fafc; border: 2px solid #e8ecf1;
  border-radius: 14px;
  transition: all 0.25s;
}
.member-search:focus-within .member-search__input-wrap,
.member-search.has-results .member-search__input-wrap {
  border-color: #6366f1; background: #fff;
  box-shadow: 0 0 0 4px rgba(99,102,241,0.08);
}
.member-search__icon { color: #94a3b8; flex-shrink: 0; }
.member-search__input {
  flex: 1; border: none; background: transparent;
  font-size: 0.93rem; color: #0f172a; outline: none;
}
.member-search__input::placeholder { color: #b0b8c1; }
.member-search__clear {
  width: 24px; height: 24px; border-radius: 50%;
  border: none; background: #e2e8f0; color: #64748b;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s;
}
.member-search__clear:hover { background: #cbd5e1; color: #334155; }

/* Dropdown */
.member-search__dropdown {
  position: absolute; top: calc(100% + 6px); left: 0; right: 0;
  background: #fff;
  border: 1px solid #e8ecf1; border-radius: 14px;
  max-height: 220px; overflow-y: auto;
  box-shadow: 0 12px 32px rgba(0,0,0,0.1);
  z-index: 20;
}
.member-search__item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px;
  cursor: pointer; transition: background 0.15s;
  border-bottom: 1px solid #f8fafc;
}
.member-search__item:last-child { border-bottom: none; }
.member-search__item:hover { background: #f8fafc; }
.member-search__item.is-selected { background: #eef2ff; }
.member-search__avatar {
  width: 38px; height: 38px; border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 15px;
  overflow: hidden; flex-shrink: 0;
}
.member-search__avatar img { width: 100%; height: 100%; object-fit: cover; }
.member-search__info { flex: 1; min-width: 0; }
.member-search__name { display: block; font-size: 0.9rem; font-weight: 600; color: #0f172a; }
.member-search__meta { display: block; font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
.member-search__check {
  width: 28px; height: 28px; border-radius: 50%;
  background: #6366f1; color: #fff;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

/* Selected member card */
.member-card {
  display: flex; align-items: center; gap: 14px;
  margin-top: 16px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1.5px solid #e2e8f0; border-radius: 16px;
}
.member-card__avatar {
  width: 50px; height: 50px; border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 20px;
  overflow: hidden; flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(99,102,241,0.3);
}
.member-card__avatar img { width: 100%; height: 100%; object-fit: cover; }
.member-card__body { flex: 1; min-width: 0; }
.member-card__name { font-size: 1rem; font-weight: 700; color: #0f172a; }
.member-card__details { display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: #64748b; margin-top: 4px; }
.member-card__dot { color: #cbd5e1; }
.member-card__role { font-weight: 500; color: #6366f1; }
.member-card__remove {
  width: 34px; height: 34px; border-radius: 10px;
  border: 1.5px solid #e2e8f0; background: #fff;
  color: #94a3b8; display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.2s; flex-shrink: 0;
}
.member-card__remove:hover { background: #fef2f2; border-color: #fecaca; color: #ef4444; }

/* Footer */
.member-modal__footer {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 1rem 1.5rem 1.5rem;
}
.member-modal__btn {
  padding: 10px 22px;
  border-radius: 12px; border: none;
  font-size: 0.88rem; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
  display: flex; align-items: center; gap: 7px;
}
.member-modal__btn--cancel {
  background: #f1f5f9; color: #475569;
}
.member-modal__btn--cancel:hover { background: #e2e8f0; }
.member-modal__btn--confirm {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(99,102,241,0.35);
}
.member-modal__btn--confirm:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99,102,241,0.45);
}
.member-modal__btn--confirm:disabled {
  opacity: 0.5; cursor: not-allowed; box-shadow: none;
}
.spin-icon { animation: spin-icon 1s linear infinite; }
@keyframes spin-icon { to { transform: rotate(360deg); } }

/* Transitions */
.modal-fade-enter-active, .modal-fade-leave-active { transition: all 0.3s cubic-bezier(0.4,0,0.2,1); }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-from .member-modal { transform: scale(0.92) translateY(12px); }
.modal-fade-leave-to .member-modal { transform: scale(0.95); }

.drop-enter-enter-active, .drop-enter-leave-active { transition: all 0.2s cubic-bezier(0.4,0,0.2,1); }
.drop-enter-enter-from, .drop-enter-leave-to { opacity: 0; transform: translateY(-6px); }

.card-rise-enter-active { transition: all 0.35s cubic-bezier(0.34,1.56,0.64,1); }
.card-rise-leave-active { transition: all 0.2s ease-in; }
.card-rise-enter-from { opacity: 0; transform: translateY(12px) scale(0.95); }
.card-rise-leave-to { opacity: 0; transform: scale(0.96); }

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
