<template>
  <div class="settings-page">
    <!-- 403 for non-admin -->
    <div v-if="!isAdmin" class="forbidden-card">
      <div class="forbidden-icon">🔒</div>
      <h2>访问受限</h2>
      <p>系统设置仅限管理员访问。如需协助，请联系系统管理员。</p>
      <NuxtLink to="/dashboard" class="back-link">返回总览面板</NuxtLink>
    </div>

    <template v-else>
      <header class="page-header">
        <h1>系统设置</h1>
        <p class="page-subtitle">管理 AI 模型配置与系统更新</p>
      </header>

      <div class="settings-grid">
        <!-- AI Configuration -->
        <section class="config-card">
          <div class="card-header">
            <span class="card-icon">🤖</span>
            <div>
              <h2>AI 模型配置</h2>
              <p class="card-desc">配置发票识别的视觉模型参数</p>
            </div>
            <span v-if="aiSaved" class="status-pill saved">已配置</span>
            <span v-else class="status-pill empty">未配置</span>
          </div>

          <form @submit.prevent="saveAiConfig" class="config-form">
            <div class="field">
              <label class="field-label">模型选择</label>
              <div class="select-wrapper">
                <select v-model="aiForm.model" class="field-select">
                  <option v-for="m in modelOptions" :key="m.value" :value="m.value">
                    {{ m.label }}
                  </option>
                </select>
                <svg class="select-chevron" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </div>
              <span class="field-hint">选择用于发票识别的 GLM 视觉模型</span>
            </div>

            <div class="field">
              <label class="field-label">API 密钥</label>
              <div class="input-password-wrapper">
                <input
                  v-model="aiForm.apiKey"
                  :type="showKey ? 'text' : 'password'"
                  class="field-input"
                  placeholder="输入 API 密钥"
                  autocomplete="off"
                />
                <button type="button" class="toggle-btn" @click="showKey = !showKey" :title="showKey ? '隐藏' : '显示'">
                  <svg v-if="!showKey" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                </button>
              </div>
              <span class="field-hint">当前密钥：{{ aiStatus.maskedKey || '未设置' }}</span>
            </div>

            <div class="field">
              <label class="field-label">API 地址</label>
              <input v-model="aiForm.apiUrl" type="text" class="field-input" placeholder="https://open.bigmodel.cn/api/paas/v4/chat/completions" />
              <span class="field-hint">可选，留空使用默认地址</span>
            </div>

            <transition name="msg-fade">
              <div v-if="aiMsg" class="form-msg" :class="aiMsgType">{{ aiMsg }}</div>
            </transition>

            <div class="form-actions-row">
              <button type="submit" class="save-btn" :disabled="aiSaving">
                <span v-if="aiSaving" class="btn-spinner"></span>
                {{ aiSaving ? '保存中...' : '保存配置' }}
              </button>
              <button type="button" class="test-btn" :disabled="testing || aiSaving" @click="testModel">
                <span v-if="testing" class="btn-spinner"></span>
                {{ testing ? '测试中...' : '测试连接' }}
              </button>
            </div>

            <transition name="msg-fade">
              <div v-if="testResult" class="form-msg" :class="testResult?.success ? 'success' : 'error'">
                {{ testResult?.text }}
              </div>
            </transition>
          </form>
        </section>

        <!-- Update Check -->
        <section class="config-card">
          <div class="card-header">
            <span class="card-icon">🔄</span>
            <div>
              <h2>系统更新</h2>
              <p class="card-desc">检查并安装最新版本</p>
            </div>
            <span class="version-badge">v{{ currentVersion }}</span>
          </div>

          <div class="update-section">
            <div class="version-row">
              <span class="version-label">当前版本</span>
              <span class="version-value">v{{ currentVersion }}</span>
            </div>

            <div v-if="updateState === 'has_update'" class="update-notice">
              <div class="update-notice-header">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <span>新版本可用：v{{ latestVersion }}</span>
                <span v-if="updateReleaseName" class="release-name">{{ updateReleaseName }}</span>
              </div>
              <p v-if="updateInfo" class="update-notes">{{ updateInfo }}</p>
              <a v-if="updateDownloadUrl" :href="updateDownloadUrl" target="_blank" class="update-now-btn">
                前往 GitHub 下载
              </a>
            </div>

            <div v-else-if="updateState === 'up_to_date'" class="update-status ok">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              已是最新版本
            </div>

            <div v-else-if="updateState === 'error'" class="update-status error">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              {{ updateError || '检查失败，请稍后重试' }}
            </div>

            <button
              class="check-btn"
              :disabled="checking"
              @click="checkUpdate"
              v-if="updateState !== 'has_update' || updateState === 'error'"
            >
              <span v-if="checking" class="btn-spinner"></span>
              {{ checking ? '检查中...' : '检查更新' }}
            </button>
          </div>
        </section>

        <!-- Audit Logs -->
        <section class="config-card audit-card">
          <div class="card-header">
            <span class="card-icon">📋</span>
            <div>
              <h2>配置变更记录</h2>
              <p class="card-desc">管理员操作审计日志</p>
            </div>
          </div>

          <div v-if="auditLoading" class="audit-loading">加载中...</div>
          <div v-else-if="auditLogs.length === 0" class="audit-empty">暂无记录</div>
          <div v-else class="audit-list">
            <div v-for="log in auditLogs" :key="log.id" class="audit-item">
              <div class="audit-meta">
                <span class="audit-admin">{{ log.admin_name }}</span>
                <span class="audit-action">{{ log.action }}</span>
                <span class="audit-target">{{ log.target }}</span>
              </div>
              <div class="audit-time">{{ formatTime(log.created_at) }}</div>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { useUserStore } from '~/stores/userStore'

