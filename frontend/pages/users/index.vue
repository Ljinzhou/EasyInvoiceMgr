<template>
  <div class="users-page">
    <div class="page-header">
      <h1 class="page-title">人员管理</h1>
      <div class="header-actions">
        <button 
          v-if="canManageUsers" 
          @click="showInviteModal = true" 
          class="action-button invite"
        >
          🎫 生成邀请码
        </button>
        <button 
          v-if="canManageUsers" 
          @click="showAddModal = true" 
          class="action-button primary"
        >
          ➕ 添加用户
        </button>
      </div>
    </div>

    <!-- 统计面板 -->
    <div class="stats-panel">
      <div class="stat-card">
        <span class="stat-value">{{ users.length }}</span>
        <span class="stat-label">总人数</span>
      </div>
      <div class="stat-card admin">
        <span class="stat-value">{{ adminCount }}</span>
        <span class="stat-label">管理员</span>
      </div>
      <div class="stat-card teacher">
        <span class="stat-value">{{ teacherCount }}</span>
        <span class="stat-label">老师</span>
      </div>
      <div class="stat-card student-admin">
        <span class="stat-value">{{ studentAdminCount }}</span>
        <span class="stat-label">学生管理员</span>
      </div>
      <div class="stat-card student">
        <span class="stat-value">{{ studentCount }}</span>
        <span class="stat-label">学生</span>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-bar">
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="搜索用户名、姓名、邮箱..." 
        class="search-input"
        @input="filterUsers"
      />
      <select v-model="filterType" @change="filterUsers" class="type-filter">
        <option value="">全部类型</option>
        <option value="admin">管理员</option>
        <option value="teacher">老师</option>
        <option value="student_admin">学生管理员</option>
        <option value="student">学生</option>
      </select>
    </div>

    <!-- 用户列表 -->
    <div class="users-table-container">
      <table class="users-table">
        <thead>
          <tr>
            <th>头像</th>
            <th>用户名</th>
            <th>真实姓名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>组织/学号</th>
            <th>状态</th>
            <th>注册时间</th>
            <th v-if="canManageUsers">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsersList" :key="user.user_id" :class="{ 'inactive': user.account_status !== 'active' }">
            <td>
              <img :src="user.avatar_url || '/default-avatar.png'" class="avatar-sm" />
            </td>
            <td>{{ user.username }}</td>
            <td><strong>{{ user.real_name }}</strong></td>
            <td>{{ user.email || '-' }}</td>
            <td>
              <span class="role-badge" :class="user.user_type">
                {{ getUserTypeText(user.user_type) }}
              </span>
            </td>
            <td>{{ user.organization || user.student_or_staff_id || '-' }}</td>
            <td>
              <span class="status-badge" :class="user.account_status">
                {{ user.account_status === 'active' ? '正常' : '禁用' }}
              </span>
            </td>
            <td>{{ formatDate(user.register_time) }}</td>
            <td v-if="canManageUsers">
              <div class="row-actions">
                <button @click="editUser(user)" class="btn-edit-sm" title="编辑">✏</button>
                <button 
                  v-if="user.account_status === 'active'" 
                  @click="toggleUserStatus(user)" 
                  class="btn-disable-sm"
                  title="禁用"
                >🔒</button>
                <button 
                  v-else 
                  @click="toggleUserStatus(user)" 
                  class="btn-enable-sm"
                  title="启用"
                >🔓</button>
                <button 
                  v-if="currentUser?.user_id !== user.user_id && user.user_type !== 'admin'" 
                  @click="confirmDeleteUser(user)" 
                  class="btn-delete-sm"
                  title="删除"
                >🗑</button>
              </div>
            </td>
          </tr>
          <tr v-if="filteredUsersList.length === 0">
            <td :colspan="canManageUsers ? 9 : 8" class="empty-row">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑用户弹窗 -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>编辑用户信息</h2>
          <button @click="showEditModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="updateUser" class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>真实姓名 *</label>
              <input v-model="editForm.real_name" type="text" required />
            </div>
            <div class="form-group">
              <label>邮箱</label>
              <input v-model="editForm.email" type="email" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>手机号</label>
              <input v-model="editForm.phone" type="tel" />
            </div>
            <div class="form-group">
              <label>组织</label>
              <input v-model="editForm.organization" type="text" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>学号/工号</label>
              <input v-model="editForm.student_or_staff_id" type="text" />
            </div>
            <div class="form-group" v-if="canChangeRole">
              <label>角色</label>
              <select v-model="editForm.user_type">
                <option value="admin">管理员</option>
                <option value="teacher">老师</option>
                <option value="student_admin">学生管理员</option>
                <option value="student">学生</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" @click="showEditModal = false" class="cancel-button">取消</button>
            <button type="submit" class="submit-button" :disabled="updating">{{ updating ? '保存中...' : '保存' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 邀请码生成弹窗 -->
    <div v-if="showInviteModal" class="modal-overlay" @click.self="showInviteModal = false">
      <div class="modal-content invite-modal">
        <div class="modal-header">
          <h2>🎫 生成邀请码</h2>
          <button @click="showInviteModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="generateInvitationCodes" class="modal-body">
          <div class="form-group">
            <label>目标用户类型 *</label>
            <select v-model="inviteForm.target_user_type" required>
              <option value="student">学生</option>
              <option value="student_admin">学生管理员</option>
              <option value="teacher">老师</option>
              <option value="admin">管理员（谨慎使用）</option>
            </select>
            <div class="field-hint">
              学生：仅可查看 | 学生管理员：可查看+部分管理 | 老师：完全管理权限
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>有效期 (天) *</label>
              <input v-model.number="inviteForm.expires_days" type="number" min="1" max="365" required />
            </div>
            <div class="form-group">
              <label>生成数量</label>
              <input v-model.number="inviteForm.quantity" type="number" min="1" max="20" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" @click="showInviteModal = false" class="cancel-button">取消</button>
            <button type="submit" class="submit-button invite-submit" :disabled="generating">
              {{ generating ? '生成中...' : '生成邀请码' }}
            </button>
          </div>
        </form>

        <!-- 生成的邀请码列表 -->
        <div v-if="generatedCodes.length > 0" class="generated-codes">
          <h3>已生成的邀请码</h3>
          <div v-for="code in generatedCodes" :key="code.code" class="code-item">
            <code class="code-text">{{ code.code }}</code>
            <span class="code-type">{{ getTypeText(code.target_user_type) }}</span>
            <span class="code-expiry">有效期至: {{ formatDateTime(code.expires_at) }}</span>
            <button @click="copyCode(code.code)" class="btn-copy">复制</button>
          </div>
        </div>
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
          <p>确定要删除用户 <strong>"{{ deletingUser?.real_name }}"</strong> 吗？</p>
          <p class="warning-text">此操作不可撤销！</p>
        </div>
        <div class="modal-footer">
          <button @click="showDeleteModal = false" class="cancel-button">取消</button>
          <button @click="deleteUser" class="delete-btn" :disabled="deleting">{{ deleting ? '删除中...' : '确认删除' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

definePageMeta({ layout: 'default' })

const { $api } = useNuxtApp()

const users = ref([])
const searchQuery = ref('')
const filterType = ref('')
const showEditModal = ref(false)
const showInviteModal = ref(false)
const showDeleteModal = ref(false)
const updating = ref(false)
const generating = ref(false)
const deleting = ref(false)
const editingUserId = ref(null)
const deletingUser = ref(null)
const generatedCodes = ref([])

const editForm = ref({
  real_name: '',
  email: '',
  phone: '',
  organization: '',
  student_or_staff_id: '',
  user_type: 'student'
})

const inviteForm = ref({
  target_user_type: 'student',
  expires_days: 30,
  quantity: 1
})

const currentUser = computed(() => {
  const userStr = localStorage.getItem('user')
  return userStr ? JSON.parse(userStr) : null
})

const canManageUsers = computed(() => {
  const userType = currentUser.value?.user_type
  return ['admin', 'teacher'].includes(userType)
})

const canChangeRole = computed(() => currentUser.value?.user_type === 'admin')

const adminCount = computed(() => users.value.filter(u => u.user_type === 'admin').length)
const teacherCount = computed(() => users.value.filter(u => u.user_type === 'teacher').length)
const studentAdminCount = computed(() => users.value.filter(u => u.user_type === 'student_admin').length)
const studentCount = computed(() => users.value.filter(u => u.user_type === 'student').length)

const filteredUsersList = computed(() => {
  let result = users.value
  
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(u =>
      (u.username && u.username.toLowerCase().includes(query)) ||
      (u.real_name && u.real_name.toLowerCase().includes(query)) ||
      (u.email && u.email.toLowerCase().includes(query))
    )
  }
  
  if (filterType.value) {
    result = result.filter(u => u.user_type === filterType.value)
  }
  
  return result
})

onMounted(async () => {
  await loadUsers()
})

const loadUsers = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get('/users', {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      users.value = response.data.data.data || response.data.data || []
    }
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

const filterUsers = () => {}

const getUserTypeText = (type) => {
  const map = { admin: '管理员', teacher: '老师', student_admin: '学生管理员', student: '学生' }
  return map[type] || type
}

const getTypeText = (type) => {
  return getUserTypeText(type)
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const editUser = (user) => {
  editingUserId.value = user.user_id
  editForm.value = {
    real_name: user.real_name,
    email: user.email || '',
    phone: user.phone || '',
    organization: user.organization || '',
    student_or_staff_id: user.student_or_staff_id || '',
    user_type: user.user_type
  }
  showEditModal.value = true
}

const updateUser = async () => {
  updating.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/users/${editingUserId.value}`, editForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      showEditModal.value = false
      await loadUsers()
      alert('更新成功')
    } else {
      alert(response.data.message || '更新失败')
    }
  } catch (error) {
    alert('更新失败，请稍后重试')
  } finally {
    updating.value = false
  }
}

const toggleUserStatus = async (user) => {
  const newStatus = user.account_status === 'active' ? 'inactive' : 'active'
  if (!confirm(`确定要${newStatus === 'active' ? '启用' : '禁用'}用户 "${user.real_name}" 吗？`)) return
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/users/${user.user_id}`, { account_status: newStatus }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      await loadUsers()
    }
  } catch (error) {
    alert('操作失败，请稍后重试')
  }
}

const confirmDeleteUser = (user) => {
  deletingUser.value = user
  showDeleteModal.value = true
}

const deleteUser = async () => {
  if (!deletingUser.value) return
  deleting.value = true
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.delete(`/users/${deletingUser.value.user_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      showDeleteModal.value = false
      deletingUser.value = null
      await loadUsers()
      alert('删除成功')
    }
  } catch (error) {
    alert('删除失败，请稍后重试')
  } finally {
    deleting.value = false
  }
}

const generateInvitationCodes = async () => {
  generating.value = true
  generatedCodes.value = []
  
  try {
    const token = localStorage.getItem('token')
    const response = await $api.post('/invitation-codes', inviteForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      generatedCodes.value = response.data.data.codes || []
      alert(`成功生成 ${response.data.data.count} 个邀请码`)
    } else {
      alert(response.data.message || '生成失败')
    }
  } catch (error) {
    alert('生成失败，请稍后重试')
  } finally {
    generating.value = false
  }
}

const copyCode = (code) => {
  navigator.clipboard.writeText(code).then(() => {
    alert('邀请码已复制到剪贴板！')
  }).catch(() => {
    prompt('复制以下邀请码:', code)
  })
}
</script>

<style scoped>
.users-page {
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

.header-actions {
  display: flex;
  gap: 0.6rem;
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

.action-button.invite {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
}
.action-button.invite:hover { transform: translateY(-1px); }

/* 统计面板 */
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
.stat-card.admin { border-left-color: #e74c3c; }
.stat-card.teacher { border-left-color: #3498db; }
.stat-card.student-admin { border-left-color: #9b59b6; }
.stat-card.student { border-left-color: #27ae60; }

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

/* 筛选栏 */
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

/* 表格 */
.users-table-container {
  background: white;
  border-radius: 10px;
  overflow-x: auto;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th {
  background: #f8f9fa;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  border-bottom: 2px solid #e9ecef;
  white-space: nowrap;
}

.users-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #333;
}

.users-table tr:hover { background: #fafbfc; }
.users-table tr.inactive { opacity: 0.6; }

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

.status-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}
.status-badge.active { background: #eaffea; color: #27ae60; }
.status-badge.inactive { background: #eee; color: #95a5a6; }

.row-actions {
  display: flex;
  gap: 4px;
}

.btn-edit-sm, .btn-delete-sm, .btn-enable-sm, .btn-disable-sm {
  padding: 3px 7px;
  font-size: 12px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-edit-sm { background: #f39c12; color: white; }
.btn-edit-sm:hover { background: #e67e22; }
.btn-delete-sm { background: #e74c3c; color: white; }
.btn-delete-sm:hover { background: #c0392b; }
.btn-enable-sm { background: #27ae60; color: white; }
.btn-disable-sm { background: #95a5a6; color: white; }

.empty-row {
  text-align: center;
  padding: 40px !important;
  color: #999;
}

/* 模态框 */
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

.invite-modal { max-width: 650px; }

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
.close-button:hover { color: #333; }

.modal-body { padding: 1.5rem; }

.form-group { margin-bottom: 1rem; }
.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 500;
  font-size: 13px;
  color: #555;
}
.form-group input, .form-group select, .form-group textarea {
  width: 100%;
  padding: 0.65rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
  box-sizing: border-box;
}
.form-group input:focus, .form-group select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
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
.cancel-button:hover { background: #e0e0e0; }

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
.submit-button:hover { opacity: 0.9; }
.submit-button:disabled { opacity: 0.6; cursor: not-allowed; }

.invite-submit {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%) !important;
}

.delete-btn {
  padding: 0.6rem 1.2rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}
.delete-btn:hover:not(:disabled) { background: #c0392b; }
.delete-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.delete-modal { max-width: 420px; }
.warning-text { color: #e74c3c; font-size: 13px; margin-top: 0.5rem; }

/* 生成的邀请码 */
.generated-codes {
  margin-top: 1.5rem;
  padding: 1.2rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}
.generated-codes h3 {
  margin: 0 0 1rem;
  font-size: 14px;
  color: #555;
}

.code-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: white;
  border-radius: 5px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.code-text {
  font-family: monospace;
  font-size: 13px;
  background: #fff3cd;
  padding: 4px 8px;
  border-radius: 3px;
  word-break: break-all;
}

.code-type {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #e8f4fd;
  color: #2980b9;
}

.code-expiry {
  font-size: 11px;
  color: #999;
}

.btn-copy {
  padding: 3px 10px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
}
.btn-copy:hover { background: #5a6fd6; }

@media (max-width: 768px) {
  .form-row { grid-template-columns: 1fr; }
  .stats-panel { grid-template-columns: repeat(2, 1fr); }
  .filter-bar { flex-direction: column; }
}
</style>