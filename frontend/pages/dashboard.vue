<template>
  <div class="dashboard">
    <h1 class="page-title">总览面板</h1>
    
    <div class="stats-grid">
      <div class="stat-card primary">
        <div class="stat-icon">📁</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.totalEvents }}</div>
          <div class="stat-label">项目总数</div>
          <div class="stat-trend" v-if="stats.ongoingEvents > 0">{{ stats.ongoingEvents }} 个进行中</div>
        </div>
      </div>
      <div class="stat-card success">
        <div class="stat-icon">🛒</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.totalRecords }}</div>
          <div class="stat-label">记录总数</div>
          <div class="stat-trend">发票 {{ stats.invoiceCount }} | 购物 {{ stats.purchaseCount }}</div>
        </div>
      </div>
      <div class="stat-card warning">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <div class="stat-value">¥{{ formatMoney(stats.totalAmount) }}</div>
          <div class="stat-label">总支出金额</div>
          <div class="stat-trend">预算使用率 {{ stats.budgetUsageRate }}%</div>
        </div>
      </div>
      <div class="stat-card info">
        <div class="stat-icon">🧾</div>
        <div class="stat-content">
          <div class="stat-value">¥{{ formatMoney(stats.invoiceTotal) }}</div>
          <div class="stat-label">发票总额</div>
          <div class="stat-trend">待报销 ¥{{ formatMoney(stats.pendingReimburse) }}</div>
        </div>
      </div>
      <div class="stat-card accent">
        <div class="stat-icon">✅</div>
        <div class="stat-content">
          <div class="stat-value">¥{{ formatMoney(stats.reimbursedAmount) }}</div>
          <div class="stat-label">已报销金额</div>
          <div class="stat-trend">报销率 {{ stats.reimburseRate }}%</div>
        </div>
      </div>
    </div>

    <div class="recent-section">
      <h2 class="section-title">最近项目</h2>
      <div class="events-list">
        <div v-for="event in recentEvents" :key="event.event_id" class="event-item" @click="$router.push(`/purchases/${event.event_id}`)">
          <div class="event-info">
            <div class="event-name">{{ event.event_name }}</div>
            <div class="event-details">
              <span class="event-status" :class="event.status">{{ getStatusText(event.status) }}</span>
              <span class="event-category">{{ event.category || '未分类' }}</span>
              <span class="event-leader" v-if="event.leader_name">👤 {{ event.leader_name }}</span>
            </div>
            <div class="event-stats-row">
              <span>💰 已花: ¥{{ formatMoney(event.spent_amount || 0) }}</span>
              <span>📋 记录: {{ event.voucher_count || 0 }}</span>
              <span>🧾 发票: {{ event.invoice_count || 0 }}</span>
            </div>
          </div>
          <div class="event-budget">
            <div class="budget-label">预算 / 已用</div>
            <div class="budget-value">¥{{ formatMoney(event.total_budget || 0) }} / ¥{{ formatMoney(event.spent_amount || 0) }}</div>
            <div class="budget-bar">
              <div class="budget-fill" :style="{ width: getBudgetPercent(event) + '%' }"></div>
            </div>
          </div>
        </div>
        <div v-if="recentEvents.length === 0" class="empty-state">
          暂无项目数据
          <NuxtLink to="/events/create" class="create-link">创建第一个项目</NuxtLink>
        </div>
      </div>
    </div>

    <div class="quick-actions">
      <h2 class="section-title">快捷操作</h2>
      <div class="actions-grid">
        <NuxtLink to="/purchases" class="action-card">
          <span class="action-icon">🛒</span>
          <span class="action-text">购买记录</span>
        </NuxtLink>
        <NuxtLink to="/events/create" class="action-card">
          <span class="action-icon">➕</span>
          <span class="action-text">新建项目</span>
        </NuxtLink>
        <NuxtLink v-if="canManageUsers" to="/users" class="action-card">
          <span class="action-icon">👥</span>
          <span class="action-text">人员管理</span>
        </NuxtLink>
        <NuxtLink v-if="canManageInvitationCodes" to="/invitation-codes" class="action-card">
          <span class="action-icon">🎫</span>
          <span class="action-text">邀请码管理</span>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCacheStore } from '~/stores/cache'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const cacheStore = useCacheStore()

const stats = ref({
  totalEvents: 0,
  totalRecords: 0,
  totalAmount: 0,
  invoiceTotal: 0,
  invoiceCount: 0,
  purchaseCount: 0,
  ongoingEvents: 0,
  reimbursedAmount: 0,
  pendingReimburse: 0,
  budgetUsageRate: 0,
  reimburseRate: 0
})

const recentEvents = ref([])

const currentUser = ref(null)

const canManageUsers = computed(() => {
  return ['admin', 'teacher', 'student_admin'].includes(currentUser.value?.user_type)
})

const canManageInvitationCodes = computed(() => {
  return ['admin', 'teacher', 'student_admin'].includes(currentUser.value?.user_type)
})

onMounted(async () => {
  console.log('=== 总览面板：页面加载 ===')
  const token = localStorage.getItem('token')
  
  if (!token) {
    navigateTo('/login')
    return
  }

  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  
  cacheStore.restoreFromLocalStorage()
  
  await loadData()
})

onUnmounted(() => {
  cacheStore.persistToLocalStorage()
})

