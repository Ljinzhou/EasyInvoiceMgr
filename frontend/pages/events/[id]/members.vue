<template>
  <div class="members-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">← 返回</button>
      <h1 class="page-title">人员管理 - {{ event?.event_name || '加载中...' }}</h1>
      <div class="header-actions">
        <button @click="openAddMemberModal" class="action-button primary">+ 添加成员</button>
      </div>
    </div>

    <!-- 统计面板 -->
    <div v-if="stats" class="stats-panel">
      <div class="stat-card total">
        <span class="stat-label">总人数</span>
        <span class="stat-value">{{ stats.total }}</span>
      </div>
      <div class="stat-card admin">
        <span class="stat-label">管理员/老师</span>
        <span class="stat-value">{{ stats.admins }}</span>
      </div>
      <div class="stat-card student-admin">
        <span class="stat-label">学生管理员</span>
        <span class="stat-value">{{ stats.studentAdmins }}</span>
      </div>
      <div class="stat-card student">
        <span class="stat-label">学生</span>
        <span class="stat-value">{{ stats.students }}</span>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索用户名、姓名..."
        class="search-input"
      />
      <select v-model="filterType" class="type-filter">
        <option value="">全部角色</option>
        <option value="admin">管理员</option>
        <option value="teacher">老师</option>
        <option value="student_admin">学生管理员</option>
        <option value="student">学生</option>
      </select>
    </div>

    <!-- 成员列表 -->
    <div class="members-table-container">
      <table class="members-table">
        <thead>
          <tr>
            <th>头像</th>
            <th>用户名</th>
            <th>真实姓名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>学号/工号</th>
            <th>加入时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in filteredMembers" :key="member.user_id">
            <td>
              <img :src="getUploadUrl(member.avatar_url) || '/default-avatar.png'" class="avatar-sm" />
            </td>
            <td>{{ member.username }}</td>
            <td><strong>{{ member.real_name }}</strong></td>
            <td>{{ member.email || '-' }}</td>
            <td>
              <span class="role-badge" :class="member.user_type">
                {{ getUserTypeText(member.user_type) }}
              </span>
            </td>
            <td>{{ member.student_or_staff_id || '-' }}</td>
            <td>{{ formatDate(member.created_at) }}</td>
            <td>
              <div class="row-actions">
                <button @click="editMember(member)" class="btn-edit-sm" title="编辑角色">✏️ 编辑</button>
                <button @click="confirmRemoveMember(member)" class="btn-remove-sm" title="移除成员">🗑 移除</button>
              </div>
            </td>
          </tr>
          <tr v-if="filteredMembers.length === 0">
            <td :colspan="8" class="empty-row">暂无成员数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加成员弹窗 -->
    <transition name="modal-fade">
      <div v-if="showAddModal" class="member-modal-mask" @mousedown.self="showAddModal = false">
        <div class="member-modal">
          <div class="member-modal__header">
            <div class="member-modal__title-row">
              <div class="member-modal__icon-box">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
              </div>
              <div>
                <h2>添加成员</h2>
                <p class="member-modal__subtitle">{{ event?.event_name }}</p>
              </div>
            </div>
            <button @click="showAddModal = false" class="member-modal__close">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="member-modal__body">
            <!-- Search -->
            <div class="member-search" :class="{ 'has-results': showMemberDropdown && filteredUsers.length > 0 }">
              <div class="member-search__input-wrap">
                <svg class="member-search__icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input
                  v-model="memberSearch"
                  type="text"
                  placeholder="搜索用户姓名或用户名..."
                  class="member-search__input"
                  @focus="showMemberDropdown = true"
                />
                <button v-if="memberSearch" @click="memberSearch = ''; filteredUsers = []" class="member-search__clear">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
              <transition name="drop-enter">
                <div v-if="showMemberDropdown && filteredUsers.length > 0" class="member-search__dropdown">
                  <div
                    v-for="user in filteredUsers"
                    :key="user.user_id"
                    class="member-search__item"
                    :class="{ 'is-selected': selectedMember?.user_id === user.user_id }"
                    @click="selectMemberToAdd(user)"
                  >
                    <div class="member-search__avatar">
                      <img v-if="user.avatar_url" :src="getUploadUrl(user.avatar_url)" alt="" />
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
                  <img v-if="selectedMember.avatar_url" :src="getUploadUrl(selectedMember.avatar_url)" alt="" />
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
            <button type="button" @click="showAddModal = false" class="member-modal__btn member-modal__btn--cancel">取消</button>
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

    <!-- 编辑成员角色弹窗 -->
    <transition name="modal-fade">
      <div v-if="showEditModal" class="member-modal-mask" @mousedown.self="showEditModal = false">
        <div class="member-modal">
          <div class="member-modal__header">
            <div class="member-modal__title-row">
              <div class="member-modal__icon-box edit-icon">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </div>
              <div>
                <h2>编辑成员角色</h2>
                <p class="member-modal__subtitle">{{ editingMember?.real_name }} (@{{ editingMember?.username }})</p>
              </div>
            </div>
            <button @click="showEditModal = false" class="member-modal__close">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="member-modal__body">
            <div class="form-group">
              <label>当前角色</label>
              <div class="current-role-display">
                <span class="role-badge" :class="editingMember?.user_type">{{ getUserTypeText(editingMember?.user_type) }}</span>
              </div>
            </div>
            <div class="form-group">
              <label>新角色</label>
              <select v-model="editRole" class="form-select">
                <option value="student">👨‍🎓 学生</option>
                <option value="student_admin">👨‍💼 学生管理员</option>
                <option value="teacher">👨‍🏫 老师</option>
              </select>
            </div>
          </div>

          <div class="member-modal__footer">
            <button type="button" @click="showEditModal = false" class="member-modal__btn member-modal__btn--cancel">取消</button>
            <button
              type="button"
              @click="updateMemberRole"
              class="member-modal__btn member-modal__btn--confirm"
              :disabled="updatingMember"
            >
              <svg v-if="updatingMember" class="spin-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              {{ updatingMember ? '保存中...' : '保存修改' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 移除确认弹窗 -->
    <transition name="modal-fade">
      <div v-if="showRemoveModal" class="member-modal-mask" @mousedown.self="showRemoveModal = false">
        <div class="member-modal remove-modal">
          <div class="member-modal__header">
            <div class="member-modal__title-row">
              <div class="member-modal__icon-box remove-icon">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <div>
                <h2>确认移除成员</h2>
                <p class="member-modal__subtitle">此操作不可撤销</p>
              </div>
            </div>
            <button @click="showRemoveModal = false" class="member-modal__close">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="member-modal__body">
            <p class="remove-warning">确定要将 <strong>{{ removingMember?.real_name }}</strong> 从该比赛中移除吗？</p>
          </div>

          <div class="member-modal__footer">
            <button type="button" @click="showRemoveModal = false" class="member-modal__btn member-modal__btn--cancel">取消</button>
            <button
              type="button"
              @click="removeMember"
              class="member-modal__btn member-modal__btn--danger"
              :disabled="removingMemberLoading"
            >
              {{ removingMemberLoading ? '移除中...' : '确认移除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

definePageMeta({ layout: 'default' })

const { $api } = useNuxtApp()
const { getUploadUrl } = useUploadUrl()
const route = useRoute()
const router = useRouter()

const eventId = computed(() => route.params.id)
const event = ref(null)
const members = ref([])
const searchQuery = ref('')
const filterType = ref('')
const stats = ref(null)

// Add member modal
const showAddModal = ref(false)
const memberSearch = ref('')
const filteredUsers = ref([])
const showMemberDropdown = ref(false)
const selectedMember = ref(null)
const addingMember = ref(false)
let searchTimer = null

// Edit member modal
const showEditModal = ref(false)
const editingMember = ref(null)
const editRole = ref('student')
const updatingMember = ref(false)

// Remove member modal
const showRemoveModal = ref(false)
const removingMember = ref(null)
const removingMemberLoading = ref(false)

// Current user
const currentUser = ref(null)

const canManageMembers = computed(() => {
  return ['admin', 'teacher', 'student_admin'].includes(currentUser.value?.user_type)
})

onMounted(async () => {
  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  await loadEvent()
  await loadMembers()
})

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/projects')
  }
}

