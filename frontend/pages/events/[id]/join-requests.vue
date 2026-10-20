<template>
  <div class="join-requests-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">← 返回</button>
      <h1 class="page-title">加入申请审核 — {{ event?.event_name || '加载中…' }}</h1>
      <div class="header-meta">
        <span class="review-mode-chip" :class="joinReviewMode">
          {{ joinReviewMode === 'auto' ? '自动审核加入' : '人工审核加入' }}
        </span>
      </div>
    </div>

    <!-- 无权审核：不渲染申请列表，也不提供任何审核入口 -->
    <div v-if="forbidden" class="forbidden-card">
      <div class="forbidden-icon">🔒</div>
      <h2>无权访问</h2>
      <p>只有该比赛的负责人、指导老师或管理员可以审核加入申请。</p>
      <button class="btn-secondary" @click="goBack">返回人员管理</button>
    </div>

    <template v-else>
      <!-- 状态筛选 -->
      <div class="filter-bar">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="filter-tab"
          :class="{ active: statusFilter === tab.value }"
          @click="statusFilter = tab.value"
        >
          {{ tab.label }}
          <span v-if="tab.value === 'pending' && pendingCount > 0" class="tab-count">{{ pendingCount }}</span>
        </button>
        <button class="btn-secondary refresh-btn" :disabled="loading" @click="loadRequests">
          {{ loading ? '刷新中…' : '刷新' }}
        </button>
      </div>

      <div v-if="errorMessage" class="alert-error">{{ errorMessage }}</div>

      <div v-if="!loading && requests.length === 0" class="empty-card">
        <div class="empty-icon">📭</div>
        <p>{{ emptyText }}</p>
      </div>

      <div class="request-list">
        <div v-for="item in requests" :key="item.request_id" class="request-card">
          <div class="request-main">
            <div class="request-avatar">{{ (item.real_name || item.username || '?').charAt(0) }}</div>
            <div class="request-info">
              <div class="request-name-row">
                <strong class="request-name">{{ item.real_name || item.username }}</strong>
                <span class="request-username">@{{ item.username }}</span>
                <span class="status-badge" :class="item.status">{{ statusText(item.status) }}</span>
              </div>
              <div class="request-meta">
                <span>申请时间：{{ formatTime(item.created_at) }}</span>
                <span class="meta-dot">·</span>
                <span>审核方式：{{ item.review_mode === 'auto' ? '自动审核' : '人工审核' }}</span>
              </div>
              <div v-if="item.status !== 'pending' && item.reviewer_name" class="request-meta">
                <span>审核人：{{ item.reviewer_name }}</span>
                <span class="meta-dot">·</span>
                <span>审核时间：{{ formatTime(item.review_time) }}</span>
              </div>
              <div v-if="item.status === 'rejected' && item.reject_reason" class="reject-reason">
                驳回理由：{{ item.reject_reason }}
              </div>
            </div>
          </div>
          <div v-if="item.status === 'pending'" class="request-actions">
            <button
              class="btn-approve"
              :disabled="processingId === item.request_id"
              @click="review(item, 'approve')"
            >
              {{ processingId === item.request_id ? '处理中…' : '✓ 通过' }}
            </button>
            <button
              class="btn-reject"
              :disabled="processingId === item.request_id"
              @click="openRejectModal(item)"
            >
              ✕ 驳回
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- 驳回理由弹窗 -->
    <div v-if="rejectTarget" class="modal-mask" @mousedown.self="closeRejectModal">
      <div class="modal-card">
        <h3 class="modal-title">驳回加入申请</h3>
        <p class="modal-subtitle">
          申请人：{{ rejectTarget.real_name || rejectTarget.username }}
        </p>
        <textarea
          v-model="rejectReason"
          rows="4"
          class="modal-textarea"
          placeholder="请填写驳回理由（可选，申请人可见）"
        ></textarea>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeRejectModal">取消</button>
          <button
            class="btn-reject"
            :disabled="processingId === rejectTarget.request_id"
            @click="confirmReject"
          >
            {{ processingId === rejectTarget.request_id ? '处理中…' : '确认驳回' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const route = useRoute()
const router = useRouter()

const eventId = computed(() => route.params.id)
const event = ref(null)

const requests = ref([])
const pendingCount = ref(0)
const joinReviewMode = ref('manual')
const statusFilter = ref('pending')
const loading = ref(false)
const errorMessage = ref('')
const forbidden = ref(false)
const processingId = ref(null)

const rejectTarget = ref(null)
const rejectReason = ref('')

const tabs = [
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
  { value: '', label: '全部' }
]

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })

const statusText = (status) => ({
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}[status] || status)

const formatTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const emptyText = computed(() => {
  if (statusFilter.value === 'pending') return '暂无待审核的加入申请'
  if (statusFilter.value === 'approved') return '暂无已通过的申请'
  if (statusFilter.value === 'rejected') return '暂无已驳回的申请'
  return '暂无加入申请记录'
})

const goBack = () => {
  router.push(`/events/${eventId.value}/members`)
}

const loadEvent = async () => {
  try {
    const response = await $api.get(`/events/${eventId.value}`, { headers: authHeaders() })
    if (response.data.code === 200) {
      event.value = response.data.data
    }
  } catch (e) {
    console.error('加载比赛信息失败:', e.message)
  }
}