const loadData = async (forceRefresh = false) => {
  const startTime = performance.now()
  
  try {
    const token = localStorage.getItem('token')
    const cacheKey = cacheStore.generateKey('/events', { page: 1, page_size: 10 })
    
    const response = await cacheStore.fetchWithCache(
      cacheKey,
      async () => {
        return await $api.get('/events', {
          headers: { Authorization: `Bearer ${token}` }
        })
      },
      { forceRefresh, expiry: 3 * 60 * 1000 }
    )
    
    if (response.data.code === 200) {
      recentEvents.value = response.data.data.data.slice(0, 5)
      
      let totalAmount = 0
      let totalRecords = 0
      let invoiceTotal = 0
      let invoiceCount = 0
      let purchaseRecordCount = 0
      let ongoingEvents = 0
      let totalBudget = 0
      let reimbursedAmount = 0
      
      recentEvents.value.forEach(event => {
        totalAmount += parseFloat(event.spent_amount || 0)
        invoiceTotal += parseFloat(event.invoice_total_amount || 0)
        invoiceCount += event.invoice_count || 0
        purchaseRecordCount += event.purchase_record_count || 0
        totalRecords += (event.invoice_count || 0) + (event.purchase_record_count || 0)
        totalBudget += parseFloat(event.total_budget || 0)
        reimbursedAmount += parseFloat(event.reimbursed_amount || 0)
        
        if (event.status === 'ongoing') ongoingEvents++
      })
      
      const pendingReimburse = Math.max(0, invoiceTotal - reimbursedAmount)
      const budgetUsageRate = totalBudget > 0 ? ((totalAmount / totalBudget) * 100).toFixed(1) : 0
      const reimburseRate = invoiceTotal > 0 ? ((reimbursedAmount / invoiceTotal) * 100).toFixed(1) : 0
      
      stats.value = {
        totalEvents: response.data.data.total,
        totalRecords,
        totalAmount,
        invoiceTotal,
        invoiceCount,
        purchaseCount: purchaseRecordCount,
        ongoingEvents,
        reimbursedAmount,
        pendingReimburse,
        budgetUsageRate,
        reimburseRate
      }
    }
  } catch (error) {
    console.error('加载数据异常:', error)
  } finally {
    console.log(`数据加载耗时: ${(performance.now() - startTime).toFixed(2)}ms`)
  }
}

const refreshData = () => {
  loadData(true)
}

const formatMoney = (val) => {
  return parseFloat(val || 0).toFixed(2)
}

const getStatusText = (status) => {
  const map = { ongoing: '进行中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

const getBudgetPercent = (event) => {
  const budget = parseFloat(event.total_budget || 0)
  const spent = parseFloat(event.spent_amount || 0)
  if (budget <= 0) return 0
  return Math.min(100, (spent / budget) * 100)
}
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 2rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease;
  border-left: 4px solid transparent;
}

.stat-card.primary { border-left-color: #667eea; }
.stat-card.success { border-left-color: #27ae60; }
.stat-card.warning { border-left-color: #f39c12; }
.stat-card.info { border-left-color: #3498db; }
.stat-card.accent { border-left-color: #9b59b6; }

.stat-card:hover {
  transform: translateY(-4px);
}

.stat-icon {
  font-size: 2.5rem;
  margin-right: 1rem;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 600;
  color: #2c3e50;
}

.stat-label {
  font-size: 0.85rem;
  color: #7f8c8d;
  margin-top: 0.25rem;
}

.stat-trend {
  font-size: 0.75rem;
  color: #95a5a6;
  margin-top: 0.35rem;
}

.recent-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.3rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 1.5rem;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.event-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 10px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.event-item:hover {
  background: #e9ecef;
  transform: translateX(4px);
}

.event-info {
  flex: 1;
}

.event-name {
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  font-size: 15px;
}

.event-details {
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
}

.event-status {
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.event-status.ongoing { background: #d4edda; color: #155724; }
.event-status.completed { background: #f8d7da; color: #721c24; }
.event-status.archived { background: #e2e3e5; color: #383d41; }

.event-category { font-size: 0.82rem; color: #6c757d; }
.event-leader { font-size: 0.82rem; color: #495057; }

.event-stats-row {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
  font-size: 0.78rem;
  color: #666;
}

.event-budget {
  text-align: right;
  min-width: 160px;
}

.budget-label {
  font-size: 0.75rem;
  color: #7f8c8d;
}

.budget-value {
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0.3rem 0;
}

.budget-bar {
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
}

.budget-fill {
  height: 100%;
  background: linear-gradient(90deg, #27ae60 0%, #f39c12 100%);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.empty-state {
  text-align: center;
  padding: 2.5rem;
  color: #7f8c8d;
}

.create-link {
  display: inline-block;
  margin-top: 0.8rem;
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}
.create-link:hover { text-decoration: underline; }

.quick-actions {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  border-radius: 10px;
  text-decoration: none;
  transition: all 0.3s ease;
}

.action-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.action-card:hover .action-text { color: white; }

.action-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.action-text {
  font-size: 0.85rem;
  color: #555;
  font-weight: 500;
  text-align: center;
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  
  .event-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .event-budget {
    text-align: left;
    width: 100%;
  }
  
  .actions-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
