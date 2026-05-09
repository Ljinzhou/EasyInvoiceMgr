<template>
  <div class="users-page">
    <div class="page-header">
      <h1 class="page-title">人员管理</h1>
      <div class="header-actions">
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
            <th>学号/工号</th>
            <th>状态</th>
            <th>注册时间</th>
            <th v-if="canManageUsers">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsersList" :key="user.user_id" :class="{ 'inactive': user.account_status !== 'active' }">
            <td>
              <div class="avatar-cell">
                <img
                  v-if="user.avatar_url && !getAvatarError(user.user_id)"
                  :src="user.avatar_url"
                  class="avatar-sm"
                  loading="lazy"
                  @error="() => setAvatarError(user.user_id, true)"
                  alt=""
                />
                <div v-else class="avatar-default-sm">
                  <svg viewBox="0 0 40 40" width="36" height="36" xmlns="http://www.w3.org/2000/svg">
                    <rect width="40" height="40" rx="20" fill="#f0f0f0"/>
                    <g transform="translate(8, 6)">
                      <circle cx="12" cy="9" r="7" fill="#d0d0d0"/>
                      <ellipse cx="12" cy="26" rx="14" ry="9" fill="#d0d0d0"/>
                    </g>
                  </svg>
                </div>
              </div>
            </td>
            <td>{{ user.username }}</td>
            <td><strong>{{ user.real_name }}</strong></td>
            <td>{{ user.email || '-' }}</td>
            <td>
              <span class="role-badge" :class="user.user_type">
                {{ getUserTypeText(user.user_type) }}
              </span>
            </td>
            <td>{{ user.student_or_staff_id || '-' }}</td>
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

    <!-- 添加用户弹窗 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content add-modal">
        <div class="modal-header">
          <h2>添加人员功能{{ currentEventName ? ` - 比赛: ${currentEventName}` : '' }}</h2>
          <button @click="showAddModal = false" class="close-button">×</button>
        </div>
        <form @submit.prevent="addUser" class="modal-body">
          <div class="form-section-title">基本信息</div>
          <div class="form-row">
            <div class="form-group" :class="{ 'has-error': formErrors.username }">
              <label>用户名 *</label>
              <input 
                v-model="addForm.username" 
                type="text" 
                required 
                placeholder="请输入用户名（3-20位字母数字）"
                :class="{ 'error-input': formErrors.username }"
                @blur="validateUsername"
              />
              <span v-if="formErrors.username" class="field-error">{{ formErrors.username }}</span>
            </div>
            <div class="form-group" :class="{ 'has-error': formErrors.real_name }">
              <label>真实姓名 *</label>
              <input 
                v-model="addForm.real_name" 
                type="text" 
                required 
                placeholder="请输入真实姓名（2-10位中文或英文）"
                :class="{ 'error-input': formErrors.real_name }"
                @blur="validateRealName"
              />
              <span v-if="formErrors.real_name" class="field-error">{{ formErrors.real_name }}</span>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group" :class="{ 'has-error': formErrors.password }">
              <label>密码 *</label>
              <input 
                v-model="addForm.password" 
                type="password" 
                required 
                placeholder="请输入密码（至少6位）" 
                minlength="6"
                :class="{ 'error-input': formErrors.password }"
                @blur="validatePassword"
              />
              <span v-if="formErrors.password" class="field-error">{{ formErrors.password }}</span>
              <!-- 密码强度指示器 -->
              <div v-if="addForm.password" class="password-strength">
                <div class="strength-bar">
                  <div 
                    class="strength-fill" 
                    :style="{ width: passwordStrength + '%' }"
                    :class="passwordStrengthClass"
                  ></div>
                </div>
                <span class="strength-text">{{ passwordStrengthText }}</span>
              </div>
            </div>
            <div class="form-group" :class="{ 'has-error': formErrors.confirm_password }">
              <label>确认密码 *</label>
              <input 
                v-model="addForm.confirm_password" 
                type="password" 
                required 
                placeholder="请再次输入密码"
                :class="{ 'error-input': formErrors.confirm_password }"
                @blur="validateConfirmPassword"
              />
              <span v-if="formErrors.confirm_password" class="field-error">{{ formErrors.confirm_password }}</span>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group" :class="{ 'has-error': formErrors.email }">
              <label>邮箱</label>
              <input 
                v-model="addForm.email" 
                type="email" 
                placeholder="请输入邮箱地址（选填）"
                :class="{ 'error-input': formErrors.email }"
                @blur="validateEmail"
              />
              <span v-if="formErrors.email" class="field-error">{{ formErrors.email }}</span>
            </div>
            <div class="form-group" :class="{ 'has-error': formErrors.phone }">
              <label>手机号</label>
              <input 
                v-model="addForm.phone" 
                type="tel" 
                placeholder="请输入手机号码（选填）"
                :class="{ 'error-input': formErrors.phone }"
                @blur="validatePhone"
              />
              <span v-if="formErrors.phone" class="field-error">{{ formErrors.phone }}</span>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>学号/工号</label>
              <input v-model="addForm.student_or_staff_id" type="text" placeholder="请输入学号或工号（选填）" />
            </div>
            <div class="form-group" :class="{ 'has-error': formErrors.user_type }">
              <label>角色 *</label>
              <select 
                v-model="addForm.user_type" 
                required
                :class="{ 'error-input': formErrors.user_type }"
                @change="validateUserType"
              >
                <option value="">请选择角色</option>
                <option value="student">👨‍🎓 学生</option>
                <option value="student_admin">👨‍💼 学生管理员</option>
                <option value="teacher">👨‍🏫 老师</option>
                <option v-if="currentUser?.user_type === 'admin'" value="admin">🔐 管理员</option>
              </select>
              <span v-if="formErrors.user_type" class="field-error">{{ formErrors.user_type }}</span>
              <div v-if="addForm.user_type" class="role-hint">
                {{ getRoleDescription(addForm.user_type) }}
              </div>
            </div>
          </div>

          <div class="form-section-title">关联比赛（可选）</div>
          <div class="form-group">
            <label>选择比赛</label>
            <select v-model="addForm.event_id">
              <option value="">不关联比赛</option>
              <option v-for="evt in availableEvents" :key="evt.event_id" :value="evt.event_id">
                📋 {{ evt.event_name }}
              </option>
            </select>
            <p class="field-hint" v-if="addForm.event_id">关联后该用户将自动获得此比赛的访问权限</p>
          </div>

          <div v-if="addError" class="error-message">
            ⚠️ {{ addError }}
          </div>

          <!-- 成功提示 -->
          <div v-if="addSuccess" class="success-message">
            ✅ {{ addSuccess }}
          </div>

          <div class="modal-footer">
            <button type="button" @click="closeAddModal" class="cancel-button">取消</button>
            <button 
              type="submit" 
              class="submit-button" 
              :disabled="adding || !isFormValid"
              :title="!isFormValid ? '请填写所有必填项' : ''"
            >
              {{ adding ? '⏳ 添加中...' : '✓ 确认添加用户' }}
            </button>
          </div>
        </form>
      </div>
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
              <label>学号/工号</label>
              <input v-model="editForm.student_or_staff_id" type="text" />
            </div>
          </div>
          <div class="form-row">
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
import { useUserStore } from '~/stores/userStore'

