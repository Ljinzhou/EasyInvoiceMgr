<template>
  <div class="login-scene">
    <!-- Decorative floating orbs for depth -->
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>

    <!-- Subtle noise overlay -->
    <div class="noise-layer"></div>

    <!-- Glass card -->
    <div class="glass-card">
      <!-- Brand header -->
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 32 32" width="28" height="28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="4" width="28" height="24" rx="4" stroke="url(#g1)" stroke-width="2.2"/>
            <path d="M2 12h28" stroke="url(#g1)" stroke-width="2"/>
            <path d="M10 18h8M10 22h5" stroke="url(#g1)" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="24" cy="20" r="3.5" stroke="url(#g1)" stroke-width="1.8"/>
            <path d="M24 18.5v3M22.5 20h3" stroke="url(#g1)" stroke-width="1.5" stroke-linecap="round"/>
            <defs>
              <linearGradient id="g1" x1="0" y1="0" x2="32" y2="32">
                <stop stop-color="#667eea"/><stop offset="1" stop-color="#764ba2"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 class="brand-name">EasyInvoice</h1>
        <p class="brand-tagline">财务管理系统</p>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="field">
          <label for="username" class="field-label">用户名</label>
          <div class="input-shell">
            <svg class="input-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <input
              id="username"
              v-model="form.username"
              type="text"
              required
              placeholder="请输入用户名"
              autocomplete="username"
            />
          </div>
        </div>

        <div class="field">
          <label for="password" class="field-label">密码</label>
          <div class="input-shell">
            <svg class="input-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </div>
        </div>

        <!-- Error message -->
        <Transition name="error-pop">
          <div v-if="error" class="error-banner">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ error }}</span>
          </div>
        </Transition>

        <!-- Submit -->
        <button type="submit" class="submit-btn" :disabled="loading">
          <Transition name="fade" mode="out-in">
            <span v-if="loading" class="btn-loading" key="loading">
              <span class="spinner"></span>
              登录中...
            </span>
            <span v-else key="idle">登 录</span>
          </Transition>
        </button>
      </form>

      <!-- Footer link -->
      <div class="card-footer">
        还没有账号？<NuxtLink to="/register" class="link">立即注册</NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '~/stores/userStore'
import { useEventStore } from '~/stores/eventStore'
import { useCacheStore } from '~/stores/cache'

definePageMeta({
  layout: false
})

const { $api } = useNuxtApp()
const userStore = useUserStore()

const form = ref({
  username: '',
  password: ''
})

const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await $api.post('/auth/login', form.value)

    if (response.data.code === 200) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('app_cache')
      userStore.clearUser()
      const eventStore = useEventStore()
      eventStore.$reset()
      const cacheStore = useCacheStore()
      cacheStore.clear()

      localStorage.setItem('token', response.data.data.token)
      userStore.saveToStorage(response.data.data.user)
      navigateTo('/dashboard')
    } else {
      error.value = response.data.message
    }
  } catch (err) {
    console.error('登录失败:', err.message)
    error.value = err.response?.data?.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ================================================================
   Luminous Frost — Glassmorphism Login
   ================================================================ */

/* --- Scene --- */
.login-scene {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  min-height: 100dvh;
  overflow: hidden;
  /* High-brightness white gradient with subtle lavender tint */
  background:
    linear-gradient(135deg,
      #f8f9ff 0%,
      #f0f2ff 20%,
      #fafbff 40%,
      #f5f0ff 60%,
      #f8f6ff 80%,
      #f0f4ff 100%
    );
}

/* --- Decorative orbs --- */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.45;
  pointer-events: none;
  will-change: transform;
}
.orb-1 {
  width: 500px; height: 500px;
  top: -15%; left: -10%;
  background: radial-gradient(circle, #c7d2fe 0%, #e0e7ff 50%, transparent 70%);
  animation: float-1 18s ease-in-out infinite;
}
.orb-2 {
  width: 400px; height: 400px;
  bottom: -10%; right: -5%;
  background: radial-gradient(circle, #ddd6fe 0%, #ede9fe 50%, transparent 70%);
  animation: float-2 22s ease-in-out infinite;
}
.orb-3 {
  width: 300px; height: 300px;
  top: 40%; right: 20%;
  background: radial-gradient(circle, #bfdbfe 0%, #dbeafe 50%, transparent 70%);
  animation: float-3 15s ease-in-out infinite;
}

@keyframes float-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(60px, 40px) scale(1.05); }
  66% { transform: translate(-30px, 60px) scale(0.95); }
}
@keyframes float-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-50px, -30px) scale(1.08); }
  66% { transform: translate(40px, -50px) scale(0.96); }
}
@keyframes float-3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-70px, 30px) scale(1.1); }
}

