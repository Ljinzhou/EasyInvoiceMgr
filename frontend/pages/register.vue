<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-header">
        <h1 class="title">创建账号</h1>
        <p class="subtitle">注册 EasyInvoiceMgr 账号</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <!-- 基础信息 -->
        <div class="form-section">
          <h3 class="section-title">基础信息</h3>
          
          <div class="form-group">
            <label>用户名 *</label>
            <input 
              v-model="form.username" 
              type="text" 
              placeholder="请输入用户名"
              required 
              minlength="3"
              maxlength="50"
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>密码 *</label>
              <input 
                v-model="form.password" 
                type="password" 
                placeholder="请输入密码（至少6位）"
                required
                minlength="6"
              />
            </div>
            <div class="form-group">
              <label>确认密码 *</label>
              <input 
                v-model="form.confirmPassword" 
                type="password" 
                placeholder="请再次输入密码"
                required
                @blur="validatePasswords"
              />
              <span v-if="passwordError" class="error-msg">{{ passwordError }}</span>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>真实姓名 *</label>
              <input 
                v-model="form.real_name" 
                type="text" 
                placeholder="请输入真实姓名"
                required
              />
            </div>
            <div class="form-group">
              <label>邮箱</label>
              <input 
                v-model="form.email" 
                type="email" 
                placeholder="请输入邮箱地址"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>手机号</label>
              <input 
                v-model="form.phone" 
                type="tel" 
                placeholder="请输入手机号码"
              />
            </div>
            <div class="form-group">
              <label>组织/学校</label>
              <input 
                v-model="form.organization" 
                type="text" 
                placeholder="请输入所属组织或学校"
              />
            </div>
          </div>

          <div class="form-group">
            <label>学号/工号</label>
            <input 
              v-model="form.student_or_staff_id" 
              type="text" 
              placeholder="请输入学号或工号（可选）"
            />
          </div>
        </div>

        <!-- 邀请码 -->
        <div class="form-section invite-section">
          <h3 class="section-title">
            🎫 邀请码
            <span class="optional-tag">可选</span>
          </h3>
          
          <div class="invite-info-box">
            <p class="invite-info-text">
              填写邀请码可以获取更高权限的账号类型：
            </p>
            <ul class="invite-type-list">
              <li><strong>学生</strong> - 默认权限，仅可查看和上传发票</li>
              <li><strong>学生管理员</strong> - 可管理部分数据，协助老师工作</li>
              <li><strong>老师</strong> - 完全管理权限，可审核发票和管理人员</li>
              <li><strong>管理员</strong> - 系统最高权限（需管理员邀请码）</li>
            </ul>
          </div>

          <div class="form-group">
            <label>邀请码</label>
            <div class="invite-input-wrapper">
              <input 
                v-model="form.invitation_code" 
                type="text" 
                placeholder="如有邀请码请输入，无则留空将注册为学生账号"
                @blur="verifyInvitationCode"
              />
              <button 
                v-if="form.invitation_code && !codeVerified" 
                type="button" 
                @click="verifyInvitationCode" 
                class="btn-verify"
                :disabled="verifyingCode"
              >
                {{ verifyingCode ? '验证中...' : '验证' }}
              </button>
            </div>
            
            <div v-if="codeVerifyResult" class="verify-result" :class="codeVerifyResult.valid ? 'success' : 'error'">
              {{ codeVerifyResult.message }}
              <span v-if="codeVerifyResult.valid" class="target-type-badge">
                → {{ getTypeText(codeVerifyResult.target_user_type) }}
              </span>
            </div>
          </div>

          <div v-if="detectedType" class="detected-type-info">
            <span class="type-label">注册后将获得：</span>
            <span class="type-value">{{ getTypeText(detectedType) }} 权限</span>
          </div>
        </div>

        <!-- 提交 -->
        <button type="submit" class="submit-btn" :disabled="registering || !!passwordError">
          {{ registering ? '注册中...' : '立即注册' }}
        </button>

        <div class="login-link">
          已有账号？<a href="/login">返回登录</a>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

