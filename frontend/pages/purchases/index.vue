<template>
  <div class="purchases-list-page">
    <div class="page-header">
      <h1 class="page-title">🛒 购买记录</h1>
      <div class="header-actions">
        <select v-model="filterEvent" class="event-filter" @change="loadEvents">
          <option value="">全部项目</option>
          <option v-for="e in events" :key="e.event_id" :value="e.event_id">{{ e.event_name }}</option>
        </select>
        <NuxtLink to="/projects" class="action-button primary">+ 新建项目</NuxtLink>
      </div>
    </div>

    <!-- 总览统计 -->
    <div class="overview-stats">
      <div class="stat-card">
        <span class="stat-icon">💰</span>
        <div class="stat-info">
          <span class="stat-value">¥{{ formatMoney(totalStats.totalAmount) }}</span>
          <span class="stat-label">总支出</span>
        </div>
      </div>
      <div class="stat-card invoice-stat">
        <span class="stat-icon">🧾</span>
        <div class="stat-info">
          <span class="stat-value">¥{{ formatMoney(totalStats.invoiceTotal) }}</span>
          <span class="stat-label">发票总额</span>
        </div>
      </div>
      <div class="stat-card pending-stat">
        <span class="stat-icon">⏳</span>
        <div class="stat-info">
          <span class="stat-value">¥{{ formatMoney(totalStats.pendingReimburse) }}</span>
          <span class="stat-label">待报销</span>
        </div>
      </div>
      <div class="stat-card count-stat">
        <span class="stat-icon">📋</span>
        <div class="stat-info">
          <span class="stat-value">{{ totalStats.recordCount }}</span>
          <span class="stat-label">记录总数</span>
        </div>
      </div>
    </div>

    <!-- 项目列表 -->
    <div class="events-grid">
      <div 
        v-for="ev in filteredEvents" 
        :key="ev.event_id" 
        class="event-card"
        @click="$router.push(`/purchases/${ev.event_id}`)"
      >
        <div class="card-header">
          <h3 class="event-name">{{ ev.event_name || '未命名项目' }}</h3>
          <span class="event-status" :class="ev.status">{{ getStatusText(ev.status) }}</span>
        </div>
        
        <div class="card-body">
          <div class="card-row">
            <span class="label">负责人：</span>
            <span class="value">{{ ev.leader_name || '-' }}</span>
          </div>
          <div class="card-row">
            <span class="label">预算：</span>
            <span class="value">¥{{ formatMoney(ev.total_budget) }}</span>
          </div>
          <div class="card-row highlight">
            <span class="label">已花费：</span>
            <span class="value amount">¥{{ formatMoney(ev.spent_amount || 0) }}</span>
          </div>
          <div class="card-row">
            <span class="label">记录数：</span>
            <span class="value">{{ ev.voucher_count || 0 }} 条</span>
          </div>
        </div>

        <div class="card-footer">
          <button class="view-btn">查看详情 →</button>
        </div>
      </div>

      <div v-if="filteredEvents.length === 0" class="empty-state">
        <span class="empty-icon">🛒</span>
        <p>暂无项目数据</p>
        <NuxtLink to="/events/create" class="create-link">创建第一个项目</NuxtLink>
      </div>
    </div>

    <!-- 快速添加记录入口 -->
    <div v-if="events.length > 0" class="quick-add-section">
      <h2>快速添加记录</h2>
      <select v-model="quickAddEventId" class="quick-select">
        <option value="">选择项目...</option>
        <option v-for="e in events" :key="e.event_id" :value="e.event_id">{{ e.event_name }}</option>
      </select>
      <button 
        @click="goToPurchasePage" 
        class="action-button quick-add"
        :disabled="!quickAddEventId"
      >添加购买记录</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useEventStore } from '~/stores/eventStore'

definePageMeta({ layout: 'default' })

const eventStore = useEventStore()
const router = useRouter()

const filterEvent = ref('')
const quickAddEventId = ref('')

// All statistics from the unified store (reactive)
const totalStats = computed(() => eventStore.totalStats)

// Events from the unified store
const events = computed(() => eventStore.events)

const filteredEvents = computed(() => {
  if (!filterEvent.value) return events.value
  return events.value.filter((e) => e.event_id == filterEvent.value)
})

onMounted(async () => {
  await eventStore.ensureLoaded()
})

const goToPurchasePage = () => {
  if (quickAddEventId.value) {
    router.push(`/purchases/${quickAddEventId.value}`)
  }
}

const getStatusText = (status) => {
  const map = { ongoing: '进行中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

const formatMoney = (val) => {
  return parseFloat(val || 0).toFixed(2)
}
</script>

<style scoped>
.purchases-list-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.8rem;
  align-items: center;
}

.event-filter {
  padding: 0.7rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.action-button {
  padding: 0.7rem 1.5rem;
  border: none;
  border-radius: 6px;
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
  font-size: 14px;
}
.action-button.primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.action-button.primary:hover { transform: translateY(-1px); opacity: 0.95; }
.action-button.quick-add { background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); }
.action-button.quick-add:disabled { opacity: 0.5; cursor: not-allowed; }

.overview-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  border-left: 4px solid #667eea;
}
.stat-card.invoice-stat { border-left-color: #f39c12; }
.stat-card.pending-stat { border-left-color: #e74c3c; }
.stat-card.count-stat { border-left-color: #3498db; }

.stat-icon { font-size: 2rem; }

.stat-info { display: flex; flex-direction: column; }
.stat-value { font-size: 22px; font-weight: 700; color: #2c3e50; }
.stat-label { font-size: 13px; color: #7f8c8d; }

.events-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 2rem;
}

.event-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  transition: all 0.3s ease;
  cursor: pointer;
}
.event-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.1);
}

.card-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.event-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: white;
}

.event-status {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(255,255,255,0.2);
  color: white;
}
.event-status.completed { background: rgba(39, 174, 96, 0.9); }
.event-status.archived { background: rgba(149, 165, 166, 0.9); }

.card-body { padding: 16px 20px; }

.card-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}
.card-row .label { color: #999; }
.card-row .value { color: #333; font-weight: 500; }
.card-row.highlight .value { color: #e74c3c; font-weight: 700; font-size: 15px; }

.card-footer {
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
  text-align: right;
}

.view-btn {
  background: none;
  border: none;
  color: #667eea;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.view-btn:hover { text-decoration: underline; }

.empty-state {
  grid-column: span -1;
  text-align: center;
  padding: 60px 20px;
  color: #999;
}
.empty-icon { font-size: 4rem; display: block; margin-bottom: 1rem; }
.create-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}
.create-link:hover { text-decoration: underline; }

.quick-add-section {
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  padding: 24px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.quick-add-section h2 {
  margin: 0;
  font-size: 18px;
  color: #2c3e50;
}
.quick-select {
  flex: 1;
  max-width: 300px;
  padding: 0.8rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  min-width: 150px;
}

@media (max-width: 768px) {
  .overview-stats { grid-template-columns: repeat(2, 1fr); }
  .events-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: stretch; }
  .header-actions { flex-direction: column; }
  .quick-add-section { flex-direction: column; align-items: stretch; }
  .quick-select { max-width: none; }
}
</style>
