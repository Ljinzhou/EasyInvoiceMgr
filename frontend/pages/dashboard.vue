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
      <button class="refresh-btn" :class="{ spinning: loading }" @click="refreshData" :disabled="loading">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
        <span>{{ loading ? '刷新中...' : '刷新' }}</span>
      </button>
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
      <div class="charts-row">
        <div class="chart-card skeleton" style="min-height:260px"></div>
        <div class="chart-card skeleton" style="min-height:260px"></div>
      </div>
      <div class="bottom-row">
        <div class="section-card skeleton" style="min-height:320px"></div>
        <div class="section-card skeleton" style="min-height:320px"></div>
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

      <!-- Charts Row -->
      <div class="charts-row">
        <!-- Spending Bar Chart -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>各项目支出对比</h3>
            <span class="chart-hint" v-if="spendingChartData.length === 0">暂无数据</span>
          </div>
          <div class="chart-body" v-if="spendingChartData.length > 0">
            <svg class="bar-chart" :viewBox="`0 0 ${barChartWidth} 180`" preserveAspectRatio="xMidYMid meet">
              <!-- Grid lines -->
              <line v-for="i in 4" :key="'gl'+i" :x1="40" :y1="i*35" :x2="barChartWidth-10" :y2="i*35" stroke="#f1f5f9" stroke-width="1"/>
              <!-- Bars -->
              <g v-for="(item, idx) in spendingChartData" :key="item.event_id">
                <rect
                  :x="barX(idx)"
                  :y="barY(item.ratio)"
                  :width="barWidth"
                  :height="barH(item.ratio)"
                  :rx="4"
                  :fill="barColor(idx)"
                  class="bar-rect"
                  style="transition: height 0.6s cubic-bezier(0.34,1.56,0.64,1), y 0.6s cubic-bezier(0.34,1.56,0.64,1)"
                >
                  <title>{{ item.name }}: ¥{{ fmt(item.spent_amount) }}</title>
                </rect>
                <text :x="barX(idx) + barWidth/2" :y="barY(item.ratio) - 6" text-anchor="middle" font-size="11" fill="#64748b" font-weight="500">
                  ¥{{ fmtK(item.spent_amount) }}
                </text>
                <text :x="barX(idx) + barWidth/2" :y="174" text-anchor="middle" font-size="10" fill="#94a3b8" class="bar-label">
                  {{ truncate(item.name, 4) }}
                </text>
              </g>
            </svg>
          </div>
          <div v-else class="chart-empty">
            <p>创建项目并添加购买记录后，这里将展示支出对比图</p>
          </div>
        </div>

        <!-- Budget Donut + Gauges -->
        <div class="chart-card">
          <div class="chart-header"><h3>预算与报销概览</h3></div>
          <div class="chart-body donut-body">
            <div class="donut-group">
              <svg viewBox="0 0 120 120" width="120" height="120">
                <circle cx="60" cy="60" r="48" fill="none" stroke="#f1f5f9" stroke-width="12"/>
                <circle
                  cx="60" cy="60" r="48" fill="none"
                  :stroke="stats.budgetUsageRate > 90 ? '#ef4444' : 'url(#donutGrad)'"
                  stroke-width="12"
                  stroke-linecap="round"
                  :stroke-dasharray="2 * Math.PI * 48"
                  :stroke-dashoffset="2 * Math.PI * 48 * (1 - stats.budgetUsageRate / 100)"
                  transform="rotate(-90 60 60)"
                  class="donut-arc"
                />
                <defs>
                  <linearGradient id="donutGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#6366f1"/>
                    <stop offset="100%" stop-color="#8b5cf6"/>
                  </linearGradient>
                </defs>
                <text x="60" y="56" text-anchor="middle" font-size="22" font-weight="700" fill="#1e293b">{{ stats.budgetUsageRate }}%</text>
                <text x="60" y="74" text-anchor="middle" font-size="9" fill="#94a3b8">预算使用率</text>
              </svg>
              <span class="donut-detail">已用 ¥{{ fmt(stats.totalAmount) }} / 总计 ¥{{ fmt(stats.totalBudget) }}</span>
            </div>
            <div class="gauge-stack">
              <div class="gauge-item">
                <div class="gauge-label"><span class="gdot blue"></span> 报销率</div>
                <div class="gauge-track"><div class="gauge-fill blue" :style="{ width: stats.reimburseRate + '%' }"></div></div>
                <span class="gauge-val">{{ stats.reimburseRate }}%</span>
              </div>
              <div class="gauge-item">
                <div class="gauge-label"><span class="gdot amber"></span> 进行中项目</div>
                <div class="gauge-track"><div class="gauge-fill amber" :style="{ width: ongoingRatio + '%' }"></div></div>
                <span class="gauge-val">{{ stats.ongoingEvents }}/{{ stats.totalEvents }}</span>
              </div>
              <div class="gauge-item">
                <div class="gauge-label"><span class="gdot green"></span> 待报销</div>
                <span class="gauge-val right">¥{{ fmt(stats.pendingReimburse) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Row: Projects -->
      <div class="bottom-row">
        <!-- Recent Projects -->
        <div class="section-card">
          <div class="section-header">
            <h3>最近项目</h3>
            <NuxtLink to="/projects" class="see-all">查看全部 &rarr;</NuxtLink>
          </div>
          <div class="project-list">
            <div
              v-for="event in recentEvents"
              :key="event.event_id"
              class="project-item"
              @click="navigateTo(`/purchases/${event.event_id}`)"
            >
              <!-- 项目头部：名称 + 状态 -->
              <div class="project-row-top">
                <div class="project-main">
                  <div class="project-status-dot" :class="event.status" :title="statusMap[event.status]"></div>
                  <div class="project-info">
                    <div class="project-name">{{ event.event_name }}</div>
                    <div class="project-meta">
                      <span v-if="event.leader_name" class="project-leader">{{ event.leader_name }}</span>
                      <span class="project-records-inline">
                        <span>🧾 {{ event.invoice_count || 0 }}</span>
                        <span>🛒 {{ event.purchase_record_count || 0 }}</span>
                      </span>
                    </div>
                  </div>
                </div>
                <!-- 剩余金额大字 -->
                <div class="project-remaining-badge" :class="remainingClass(event)">
                  <span class="remaining-label">剩余</span>
                  <span class="remaining-value">¥{{ fmt(getEventRemaining(event)) }}</span>
                </div>
              </div>

              <!-- 预算条 + 三栏数字 -->
              <div class="project-budget-section">
                <div class="budget-bar-track">
                  <div
                    class="budget-bar-fill"
                    :class="progressClass(event)"
                    :style="{ width: Math.min(100, budgetUsagePercent(event)) + '%' }"
                  ></div>
                </div>
                <div class="budget-three-cols">
                  <div class="budget-col">
                    <span class="col-label">总预算</span>
                    <span class="col-value">¥{{ fmt(event.total_budget) }}</span>
                  </div>
                  <div class="budget-col">
                    <span class="col-label">已用</span>
                    <span class="col-value spent">¥{{ fmt(event.spent_amount) }}</span>
                  </div>
                  <div class="budget-col">
                    <span class="col-label">使用率</span>
                    <span class="col-value" :class="progressClass(event)">{{ budgetUsagePercent(event).toFixed(1) }}%</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="recentEvents.length === 0" class="list-empty">暂无项目</div>
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEventStore } from '~/stores/eventStore'

definePageMeta({ layout: 'default' })

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

// Stats
const stats = computed(() => eventStore.fullStats)
const recentEvents = computed(() => eventStore.events.slice(0, 5))

const statusMap: Record<string, string> = { ongoing: '进行中', completed: '已完成', archived: '已归档' }

const lastUpdatedText = computed(() => {
  if (!eventStore.lastFetchTime) return ''
  return '更新于 ' + new Date(eventStore.lastFetchTime).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

const ongoingRatio = computed(() => {
  if (stats.value.totalEvents === 0) return 0
  return Math.round((stats.value.ongoingEvents / stats.value.totalEvents) * 100)
})

// Stat cards config
const statCards = computed(() => {
  const s = stats.value
  return [
    { key: 'events', variant: 'indigo', value: s.totalEvents, label: '项目总数', sub: `${s.ongoingEvents} 个进行中`, subTrend: '', link: '/projects', prefix: '', displayValue: String(s.totalEvents) },
    { key: 'records', variant: 'emerald', value: s.totalRecords, label: '记录总数', sub: `发票 ${s.invoiceCount} | 购物 ${s.purchaseCount}`, subTrend: '', link: '/purchases', prefix: '', displayValue: String(s.totalRecords) },
    { key: 'spending', variant: 'amber', value: s.totalAmount, label: '总支出金额', sub: `预算使用率 ${s.budgetUsageRate}%`, subTrend: s.budgetUsageRate > 80 ? 'warn' : '', link: '', prefix: '¥', displayValue: fmt(s.totalAmount) },
    { key: 'invoice', variant: 'sky', value: s.invoiceTotal, label: '发票总额', sub: `待报销 ¥${fmt(s.pendingReimburse)}`, subTrend: '', link: '', prefix: '¥', displayValue: fmt(s.invoiceTotal) },
    { key: 'reimburse', variant: 'violet', value: s.reimbursedAmount, label: '已报销金额', sub: `报销率 ${s.reimburseRate}%`, subTrend: s.reimburseRate > 70 ? 'up' : '', link: '', prefix: '¥', displayValue: fmt(s.reimbursedAmount) },
  ]
})

// Spending bar chart data
const spendingChartData = computed(() => {
  return eventStore.events
    .filter(e => (e.spent_amount || 0) > 0)
    .sort((a, b) => (b.spent_amount || 0) - (a.spent_amount || 0))
    .slice(0, 8)
    .map(e => ({
      event_id: e.event_id,
      name: e.event_name,
      spent_amount: e.spent_amount || 0,
      ratio: 0,
    }))
    .map((item, _, arr) => {
      const max = arr[0]?.spent_amount || 1
      return { ...item, ratio: max > 0 ? item.spent_amount / max : 0 }
    })
})

const barCount = computed(() => Math.max(spendingChartData.value.length, 1))
const barChartWidth = computed(() => Math.max(300, barCount.value * 80 + 60))
const barGap = computed(() => Math.min(16, 120 / barCount.value))
const barWidth = computed(() => (barChartWidth.value - 60) / barCount.value - barGap.value)

function barX(idx: number) { return 40 + idx * (barWidth.value + barGap.value) }
function barY(ratio: number) { return 140 - ratio * 105 }
function barH(ratio: number) { return Math.max(ratio * 105, 3) }

const barColors = ['#6366f1', '#8b5cf6', '#a78bfa', '#7c3aed', '#6d28d9', '#5b21b6', '#4c1d95', '#3b0764']
function barColor(idx: number) { return barColors[idx % barColors.length] }

// Helpers
function fmt(v: any): string {
  return parseFloat(String(v || 0)).toFixed(2)
}
function fmtK(v: any): string {
  const n = parseFloat(String(v || 0))
  return n >= 10000 ? (n / 10000).toFixed(1) + 'w' : n.toFixed(0)
}
function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}
function progressClass(event: any): string {
  const pct = (event.spent_amount / (event.total_budget || 1)) * 100
  if (pct > 90) return 'danger'
  if (pct > 70) return 'warn'
  return 'ok'
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

function budgetUsagePercent(event: any): number {
  const budget = Number(event.total_budget || 0)
  const spent = Number(event.spent_amount || 0)
  if (budget <= 0) return 0
  return Math.min(100, (spent / budget) * 100)
}

async function refreshData() {
  await eventStore.invalidateAndRefresh({ pageSize: 100 })
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) { navigateTo('/login'); return }
  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  await eventStore.ensureLoaded()
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
}
.header-left { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
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

/* ===== CHARTS ROW ===== */
.charts-row {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.chart-card {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 1.25rem;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
}
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.chart-header h3 { font-size: 0.95rem; font-weight: 600; color: var(--text-1); margin: 0; }
.chart-hint { font-size: 0.75rem; color: var(--text-3); }
.chart-body { overflow-x: auto; }
.chart-empty { text-align: center; padding: 2rem; color: var(--text-3); font-size: 0.85rem; }

.bar-chart { width: 100%; min-width: 280px; height: auto; }
.bar-label { transition: opacity 0.3s; }

/* Donut */
.donut-body { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.donut-group { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.donut-detail { font-size: 0.73rem; color: var(--text-3); text-align: center; }
.donut-arc { transition: stroke-dashoffset 0.8s cubic-bezier(0.34,1.56,0.64,1); }

.gauge-stack { flex: 1; display: flex; flex-direction: column; gap: 1rem; min-width: 140px; }
.gauge-item { display: flex; align-items: center; gap: 8px; }
.gauge-label { font-size: 0.78rem; color: var(--text-2); display: flex; align-items: center; gap: 6px; min-width: 85px; }
.gdot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.gdot.blue  { background: #6366f1; }
.gdot.amber { background: #f59e0b; }
.gdot.green { background: #10b981; }
.gauge-track { flex: 1; height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden; min-width: 60px; }
.gauge-fill { height: 100%; border-radius: 3px; transition: width 0.8s cubic-bezier(0.34,1.56,0.64,1); }
.gauge-fill.blue  { background: #6366f1; }
.gauge-fill.amber { background: #f59e0b; }
.gauge-val { font-size: 0.78rem; font-weight: 600; color: var(--text-1); min-width: 36px; text-align: right; }
.gauge-val.right { min-width: 80px; }

/* ===== BOTTOM ROW ===== */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.section-card {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 1.25rem;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
}
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.section-header h3 { font-size: 0.95rem; font-weight: 600; color: var(--text-1); margin: 0; }
.see-all { font-size: 0.8rem; color: #6366f1; text-decoration: none; font-weight: 500; }
.see-all:hover { text-decoration: underline; }

/* Project List */
.project-list { display: flex; flex-direction: column; gap: 0; }
.project-item {
  padding: 1rem 0.75rem; border-bottom: 1px solid #f1f5f9;
  cursor: pointer; transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
  border-radius: 10px;
}
.project-item:last-child { border-bottom: none; }
.project-item:hover {
  background: linear-gradient(135deg, #f8faff 0%, #f5f3ff 100%);
  margin: 0 -0.75rem; padding-left: 1rem; padding-right: 1rem;
  border-bottom-color: transparent;
  transform: translateX(2px);
}

/* 项目头部行 */
.project-row-top {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 0.75rem;
}
.project-main { display: flex; align-items: flex-start; gap: 10px; flex: 1; min-width: 0; }
.project-status-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; margin-top: 5px; }
.project-status-dot.ongoing   { background: #10b981; box-shadow: 0 0 6px rgba(16,185,129,0.4); }
.project-status-dot.completed { background: #94a3b8; }
.project-status-dot.archived  { background: #cbd5e1; }
.project-name { font-size: 0.92rem; font-weight: 600; color: var(--text-1); line-height: 1.3; }
.project-meta { display: flex; gap: 8px; margin-top: 3px; font-size: 0.75rem; color: var(--text-3); align-items: center; }
.project-leader { background: #f1f5f9; padding: 1px 7px; border-radius: 4px; }
.project-records-inline { display: flex; gap: 8px; }

/* 剩余金额徽章 */
.project-remaining-badge {
  display: flex; flex-direction: column; align-items: flex-end;
  padding: 6px 12px; border-radius: 10px; flex-shrink: 0;
  min-width: 100px;
  transition: all 0.25s;
}
.project-remaining-badge.ok {
  background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
  border: 1px solid #bbf7d0;
}
.project-remaining-badge.warn {
  background: linear-gradient(135deg, #fffbeb 0%, #fefce8 100%);
  border: 1px solid #fde68a;
}
.project-remaining-badge.danger {
  background: linear-gradient(135deg, #fef2f2 0%, #fff1f2 100%);
  border: 1px solid #fecaca;
}
.remaining-label { font-size: 0.68rem; color: var(--text-3); font-weight: 500; letter-spacing: 0.03em; }
.remaining-value { font-size: 1.05rem; font-weight: 700; line-height: 1.3; }
.project-remaining-badge.ok .remaining-value { color: #059669; }
.project-remaining-badge.warn .remaining-value { color: #d97706; }
.project-remaining-badge.danger .remaining-value { color: #dc2626; }

/* 预算区域 */
.project-budget-section { padding-left: 19px; }
.budget-bar-track { height: 5px; background: #f1f5f9; border-radius: 3px; overflow: hidden; margin-bottom: 8px; }
.budget-bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s cubic-bezier(0.34,1.56,0.64,1); }
.budget-bar-fill.ok { background: linear-gradient(90deg, #6366f1, #8b5cf6); }
.budget-bar-fill.warn { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.budget-bar-fill.danger { background: linear-gradient(90deg, #ef4444, #f87171); }

.budget-three-cols {
  display: flex; gap: 1.5rem;
}
.budget-col { display: flex; flex-direction: column; gap: 1px; }
.col-label { font-size: 0.68rem; color: var(--text-3); font-weight: 500; letter-spacing: 0.03em; }
.col-value { font-size: 0.82rem; font-weight: 600; color: var(--text-1); }
.col-value.spent { color: #6366f1; }
.col-value.ok { color: #059669; }
.col-value.warn { color: #d97706; }
.col-value.danger { color: #dc2626; }

.list-empty { text-align: center; padding: 2rem; color: var(--text-3); font-size: 0.85rem; }

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

/* ===== RESPONSIVE ===== */
@media (max-width: 1024px) {
  .charts-row { grid-template-columns: 1fr; }
  .bottom-row { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .dash-header { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
  .refresh-btn { align-self: stretch; justify-content: center; min-height: 44px; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .stat-value { font-size: 1.3rem; }
  .donut-body { justify-content: center; }
  .quick-actions { gap: 0.5rem; }
  .action-card { flex: 1; min-width: calc(50% - 0.5rem); justify-content: center; min-height: 44px; }
}
@media (max-width: 480px) {
  .page-title { font-size: 1.3rem; }
  .stats-grid { grid-template-columns: 1fr; }
  .stat-card { padding: 1rem; }
  .project-row-top { flex-direction: column; gap: 0.5rem; }
  .project-remaining-badge { align-self: flex-start; flex-direction: row; gap: 6px; align-items: center; }
  .budget-three-cols { gap: 1rem; }
  .empty-actions { flex-direction: column; }
  .empty-state { padding: 2.5rem 1.5rem; }
  .empty-state h2 { font-size: 1.15rem; }
  .action-card { min-width: 100%; }
  .donut-body { flex-direction: column; align-items: center; }
  .gauge-stack { width: 100%; }
  .gauge-val.right { min-width: 60px; }
}
</style>
