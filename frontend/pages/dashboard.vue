<template>
  <div class="dashboard">
    <!-- Header -->
    <header class="dash-header">
      <div class="header-left">
        <h1 class="page-title">总览面板</h1>
        <span v-if="!loading && hasData" class="last-updated">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {{ lastUpdatedText }}
        </span>
        <span v-if="isDataStale && hasData" class="stale-badge">数据已过期</span>
      </div>
      <div class="header-right">
        <select v-if="hasData" v-model="selectedEventId" class="project-selector">
          <option :value="null">全部项目汇总</option>
          <option v-for="ev in eventStore.events" :key="ev.event_id" :value="ev.event_id">{{ ev.event_name }}</option>
        </select>
        <button class="refresh-btn" :class="{ spinning: loading }" @click="refreshData" :disabled="loading">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          <span>{{ loading ? '刷新中...' : '刷新' }}</span>
        </button>
      </div>
    </header>

    <!-- SKELETON LOADING -->
    <template v-if="loading && !hasData">
      <div class="stats-grid">
        <div v-for="i in 5" :key="'sk'+i" class="stat-card skeleton">
          <div class="sk-circle"></div>
          <div class="sk-lines">
            <div class="sk-line short"></div>
            <div class="sk-line long"></div>
          </div>
        </div>
      </div>
    </template>

    <!-- EMPTY STATE -->
    <template v-else-if="!loading && !hasData">
      <div class="empty-state">
        <div class="empty-illustration">
          <svg viewBox="0 0 200 120" width="200" height="120">
            <rect x="20" y="30" width="45" height="55" rx="6" fill="#e2e8f0"/>
            <rect x="75" y="15" width="45" height="70" rx="6" fill="#cbd5e1"/>
            <rect x="130" y="40" width="45" height="45" rx="6" fill="#e2e8f0"/>
            <circle cx="42" cy="50" r="8" fill="white" opacity="0.6"/>
            <circle cx="152" cy="58" r="8" fill="white" opacity="0.6"/>
            <path d="M60 85 L75 70 L90 78 L105 62 L120 72 L135 58" stroke="#94a3b8" stroke-width="2.5" fill="none" stroke-linecap="round"/>
          </svg>
        </div>
        <h2>欢迎使用财务管理系统</h2>
        <p>还没有任何项目数据，创建一个项目开始管理你的发票和支出吧。</p>
        <div class="empty-actions">
          <NuxtLink to="/events/create" class="btn-primary">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            创建第一个项目
          </NuxtLink>
          <NuxtLink to="/purchases" class="btn-secondary">浏览购买记录</NuxtLink>
        </div>
      </div>
    </template>

    <!-- MAIN CONTENT -->
    <template v-else>
      <!-- Stat Cards -->
      <div class="stats-grid">
        <div
          v-for="card in statCards"
          :key="card.key"
          class="stat-card"
          :class="[card.variant]"
          @click="card.link ? navigateTo(card.link) : undefined"
          :style="card.link ? 'cursor:pointer' : ''"
        >
          <div class="stat-icon-box">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path v-if="card.key==='events'" d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              <path v-else-if="card.key==='records'" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline v-if="card.key==='records'" points="14 2 14 8 20 8"/><line v-if="card.key==='records'" x1="16" y1="13" x2="8" y2="13"/><line v-if="card.key==='records'" x1="16" y1="17" x2="8" y2="17"/><polyline v-if="card.key==='records'" points="10 9 9 9 8 9"/>
              <path v-else-if="card.key==='spending'" d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
              <path v-else-if="card.key==='invoice'" d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1-2-1Z"/>
              <path v-else-if="card.key==='reimburse'" d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline v-if="card.key==='reimburse'" points="22 4 12 14.01 9 11.01"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-value" :class="{ 'value-sm': card.value.length > 9 }">
              <span v-if="card.prefix">{{ card.prefix }}</span>{{ card.displayValue }}
            </div>
            <div class="stat-label">{{ card.label }}</div>
            <div class="stat-sub" v-if="card.sub">
              <span :class="card.subTrend">{{ card.sub }}</span>
            </div>
          </div>
        </div>
      </div>


      <!-- Per-Project Donut Cards -->
      <div v-if="hasData" class="project-donuts-section">
        <h3 class="section-title">各项目预算概览</h3>
        <div class="donut-cards-grid">
          <div
            v-for="ev in eventStore.events"
            :key="ev.event_id"
            class="donut-card"
            :class="[accentClass(ev), { selected: ev.event_id === selectedEventId }]"
            @click="selectedEventId = ev.event_id; navigateTo(`/purchases/${ev.event_id}`)"
          >
            <div class="dc-header">
              <div class="dc-status-dot" :class="ev.status"></div>
              <h4 class="dc-name">{{ ev.event_name }}</h4>
              <span class="dc-leader" v-if="ev.leader_name">{{ ev.leader_name }}</span>
            </div>
            <div class="dc-body">
              <div class="dc-donut">
                <svg viewBox="0 0 100 100" width="100" height="100">
                  <circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" stroke-width="8"/>
                  <circle
                    cx="50" cy="50" r="42" fill="none"
                    :stroke="budgetUsagePercent(ev) > 90 ? '#ef4444' : 'url(#dg-' + ev.event_id + ')'"
                    stroke-width="8"
                    stroke-linecap="round"
                    :stroke-dasharray="2 * Math.PI * 42"
                    :stroke-dashoffset="2 * Math.PI * 42 * (1 - Math.min(100, budgetUsagePercent(ev)) / 100)"
                    transform="rotate(-90 50 50)"
                    class="donut-arc"
                  />
                  <defs>
                    <linearGradient :id="'dg-' + ev.event_id" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#6366f1"/>
                      <stop offset="100%" stop-color="#8b5cf6"/>
                    </linearGradient>
                  </defs>
                  <text x="50" y="49" text-anchor="middle" font-size="20" font-weight="700" fill="#1e293b">{{ Math.round(budgetUsagePercent(ev)) }}%</text>
                  <text x="50" y="66" text-anchor="middle" font-size="8.5" fill="#94a3b8">使用率</text>
                </svg>
              </div>
              <div class="dc-info">
                <div class="dc-amounts">
                  <div class="dc-amt">
                    <span class="dc-amt-label">已用</span>
                    <span class="dc-amt-value spent">¥{{ fmt(ev.spent_amount) }}</span>
                  </div>
                  <div class="dc-amt">
                    <span class="dc-amt-label">总预算</span>
                    <span class="dc-amt-value">¥{{ fmt(ev.total_budget) }}</span>
                  </div>
                  <div class="dc-amt">
                    <span class="dc-amt-label">剩余</span>
                    <span class="dc-amt-value" :class="remainingClass(ev)">¥{{ fmt(getEventRemaining(ev)) }}</span>
                  </div>
                  <div class="dc-amt">
                    <span class="dc-amt-label">发票总额</span>
                    <span class="dc-amt-value invoice">¥{{ fmt(ev.invoice_total_amount) }}</span>
                  </div>
                </div>
                <div class="dc-bar-row">
                  <span class="dc-bar-label">预算使用</span>
                  <div class="dc-bar-track">
                    <div class="dc-bar-fill" :class="progressClass(ev)" :style="{ width: Math.min(100, budgetUsagePercent(ev)) + '%' }"></div>
                  </div>
                  <span class="dc-bar-val" :class="progressClass(ev)">{{ Math.round(budgetUsagePercent(ev)) }}%</span>
                </div>
                <div class="dc-bar-row">
                  <span class="dc-bar-label">报销率</span>
                  <div class="dc-bar-track">
                    <div class="dc-bar-fill reimburse" :style="{ width: getReimburseRate(ev) + '%' }"></div>
                  </div>
                  <span class="dc-bar-val reimburse-val">{{ getReimburseRate(ev) }}%</span>
                </div>
                <div class="dc-meta">
                  <span class="dc-meta-tag">🧾 {{ ev.invoice_count || 0 }} 发票</span>
                  <span class="dc-meta-tag">🛒 {{ ev.purchase_record_count || 0 }} 购物</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>


      <!-- Quick Actions -->
      <div class="quick-actions">
        <NuxtLink to="/purchases" class="action-card">
          <div class="action-icon-ring purple">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
          </div>
          <span>购买记录</span>
        </NuxtLink>
        <NuxtLink to="/events/create" class="action-card">
          <div class="action-icon-ring green">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </div>
          <span>新建项目</span>
        </NuxtLink>
        <NuxtLink v-if="canManageUsers" to="/users" class="action-card">
          <div class="action-icon-ring blue">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <span>人员管理</span>
        </NuxtLink>
        <NuxtLink v-if="canManageInvitationCodes" to="/invitation-codes" class="action-card">
          <div class="action-icon-ring amber">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          </div>
          <span>邀请码</span>
        </NuxtLink>
      </div>

      <!-- User Ranking Section -->
      <div v-if="hasData" ref="rankingSectionRef" class="ranking-section">
        <div class="section-card">
          <div class="section-header">
            <h3>🏆 用户消费排名</h3>
            <div class="ranking-controls">
              <select v-model="rankingEventFilter" class="ranking-filter">
                <option :value="null">所有项目合计</option>
                <option v-for="ev in eventStore.events" :key="ev.event_id" :value="ev.event_id">{{ ev.event_name }}</option>
              </select>
            </div>
          </div>
          <div v-if="rankingLoading" class="ranking-skeleton">
            <div v-for="i in 5" :key="'rk'+i" class="ranking-sk-item">
              <div class="sk-circle-sm"></div>
              <div class="sk-line long"></div>
              <div class="sk-line short"></div>
            </div>
          </div>
          <div v-else-if="rankingData.length === 0" class="ranking-empty">
            <p>暂无消费记录数据</p>
          </div>
          <div v-else class="ranking-list">
            <div v-for="(item, idx) in rankingData" :key="item.user_id" class="ranking-item">
              <span class="rank-number" :class="{ 'top1': idx === 0, 'top2': idx === 1, 'top3': idx === 2 }">
                <template v-if="idx === 0">🥇</template>
                <template v-else-if="idx === 1">🥈</template>
                <template v-else-if="idx === 2">🥉</template>
                <template v-else>{{ idx + 1 }}</template>
              </span>
              <div class="rank-avatar" :class="{ 'gold': idx === 0, 'silver': idx === 1, 'bronze': idx === 2 }">{{ (item.real_name || '?').charAt(0).toUpperCase() }}</div>
              <div class="rank-info">
                <span class="rank-name">{{ item.real_name }}</span>
                <span class="rank-meta">{{ item.record_count }} 条记录</span>
              </div>
              <div class="rank-amount-col">
                <span class="rank-amount">¥{{ formatMoney(item.total_amount) }}</span>
                <div class="rank-bar-bg">
                  <div class="rank-bar-fill" :style="{ width: maxAmount > 0 ? (item.total_amount / maxAmount * 100) + '%' : '0%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useEventStore } from '~/stores/eventStore'