definePageMeta({ layout: 'default', auth: false })

const { $api } = useNuxtApp()

const form = ref({
  username: '',
  password: '',
  confirmPassword: '',
  real_name: '',
  email: '',
  phone: '',
  organization: '',
  student_or_staff_id: '',
  invitation_code: ''
})

const registering = ref(false)
const verifyingCode = ref(false)
const passwordError = ref('')
const codeVerifyResult = ref(null)

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
    return
  }

  verifyingCode.value = true
  
  try {
    const response = await $api.post('/invitation-codes/verify', { code })
    
    if (response.data.code === 200) {
      const data = response.data.data
      codeVerifyResult.value = {
        valid: data.valid,
        message: data.valid ? '✅ 邀请码有效！' : `❌ ${data.reason || '邀请码无效'}`,
        target_user_type: data.valid ? data.target_user_type : null
      }
    } else {
      codeVerifyResult.value = {
        valid: false,
        message: response.data.message || '验证失败',
        target_user_type: null
      }
    }
  } catch (error) {
    codeVerifyResult.value = {
      valid: false,
      message: '验证请求失败，请稍后重试',
      target_user_type: null
    }
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
      organization: form.value.organization || null,
      student_or_staff_id: form.value.student_or_staff_id || null,
      user_type: user_type,
      invitation_code: form.value.invitation_code?.trim() || null
    }

    const response = await $api.post('/auth/register', payload)
    
    if (response.data.code === 200) {
      alert('🎉 注册成功！正在跳转到登录页...')
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
.register-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  padding: 20px;
}

.register-container {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 580px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.title {
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 8px;
}

.subtitle {
  color: #7f8c8d;
  margin: 0;
  font-size: 14px;
}

.form-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #34495e;
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 2px solid #ecf0f1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.optional-tag {
  font-size: 11px;
  font-weight: 500;
  background: #e8eaf6;
  color: #667eea;
  padding: 2px 8px;
  border-radius: 10px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.25s ease;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.12);
}

.error-msg {
  display: block;
  font-size: 12px;
  color: #e74c3c;
  margin-top: 4px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

/* 邀请码区域 */
.invite-section {
  background: linear-gradient(135deg, #fafbff 0%, #f5f3ff 100%);
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e8eaf6;
}

.invite-info-box {
  background: white;
  padding: 14px 18px;
  border-radius: 8px;
  margin-bottom: 16px;
  border-left: 4px solid #667eea;
}

.invite-info-text {
  margin: 0 0 10px;
  font-size: 13px;
  color: #555;
  font-weight: 500;
}

.invite-type-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #666;
  line-height: 1.9;
}
.invite-type-list strong { color: #333; }

.invite-input-wrapper {
  display: flex;
  gap: 8px;
}
.invite-input-wrapper input { flex: 1; }

.btn-verify {
  padding: 10px 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  font-size: 13px;
  white-space: nowrap;
  transition: all 0.25s ease;
}
.btn-verify:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(102,126,234,0.35); }
.btn-verify:disabled { opacity: 0.6; cursor: not-allowed; }

.verify-result {
  margin-top: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
}
.verify-result.success { background: #eaffea; color: #27ae60; border: 1px solid #b8e99b; }
.verify-result.error { background: #fff5f5; color: #e74c3c; border: 1px solid #f5c6cb; }

.target-type-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.detected-type-info {
  margin-top: 12px;
  padding: 10px 14px;
  background: white;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
  border: 1px dashed #bbb;
}
.type-label { color: #777; }
.type-value { font-weight: 700; color: #667eea; margin-left: 4px; }

.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 8px;
}
.submit-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102,126,234,0.35); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.login-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #999;
}
.login-link a {
  color: #667eea;
  font-weight: 600;
  text-decoration: none;
}
.login-link a:hover { text-decoration: underline; }

@media (max-width: 600px) {
  .register-container { padding: 24px; }
  .form-row { grid-template-columns: 1fr; }
  .invite-input-wrapper { flex-direction: column; }
  .btn-verify { width: 100%; }
}
</style>