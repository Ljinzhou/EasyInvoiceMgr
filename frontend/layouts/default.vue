<template>
  <div class="layout-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>财务管理系统</h2>
      </div>
      <nav class="sidebar-nav">
        <NuxtLink to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }">
          <span class="nav-icon">📊</span>
          <span class="nav-text">总览面板</span>
        </NuxtLink>
        <NuxtLink to="/purchases" class="nav-item" :class="{ active: $route.path.startsWith('/purchases') }">
          <span class="nav-icon">🛒</span>
          <span class="nav-text">购买记录</span>
        </NuxtLink>
        <NuxtLink to="/projects" class="nav-item" :class="{ active: $route.path.startsWith('/projects') }">
          <span class="nav-icon">📁</span>
          <span class="nav-text">项目管理</span>
        </NuxtLink>
        <NuxtLink v-if="canManageUsers" to="/users" class="nav-item" :class="{ active: $route.path.startsWith('/users') }">
          <span class="nav-icon">👥</span>
          <span class="nav-text">人员管理</span>
        </NuxtLink>
        <NuxtLink v-if="canManageInvitationCodes" to="/invitation-codes" class="nav-item" :class="{ active: $route.path.startsWith('/invitation-codes') }">
          <span class="nav-icon">🎫</span>
          <span class="nav-text">邀请码管理</span>
        </NuxtLink>
      </nav>
      <div class="sidebar-footer">
        <div class="user-info" @click="showSettingsModal = true">
          <div class="user-avatar">
            <template v-if="userAvatarUrl && !avatarLoadError">
              <img
                :src="userAvatarUrl"
                class="avatar-image"
                loading="lazy"
                @error="avatarLoadError = true"
                alt=""
              />
            </template>
            <span v-else class="avatar-initial">{{ userInitial }}</span>
          </div>
          <div class="user-details">
            <div class="user-name">{{ userName }}</div>
            <div class="user-role">{{ userRole }}</div>
          </div>
          <button class="settings-btn" title="设置">⚙️</button>
        </div>
        <button @click="handleLogout" class="logout-button">退出登录</button>
      </div>
    </aside>
    <main class="main-content">
      <slot />
    </main>

    <div v-if="showSettingsModal" class="modal-overlay" @click.self="showSettingsModal = false">
      <div class="settings-modal">
        <div class="modal-header">
          <h2>⚙️ 个人设置</h2>
          <button @click="showSettingsModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="settings-tabs">
            <button 
              :class="['tab-btn', { active: activeTab === 'profile' }]" 
              @click="activeTab = 'profile'"
            >基本信息</button>
            <button 
              :class="['tab-btn', { active: activeTab === 'permissions' }]" 
              @click="activeTab = 'permissions'"
            >权限说明</button>
          </div>

          <div v-if="activeTab === 'profile'" class="tab-content">
            <div class="profile-avatar-section">
              <AvatarUpload
                :current-avatar-url="userAvatarUrl"
                @avatar-updated="handleAvatarUpdated"
              />
            </div>
            <div class="section-divider"></div>
            <form @submit.prevent="saveSettings" class="settings-form">
              <div class="form-group">
                <label>用户名</label>
                <input v-model="settingsForm.username" type="text" disabled class="disabled-input" />
              </div>
              <div class="form-group">
                <label>真实姓名</label>
                <input v-model="settingsForm.real_name" type="text" required />
              </div>
              <div class="form-group">
                <label>邮箱</label>
                <input v-model="settingsForm.email" type="email" />
              </div>
              <div class="form-group">
                <label>手机号</label>
                <input v-model="settingsForm.phone" type="tel" />
              </div>
              <div class="form-group">
                <label>学号/工号</label>
                <input v-model="settingsForm.student_or_staff_id" type="text" />
              </div>
              <div class="form-group">
                <label>当前角色</label>
                <input :value="userRole" type="text" disabled class="disabled-input" />
              </div>
              <div class="form-actions">
                <button type="button" @click="showSettingsModal = false" class="cancel-btn">取消</button>
                <button type="submit" class="save-btn" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
              </div>
            </form>
          </div>

          <div v-if="activeTab === 'permissions'" class="tab-content">
            <div class="permissions-info">
              <h3>当前权限：{{ userRole }}</h3>
              <p class="permission-desc">{{ permissionDescription }}</p>
            </div>
            <div class="permissions-matrix">
              <h3>权限操作矩阵</h3>
              <table class="matrix-table">
                <thead>
                  <tr>
                    <th>功能模块</th>
                    <th>管理员</th>
                    <th>教师</th>
                    <th>学生管理员</th>
                    <th>学生</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>查看发票</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                  </tr>
                  <tr>
                    <td>上传发票</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                  </tr>
                  <tr>
                    <td>审核发票</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="denied">✗</td>
                  </tr>
                  <tr>
                    <td>创建/管理项目</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="denied">✗</td>
                    <td class="denied">✗</td>
                  </tr>
                  <tr>
                    <td>人员管理</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="denied">✗</td>
                  </tr>
                  <tr>
                    <td>邀请码管理</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="denied">✗</td>
                  </tr>
                  <tr>
                    <td>修改用户角色</td>
                    <td class="allowed">✓</td>
                    <td class="denied">✗</td>
                    <td class="denied">✗</td>
                    <td class="denied">✗</td>
                  </tr>
                  <tr>
                    <td>删除用户</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="allowed">✓</td>
                    <td class="denied">✗</td>
                  </tr>
                  <tr>
                    <td>系统设置</td>
                    <td class="allowed">✓</td>
                    <td class="denied">✗</td>
                    <td class="denied">✗</td>
                    <td class="denied">✗</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const { $api } = useNuxtApp()
