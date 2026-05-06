<template>
  <div class="register-scene">
    <!-- Decorative floating orbs -->
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>

    <!-- Noise overlay -->
    <div class="noise-layer"></div>

    <!-- Glass card -->
    <div class="glass-card">
      <!-- Brand header -->
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 32 32" width="28" height="28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="4" width="28" height="24" rx="4" stroke="url(#rg1)" stroke-width="2.2"/>
            <path d="M2 12h28" stroke="url(#rg1)" stroke-width="2"/>
            <path d="M10 18h8M10 22h5" stroke="url(#rg1)" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="24" cy="20" r="3.5" stroke="url(#rg1)" stroke-width="1.8"/>
            <path d="M24 18.5v3M22.5 20h3" stroke="url(#rg1)" stroke-width="1.5" stroke-linecap="round"/>
            <defs>
              <linearGradient id="rg1" x1="0" y1="0" x2="32" y2="32">
                <stop stop-color="#667eea"/><stop offset="1" stop-color="#764ba2"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 class="brand-name">创建账号</h1>
        <p class="brand-tagline">注册 EasyInvoice 账号</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <!-- Section: Basic Info -->
        <div class="form-section">
          <div class="section-header">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            <span>基础信息</span>
          </div>

          <div class="field">
            <label class="field-label">用户名 <em class="req">*</em></label>
            <div class="input-shell">
              <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <input v-model="form.username" type="text" placeholder="请输入用户名" required minlength="3" maxlength="50" />
            </div>
          </div>

          <div class="form-row">
            <div class="field">
              <label class="field-label">密码 <em class="req">*</em></label>
              <div class="input-shell">
                <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <input v-model="form.password" type="password" placeholder="至少6位" required minlength="6" />
              </div>
            </div>
            <div class="field">
              <label class="field-label">确认密码 <em class="req">*</em></label>
              <div class="input-shell">
                <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" required @blur="validatePasswords" />
              </div>
              <Transition name="err-slide">
                <span v-if="passwordError" class="field-error">{{ passwordError }}</span>
              </Transition>
            </div>
          </div>

          <div class="form-row">
            <div class="field">
              <label class="field-label">真实姓名 <em class="req">*</em></label>
              <div class="input-shell">
                <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                <input v-model="form.real_name" type="text" placeholder="请输入真实姓名" required />
              </div>
            </div>
            <div class="field">
              <label class="field-label">邮箱</label>
              <div class="input-shell">
                <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
                <input v-model="form.email" type="email" placeholder="选填" />
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="field">
              <label class="field-label">手机号</label>
              <div class="input-shell">
                <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
                <input v-model="form.phone" type="tel" placeholder="选填" />
              </div>
            </div>
            <div class="field">
              <label class="field-label">学号/工号</label>
              <div class="input-shell">
                <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/></svg>
                <input v-model="form.student_or_staff_id" type="text" placeholder="选填" />
              </div>
            </div>
          </div>
        </div>

        <!-- Section: Invitation Code -->
        <div class="form-section invite-section">
          <div class="section-header">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/>
            </svg>
            <span>邀请码</span>
            <span class="optional-tag">可选</span>
          </div>

          <div class="invite-info">
            <p class="invite-info-text">填写邀请码可获取更高权限：</p>
            <div class="invite-roles">
              <span class="role-chip student">学生</span>
              <span class="role-chip student-admin">学生管理员</span>
              <span class="role-chip teacher">老师</span>
              <span class="role-chip admin">管理员</span>
            </div>
          </div>

          <div class="field">
            <label class="field-label">邀请码</label>
            <div class="invite-input-row">
              <div class="input-shell invite-input">
                <svg class="input-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78Zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
                <input v-model="form.invitation_code" type="text" placeholder="如有请输入，留空则注册为学生" @blur="verifyInvitationCode" />
              </div>
              <Transition name="fade">
                <button v-if="form.invitation_code && !codeVerified" type="button" @click="verifyInvitationCode" class="btn-verify" :disabled="verifyingCode">
                  <span v-if="verifyingCode" class="btn-spinner-sm"></span>
                  {{ verifyingCode ? '验证中' : '验证' }}
                </button>
              </Transition>
            </div>

            <Transition name="err-slide">
              <div v-if="codeVerifyResult" class="verify-result" :class="codeVerifyResult.valid ? 'success' : 'error'">
                <span>{{ codeVerifyResult.message }}</span>
                <span v-if="codeVerifyResult.valid" class="target-badge">{{ getTypeText(codeVerifyResult.target_user_type) }}</span>
              </div>
            </Transition>
          </div>

          <Transition name="err-slide">
            <div v-if="detectedType" class="detected-type">
              <span class="detected-label">注册后将获得</span>
              <span class="detected-value">{{ getTypeText(detectedType) }}</span>
              <span class="detected-label">权限</span>
            </div>
          </Transition>
        </div>

        <!-- Submit -->
        <button type="submit" class="submit-btn" :disabled="registering || !!passwordError">
          <Transition name="fade" mode="out-in">
            <span v-if="registering" class="btn-loading" key="loading">
              <span class="spinner"></span>
              注册中...
            </span>
            <span v-else key="idle">立即注册</span>
          </Transition>
        </button>

        <div class="card-footer">
          已有账号？<NuxtLink to="/login" class="link">返回登录</NuxtLink>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

