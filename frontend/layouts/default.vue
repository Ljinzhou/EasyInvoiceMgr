<template>
  <div class="layout-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>发票管理系统</h2>
      </div>
      <nav class="sidebar-nav">
        <NuxtLink to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }">
          <span class="nav-icon">📊</span>
          <span class="nav-text">总览面板</span>
        </NuxtLink>
        <NuxtLink to="/invoices" class="nav-item" :class="{ active: $route.path.startsWith('/invoices') }">
          <span class="nav-icon">📄</span>
          <span class="nav-text">发票管理</span>
        </NuxtLink>
        <NuxtLink to="/projects" class="nav-item" :class="{ active: $route.path.startsWith('/projects') }">
          <span class="nav-icon">📁</span>
          <span class="nav-text">项目管理</span>
        </NuxtLink>
      </nav>
      <div class="sidebar-footer">
        <div class="user-info">
          <div class="user-avatar">{{ userInitial }}</div>
          <div class="user-details">
            <div class="user-name">{{ userName }}</div>
            <div class="user-role">{{ userRole }}</div>
          </div>
        </div>
        <button @click="handleLogout" class="logout-button">退出登录</button>
      </div>
    </aside>
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'

const { $api } = useNuxtApp()
const route = useRoute()

const user = ref(null)

onMounted(() => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    user.value = JSON.parse(userStr)
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