const loadEvent = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/events/${eventId.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      event.value = response.data.data
    }
  } catch (e) {
    console.error('加载比赛信息失败:', e.message)
  }
}

const loadMembers = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/events/${eventId.value}/members`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      const membersList = response.data.data.members || []

      members.value = membersList

      stats.value = {
        total: membersList.length,
        admins: membersList.filter(u => u.user_type === 'admin' || u.user_type === 'teacher').length,
        studentAdmins: membersList.filter(u => u.user_type === 'student_admin').length,
        students: membersList.filter(u => u.user_type === 'student').length
      }
    }
  } catch (e) {
    console.error('加载成员列表失败:', e.message)
  }
}

const filteredMembers = computed(() => {
  let result = members.value

  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(u =>
      (u.username && u.username.toLowerCase().includes(query)) ||
      (u.real_name && u.real_name.toLowerCase().includes(query))
    )
  }

  if (filterType.value) {
    result = result.filter(u => u.user_type === filterType.value)
  }

  return result
})

// ===== Add Member =====
const openAddMemberModal = () => {
  memberSearch.value = ''
  filteredUsers.value = []
  selectedMember.value = null
  showAddModal.value = true
}

// Watch memberSearch to trigger user search
watch(memberSearch, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!val || !val.trim()) {
    filteredUsers.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await $api.get('/auth/users', {
        params: { search: val.trim() },
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.data.code === 200) {
        const users = response.data.data.data || response.data.data || []
        // Filter out already existing members
        const existingIds = new Set(members.value.map(m => m.user_id))
        filteredUsers.value = (Array.isArray(users) ? users : []).filter(u => !existingIds.has(u.user_id)).slice(0, 10)
      }
    } catch (e) {
      filteredUsers.value = []
    }
  }, 300)
})

const selectMemberToAdd = (user) => {
  selectedMember.value = user
  memberSearch.value = user.real_name
  showMemberDropdown.value = false
}

const addMember = async () => {
  if (!selectedMember.value) return

  addingMember.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post(`/events/${eventId.value}/members`, {
      user_id: selectedMember.value.user_id,
      role_in_event: 'student'
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      showAddModal.value = false
      await loadMembers()
    } else {
      alert(response.data.message || '添加失败')
    }
  } catch (error) {
    console.error('添加成员失败:', error.message)
    alert('添加成员失败，请稍后重试')
  } finally {
    addingMember.value = false
  }
}

// ===== Edit Member =====
const editMember = (member) => {
  editingMember.value = member
  editRole.value = member.user_type === 'admin' ? 'teacher' : member.user_type
  showEditModal.value = true
}

const updateMemberRole = async () => {
  if (!editingMember.value) return
  updatingMember.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/events/${eventId.value}/members/${editingMember.value.user_id}`, {
      role_in_event: editRole.value
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      showEditModal.value = false
      await loadMembers()
    } else {
      alert(response.data.message || '更新失败')
    }
  } catch (error) {
    console.error('更新成员角色失败:', error.message)
    alert('更新失败，请稍后重试')
  } finally {
    updatingMember.value = false
  }
}