const loadRequests = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const response = await $api.get(`/events/${eventId.value}/join-requests`, {
      headers: authHeaders(),
      params
    })
    if (response.data.code === 200) {
      requests.value = response.data.data.requests || []
      pendingCount.value = response.data.data.pending_count || 0
      joinReviewMode.value = response.data.data.join_review_mode || 'manual'
    }
  } catch (e) {
    if (e.response?.status === 403) {
      forbidden.value = true
      return
    }
    errorMessage.value = e.response?.data?.message || '加载加入申请失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const review = async (item, action, reason = null) => {
  processingId.value = item.request_id
  try {
    const payload = { action }
    if (reason) payload.reject_reason = reason
    const response = await $api.post(
      `/events/${eventId.value}/join-requests/${item.request_id}/review`,
      payload,
      { headers: authHeaders() }
    )
    alert(response.data.message || '操作成功')
    closeRejectModal()
    await loadRequests()
  } catch (e) {
    alert(e.response?.data?.message || '审核失败，请稍后重试')
  } finally {
    processingId.value = null
  }
}

const openRejectModal = (item) => {
  rejectTarget.value = item
  rejectReason.value = ''
}

const closeRejectModal = () => {
  rejectTarget.value = null
  rejectReason.value = ''
}

const confirmReject = async () => {
  if (!rejectTarget.value) return
  await review(rejectTarget.value, 'reject', rejectReason.value.trim() || null)
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    navigateTo('/login')
    return
  }
  await loadEvent()
  await loadRequests()
})
</script>

<style scoped>
.join-requests-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}

.back-button {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.back-button:hover { border-color: #667eea; color: #667eea; }

.page-title {
  flex: 1;
  margin: 0;
  font-size: 1.35rem;
  color: #2d3748;
}

.header-meta { display: flex; align-items: center; gap: 0.5rem; }

.review-mode-chip {
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 12px;
  background: #eef2ff;
  color: #4338ca;
  border: 1px solid #c7d2fe;
}
.review-mode-chip.auto { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }

.filter-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.filter-tab {
  padding: 0.45rem 0.9rem;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 999px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-tab:hover { border-color: #a5b4fc; }
.filter-tab.active {
  background: #4c51bf;
  border-color: #4c51bf;
  color: #fff;
}

.tab-count {
  display: inline-block;
  margin-left: 0.35rem;
  min-width: 1.15rem;
  padding: 0 0.3rem;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  line-height: 1.15rem;
  text-align: center;
}

.refresh-btn { margin-left: auto; }

.btn-secondary {
  padding: 0.45rem 0.95rem;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { border-color: #667eea; color: #667eea; }
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }

.alert-error {
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  font-size: 13px;
}

.empty-card,
.forbidden-card {
  padding: 3rem 1.5rem;
  text-align: center;
  background: #fff;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
  color: #6b7280;
}
.forbidden-card h2 { margin: 0.75rem 0 0.5rem; color: #374151; font-size: 1.1rem; }
.forbidden-card p { margin: 0 0 1.25rem; font-size: 13px; }
.empty-icon,
.forbidden-icon { font-size: 2rem; }

.request-list { display: flex; flex-direction: column; gap: 0.75rem; }

.request-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.15rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.request-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 2px 10px rgba(76, 81, 191, 0.06);
}

.request-main { display: flex; align-items: flex-start; gap: 0.85rem; min-width: 0; }

.request-avatar {
  width: 2.4rem;
  height: 2.4rem;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-weight: 600;
}

.request-info { min-width: 0; }
.request-name-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.request-name { color: #1f2937; font-size: 14px; }
.request-username { color: #9ca3af; font-size: 12px; }

.status-badge {
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 11px;
}
.status-badge.pending { background: #fef3c7; color: #b45309; }
.status-badge.approved { background: #ecfdf5; color: #047857; }
.status-badge.rejected { background: #fef2f2; color: #b91c1c; }

.request-meta {
  margin-top: 0.3rem;
  font-size: 12px;
  color: #6b7280;
}
.meta-dot { margin: 0 0.4rem; }

.reject-reason {
  margin-top: 0.35rem;
  font-size: 12px;
  color: #b91c1c;
}

.request-actions { display: flex; gap: 0.5rem; flex: none; }

.btn-approve,
.btn-reject {
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.btn-approve { background: #059669; color: #fff; }
.btn-approve:hover:not(:disabled) { background: #047857; }
.btn-reject {
  background: #fff;
  color: #b91c1c;
  border-color: #fecaca;
}
.btn-reject:hover:not(:disabled) { background: #fef2f2; }
.btn-approve:disabled,
.btn-reject:disabled { opacity: 0.6; cursor: not-allowed; }

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  z-index: 50;
}

.modal-card {
  width: 100%;
  max-width: 460px;
  background: #fff;
  border-radius: 12px;
  padding: 1.35rem 1.5rem 1.15rem;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.2);
}

.modal-title { margin: 0 0 0.35rem; font-size: 1.05rem; color: #1f2937; }
.modal-subtitle { margin: 0 0 0.9rem; font-size: 13px; color: #6b7280; }

.modal-textarea {
  width: 100%;
  padding: 0.7rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
}
.modal-textarea:focus { outline: none; border-color: #667eea; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

@media (max-width: 640px) {
  .request-card { flex-direction: column; align-items: stretch; }
  .request-actions { justify-content: flex-end; }
}
</style>