definePageMeta({ layout: false })

const { $api } = useNuxtApp()

const form = ref({
  username: '',
  password: '',
  confirmPassword: '',
  real_name: '',
  email: '',
  phone: '',
  student_or_staff_id: '',
  invitation_code: ''
})

const registering = ref(false)
const verifyingCode = ref(false)
const passwordError = ref('')
const codeVerifyResult = ref(null)
const codeVerified = ref(false)

const detectedType = computed(() => {
  if (codeVerifyResult.value?.valid) {
    return codeVerifyResult.value.target_user_type
  }
  return form.value.invitation_code ? null : 'student'
})

const validatePasswords = () => {
  if (form.value.password !== form.value.confirmPassword) {
    passwordError.value = '两次输入的密码不一致'
  } else {
    passwordError.value = ''
  }
}

const verifyInvitationCode = async () => {
  const code = form.value.invitation_code?.trim()

  if (!code) {
    codeVerifyResult.value = null
    codeVerified.value = false
    return
  }

  verifyingCode.value = true

  try {
    const response = await $api.post('/invitation-codes/verify', { code })

    if (response.data.code === 200) {
      const data = response.data.data
      codeVerifyResult.value = {
        valid: data.valid,
        message: data.valid ? '邀请码有效！' : `${data.reason || '邀请码无效'}`,
        target_user_type: data.valid ? data.target_user_type : null
      }
      codeVerified.value = data.valid
    } else {
      codeVerifyResult.value = {
        valid: false,
        message: response.data.message || '验证失败',
        target_user_type: null
      }
      codeVerified.value = false
    }
  } catch (error) {
    codeVerifyResult.value = {
      valid: false,
      message: '验证请求失败，请稍后重试',
      target_user_type: null
    }
    codeVerified.value = false
  } finally {
    verifyingCode.value = false
  }
}

const getTypeText = (type) => {
  const map = {
    admin: '管理员',
    teacher: '老师',
    student_admin: '学生管理员',
    student: '学生'
  }
  return map[type] || type
}

const handleRegister = async () => {
  if (form.value.password !== form.value.confirmPassword) {
    passwordError.value = '两次输入的密码不一致'
    return
  }

  registering.value = true

  try {
    let user_type = 'student'

    if (form.value.invitation_code?.trim() && codeVerifyResult.value?.valid) {
      user_type = codeVerifyResult.value.target_user_type
    }

    const payload = {
      username: form.value.username,
      password: form.value.password,
      real_name: form.value.real_name,
      email: form.value.email || null,
      phone: form.value.phone || null,
      student_or_staff_id: form.value.student_or_staff_id || null,
      user_type: user_type,
      invitation_code: form.value.invitation_code?.trim() || null
    }

    const response = await $api.post('/auth/register', payload)

    if (response.data.code === 200) {
      alert('注册成功！正在跳转到登录页...')
      navigateTo('/login')
    } else {
      alert('注册失败：' + (response.data.message || '未知错误'))
    }
  } catch (error) {
    const msg = error.response?.data?.message || error.message || '注册失败，请稍后重试'
    alert('注册失败：' + msg)
  } finally {
    registering.value = false
  }
}
</script>