definePageMeta({ layout: 'default' })

const { $api } = useNuxtApp()
const eventStore = useEventStore()
const currentUser = ref<any>(null)
const loading = computed(() => eventStore.loading)
const hasData = computed(() => eventStore.events.length > 0)
const isDataStale = computed(() => eventStore.isStale)

const canManageUsers = computed(() =>
  ['admin', 'teacher', 'student_admin'].includes(currentUser.value?.user_type)
)
const canManageInvitationCodes = computed(() =>
  ['admin', 'teacher', 'student_admin'].includes(currentUser.value?.user_type)
)

// Project selector
const selectedEventId = ref<number | null>(null)
const selectedEvent = computed(() =>
  selectedEventId.value ? eventStore.events.find(e => e.event_id === selectedEventId.value) || null : null
)

// Stats
const stats = computed(() => eventStore.fullStats)

const lastUpdatedText = computed(() => {
  if (!eventStore.lastFetchTime) return ''
  return '更新于 ' + new Date(eventStore.lastFetchTime).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

// Stat cards config - per-project or aggregate
const statCards = computed(() => {
  if (selectedEvent.value) {
    const ev = selectedEvent.value
    const s: any = {
      totalEvents: 1,
      ongoingEvents: ev.status === 'ongoing' ? 1 : 0,
      totalRecords: (ev.invoice_count || 0) + (ev.purchase_record_count || 0),
      invoiceCount: ev.invoice_count || 0,
      purchaseCount: ev.purchase_record_count || 0,
      totalAmount: Number(ev.spent_amount || 0),
      totalBudget: Number(ev.total_budget || 0),
      invoiceTotal: Number(ev.invoice_total_amount || 0),
      reimbursedAmount: Number(ev.reimbursed_amount || 0),
      budgetUsageRate: Number(ev.total_budget || 0) > 0 ? ((Number(ev.spent_amount || 0) / Number(ev.total_budget || 0)) * 100).toFixed(1) : '0.0',
      reimburseRate: Number(ev.invoice_total_amount || 0) > 0 ? ((Number(ev.reimbursed_amount || 0) / Number(ev.invoice_total_amount || 0)) * 100).toFixed(1) : '0.0',
      pendingReimburse: Math.max(0, Number(ev.invoice_total_amount || 0) - Number(ev.reimbursed_amount || 0)),
    }
    return [
      { key: 'events', variant: 'indigo', value: s.totalEvents, label: '选中项目', sub: `${ev.status === 'ongoing' ? '进行中' : ev.status === 'completed' ? '已完成' : '已归档'}`, subTrend: '', link: `/purchases/${ev.event_id}`, prefix: '', displayValue: ev.event_name.length > 10 ? ev.event_name.slice(0, 10) + '…' : ev.event_name },
      { key: 'records', variant: 'emerald', value: s.totalRecords, label: '记录总数', sub: `发票 ${s.invoiceCount} | 购物 ${s.purchaseCount}`, subTrend: '', link: `/purchases/${ev.event_id}`, prefix: '', displayValue: String(s.totalRecords) },
      { key: 'spending', variant: 'amber', value: s.totalAmount, label: '支出金额', sub: `预算使用率 ${s.budgetUsageRate}%`, subTrend: Number(s.budgetUsageRate) > 80 ? 'warn' : '', link: '', prefix: '¥', displayValue: fmt(s.totalAmount) },
      { key: 'invoice', variant: 'sky', value: s.invoiceTotal, label: '发票总额', sub: `待报销 ¥${fmt(s.pendingReimburse)}`, subTrend: '', link: '', prefix: '¥', displayValue: fmt(s.invoiceTotal) },
      { key: 'reimburse', variant: 'violet', value: s.reimbursedAmount, label: '已报销金额', sub: `报销率 ${s.reimburseRate}%`, subTrend: Number(s.reimburseRate) > 70 ? 'up' : '', link: '', prefix: '¥', displayValue: fmt(s.reimbursedAmount) },
    ]
  }
  const s = stats.value
  return [
    { key: 'events', variant: 'indigo', value: s.totalEvents, label: '项目总数', sub: `${s.ongoingEvents} 个进行中`, subTrend: '', link: '/projects', prefix: '', displayValue: String(s.totalEvents) },
    { key: 'records', variant: 'emerald', value: s.totalRecords, label: '记录总数', sub: `发票 ${s.invoiceCount} | 购物 ${s.purchaseCount}`, subTrend: '', link: '/purchases', prefix: '', displayValue: String(s.totalRecords) },
    { key: 'spending', variant: 'amber', value: s.totalAmount, label: '总支出金额', sub: `预算使用率 ${s.budgetUsageRate}%`, subTrend: Number(s.budgetUsageRate) > 80 ? 'warn' : '', link: '', prefix: '¥', displayValue: fmt(s.totalAmount) },
    { key: 'invoice', variant: 'sky', value: s.invoiceTotal, label: '发票总额', sub: `待报销 ¥${fmt(s.pendingReimburse)}`, subTrend: '', link: '', prefix: '¥', displayValue: fmt(s.invoiceTotal) },
    { key: 'reimburse', variant: 'violet', value: s.reimbursedAmount, label: '已报销金额', sub: `报销率 ${s.reimburseRate}%`, subTrend: Number(s.reimburseRate) > 70 ? 'up' : '', link: '', prefix: '¥', displayValue: fmt(s.reimbursedAmount) },
  ]
})

// Helpers
function fmt(v: any): string {
  return parseFloat(String(v || 0)).toFixed(2)
}
function formatMoney(v: any): string {
  return parseFloat(String(v || 0)).toFixed(2)
}
function getEventRemaining(event: any): number {
  return Number(event.total_budget || 0) - Number(event.spent_amount || 0)
}

function remainingClass(event: any): string {
  const pct = budgetUsagePercent(event)
  if (pct > 90) return 'danger'
  if (pct > 70) return 'warn'
  return 'ok'
}

function progressClass(event: any): string {
  return remainingClass(event)
}

function accentClass(event: any): string {
  return 'accent-' + remainingClass(event)
}

function budgetUsagePercent(event: any): number {
  const budget = Number(event.total_budget || 0)
  const spent = Number(event.spent_amount || 0)
  if (budget <= 0) return 0
  return Math.min(100, (spent / budget) * 100)
}

function getReimburseRate(event: any): number {
  const invoiceTotal = Number(event.invoice_total_amount || 0)
  const reimbursed = Number(event.reimbursed_amount || 0)
  if (invoiceTotal <= 0) return 0
  return Math.min(100, Math.round((reimbursed / invoiceTotal) * 100))
}

// Ranking
const rankingEventFilter = ref<number | null>(null)
const rankingData = ref<any[]>([])
const rankingLoading = ref(false)
const rankingVisible = ref(false)
const rankingSectionRef = ref<HTMLElement | null>(null)

const maxAmount = computed(() => {
  if (rankingData.value.length === 0) return 1
  return Math.max(...rankingData.value.map(r => r.total_amount || 0))
})

async function fetchRanking() {
  rankingLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const params: any = {}
    if (rankingEventFilter.value) params.event_id = rankingEventFilter.value
    const resp = await $api.get('/events/stats/user-summary', {
      params,
      headers: { Authorization: `Bearer ${token}` }
    })
    if (resp.data.code === 200) {
      rankingData.value = resp.data.data.rankings || []
    }
  } catch (e) {
    console.error('Failed to fetch ranking:', e)
  } finally {
    rankingLoading.value = false
  }
}

watch(rankingEventFilter, () => {
  if (rankingVisible.value) fetchRanking()
})

async function refreshData() {
  await eventStore.invalidateAndRefresh({ pageSize: 100 })
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) { navigateTo('/login'); return }
  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  await eventStore.ensureLoaded()

  // Lazy load ranking when visible
  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      rankingVisible.value = true
      fetchRanking()
      observer.disconnect()
    }
  }, { rootMargin: '200px' })
  if (rankingSectionRef.value) observer.observe(rankingSectionRef.value)
})
</script>

