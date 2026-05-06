<template>
  <div class="layout-container">
    <!-- 移动端顶部导航栏 -->
    <div class="mobile-topbar">
      <button class="hamburger-btn" @click="toggleMobileMenu" :class="{ active: mobileMenuOpen }">
        <span></span><span></span><span></span>
      </button>
      <h2 class="mobile-title">财务管理系统</h2>
      <button class="mobile-settings-btn" @click="showSettingsModal = true" title="设置">⚙️</button>
    </div>

    <!-- 移动端遮罩层 -->
    <div v-if="mobileMenuOpen" class="mobile-overlay" @click="mobileMenuOpen = false"></div>

    <aside class="sidebar" :class="{ 'mobile-open': mobileMenuOpen }">
      <div class="sidebar-header">
        <h2>财务管理系统</h2>
      </div>
      <nav class="sidebar-nav">
        <NuxtLink to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }" @click="mobileMenuOpen = false">
          <span class="nav-icon">📊</span>
          <span class="nav-text">总览面板</span>
        </NuxtLink>
        <NuxtLink to="/purchases" class="nav-item" :class="{ active: $route.path.startsWith('/purchases') }" @click="mobileMenuOpen = false">
          <span class="nav-icon">🛒</span>
          <span class="nav-text">购买记录</span>
        </NuxtLink>
        <NuxtLink to="/projects" class="nav-item" :class="{ active: $route.path.startsWith('/projects') }" @click="mobileMenuOpen = false">
          <span class="nav-icon">📁</span>
          <span class="nav-text">项目管理</span>
        </NuxtLink>
        <NuxtLink v-if="canManageUsers" to="/users" class="nav-item" :class="{ active: $route.path.startsWith('/users') }" @click="mobileMenuOpen = false">
          <span class="nav-icon">👥</span>
          <span class="nav-text">人员管理</span>
        </NuxtLink>
        <NuxtLink v-if="canManageInvitationCodes" to="/invitation-codes" class="nav-item" :class="{ active: $route.path.startsWith('/invitation-codes') }" @click="mobileMenuOpen = false">
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
              <transition name="toast-fade">
                <div v-if="settingsMsg" class="settings-msg" :class="settingsMsgType">{{ settingsMsg }}</div>
              </transition>
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

  <!-- 全局操作提示 -->
  <transition name="global-toast-fade">
    <div v-if="globalToast.visible" class="global-toast" :class="globalToast.type">
      <svg v-if="globalToast.type === 'success'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
      <span>{{ globalToast.message }}</span>
    </div>
  </transition>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

const { $api } = useNuxtApp()
const route = useRoute()

const user = ref(null)
const showSettingsModal = ref(false)
const activeTab = ref('profile')
const saving = ref(false)
const mobileMenuOpen = ref(false)

const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

// 路由变化时关闭移动端菜单
watch(() => route.path, () => {
  mobileMenuOpen.value = false
})
const userAvatarUrl = ref('')
	const avatarLoadError = ref(false)
	const settingsMsg = ref('')
	const settingsMsgType = ref('success')
	const globalToast = reactive({ visible: false, message: '', type: 'success' })
	let globalToastTimer = null

	function showGlobalToast(message, type = 'success') {
	  globalToast.visible = true
	  globalToast.message = message
	  globalToast.type = type
	  if (globalToastTimer) clearTimeout(globalToastTimer)
	  globalToastTimer = setTimeout(() => { globalToast.visible = false }, 2500)
	}

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
    localStorage.setItem('user', JSON.stringify(user.value))
  }
  // 上传头像成功后关闭设置页面并提示
  if (newUrl) {
    showSettingsModal.value = false
    showGlobalToast('头像保存成功')
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
      settingsMsg.value = '设置保存成功'
      settingsMsgType.value = 'success'
    } else {
      settingsMsg.value = response.data.message || '保存失败'
      settingsMsgType.value = 'error'
    }
  } catch (error) {
    settingsMsg.value = '保存失败，请稍后重试'
    settingsMsgType.value = 'error'
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
/* ===== 移动端顶部栏（桌面端隐藏） ===== */
.mobile-topbar {
  display: none;
}

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
  flex-shrink: 0;
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
  min-height: 44px;
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
  min-width: 0;
}