const route = useRoute()

const user = ref(null)
const showSettingsModal = ref(false)
const activeTab = ref('profile')
const saving = ref(false)
const userAvatarUrl = ref('')
const avatarLoadError = ref(false)

const settingsForm = ref({
  username: '',
  real_name: '',
  email: '',
  phone: '',
  student_or_staff_id: ''
})

onMounted(() => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    user.value = JSON.parse(userStr)
    userAvatarUrl.value = user.value?.avatar_url || ''
    settingsForm.value = {
      username: user.value.username || '',
      real_name: user.value.real_name || '',
      email: user.value.email || '',
      phone: user.value.phone || '',
      student_or_staff_id: user.value.student_or_staff_id || ''
    }
  }
})

const userName = computed(() => user.value?.real_name || '未登录')
const userRole = computed(() => {
  const roles = {
    admin: '管理员',
    teacher: '教师',
    student_admin: '学生管理员',
    student: '学生'
  }
  return roles[user.value?.user_type] || '未知'
})
const userInitial = computed(() => userName.value.charAt(0).toUpperCase())

const canManageUsers = computed(() => {
  return ['admin', 'teacher', 'student_admin'].includes(user.value?.user_type)
})

const canManageInvitationCodes = computed(() => {
  return ['admin', 'teacher', 'student_admin'].includes(user.value?.user_type)
})

const permissionDescription = computed(() => {
  const descriptions = {
    admin: '拥有系统最高权限，可管理所有用户、项目和发票，可修改用户角色和系统设置。',
    teacher: '拥有完全管理权限，可审核发票、管理项目和人员，可管理邀请码。',
    student_admin: '可审核发票、管理人员和邀请码，协助老师进行数据管理工作。',
    student: '默认权限，仅可查看和上传发票。'
  }
  return descriptions[user.value?.user_type] || ''
})