const userStore = useUserStore()

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

const users = ref([])
const searchQuery = ref('')
const filterType = ref('')
const showAddModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const updating = ref(false)
const deleting = ref(false)
const adding = ref(false)
const addError = ref('')
const addSuccess = ref('')
const formErrors = ref({
  username: '',
  real_name: '',
  password: '',
  confirm_password: '',
  email: '',
  phone: '',
  user_type: ''
})
const editingUserId = ref(null)
const deletingUser = ref(null)
const availableEvents = ref([])
const currentEventName = ref('')
const avatarErrors = ref(new Set())

const editForm = ref({
  real_name: '',
  email: '',
  phone: '',
  student_or_staff_id: '',
  user_type: 'student'
})

const addForm = ref({
  username: '',
  real_name: '',
  password: '',
  confirm_password: '',
  email: '',
  phone: '',
  student_or_staff_id: '',
  user_type: '',
  event_id: ''
})

const currentUser = ref(null)

const canManageUsers = computed(() => {
  const userType = currentUser.value?.user_type
  return ['admin', 'teacher', 'student_admin'].includes(userType)
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
  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  
  await loadUsers()
  await loadEvents()
  
  const urlParams = new URLSearchParams(window.location.search)
  const eventId = urlParams.get('event_id')
  if (eventId) {
    addForm.value.event_id = eventId
    currentEventName.value = await getEventName(eventId)
  }
})

