<template>
  <div class="container">
    <h1>Easy Invoice Manager</h1>
    <HelloWorld msg="Welcome to Invoice Management System" />
    <div class="features">
      <div class="feature">
        <h3>📊 Dashboard</h3>
        <p>View your invoice statistics and analytics</p>
      </div>
      <div class="feature">
        <h3>📄 Invoices</h3>
        <p>Create, manage and send invoices</p>
      </div>
      <div class="feature">
        <h3>👥 Clients</h3>
        <p>Manage your client information</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

definePageMeta({
  layout: false
})

onMounted(() => {
  console.log('=== 首页加载 ===')
  const token = localStorage.getItem('token')
  console.log('检查token:', token ? '已登录' : '未登录')
  
  if (token) {
    console.log('用户已登录，跳转到总览面板')
    navigateTo('/dashboard')
  } else {
    console.log('用户未登录，跳转到登录页面')
    navigateTo('/login')
  }
})
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

h1 {
  font-size: 3rem;
  margin-bottom: 2rem;
  color: #333;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 3rem;
}

.feature {
  padding: 2rem;
  background: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.feature h3 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #42b883;
}

.feature p {
  color: #666;
}
</style>