/* --- Noise texture overlay --- */
.noise-layer {
  position: fixed;
  inset: 0;
  opacity: 0.025;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 200px 200px;
}

/* --- Glass card --- */
.glass-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  margin: 0 24px;
  padding: 44px 40px 36px;
  /* Glassmorphism */
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(24px) saturate(1.4);
  -webkit-backdrop-filter: blur(24px) saturate(1.4);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 24px;
  box-shadow:
    0 8px 32px rgba(102, 126, 234, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.03),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  /* Entry animation */
  animation: card-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.97);
  }
}

/* --- Brand --- */
.brand {
  text-align: center;
  margin-bottom: 36px;
}

.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 1px solid rgba(102, 126, 234, 0.15);
  margin-bottom: 16px;
}

.brand-name {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1e293b;
  margin: 0 0 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-tagline {
  font-size: 0.85rem;
  color: #94a3b8;
  margin: 0;
  letter-spacing: 0.04em;
}

/* --- Form --- */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* --- Field --- */
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.02em;
}

.input-shell {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 16px;
  color: #94a3b8;
  pointer-events: none;
  transition: color 0.25s;
}

.input-shell input {
  width: 100%;
  padding: 14px 16px 14px 46px;
  font-size: 0.95rem;
  color: #1e293b;
  background: rgba(255, 255, 255, 0.6);
  border: 1.5px solid rgba(148, 163, 184, 0.25);
  border-radius: 14px;
  outline: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.input-shell input::placeholder {
  color: #b0b8c8;
}

.input-shell input:focus {
  border-color: #667eea;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.input-shell:focus-within .input-icon {
  color: #667eea;
}

/* --- Error banner --- */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 12px;
  color: #dc2626;
  font-size: 0.85rem;
  font-weight: 500;
}

.error-pop-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.error-pop-leave-active {
  transition: all 0.2s ease-in;
}
.error-pop-enter-from {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}
.error-pop-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

/* --- Submit button --- */
.submit-btn {
  position: relative;
  width: 100%;
  padding: 15px 24px;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 14px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.25);
}

.submit-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.3s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.35);
}

.submit-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.submit-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-loading {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2.5px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Transition: fade */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* --- Card footer --- */
.card-footer {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  text-align: center;
  font-size: 0.85rem;
  color: #94a3b8;
}

.link {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.link:hover {
  color: #764ba2;
}

/* ================================================================
   RESPONSIVE
   ================================================================ */

/* Tablet */
@media (max-width: 1024px) {
  .glass-card {
    max-width: 400px;
    padding: 40px 36px 32px;
  }
}

/* Mobile */
@media (max-width: 768px) {
  .login-scene {
    padding: 24px 16px;
    align-items: flex-start;
    padding-top: 12vh;
  }

  .glass-card {
    margin: 0;
    padding: 36px 28px 30px;
    border-radius: 20px;
  }

  .orb-1 { width: 350px; height: 350px; }
  .orb-2 { width: 280px; height: 280px; }
  .orb-3 { width: 200px; height: 200px; }
}

/* Small mobile */
@media (max-width: 480px) {
  .login-scene {
    padding: 16px 12px;
    padding-top: 8vh;
  }

  .glass-card {
    padding: 32px 22px 26px;
    border-radius: 18px;
  }

  .brand-icon {
    width: 46px;
    height: 46px;
    border-radius: 14px;
    margin-bottom: 12px;
  }

  .brand-name {
    font-size: 1.35rem;
  }

  .brand-tagline {
    font-size: 0.8rem;
  }

  .brand {
    margin-bottom: 28px;
  }

  .login-form {
    gap: 16px;
  }

  .input-shell input {
    min-height: 48px;
    padding: 13px 14px 13px 44px;
    font-size: 16px; /* prevent iOS zoom */
    border-radius: 12px;
  }

  .input-icon {
    left: 14px;
  }

  .submit-btn {
    min-height: 48px;
    padding: 14px 20px;
    font-size: 0.95rem;
    border-radius: 12px;
  }

  .error-banner {
    padding: 10px 14px;
    font-size: 0.82rem;
    border-radius: 10px;
  }

  .card-footer {
    margin-top: 22px;
    padding-top: 16px;
    font-size: 0.82rem;
  }

  /* Reduce animation on small screens */
  .orb { opacity: 0.3; }
}

/* Very small phones */
@media (max-width: 375px) {
  .glass-card {
    padding: 28px 18px 22px;
    border-radius: 16px;
  }

  .brand-name {
    font-size: 1.25rem;
  }
}
</style>