<style scoped>
/* ================================================================
   Luminous Frost — Glassmorphism Register
   ================================================================ */

/* --- Scene --- */
.register-scene {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  min-height: 100dvh;
  overflow: hidden;
  padding: 32px 20px;
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

/* --- Orbs --- */
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
  animation: rfloat-1 18s ease-in-out infinite;
}
.orb-2 {
  width: 400px; height: 400px;
  bottom: -10%; right: -5%;
  background: radial-gradient(circle, #ddd6fe 0%, #ede9fe 50%, transparent 70%);
  animation: rfloat-2 22s ease-in-out infinite;
}
.orb-3 {
  width: 300px; height: 300px;
  top: 50%; right: 15%;
  background: radial-gradient(circle, #bfdbfe 0%, #dbeafe 50%, transparent 70%);
  animation: rfloat-3 15s ease-in-out infinite;
}

@keyframes rfloat-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(60px, 40px) scale(1.05); }
  66% { transform: translate(-30px, 60px) scale(0.95); }
}
@keyframes rfloat-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-50px, -30px) scale(1.08); }
  66% { transform: translate(40px, -50px) scale(0.96); }
}
@keyframes rfloat-3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-70px, 30px) scale(1.1); }
}

/* --- Noise --- */
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
  max-width: 520px;
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
  padding: 40px 36px 36px;
  animation: rcard-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes rcard-in {
  from { opacity: 0; transform: translateY(24px) scale(0.97); }
}

/* --- Brand --- */
.brand {
  text-align: center;
  margin-bottom: 32px;
}

.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  border-radius: 15px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 1px solid rgba(102, 126, 234, 0.15);
  margin-bottom: 14px;
}

.brand-name {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
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
}

/* --- Form --- */
.register-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* --- Section --- */
.form-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1.5px solid rgba(148, 163, 184, 0.12);
  font-size: 0.88rem;
  font-weight: 600;
  color: #334155;
}

.section-header svg {
  color: #667eea;
  flex-shrink: 0;
}

.optional-tag {
  font-size: 0.7rem;
  font-weight: 600;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  padding: 2px 8px;
  border-radius: 8px;
  margin-left: auto;
}

/* --- Field --- */
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
}

