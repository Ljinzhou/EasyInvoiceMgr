<template>
  <div class="dashboard">
    <h1 class="page-title">总览面板</h1>
    
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📁</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.totalEvents }}</div>
          <div class="stat-label">总比赛数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📄</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.totalInvoices }}</div>
          <div class="stat-label">总发票数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <div class="stat-value">¥{{ stats.totalAmount.toFixed(2) }}</div>
          <div class="stat-label">总金额</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.approvedInvoices }}</div>
          <div class="stat-label">已审核发票</div>
        </div>
      </div>
    </div>

    <div class="recent-section">
      <h2 class="section-title">最近比赛</h2>
      <div class="events-list">
        <div v-for="event in recentEvents" :key="event.event_id" class="event-item">
          <div class="event-info">
            <div class="event-name">{{ event.event_name }}</div>
            <div class="event-details">
              <span class="event-status" :class="event.status">{{ event.status === 'ongoing' ? '进行中' : '已结束' }}</span>
              <span class="event-category">{{ event.category || '未分类' }}</span>
            </div>
          </div>
          <div class="event-budget">
            <div class="budget-label">预算</div>
            <div class="budget-value">¥{{ parseFloat(event.total_budget).toFixed(2) }}</div>
          </div>
        </div>
        <div v-if="recentEvents.length === 0" class="empty-state">
          暂无比赛数据
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()

const stats = ref({
  totalEvents: 0,
  totalInvoices: 0,
  totalAmount: 0,
  approvedInvoices: 0
})

const recentEvents = ref([])

onMounted(async () => {
  console.log('=== 总览面板：页面加载 ===')
  const token = localStorage.getItem('token')
  console.log('检查token:', token ? '已登录' : '未登录')
  
  if (!token) {
    console.log('用户未登录，跳转到登录页面')
    navigateTo('/login')
    return
  }
  
  await loadData()
})

const loadData = async () => {
  console.log('=== 总览面板：开始加载数据 ===')
  try {
    const token = localStorage.getItem('token')
    console.log('获取token:', token ? '已获取' : '未获取')
    
    console.log('发送请求: GET /api/events')
    const response = await $api.get('/events', {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    console.log('响应状态:', response.status)
    console.log('响应数据:', response.data)
    
    if (response.data.code === 200) {
      console.log('成功获取比赛数据，总数:', response.data.data.total)
      recentEvents.value = response.data.data.data.slice(0, 5)
      stats.value.totalEvents = response.data.data.total
      
      let totalAmount = 0
      let totalInvoices = 0
      recentEvents.value.forEach(event => {
        totalAmount += parseFloat(event.invoice_total_amount || 0)
        totalInvoices += event.invoice_count || 0
      })
      stats.value.totalAmount = totalAmount
      stats.value.totalInvoices = totalInvoices
      console.log('统计数据计算完成:', stats.value)
    } else {
      console.error('获取数据失败，错误码:', response.data.code)
      console.error('错误信息:', response.data.message)
    }
  } catch (error) {
    console.error('=== 总览面板：加载数据异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    console.error('错误响应数据:', error.response?.data)
    console.error('错误状态码:', error.response?.status)
    console.error('错误消息:', error.message)
  } finally {
    console.log('=== 总览面板：数据加载结束 ===')
  }
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
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
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
  font-size: 0.9rem;
  color: #7f8c8d;
  margin-top: 0.3rem;
}

.recent-section {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
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
  border-radius: 8px;
  transition: background 0.3s ease;
}

.event-item:hover {
  background: #e9ecef;
}

.event-info {
  flex: 1;
}

.event-name {
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.event-details {
  display: flex;
  gap: 0.8rem;
}

.event-status {
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.event-status.ongoing {
  background: #d4edda;
  color: #155724;
}

.event-status.finished {
  background: #f8d7da;
  color: #721c24;
}

.event-category {
  font-size: 0.85rem;
  color: #6c757d;
}

.event-budget {
  text-align: right;
}

.budget-label {
  font-size: 0.8rem;
  color: #7f8c8d;
}

.budget-value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #2c3e50;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .event-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .event-budget {
    text-align: left;
    width: 100%;
  }
}
</style>
