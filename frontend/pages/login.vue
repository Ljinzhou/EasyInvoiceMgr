<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="login-title">登录</h1>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            required
            placeholder="请输入用户名"
          />
        </div>
        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            required
            placeholder="请输入密码"
          />
        </div>
        <div v-if="error" class="error-message">{{ error }}</div>
        <button type="submit" :disabled="loading" class="login-button">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

definePageMeta({
  layout: false
})

const { $api } = useNuxtApp()

const form = ref({
  username: '',
  password: ''
})

const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  
  console.log('=== 开始登录 ===')
  console.log('登录表单数据:', form.value)
  
  try {
    console.log('发送登录请求到: /api/login')
    const response = await $api.post('/login', form.value)
    
    console.log('登录响应状态:', response.status)
    console.log('登录响应数据:', response.data)
    
    if (response.data.code === 200) {
      console.log('登录成功，保存token和用户信息')
      localStorage.setItem('token', response.data.data.token)
      localStorage.setItem('user', JSON.stringify(response.data.data.user))
      console.log('准备跳转到总览面板')
      navigateTo('/dashboard')
    } else {
      console.error('登录失败，错误码:', response.data.code)
      console.error('错误信息:', response.data.message)
      error.value = response.data.message
    }
  } catch (err) {
    console.error('=== 登录异常 ===')
    console.error('错误对象:', err)
    console.error('错误响应:', err.response)
    console.error('错误响应数据:', err.response?.data)
    console.error('错误状态码:', err.response?.status)
    console.error('错误消息:', err.message)
    
    error.value = err.response?.data?.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
    console.log('=== 登录流程结束 ===')
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: white;
  padding: 2rem;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
}

.login-title {
  text-align: center;
  color: #333;
  margin-bottom: 2rem;
}

.login-form {
  display: flex;
  flex-direction: column;
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
}

.form-group input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.error-message {
  color: #e74c3c;
  font-size: 0.9rem;
  text-align: center;
}

.login-button {
  padding: 0.75rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 1rem;
  cursor: pointer;
  transition: opacity 0.3s;
}

.login-button:hover:not(:disabled) {
  opacity: 0.9;
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 480px) {
  .login-card {
    margin: 1rem;
    padding: 1.5rem;
  }
}
</style>