const { $api } = useNuxtApp()
const userStore = useUserStore()
userStore.loadFromStorage()

const isAdmin = computed(() => userStore.userType === 'admin')

const modelOptions = [
  { value: 'GLM-4V-Flash', label: 'GLM-4V-Flash（推荐）' },
  { value: 'GLM-4.7-Flash', label: 'GLM-4.7-Flash' },
  { value: 'GLM-4.6V-Flash', label: 'GLM-4.6V-Flash' },
  { value: 'GLM-4.1V-Thinking-Flash', label: 'GLM-4.1V-Thinking-Flash' },
  { value: 'GLM-4-Flash-250414', label: 'GLM-4-Flash-250414' },
]

// ---- AI Config ----
const aiForm = reactive({ model: 'GLM-4V-Flash', apiKey: '', apiUrl: '' })
const aiStatus = reactive({ maskedKey: '' })
const showKey = ref(false)
const aiSaving = ref(false)
const aiSaved = ref(false)
const aiMsg = ref('')
const aiMsgType = ref('success')
let aiMsgTimer: ReturnType<typeof setTimeout> | null = null

function showAiMsg(text: string, type: 'success' | 'error') {
  aiMsg.value = text
  aiMsgType.value = type
  if (aiMsgTimer) clearTimeout(aiMsgTimer)
  aiMsgTimer = setTimeout(() => { aiMsg.value = '' }, 4000)
}

async function loadAiConfig() {
  try {
    const { data } = await $api.get('/system/config')
    if (data.code === 200) {
      const cfg = data.data
      aiForm.model = cfg.ai_model?.value || 'GLM-4V-Flash'
      aiForm.apiUrl = cfg.ai_api_url?.value || ''
      aiStatus.maskedKey = cfg.ai_api_key?.has_value ? cfg.ai_api_key.value : ''
      aiSaved.value = !!(cfg.ai_model?.has_value || cfg.ai_api_key?.has_value)
    }
  } catch (e) {
    // silent
  }
}

async function saveAiConfig() {
  aiSaving.value = true
  try {
    const configs: Record<string, string> = {}
    if (aiForm.model) configs.ai_model = aiForm.model
    if (aiForm.apiKey) configs.ai_api_key = aiForm.apiKey
    if (aiForm.apiUrl) configs.ai_api_url = aiForm.apiUrl

    const { data } = await $api.put('/system/config', { configs })
    if (data.code === 200) {
      showAiMsg('AI 配置保存成功', 'success')
      aiForm.apiKey = ''
      aiSaved.value = true
      await loadAiConfig()
    } else {
      showAiMsg(data.message || '保存失败', 'error')
    }
  } catch (e: any) {
    showAiMsg(e.response?.data?.message || '保存失败，请稍后重试', 'error')
  } finally {
    aiSaving.value = false
  }
}

// ---- Test Model ----
const testing = ref(false)
const testResult = ref<{ success: boolean; text: string } | null>(null)
let testMsgTimer: ReturnType<typeof setTimeout> | null = null

async function testModel() {
  testing.value = true
  testResult.value = null
  try {
    const { data } = await $api.post('/system/test-model')
    if (data.code === 200) {
      testResult.value = {
        success: true,
        text: `测试通过 · 模型 ${data.data.model} · 延迟 ${data.data.latency_ms}ms`
      }
    } else {
      testResult.value = { success: false, text: data.message || '测试失败' }
    }
  } catch (e: any) {
    testResult.value = {
      success: false,
      text: e.response?.data?.message || '测试请求失败'
    }
  } finally {
    testing.value = false
    if (testMsgTimer) clearTimeout(testMsgTimer)
    testMsgTimer = setTimeout(() => { testResult.value = null }, 6000)
  }
}