// ===== Remove Member =====
const confirmRemoveMember = (member) => {
  removingMember.value = member
  showRemoveModal.value = true
}

const removeMember = async () => {
  if (!removingMember.value) return
  removingMemberLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.delete(`/events/${eventId.value}/members/${removingMember.value.user_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      showRemoveModal.value = false
      await loadMembers()
    } else {
      alert(response.data.message || '移除失败')
    }
  } catch (error) {
    console.error('移除成员失败:', error.message)
    alert('移除失败，请稍后重试')
  } finally {
    removingMemberLoading.value = false
  }
}

const getUserTypeText = (type) => {
  const map = { admin: '管理员', teacher: '老师', student_admin: '学生管理员', student: '学生' }
  return map[type] || type
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.members-page {
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
.stat-card.admin { border-left-color: #e74c3c; }
.stat-card.student-admin { border-left-color: #9b59b6; }
.stat-card.student { border-left-color: #27ae60; }

.stat-label { display: block; font-size: 12px; color: #7f8c8d; margin-bottom: 4px; }
.stat-value { display: block; font-size: 24px; font-weight: 700; color: #2c3e50; }

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 1.2rem;
}

.search-input {
  flex: 1;
  padding: 0.7rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}
.search-input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.15); }

.type-filter {
  padding: 0.7rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.members-table-container {
  background: white;
  border-radius: 10px;
  overflow-x: auto;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.members-table {
  width: 100%;
  border-collapse: collapse;
}

.members-table th {
  background: #f8f9fa;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  border-bottom: 2px solid #e9ecef;
  white-space: nowrap;
}

.members-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #333;
}

.members-table tr:hover { background: #fafbfc; }

.avatar-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #ecf0f1;
}

.role-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}
.role-badge.admin { background: #fee; color: #c0392b; }
.role-badge.teacher { background: #eef7ff; color: #2980b9; }
.role-badge.student-admin { background: #f4ecff; color: #8e44ad; }
.role-badge.student { background: #eaffea; color: #27ae60; }

.empty-row {
  text-align: center;
  padding: 40px !important;
  color: #999;
}

/* Row actions */
.row-actions {
  display: flex;
  gap: 6px;
}

.btn-edit-sm {
  padding: 4px 10px;
  background: #f39c12;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}
.btn-edit-sm:hover { background: #e67e22; }

.btn-remove-sm {
  padding: 4px 10px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}
.btn-remove-sm:hover { background: #c0392b; }

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
  width: 90%; max-width: 520px;
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
.member-modal__icon-box.edit-icon {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #d97706;
}
.member-modal__icon-box.remove-icon {
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  color: #dc2626;
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
.member-modal__btn--danger {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  color: #fff;
  box-shadow: 0 4px 14px rgba(220,38,38,0.35);
}
.member-modal__btn--danger:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(220,38,38,0.45);
}
.member-modal__btn--danger:disabled {
  opacity: 0.5; cursor: not-allowed; box-shadow: none;
}
.spin-icon { animation: spin-icon 1s linear infinite; }
@keyframes spin-icon { to { transform: rotate(360deg); } }

/* Edit modal form */
.form-group { margin-bottom: 1rem; }
.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 500;
  font-size: 13px;
  color: #555;
}
.current-role-display { padding: 8px 0; }
.form-select {
  width: 100%;
  padding: 0.7rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.93rem;
  color: #0f172a;
  background: #fff;
  outline: none;
  transition: border-color 0.25s;
}
.form-select:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }

/* Remove warning */
.remove-warning {
  font-size: 0.93rem;
  color: #475569;
  line-height: 1.6;
}

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

@media (max-width: 768px) {
  .page-header { flex-direction: column; align-items: flex-start; }
  .stats-panel { grid-template-columns: repeat(2, 1fr); }
  .filter-bar { flex-direction: column; }
  .search-input, .type-filter { min-height: 44px; }
  .action-button { min-height: 44px; width: 100%; justify-content: center; }
  .back-button { min-height: 44px; width: 100%; }
}

@media (max-width: 480px) {
  .members-page { padding: 0 0.25rem; }
  .page-title { font-size: 1.3rem; }
  .stats-panel { grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat-card { padding: 12px; }
  .stat-value { font-size: 20px; }
  .members-table th,
  .members-table td { padding: 10px 12px; font-size: 12px; }
  .members-table-container { border-radius: 8px; }
  .avatar-sm { width: 30px; height: 30px; }
  .btn-edit-sm, .btn-remove-sm { min-width: 44px; min-height: 36px; }
}
</style>