.user-name {
  font-weight: 500;
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  min-height: 44px;
}

.logout-button:hover {
  background: rgba(255, 255, 255, 0.2);
}

.main-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
  min-width: 0;
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
  padding: 1rem;
}

.settings-modal {
  background: white;
  border-radius: 12px;
  width: 100%;
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
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
  border-radius: 12px 12px 0 0;
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
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
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
  min-height: 44px;
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
  min-height: 44px;
  box-sizing: border-box;
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
  min-height: 44px;
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

.settings-msg {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  text-align: center;
}
.settings-msg.success {
  background: #d4edda; color: #155724;
}
.settings-msg.error {
  background: #f8d7da; color: #721c24;
}

.toast-fade-enter-active, .toast-fade-leave-active { transition: all .3s ease; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(6px); }

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

.permissions-matrix {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  min-width: 400px;
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

/* ===== 响应式：平板端 ===== */
@media (max-width: 1024px) {
  .main-content {
    padding: 1.5rem;
  }
}

/* ===== 响应式：移动端 ===== */
@media (max-width: 768px) {
  /* 显示移动端顶部栏 */
  .mobile-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1rem;
    height: 56px;
    background: linear-gradient(135deg, #2c3e50 0%, #1a252f 100%);
    color: white;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .mobile-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .mobile-settings-btn {
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    padding: 0.5rem;
    min-width: 44px;
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* 汉堡按钮 */
  .hamburger-btn {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 44px;
    height: 44px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    gap: 5px;
  }

  .hamburger-btn span {
    display: block;
    width: 22px;
    height: 2px;
    background: white;
    border-radius: 2px;
    transition: all 0.3s ease;
  }

  .hamburger-btn.active span:nth-child(1) {
    transform: rotate(45deg) translate(5px, 5px);
  }

  .hamburger-btn.active span:nth-child(2) {
    opacity: 0;
  }

  .hamburger-btn.active span:nth-child(3) {
    transform: rotate(-45deg) translate(5px, -5px);
  }

  /* 遮罩层 */
  .mobile-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 200;
    animation: fadeIn 0.2s ease;
  }

  /* 侧边栏变为抽屉 */
  .layout-container {
    flex-direction: column;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 280px;
    max-width: 85vw;
    z-index: 300;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar-header {
    padding: 1.2rem;
    display: flex;
    align-items: center;
    min-height: 56px;
  }

  .sidebar-header h2 {
    font-size: 1.1rem;
  }

  .sidebar-nav {
    flex: 1;
    padding: 0.5rem 0;
  }

  .nav-item {
    padding: 0.85rem 1.2rem;
    border-left: 3px solid transparent;
    min-height: 48px;
  }

  .nav-item.active {
    border-left-color: #667eea;
    border-bottom-color: transparent;
  }

  .sidebar-footer {
    padding: 1rem 1.2rem;
  }

  .main-content {
    padding: 1rem;
  }

  /* 设置弹窗移动端优化 */
  .settings-modal {
    width: 100%;
    max-width: none;
    max-height: 90vh;
    border-radius: 12px 12px 0 0;
    margin-top: auto;
  }

  .modal-header h2 {
    font-size: 1.05rem;
  }

  .modal-body {
    padding: 1rem;
  }

  .form-group input {
    font-size: 16px; /* 防止iOS自动缩放 */
  }
}

/* ===== 响应式：小屏手机 ===== */
@media (max-width: 480px) {
  .mobile-topbar {
    padding: 0 0.75rem;
    height: 50px;
  }

  .mobile-title {
    font-size: 0.9rem;
  }

  .main-content {
    padding: 0.75rem;
  }
}

/* ---- 全局 Toast ---- */
.global-toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  pointer-events: none;
  max-width: 90vw;
}
.global-toast.success {
  background: #d4edda;
  color: #155724;
}
.global-toast.error {
  background: #f8d7da;
  color: #721c24;
}

.global-toast-fade-enter-active,
.global-toast-fade-leave-active {
  transition: all 0.35s ease;
}
.global-toast-fade-enter-from,
.global-toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-16px);
}
</style>