// ---- Update Check ----
const currentVersion = ref('1.2.0')
const latestVersion = ref('')
const updateInfo = ref('')
const updateReleaseName = ref('')
const updateDownloadUrl = ref('')
const updateState = ref<'idle' | 'checking' | 'has_update' | 'up_to_date' | 'error'>('idle')
const updateError = ref('')
const checking = ref(false)

async function checkUpdate() {
  checking.value = true
  updateState.value = 'checking'
  try {
    const { data } = await $api.get('/system/check-update')
    if (data.code === 200) {
      currentVersion.value = data.data.current_version
      if (data.data.has_update) {
        updateState.value = 'has_update'
        latestVersion.value = data.data.update_info?.version || data.data.latest_version
        updateInfo.value = data.data.update_info?.release_notes || ''
        updateReleaseName.value = data.data.update_info?.release_name || ''
        updateDownloadUrl.value = data.data.update_info?.download_url || ''
      } else {
        updateState.value = 'up_to_date'
      }
    } else {
      updateState.value = 'error'
      updateError.value = data.message || '检查失败'
    }
  } catch (e: any) {
    updateState.value = 'error'
    updateError.value = e.response?.data?.message || '网络错误'
  } finally {
    checking.value = false
  }
}

// ---- Audit Logs ----
const auditLogs = ref<any[]>([])
const auditLoading = ref(false)

async function loadAuditLogs() {
  auditLoading.value = true
  try {
    const { data } = await $api.get('/system/audit-logs', { params: { per_page: 10 } })
    if (data.code === 200) {
      auditLogs.value = data.data.logs || []
    }
  } catch (e) {
    // silent
  } finally {
    auditLoading.value = false
  }
}

function formatTime(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  if (isAdmin.value) {
    loadAiConfig()
    loadAuditLogs()
  }
})

// Head
useHead({ title: '系统设置 - 财务管理系统' })
</script>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}

/* ---- Forbidden ---- */
.forbidden-card {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.forbidden-icon { font-size: 3rem; margin-bottom: 1rem; }
.forbidden-card h2 { margin: 0 0 .5rem; color: #2c3e50; font-size: 1.3rem; }
.forbidden-card p { margin: 0 0 1.5rem; color: #666; font-size: .9rem; }
.back-link {
  display: inline-block;
  padding: .6rem 1.5rem;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 6px;
  text-decoration: none;
  font-size: .9rem;
  transition: opacity .2s;
}
.back-link:hover { opacity: .85; }

/* ---- Page Header ---- */
.page-header {
  margin-bottom: 2rem;
}
.page-header h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a252f;
  letter-spacing: -.02em;
}
.page-subtitle {
  margin: .3rem 0 0;
  color: #8899a6;
  font-size: .9rem;
}

/* ---- Cards ---- */
.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.config-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  border: 1px solid rgba(0,0,0,.04);
}
.card-header {
  display: flex;
  align-items: center;
  gap: .75rem;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #f0f2f5;
}
.card-icon { font-size: 1.3rem; }
.card-header h2 { margin: 0; font-size: 1.05rem; font-weight: 600; color: #2c3e50; }
.card-desc { margin: .15rem 0 0; font-size: .82rem; color: #8899a6; }

.status-pill {
  margin-left: auto;
  font-size: .75rem;
  padding: .25rem .65rem;
  border-radius: 20px;
  font-weight: 500;
}
.status-pill.saved { background: #eafaf1; color: #1e7e34; }
.status-pill.empty { background: #fef3e2; color: #b7791f; }

.version-badge {
  margin-left: auto;
  font-size: .78rem;
  font-weight: 600;
  color: #667eea;
  background: rgba(102,126,234,.1);
  padding: .2rem .6rem;
  border-radius: 4px;
}

/* ---- Form ---- */
.config-form { display: flex; flex-direction: column; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: .3rem; }
.field-label {
  font-size: .85rem;
  font-weight: 600;
  color: #334155;
}
.field-hint {
  font-size: .78rem;
  color: #94a3b8;
}

/* Select */
.select-wrapper {
  position: relative;
}
.field-select {
  width: 100%;
  padding: .65rem .75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: .9rem;
  color: #1e293b;
  background: white;
  appearance: none;
  cursor: pointer;
  transition: border-color .2s, box-shadow .2s;
  min-height: 44px;
  box-sizing: border-box;
}
.field-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102,126,234,.12);
}
.select-chevron {
  position: absolute;
  right: .75rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #94a3b8;
}

/* Input */
.field-input {
  width: 100%;
  padding: .65rem .75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: .9rem;
  color: #1e293b;
  transition: border-color .2s, box-shadow .2s;
  min-height: 44px;
  box-sizing: border-box;
}
.field-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102,126,234,.12);
}
.field-input::placeholder { color: #cbd5e1; }

.input-password-wrapper {
  position: relative;
  display: flex;
}
.input-password-wrapper .field-input {
  padding-right: 2.75rem;
}
.toggle-btn {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  transition: color .2s;
}
.toggle-btn:hover { color: #475569; }

/* Buttons */
.form-actions-row {
  display: flex;
  gap: .75rem;
  align-items: center;
}

.test-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: .7rem 1.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  min-height: 44px;
  background: white;
  color: #334155;
}
.test-btn:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; }
.test-btn:disabled { opacity: .55; cursor: not-allowed; }

.save-btn, .check-btn, .update-now-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: .7rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  min-height: 44px;
}
.save-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  align-self: flex-start;
}
.save-btn:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
.save-btn:disabled { opacity: .55; cursor: not-allowed; }