const loadUsers = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get('/auth/users', {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      users.value = response.data.data.data || response.data.data || []
    }
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

const closeAddModal = () => {
  showAddModal.value = false
  resetAddForm()
}

const loadEvents = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get('/events', {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      availableEvents.value = response.data.data.data || []
    }
  } catch (error) {
    console.error('加载比赛列表失败:', error)
  }
}

const getEventName = async (eventId) => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/events/${eventId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      return response.data.data.event_name
    }
  } catch (error) {
    console.error('获取比赛名称失败:', error)
  }
  return ''
}

const addUser = async () => {
  addError.value = ''
  addSuccess.value = ''
  
  // 执行所有验证
  const validations = [
    validateUsername(),
    validateRealName(),
    validatePassword(),
    validateConfirmPassword(),
    validateEmail(),
    validatePhone(),
    validateUserType()
  ]
  
  // 检查是否有验证失败
  if (validations.some(v => !v)) {
    addError.value = '请修正表单中的错误后再提交'
    return
  }
  
  adding.value = true
  
  try {
    const token = localStorage.getItem('token')
    const payload = {
      username: addForm.value.username.trim(),
      real_name: addForm.value.real_name.trim(),
      password: addForm.value.password,
      email: addForm.value.email?.trim() || null,
      phone: addForm.value.phone?.trim() || null,
      student_or_staff_id: addForm.value.student_or_staff_id?.trim() || null,
      user_type: addForm.value.user_type
    }
    
    console.log('提交用户数据:', { ...payload, password: '***' })
    
    const response = await $api.post('/auth/register', payload, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    console.log('注册响应:', response.data)
    
    if (response.data.code === 200 || response.data.code === 201) {
      // 显示成功消息
      const newUser = response.data.data
      addSuccess.value = `✅ 用户 "${newUser.real_name}"（@${newUser.username}）添加成功！`
      
      // 延迟关闭弹窗，让用户看到成功提示
      setTimeout(() => {
        closeAddModal()
        loadUsers()
        
        // 显示全局成功提示
        alert(`🎉 用户添加成功！\n\n用户名：${newUser.username}\n真实姓名：${newUser.real_name}\n角色：${getUserTypeText(newUser.user_type)}\n\n该用户现在可以使用系统了。`)
      }, 1500)
      
    } else if (response.data.code === 1001) {
      formErrors.value.username = '用户名已存在，请使用其他用户名'
      addError.value = '用户名已被占用，请更换后重试'
    } else if (response.data.code === 1002) {
      formErrors.value.email = '邮箱已被注册'
      addError.value = '邮箱已被其他账号使用，请检查后重试'
    } else {
      addError.value = response.data.message || '添加失败，请稍后重试'
    }
  } catch (error) {
    console.error('添加用户失败:', error)
    if (error.response?.status === 401) {
      addError.value = '登录已过期，请重新登录后操作'
    } else if (error.response?.status === 403) {
      addError.value = '权限不足，只有管理员可以添加用户'
    } else if (error.response?.data?.message) {
      addError.value = `服务器返回错误：${error.response.data.message}`
    } else {
      addError.value = '网络错误或服务器异常，请稍后重试'
    }
  } finally {
    adding.value = false
  }
}

const resetAddForm = () => {
  addForm.value = {
    username: '',
    real_name: '',
    password: '',
    confirm_password: '',
    email: '',
    phone: '',
    student_or_staff_id: '',
    user_type: '',
    event_id: ''
  }
  addError.value = ''
  addSuccess.value = ''
  formErrors.value = {
    username: '',
    real_name: '',
    password: '',
    confirm_password: '',
    email: '',
    phone: '',
    user_type: ''
  }
}

// 表单验证计算属性
const isFormValid = computed(() => {
  return (
    addForm.value.username &&
    addForm.value.real_name &&
    addForm.value.password &&
    addForm.value.confirm_password &&
    addForm.value.user_type &&
    !Object.values(formErrors.value).some(error => error !== '')
  )
})

// 密码强度计算
const passwordStrength = computed(() => {
  const password = addForm.value.password || ''
  let strength = 0
  
  if (password.length >= 6) strength += 25
  if (password.length >= 10) strength += 15
  if (/[a-z]/.test(password)) strength += 15
  if (/[A-Z]/.test(password)) strength += 15
  if (/[0-9]/.test(password)) strength += 15
  if (/[^a-zA-Z0-9]/.test(password)) strength += 15
  
  return Math.min(strength, 100)
})

const passwordStrengthClass = computed(() => {
  if (passwordStrength.value < 40) return 'weak'
  if (passwordStrength.value < 70) return 'medium'
  return 'strong'
})

const passwordStrengthText = computed(() => {
  if (passwordStrength.value < 40) return '⚠️ 弱 - 建议使用更复杂的密码'
  if (passwordStrength.value < 70) return '👍 中等强度'
  return '✅ 强 - 密码安全性良好'
})

// 验证函数
const validateUsername = () => {
  const username = addForm.value.username
  if (!username) {
    formErrors.value.username = '用户名不能为空'
    return false
  }
  if (username.length < 3 || username.length > 20) {
    formErrors.value.username = '用户名长度应在3-20位之间'
    return false
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    formErrors.value.username = '用户名只能包含字母、数字和下划线'
    return false
  }
  formErrors.value.username = ''
  return true
}

const validateRealName = () => {
  const name = addForm.value.real_name
  if (!name) {
    formErrors.value.real_name = '真实姓名不能为空'
    return false
  }
  if (name.length < 2 || name.length > 10) {
    formErrors.value.real_name = '姓名长度应在2-10位之间'
    return false
  }
  formErrors.value.real_name = ''
  return true
}

const validatePassword = () => {
  const password = addForm.value.password
  if (!password) {
    formErrors.value.password = '密码不能为空'
    return false
  }
  if (password.length < 6) {
    formErrors.value.password = '密码长度至少6位'
    return false
  }
  formErrors.value.password = ''
  
  // 同时验证确认密码
  if (addForm.value.confirm_password && password !== addForm.value.confirm_password) {
    formErrors.value.confirm_password = '两次输入的密码不一致'
  } else {
    formErrors.value.confirm_password = ''
  }
  
  return true
}

const validateConfirmPassword = () => {
  const confirmPassword = addForm.value.confirm_password
  if (!confirmPassword) {
    formErrors.value.confirm_password = '请再次输入密码'
    return false
  }
  if (confirmPassword !== addForm.value.password) {
    formErrors.value.confirm_password = '两次输入的密码不一致'
    return false
  }
  formErrors.value.confirm_password = ''
  return true
}

const validateEmail = () => {
  const email = addForm.value.email
  if (!email) {
    formErrors.value.email = ''
    return true // 邮箱是选填的
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email)) {
    formErrors.value.email = '邮箱格式不正确'
    return false
  }
  formErrors.value.email = ''
  return true
}