function handleAvatarUpdated(newUrl) {
  userAvatarUrl.value = newUrl || ''
  avatarLoadError.value = false
  if (user.value) {
    user.value.avatar_url = newUrl || null
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/auth/users/${user.value.user_id}`, settingsForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    if (response.data.code === 200) {
      const updatedUser = { ...user.value, ...settingsForm.value }
      localStorage.setItem('user', JSON.stringify(updatedUser))
      user.value = updatedUser
      alert('设置保存成功')
    } else {
      alert(response.data.message || '保存失败')
    }
  } catch (error) {
    alert('保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  navigateTo('/login')
}
</script>

<style scoped>
.layout-container {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  width: 260px;
  background: linear-gradient(180deg, #2c3e50 0%, #1a252f 100%);
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
}

.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
}

.sidebar-nav {
  flex: 1;
  padding: 1rem 0;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.9rem 1.5rem;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: all 0.3s ease;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-item.active {
  background: rgba(102, 126, 234, 0.2);
  color: white;
  border-left-color: #667eea;
}

.nav-icon {
  font-size: 1.2rem;
  margin-right: 0.8rem;
}

.nav-text {
  font-size: 0.95rem;
}

.sidebar-footer {
  padding: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-info {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: background 0.3s ease;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 0.8rem;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-initial {
  font-weight: bold;
  color: white;
}

.user-details {
  flex: 1;
}

.user-name {
  font-weight: 500;
  font-size: 0.95rem;
}

.user-role {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.logout-button {
  width: 100%;
  padding: 0.7rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
}

.logout-button:hover {
  background: rgba(255, 255, 255, 0.2);
}

.main-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

.settings-btn {
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  padding: 0.3rem;
  opacity: 0.7;
  transition: opacity 0.3s;
}

.settings-btn:hover {
  opacity: 1;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.settings-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem 1.5rem;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.settings-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tab-btn {
  flex: 1;
  padding: 0.7rem 1rem;
  border: 1px solid #ddd;
  background: white;
  cursor: pointer;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: all 0.3s;
}

.tab-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: #555;
}

.form-group input {
  padding: 0.7rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.disabled-input {
  background: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 0.8rem;
  margin-top: 1rem;
}

.cancel-btn, .save-btn {
  flex: 1;
  padding: 0.7rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.3s;
}

.cancel-btn {
  background: #f0f0f0;
  color: #666;
}

.cancel-btn:hover {
  background: #e0e0e0;
}

.save-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.save-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.profile-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 0.5rem;
}

.section-divider {
  width: 100%;
  height: 1px;
  background: #eee;
  margin: 0.8rem 0 1.2rem;
}

.permissions-info {
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.permissions-info h3 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  color: #2c3e50;
}

.permission-desc {
  margin: 0;
  font-size: 0.85rem;
  color: #666;
  line-height: 1.5;
}

.permissions-matrix h3 {
  margin: 0 0 1rem;
  font-size: 1rem;
  color: #2c3e50;
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.matrix-table th,
.matrix-table td {
  padding: 0.7rem 0.5rem;
  text-align: center;
  border: 1px solid #e0e0e0;
}

.matrix-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.matrix-table th:first-child,
.matrix-table td:first-child {
  text-align: left;
  padding-left: 0.8rem;
}

.matrix-table .allowed {
  color: #27ae60;
  font-weight: bold;
}

.matrix-table .denied {
  color: #e74c3c;
}

.matrix-table tr:hover {
  background: #fafafa;
}

@media (max-width: 768px) {
  .layout-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    min-height: auto;
  }
  
  .sidebar-nav {
    display: flex;
    padding: 0.5rem;
    overflow-x: auto;
  }
  
  .nav-item {
    padding: 0.7rem 1rem;
    white-space: nowrap;
    border-left: none;
    border-bottom: 2px solid transparent;
  }
  
  .nav-item.active {
    border-left-color: transparent;
    border-bottom-color: #667eea;
  }
  
  .sidebar-footer {
    display: none;
  }
  
  .main-content {
    padding: 1rem;
  }
}
</style>