<style scoped>
/* ===== DESIGN TOKENS ===== */
.dashboard {
  --dash-bg: #f2f4f7;
  --card-bg: #ffffff;
  --text-1: #0f172a;
  --text-2: #475569;
  --text-3: #94a3b8;
  --border: #e8ecf1;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
  --shadow-hover: 0 8px 25px rgba(0,0,0,0.08);
  --radius: 14px;
  --radius-sm: 10px;
  max-width: 1320px;
  margin: 0 auto;
}

/* ===== HEADER ===== */
.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.75rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.header-left { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.header-right { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.project-selector {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.85rem;
  color: var(--text-1);
  background: var(--card-bg);
  cursor: pointer;
  min-height: 44px;
  max-width: 240px;
  outline: none;
  transition: border-color 0.2s;
}
.project-selector:focus { border-color: #6366f1; }
.page-title {
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--text-1);
  margin: 0;
  letter-spacing: -0.02em;
}
.last-updated {
  display: flex; align-items: center; gap: 5px;
  font-size: 0.78rem; color: var(--text-3);
}
.stale-badge {
  font-size: 0.72rem;
  background: #fef3c7; color: #92400e;
  padding: 2px 8px; border-radius: 10px; font-weight: 500;
}
.refresh-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.85rem; color: var(--text-2);
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}
.refresh-btn:hover { background: #f8fafc; border-color: #cbd5e1; }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.refresh-btn.spinning svg { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== SKELETON ===== */
.skeleton {
  animation: shim 1.6s ease-in-out infinite;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  pointer-events: none;
}
@keyframes shim { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.stat-card.skeleton {
  display: flex; align-items: center; gap: 1rem; padding: 1.5rem;
  border-radius: var(--radius); min-height: 90px;
}
.sk-circle { width: 44px; height: 44px; border-radius: 50%; background: #e2e8f0; flex-shrink: 0; }
.sk-lines { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.sk-line { height: 12px; background: #e2e8f0; border-radius: 4px; }
.sk-line.short { width: 45%; }
.sk-line.long { width: 75%; }

/* ===== EMPTY STATE ===== */
.empty-state {
  text-align: center; padding: 4rem 2rem;
  background: var(--card-bg); border-radius: var(--radius);
  box-shadow: var(--shadow-card);
}
.empty-illustration { margin-bottom: 1.5rem; }
.empty-state h2 { font-size: 1.4rem; color: var(--text-1); margin: 0 0 0.5rem; }
.empty-state p { color: var(--text-2); margin: 0 0 2rem; font-size: 0.95rem; }
.empty-actions { display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap; }
.btn-primary, .btn-secondary {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 22px; border-radius: 8px;
  font-size: 0.9rem; font-weight: 600; text-decoration: none;
  transition: all 0.2s;
}
.btn-primary { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(99,102,241,0.35); }
.btn-secondary { background: #f1f5f9; color: var(--text-2); border: 1px solid var(--border); }
.btn-secondary:hover { background: #e2e8f0; }

/* ===== STAT CARDS ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.stat-card {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 1.35rem 1.25rem;
  display: flex; align-items: center; gap: 1rem;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
  transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
  position: relative; overflow: hidden;
}
.stat-card::before {
  content: ''; position: absolute;
  top: 0; left: 0; width: 100%; height: 3px;
  opacity: 0; transition: opacity 0.25s;
}
.stat-card.indigo::before { background: #6366f1; }
.stat-card.emerald::before { background: #10b981; }
.stat-card.amber::before  { background: #f59e0b; }
.stat-card.sky::before    { background: #3b82f6; }
.stat-card.violet::before { background: #8b5cf6; }
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}
.stat-card:hover::before { opacity: 1; }
.stat-icon-box {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.stat-card.indigo .stat-icon-box { background: #eef2ff; color: #6366f1; }
.stat-card.emerald .stat-icon-box { background: #ecfdf5; color: #10b981; }
.stat-card.amber .stat-icon-box  { background: #fffbeb; color: #f59e0b; }
.stat-card.sky .stat-icon-box    { background: #eff6ff; color: #3b82f6; }
.stat-card.violet .stat-icon-box { background: #f5f3ff; color: #8b5cf6; }

.stat-content { min-width: 0; }
.stat-value {
  font-size: 1.55rem; font-weight: 700; color: var(--text-1);
  letter-spacing: -0.02em; line-height: 1.2;
}
.stat-value.value-sm { font-size: 1.2rem; }
.stat-label { font-size: 0.82rem; color: var(--text-2); margin-top: 2px; }
.stat-sub { font-size: 0.73rem; color: var(--text-3); margin-top: 4px; }
.stat-sub .warn { color: #ef4444; }
.stat-sub .up { color: #10b981; }

/* ===== DONUT ===== */
.donut-arc { transition: stroke-dashoffset 0.8s cubic-bezier(0.34,1.56,0.64,1); }

.section-card {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 1.25rem;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
}
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.section-header h3 { font-size: 0.95rem; font-weight: 600; color: var(--text-1); margin: 0; }

/* ===== QUICK ACTIONS ===== */
.quick-actions {
  display: flex; gap: 0.75rem; flex-wrap: wrap;
}
.action-card {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  text-decoration: none; font-size: 0.85rem; font-weight: 500; color: var(--text-2);
  transition: all 0.2s;
  box-shadow: var(--shadow-card);
}
.action-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
  border-color: #cbd5e1;
}
.action-icon-ring {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
}
.action-icon-ring.purple { background: #eef2ff; color: #6366f1; }
.action-icon-ring.green  { background: #ecfdf5; color: #10b981; }
.action-icon-ring.blue   { background: #eff6ff; color: #3b82f6; }
.action-icon-ring.amber  { background: #fffbeb; color: #f59e0b; }

/* ===== PER-PROJECT DONUT CARDS ===== */
.project-donuts-section {
  margin-bottom: 1.25rem;
}
.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-1);
  margin: 0 0 0.75rem;
}
.donut-cards-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Card */
.donut-card {
  position: relative;
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 1.1rem 1.35rem 1.1rem 1.1rem;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
  border-left: 4px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
  overflow: hidden;
}
.donut-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius);
  background: radial-gradient(ellipse at 0% 50%, rgba(99,102,241,0.03) 0%, transparent 60%);
  pointer-events: none;
}
.donut-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
  border-left-width: 5px;
}
.donut-card.selected {
  border-color: #cbd5e1;
  border-left-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99,102,241,0.10), var(--shadow-card);
}
/* Accent border colors */
.donut-card.accent-ok     { border-left-color: #6366f1; }
.donut-card.accent-warn   { border-left-color: #f59e0b; }
.donut-card.accent-danger { border-left-color: #ef4444; }
.donut-card.accent-ok:hover     { border-left-color: #4f46e5; }
.donut-card.accent-warn:hover   { border-left-color: #d97706; }
.donut-card.accent-danger:hover { border-left-color: #dc2626; }

/* Card header */
.dc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 0.7rem;
}
.dc-status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dc-status-dot.ongoing   { background: #10b981; box-shadow: 0 0 6px rgba(16,185,129,0.4); }
.dc-status-dot.completed { background: #94a3b8; }
.dc-status-dot.archived  { background: #cbd5e1; }
.dc-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-1);
  margin: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dc-leader {
  font-size: 0.7rem;
  color: var(--text-3);
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}

/* Card body */
.dc-body {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}
.dc-donut {
  flex-shrink: 0;
}
.dc-donut svg {
  display: block;
}
.dc-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* 4-column amounts grid */
.dc-amounts {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.6rem;
}
.dc-amt {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.dc-amt-label {
  font-size: 0.66rem;
  color: var(--text-3);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.dc-amt-value {
  font-size: 0.88rem;
  font-weight: 650;
  color: var(--text-1);
  letter-spacing: -0.01em;
}
.dc-amt-value.spent   { color: #6366f1; }
.dc-amt-value.invoice { color: #3b82f6; }
.dc-amt-value.ok      { color: #059669; }
.dc-amt-value.warn    { color: #d97706; }
.dc-amt-value.danger  { color: #dc2626; }

/* Progress bar rows */
.dc-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dc-bar-label {
  font-size: 0.7rem;
  color: var(--text-3);
  min-width: 48px;
  font-weight: 500;
}
.dc-bar-track {
  flex: 1;
  height: 5px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
  min-width: 50px;
}
.dc-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.7s cubic-bezier(0.34,1.56,0.64,1);
}
.dc-bar-fill.ok     { background: linear-gradient(90deg, #6366f1, #818cf8); }
.dc-bar-fill.warn   { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.dc-bar-fill.danger { background: linear-gradient(90deg, #ef4444, #f87171); }
.dc-bar-fill.reimburse { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.dc-bar-val {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-2);
  min-width: 30px;
  text-align: right;
}
.dc-bar-val.ok     { color: #059669; }
.dc-bar-val.warn   { color: #d97706; }
.dc-bar-val.danger { color: #dc2626; }
.dc-bar-val.reimburse-val { color: #3b82f6; }

/* Meta tags */
.dc-meta {
  display: flex;
  gap: 8px;
}
.dc-meta-tag {
  font-size: 0.7rem;
  color: var(--text-3);
  background: #f8fafc;
  padding: 3px 8px;
  border-radius: 5px;
  border: 1px solid #f1f5f9;
}

/* ===== RANKING SECTION ===== */
.ranking-section {
  margin-bottom: 1.25rem;
}
.ranking-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.ranking-filter {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.8rem;
  color: var(--text-1);
  background: var(--card-bg);
  cursor: pointer;
  min-height: 36px;
  outline: none;
}
.ranking-filter:focus { border-color: #6366f1; }

.ranking-skeleton {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
}
.ranking-sk-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.5rem;
}
.sk-circle-sm {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: #e2e8f0;
  flex-shrink: 0;
}
.ranking-empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-3);
  font-size: 0.85rem;
}
.ranking-list {
  display: flex;
  flex-direction: column;
}
.ranking-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 0.6rem;
  border-bottom: 1px solid #f8fafc;
  transition: background 0.2s;
  border-radius: 8px;
}
.ranking-item:last-child { border-bottom: none; }
.ranking-item:hover { background: #fafbfd; }
.rank-number {
  width: 28px;
  text-align: center;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-3);
  flex-shrink: 0;
}
.rank-number.top1, .rank-number.top2, .rank-number.top3 {
  font-size: 1.1rem;
}
.rank-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #f1f5f9;
  color: var(--text-2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
}
.rank-avatar.gold { background: linear-gradient(135deg, #fef3c7, #fde68a); color: #92400e; }
.rank-avatar.silver { background: linear-gradient(135deg, #f1f5f9, #e2e8f0); color: #475569; }
.rank-avatar.bronze { background: linear-gradient(135deg, #fef2f2, #fed7aa); color: #9a3412; }
.rank-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rank-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-1);
}
.rank-meta {
  font-size: 0.72rem;
  color: var(--text-3);
}
.rank-amount-col {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  min-width: 100px;
}
.rank-amount {
  font-size: 0.88rem;
  font-weight: 700;
  color: #6366f1;
}
.rank-bar-bg {
  width: 80px;
  height: 4px;
  background: #f1f5f9;
  border-radius: 2px;
  overflow: hidden;
}
.rank-bar-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  transition: width 0.6s ease;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
  .dash-header { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
  .header-right { width: 100%; }
  .project-selector { max-width: none; flex: 1; }
  .refresh-btn { align-self: stretch; justify-content: center; min-height: 44px; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .stat-value { font-size: 1.3rem; }
  .quick-actions { gap: 0.5rem; }
  .action-card { flex: 1; min-width: calc(50% - 0.5rem); justify-content: center; min-height: 44px; }
  .ranking-controls { flex-wrap: wrap; }
  .rank-amount-col { min-width: 80px; }
  .rank-bar-bg { width: 60px; }
}
@media (max-width: 480px) {
  .page-title { font-size: 1.3rem; }
  .stats-grid { grid-template-columns: 1fr; }
  .stat-card { padding: 1rem; }
  .donut-card { padding: 1rem; border-left-width: 3px; }
  .dc-body { flex-direction: column; align-items: center; }
  .dc-info { width: 100%; }
  .dc-amounts { grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }
  .dc-bar-row { width: 100%; }
  .dc-meta { justify-content: center; }
  .empty-actions { flex-direction: column; }
  .empty-state { padding: 2.5rem 1.5rem; }
  .empty-state h2 { font-size: 1.15rem; }
  .action-card { min-width: 100%; }
  .ranking-item { flex-wrap: wrap; gap: 0.5rem; }
  .rank-amount-col { min-width: 100%; flex-direction: row; align-items: center; gap: 8px; }
  .rank-bar-bg { flex: 1; }
  .header-right { flex-direction: column; align-items: stretch; }
  .project-selector { max-width: none; width: 100%; }
}
</style>