const validatePhone = () => {
  const phone = addForm.value.phone
  if (!phone) {
    formErrors.value.phone = ''
    return true // 手机号是选填的
  }
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!phoneRegex.test(phone)) {
    formErrors.value.phone = '手机号格式不正确（11位数字）'
    return false
  }
  formErrors.value.phone = ''
  return true
}

const validateUserType = () => {
  if (!addForm.value.user_type) {
    formErrors.value.user_type = '请选择用户角色'
    return false
  }
  formErrors.value.user_type = ''
  return true
}

const getRoleDescription = (type) => {
  const descriptions = {
    student: '📚 仅可查看比赛信息和自己的记录',
    student_admin: '🛠️ 可查看+部分管理功能（审核、统计）',
    teacher: '🎓 完全管理权限（创建、编辑、删除）',
    admin: '🔐 系统管理员权限（最高权限，谨慎使用）'
  }
  return descriptions[type] || ''
}

const getUserTypeText = (type) => {
  const map = { admin: '管理员', teacher: '老师', student_admin: '学生管理员', student: '学生' }
  return map[type] || type
}

function getAvatarError(userId) {
  return avatarErrors.value.has(userId)
}

function setAvatarError(userId, hasError) {
  if (hasError) {
    avatarErrors.value = new Set([...avatarErrors.value, userId])
  } else {
    const next = new Set(avatarErrors.value)
    next.delete(userId)
    avatarErrors.value = next
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const editUser = (user) => {
  editingUserId.value = user.user_id
  editForm.value = {
    real_name: user.real_name,
    email: user.email || '',
    phone: user.phone || '',
    student_or_staff_id: user.student_or_staff_id || '',
    user_type: user.user_type
  }
  showEditModal.value = true
}

const updateUser = async () => {
  updating.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/auth/users/${editingUserId.value}`, editForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      showEditModal.value = false
      await loadUsers()
      // 如果编辑的是当前登录用户，同步更新 store 使 UI 立即刷新
      if (editingUserId.value === userStore.userId) {
        userStore.saveToStorage(editForm.value)
      }
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
    const response = await $api.put(`/auth/users/${user.user_id}`, { account_status: newStatus }, {
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
    const response = await $api.delete(`/auth/users/${deletingUser.value.user_id}`, {
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

.avatar-cell {
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #ecf0f1;
}

.avatar-default-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid #ecf0f1;
  display: flex;
  align-items: center;
  justify-content: center;
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

.add-modal { max-width: 700px; }

.form-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #667eea;
}

/* 表单错误状态 */
.has-error {
  position: relative;
}
.has-error .error-input {
  border-color: #e74c3c;
  background-color: #fff5f5;
}
.has-error .error-input:focus {
  outline: none;
  border-color: #e74c3c;
  box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
}

.field-error {
  display: block;
  font-size: 11px;
  color: #e74c3c;
  margin-top: 4px;
  font-weight: 500;
}

/* 密码强度指示器 */
.password-strength {
  margin-top: 8px;
}
.strength-bar {
  width: 100%;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 4px;
}
.strength-fill {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 3px;
}
.strength-fill.weak {
  background: linear-gradient(90deg, #e74c3c 0%, #f39c12 100%);
}
.strength-fill.medium {
  background: linear-gradient(90deg, #f39c12 0%, #f1c40f 100%);
}
.strength-fill.strong {
  background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
}
.strength-text {
  font-size: 11px;
  color: #666;
}

/* 角色提示 */
.role-hint {
  margin-top: 6px;
  padding: 8px 12px;
  background: #f0f7ff;
  border-left: 3px solid #3498db;
  border-radius: 4px;
  font-size: 11px;
  color: #2980b9;
  line-height: 1.5;
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

.error-message {
  background: #fff5f5;
  color: #e74c3c;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 13px;
  border-left: 4px solid #e74c3c;
}

.success-message {
  background: #f0fff0;
  color: #27ae60;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 13px;
  border-left: 4px solid #27ae60;
}

.field-hint {
  font-size: 11px;
  color: #7f8c8d;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .form-row { grid-template-columns: 1fr; }
  .stats-panel { grid-template-columns: repeat(2, 1fr); }
  .filter-bar { flex-direction: column; }
  .search-input, .type-filter { min-height: 44px; }
  .action-button { min-height: 44px; }
  .page-header { flex-direction: column; align-items: flex-start; }
  .header-actions { width: 100%; }
  .header-actions .action-button { width: 100%; justify-content: center; }
  .modal-content { width: 95%; max-height: 85vh; }
  .add-modal { max-width: none; }
  .modal-footer { flex-direction: column; }
  .cancel-button, .submit-button { width: 100%; min-height: 44px; }
}

@media (max-width: 480px) {
  .page-title { font-size: 1.5rem; }
  .stats-panel { grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat-card { padding: 12px; }
  .stat-value { font-size: 20px; }
  .users-table th, .users-table td { padding: 10px 12px; font-size: 12px; }
  .users-table-container { border-radius: 8px; }
  .avatar-sm, .avatar-default-sm { width: 30px; height: 30px; }
  .btn-edit-sm, .btn-delete-sm, .btn-enable-sm, .btn-disable-sm {
    min-width: 32px; min-height: 32px; padding: 4px 8px;
  }
  .row-actions { gap: 6px; }
  .modal-body { padding: 1rem; }
  .modal-header { padding: 1rem; }
  .form-group input, .form-group select { min-height: 44px; }
}
</style>