.check-btn {
  background: white;
  color: #334155;
  border: 1px solid #e2e8f0;
  margin-top: 1rem;
}
.check-btn:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; }
.check-btn:disabled { opacity: .55; cursor: not-allowed; }

.update-now-btn {
  background: linear-gradient(135deg, #27ae60, #2ecc71);
  color: white;
  margin-top: .75rem;
}
.update-now-btn:hover:not(:disabled) { opacity: .9; }
.update-now-btn:disabled { opacity: .55; cursor: not-allowed; }

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Messages */
.form-msg {
  padding: .6rem .85rem;
  border-radius: 8px;
  font-size: .85rem;
  font-weight: 500;
}
.form-msg.success { background: #eafaf1; color: #1e7e34; }
.form-msg.error { background: #fdf2f2; color: #9b1c1c; }

.msg-fade-enter-active, .msg-fade-leave-active { transition: all .25s ease; }
.msg-fade-enter-from, .msg-fade-leave-to { opacity: 0; transform: translateY(-4px); }

/* ---- Update Section ---- */
.update-section { padding-top: .25rem; }
.version-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .6rem 0;
}
.version-label { color: #64748b; font-size: .9rem; }
.version-value { font-weight: 600; color: #1e293b; font-size: .9rem; }

.update-notice {
  margin-top: .75rem;
  padding: 1rem;
  background: linear-gradient(135deg, #eff6ff, #f0f9ff);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
}
.update-notice-header {
  display: flex;
  align-items: center;
  gap: .5rem;
  font-weight: 600;
  color: #1e40af;
  margin-bottom: .35rem;
  flex-wrap: wrap;
}
.release-name {
  font-size: .78rem;
  font-weight: 400;
  color: #64748b;
}
.update-notes {
  font-size: .85rem;
  color: #475569;
  margin: .5rem 0;
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}

.update-status {
  display: flex;
  align-items: center;
  gap: .5rem;
  margin-top: .75rem;
  padding: .6rem .85rem;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 500;
}
.update-status.ok { background: #eafaf1; color: #1e7e34; }
.update-status.error { background: #fdf2f2; color: #9b1c1c; }

/* ---- Audit ---- */
.audit-card { overflow: hidden; }
.audit-loading, .audit-empty {
  text-align: center;
  padding: 1.5rem;
  color: #94a3b8;
  font-size: .88rem;
}
.audit-list {
  max-height: 240px;
  overflow-y: auto;
}
.audit-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .65rem 0;
  border-bottom: 1px solid #f1f5f9;
}
.audit-item:last-child { border-bottom: none; }
.audit-meta {
  display: flex;
  gap: .5rem;
  align-items: center;
  font-size: .85rem;
}
.audit-admin { font-weight: 600; color: #1e293b; }
.audit-action {
  color: #667eea;
  font-size: .78rem;
  background: rgba(102,126,234,.08);
  padding: .1rem .5rem;
  border-radius: 4px;
}
.audit-target { color: #64748b; }
.audit-time { font-size: .78rem; color: #94a3b8; flex-shrink: 0; margin-left: 1rem; }

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .settings-page { padding: 0; }
  .page-header h1 { font-size: 1.3rem; }
  .config-card { padding: 1.15rem; border-radius: 10px; }
  .audit-meta { flex-wrap: wrap; }
}
</style>
