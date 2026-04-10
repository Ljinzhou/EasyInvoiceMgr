<template>
  <div class="members-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">← 返回</button>
      <h1 class="page-title">成员列表 - {{ event?.event_name || '加载中...' }}</h1>
      <div class="header-actions">
        <button @click="goToAddMember" class="action-button primary">+ 添加成员</button>
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
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in filteredMembers" :key="member.user_id">
            <td>
              <img :src="member.avatar_url || '/default-avatar.png'" class="avatar-sm" />
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
          </tr>
          <tr v-if="filteredMembers.length === 0">
            <td :colspan="7" class="empty-row">暂无成员数据</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

definePageMeta({ layout: 'default' })

const { $api } = useNuxtApp()
const route = useRoute()
const router = useRouter()

const eventId = computed(() => route.params.id)
const event = ref(null)
const members = ref([])
const searchQuery = ref('')
const filterType = ref('')
const stats = ref(null)

onMounted(async () => {
  await loadEvent()
  await loadMembers()
})

const goBack = () => {
  router.push(`/purchases/${eventId.value}`)
}

const goToAddMember = () => {
  router.push(`/users?event_id=${eventId.value}`)
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
    console.error('加载比赛信息失败:', e)
  }
}

const loadMembers = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get('/auth/users', {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      const allUsers = response.data.data.data || response.data.data || []
      
      // TODO: 这里应该根据实际的后端API获取比赛的成员列表
      // 目前先显示所有用户，后续可以根据event_members关联表筛选
      members.value = allUsers
      
      // 计算统计数据
      stats.value = {
        total: allUsers.length,
        admins: allUsers.filter(u => u.user_type === 'admin' || u.user_type === 'teacher').length,
        studentAdmins: allUsers.filter(u => u.user_type === 'student_admin').length,
        students: allUsers.filter(u => u.user_type === 'student').length
      }
    }
  } catch (e) {
    console.error('加载成员列表失败:', e)
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

@media (max-width: 768px) {
  .page-header { flex-direction: column; align-items: flex-start; }
  .stats-panel { grid-template-columns: repeat(2, 1fr); }
  .filter-bar { flex-direction: column; }
}
</style>
