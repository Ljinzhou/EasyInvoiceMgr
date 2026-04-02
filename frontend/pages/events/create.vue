<template>
  <div class="create-event-container">
    <div class="create-event-card">
      <h1 class="create-event-title">{{ isEditMode ? '编辑比赛' : '创建比赛' }}</h1>
      <form @submit.prevent="handleSubmit" class="create-event-form">
        <div class="form-group">
          <label for="event_name">比赛名称 *</label>
          <input
            id="event_name"
            v-model="form.event_name"
            type="text"
            required
            placeholder="请输入比赛名称"
          />
        </div>

        <div class="form-group">
          <label for="description">比赛描述</label>
          <textarea
            id="description"
            v-model="form.description"
            rows="4"
            placeholder="请输入比赛描述"
          ></textarea>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="category">比赛类别</label>
            <input
              id="category"
              v-model="form.category"
              type="text"
              placeholder="请输入比赛类别"
            />
          </div>
          <div class="form-group">
            <label for="location">比赛地点</label>
            <input
              id="location"
              v-model="form.location"
              type="text"
              placeholder="请输入比赛地点"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="event_start_time">开始时间 *</label>
            <input
              id="event_start_time"
              v-model="form.event_start_time"
              type="datetime-local"
              required
            />
          </div>
          <div class="form-group">
            <label for="event_end_time">结束时间 *</label>
            <input
              id="event_end_time"
              v-model="form.event_end_time"
              type="datetime-local"
              required
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="upload_start_time">上传开始时间</label>
            <input
              id="upload_start_time"
              v-model="form.upload_start_time"
              type="datetime-local"
            />
          </div>
          <div class="form-group">
            <label for="upload_end_time">上传结束时间</label>
            <input
              id="upload_end_time"
              v-model="form.upload_end_time"
              type="datetime-local"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="total_budget">总预算 (元)</label>
            <input
              id="total_budget"
              v-model.number="form.total_budget"
              type="number"
              step="0.01"
              min="0"
              placeholder="请输入总预算"
            />
          </div>
          <div class="form-group">
            <label>负责人</label>
            <div class="autocomplete-wrapper">
              <input
                v-model="leaderSearch"
                type="text"
                placeholder="输入姓名搜索负责人"
                @input="searchUsers"
                @focus="showDropdown = true"
                @blur="hideDropdown"
              />
              <div v-if="showDropdown && filteredUsers.length > 0" class="dropdown">
                <div
                  v-for="user in filteredUsers"
                  :key="user.user_id"
                  class="dropdown-item"
                  @mousedown="selectLeader(user)"
                >
                  <div class="user-name">{{ user.real_name }}</div>
                  <div class="user-info">{{ user.organization || '' }} {{ getUserTypeText(user.user_type) }}</div>
                </div>
              </div>
              <div v-if="showDropdown && leaderSearch && filteredUsers.length === 0" class="dropdown empty">
                <div class="dropdown-item">未找到匹配的用户</div>
              </div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="switch-label">
            <span>是否需要审核发票</span>
            <label class="switch">
              <input type="checkbox" v-model="form.need_invoice_review" />
              <span class="slider round"></span>
            </label>
          </label>
          <p class="switch-hint">
            {{ form.need_invoice_review ? '开启后，上传的发票需要管理员审核通过后才生效' : '关闭后，上传的发票将自动通过审核' }}
          </p>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="success" class="success-message">{{ success }}</div>

        <div class="button-group">
          <button type="button" @click="resetForm" class="reset-button">
            重置
          </button>
          <button type="submit" :disabled="loading" class="submit-button">
            {{ loading ? '创建中...' : '创建比赛' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const route = useRoute()

const isEditMode = computed(() => !!route.params.id)
const eventId = computed(() => route.params.id)

const form = ref({
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

const loading = ref(false)
const error = ref('')
const success = ref('')

const leaderSearch = ref('')
const filteredUsers = ref([])
const showDropdown = ref(false)
let searchTimeout = null

onMounted(async () => {
  console.log('=== 创建/编辑比赛：页面加载 ===')
  const token = localStorage.getItem('token')
  console.log('检查token:', token ? '已登录' : '未登录')
  
  if (!token) {
    console.log('用户未登录，跳转到登录页面')
    navigateTo('/login')
    return
  }
  console.log('用户已登录，可以操作比赛')
  
  // 如果是编辑模式，加载现有数据
  if (isEditMode.value && eventId.value) {
    await loadEventData()
  }
  
  const userStr = localStorage.getItem('user')
  if (userStr) {
    const user = JSON.parse(userStr)
    console.log('当前登录用户:', user)
    if (user.user_type === 'admin' || user.user_type === 'teacher') {
      form.value.leader_id = user.user_id
      leaderSearch.value = user.real_name
      console.log('默认负责人已设置:', user.real_name)
    }
  }
})

const searchUsers = async () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  
  if (!leaderSearch.value) {
    filteredUsers.value = []
    return
  }
  
  searchTimeout = setTimeout(async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await $api.get(`/users?search=${leaderSearch.value}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.data.code === 200) {
        filteredUsers.value = response.data.data.filter(u => 
          u.user_type === 'admin' || u.user_type === 'teacher'
        )
      }
    } catch (err) {
      console.error('搜索用户失败:', err)
    }
  }, 300)
}

const selectLeader = (user) => {
  form.value.leader_id = user.user_id
  leaderSearch.value = user.real_name
  showDropdown.value = false
}

const hideDropdown = () => {
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

const getUserTypeText = (type) => {
  const types = {
    admin: '管理员',
    teacher: '教师',
    student_admin: '学生管理员',
    student: '学生'
  }
  return types[type] || ''
}

const validateForm = () => {
  if (!form.value.event_name) {
    error.value = '比赛名称不能为空'
    return false
  }
  
  if (!form.value.event_start_time || !form.value.event_end_time) {
    error.value = '开始时间和结束时间不能为空'
    return false
  }
  
  const startTime = new Date(form.value.event_start_time)
  const endTime = new Date(form.value.event_end_time)
  
  if (startTime >= endTime) {
    error.value = '开始时间必须早于结束时间'
    return false
  }
  
  if (form.value.total_budget < 0) {
    error.value = '预算不能为负数'
    return false
  }
  
  return true
}

const loadEventData = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/events/${eventId.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      const event = response.data.data
      form.value = {
        event_name: event.event_name || '',
        description: event.description || '',
        category: event.category || '',
        location: event.location || '',
        event_start_time: event.event_start_time ? event.event_start_time.split('T')[0] : '',
        event_end_time: event.event_end_time ? event.event_end_time.split('T')[0] : '',
        upload_start_time: event.upload_start_time ? event.upload_start_time.split('T')[0] : '',
        upload_end_time: event.upload_end_time ? event.upload_end_time.split('T')[0] : '',
        total_budget: parseFloat(event.total_budget) || 0,
        leader_id: event.leader_id || null,
        need_invoice_review: event.need_invoice_review !== false // 默认为true
      }
      
      console.log('比赛数据加载成功:', form.value)
    } else {
      error.value = '加载比赛数据失败'
    }
  } catch (err) {
    console.error('加载比赛数据异常:', err)
    error.value = err.response?.data?.message || '加载失败，请稍后重试'
  }
}

const handleSubmit = async () => {
  error.value = ''
  success.value = ''
  
  if (!validateForm()) {
    return
  }
  
  loading.value = true
  
  try {
    const token = localStorage.getItem('token')
    
    let response
    if (isEditMode.value) {
      // 编辑模式：PUT请求
      response = await $api.put(`/events/${eventId.value}`, form.value, {
        headers: { Authorization: `Bearer ${token}` }
      })
    } else {
      // 创建模式：POST请求
      response = await $api.post('/events', form.value, {
        headers: { Authorization: `Bearer ${token}` }
      })
    }
    
    if (response.data.code === 200) {
      success.value = isEditMode.value ? '比赛更新成功！' : '比赛创建成功！'
      if (!isEditMode.value) {
        resetForm()
      }
    } else {
      error.value = response.data.message
    }
  } catch (err) {
    if (err.response?.status === 401) {
      error.value = '登录已过期，请重新登录'
      setTimeout(() => {
        navigateTo('/login')
      }, 2000)
    } else {
      error.value = err.response?.data?.message || '创建失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = {
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
  }
  leaderSearch.value = ''
  error.value = ''
  success.value = ''
}
</script>

<style scoped>
.create-event-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 100vh;
  background: #f5f5f5;
  padding: 2rem 1rem;
}

.create-event-card {
  background: white;
  padding: 2rem;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 800px;
}

.create-event-title {
  text-align: center;
  color: #333;
  margin-bottom: 2rem;
  font-size: 1.8rem;
}

.create-event-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #555;
  font-size: 0.9rem;
}

.form-group input,
.form-group textarea {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
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
  max-height: 250px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  margin-top: 4px;
}

.dropdown-item {
  padding: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #f0f0f0;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background: #f8f9fa;
}

.dropdown.empty .dropdown-item {
  color: #999;
  cursor: default;
}

.dropdown.empty .dropdown-item:hover {
  background: white;
}

.user-name {
  font-weight: 500;
  color: #2c3e50;
}

.user-info {
  font-size: 0.85rem;
  color: #7f8c8d;
  margin-top: 0.25rem;
}

.error-message {
  color: #e74c3c;
  font-size: 0.9rem;
  text-align: center;
  padding: 0.5rem;
  background: #ffeaea;
  border-radius: 5px;
}

.success-message {
  color: #27ae60;
  font-size: 0.9rem;
  text-align: center;
  padding: 0.5rem;
  background: #e8f8f0;
  border-radius: 5px;
}

.button-group {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.reset-button,
.submit-button {
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 5px;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.3s;
}

.reset-button {
  background: #95a5a6;
  color: white;
}

.submit-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.reset-button:hover,
.submit-button:hover:not(:disabled) {
  opacity: 0.9;
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.switch-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
  color: #555;
}

.switch {
  position: relative;
  display: inline-block;
  width: 60px;
  height: 34px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 34px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 26px;
  width: 26px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #667eea;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

.switch-hint {
  font-size: 0.85rem;
  color: #7f8c8d;
  margin-top: 0.25rem;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .create-event-card {
    padding: 1.5rem;
  }
  
  .button-group {
    flex-direction: column;
  }
  
  .reset-button,
  .submit-button {
    width: 100%;
  }
}
</style>