.req {
  color: #ef4444;
  font-style: normal;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

/* --- Input shell --- */
.input-shell {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 14px;
  color: #94a3b8;
  pointer-events: none;
  transition: color 0.25s;
  flex-shrink: 0;
}

.input-shell input {
  width: 100%;
  padding: 12px 14px 12px 42px;
  font-size: 0.9rem;
  color: #1e293b;
  background: rgba(255, 255, 255, 0.6);
  border: 1.5px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  outline: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
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

/* --- Field error --- */
.field-error {
  display: block;
  font-size: 0.78rem;
  color: #dc2626;
  font-weight: 500;
  padding-left: 2px;
}

.err-slide-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.err-slide-leave-active {
  transition: all 0.2s ease-in;
}
.err-slide-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
.err-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* --- Invite section --- */
.invite-section {
  background: rgba(102, 126, 234, 0.04);
  border: 1.5px solid rgba(102, 126, 234, 0.1);
  border-radius: 16px;
  padding: 20px;
}

.invite-info {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 10px;
  padding: 12px 16px;
  border-left: 3px solid #667eea;
}

.invite-info-text {
  margin: 0 0 10px;
  font-size: 0.82rem;
  color: #475569;
  font-weight: 500;
}

.invite-roles {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.role-chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 8px;
  font-size: 0.72rem;
  font-weight: 600;
}

.role-chip.student { background: rgba(34, 197, 94, 0.1); color: #16a34a; }
.role-chip.student-admin { background: rgba(139, 92, 246, 0.1); color: #7c3aed; }
.role-chip.teacher { background: rgba(59, 130, 246, 0.1); color: #2563eb; }
.role-chip.admin { background: rgba(239, 68, 68, 0.1); color: #dc2626; }

.invite-input-row {
  display: flex;
  gap: 10px;
}

.invite-input {
  flex: 1;
}

.btn-verify {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 20px;
  height: auto;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  transition: all 0.25s ease;
  flex-shrink: 0;
}

.btn-verify:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
}

.btn-verify:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* --- Verify result --- */
.verify-result {
  margin-top: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.verify-result.success {
  background: rgba(34, 197, 94, 0.08);
  color: #16a34a;
  border: 1px solid rgba(34, 197, 94, 0.15);
}

.verify-result.error {
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.target-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3px 12px;
  border-radius: 8px;
  font-size: 0.72rem;
  font-weight: 700;
}

/* --- Detected type --- */
.detected-type {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 14px;
  background: rgba(102, 126, 234, 0.06);
  border: 1px dashed rgba(102, 126, 234, 0.2);
  border-radius: 10px;
  font-size: 0.82rem;
}

.detected-label { color: #94a3b8; }
.detected-value { font-weight: 700; color: #667eea; }

/* --- Submit --- */
.submit-btn {
  position: relative;
  width: 100%;
  padding: 15px 24px;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.04em;
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

.submit-btn:hover:not(:disabled)::before { opacity: 1; }

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

@keyframes spin { to { transform: rotate(360deg); } }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* --- Footer --- */
.card-footer {
  margin-top: 24px;
  padding-top: 18px;
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

.link:hover { color: #764ba2; }

/* ================================================================
   RESPONSIVE
   ================================================================ */

@media (max-width: 1024px) {
  .glass-card {
    max-width: 480px;
    padding: 36px 32px 32px;
  }
}

@media (max-width: 768px) {
  .register-scene {
    padding: 20px 16px;
    align-items: flex-start;
    padding-top: 6vh;
  }

  .glass-card {
    padding: 32px 24px 28px;
    border-radius: 20px;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .orb-1 { width: 350px; height: 350px; }
  .orb-2 { width: 280px; height: 280px; }
  .orb-3 { width: 200px; height: 200px; }
}

@media (max-width: 480px) {
  .register-scene {
    padding: 12px 10px;
    padding-top: 4vh;
  }

  .glass-card {
    padding: 28px 18px 24px;
    border-radius: 18px;
  }

  .brand-icon {
    width: 44px;
    height: 44px;
    border-radius: 13px;
    margin-bottom: 10px;
  }

  .brand-name { font-size: 1.3rem; }
  .brand-tagline { font-size: 0.8rem; }
  .brand { margin-bottom: 24px; }

  .input-shell input {
    min-height: 48px;
    padding: 12px 12px 12px 40px;
    font-size: 16px; /* prevent iOS zoom */
    border-radius: 10px;
  }

  .input-icon { left: 12px; }

  .section-header { font-size: 0.82rem; }

  .invite-section { padding: 16px; }
  .invite-info { padding: 10px 14px; }

  .invite-input-row {
    flex-direction: column;
    gap: 10px;
  }

  .btn-verify {
    width: 100%;
    min-height: 44px;
    justify-content: center;
    padding: 12px 20px;
  }

  .submit-btn {
    min-height: 48px;
    padding: 14px 20px;
    font-size: 0.95rem;
    border-radius: 12px;
  }

  .verify-result {
    padding: 8px 12px;
    font-size: 0.78rem;
  }

  .detected-type {
    padding: 8px 12px;
    font-size: 0.78rem;
  }

  .card-footer {
    margin-top: 18px;
    padding-top: 14px;
    font-size: 0.82rem;
  }

  .orb { opacity: 0.3; }
}

@media (max-width: 375px) {
  .glass-card {
    padding: 24px 14px 20px;
    border-radius: 16px;
  }

  .brand-name { font-size: 1.2rem; }

  .role-chip {
    font-size: 0.68rem;
    padding: 2px 8px;
  }
}
</style>
