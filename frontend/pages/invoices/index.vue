<template>
  <div class="invoices-page">
    <div class="page-header">
      <h1 class="page-title">发票管理</h1>
      <p class="page-description">选择一个比赛查看和管理相关发票</p>
    </div>

    <div class="events-grid">
      <div v-for="event in events" :key="event.event_id" class="event-card">
        <div class="event-header">
          <h3 class="event-title">{{ event.event_name }}</h3>
          <span class="event-status" :class="event.status">
            {{ event.status === 'ongoing' ? '进行中' : '已结束' }}
          </span>
        </div>
        <div class="event-body">
          <div class="event-info-row">
            <span class="info-label">类别：</span>
            <span class="info-value">{{ event.category || '未分类' }}</span>
          </div>
          <div class="event-info-row">
            <span class="info-label">地点：</span>
            <span class="info-value">{{ event.location || '未设置' }}</span>
          </div>
          <div class="event-info-row">
            <span class="info-label">时间：</span>
            <span class="info-value">{{ formatDate(event.event_start_time) }} - {{ formatDate(event.event_end_time) }}</span>
          </div>
          <div class="event-info-row">
            <span class="info-label">预算：</span>
            <span class="info-value budget">¥{{ parseFloat(event.total_budget).toFixed(2) }}</span>
          </div>
          <div class="event-info-row">
            <span class="info-label">发票数：</span>
            <span class="info-value">{{ event.invoice_count || 0 }} 张</span>
          </div>
        </div>
        <div class="event-footer">
          <button @click="enterEvent(event)" class="enter-button">进入管理</button>
        </div>
      </div>
      
      <div v-if="events.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-text">暂无比赛数据</div>
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

const events = ref([])

onMounted(async () => {
  console.log('=== 发票管理：页面加载 ===')
  const token = localStorage.getItem('token')
  console.log('检查token:', token ? '已登录' : '未登录')
  
  if (!token) {
    console.log('用户未登录，跳转到登录页面')
    navigateTo('/login')
    return
  }
  
  await loadEvents()
})

const loadEvents = async () => {
  console.log('=== 发票管理：开始加载比赛列表 ===')
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
      console.log('成功获取比赛列表，数量:', response.data.data.data.length)
      events.value = response.data.data.data
    } else {
      console.error('获取比赛列表失败，错误码:', response.data.code)
      console.error('错误信息:', response.data.message)
    }
  } catch (error) {
    console.error('=== 发票管理：加载比赛列表异常 ===')
    console.error('错误对象:', error)
    console.error('错误响应:', error.response)
    console.error('错误响应数据:', error.response?.data)
    console.error('错误状态码:', error.response?.status)
    console.error('错误消息:', error.message)
  } finally {
    console.log('=== 发票管理：比赛列表加载结束 ===')
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '未设置'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

const enterEvent = (event) => {
  navigateTo(`/invoices/${event.event_id}`)
}
</script>

<style scoped>
.invoices-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.page-description {
  color: #7f8c8d;
  font-size: 1rem;
}

.events-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.event-card {
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.event-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
}

.event-header {
  padding: 1.2rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.event-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.event-status {
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.2);
}

.event-status.ongoing {
  background: #27ae60;
}

.event-status.finished {
  background: #e74c3c;
}

.event-body {
  padding: 1.5rem;
}

.event-info-row {
  display: flex;
  margin-bottom: 0.8rem;
  font-size: 0.95rem;
}

.info-label {
  color: #7f8c8d;
  width: 70px;
  flex-shrink: 0;
}

.info-value {
  color: #2c3e50;
  flex: 1;
}

.info-value.budget {
  font-weight: 600;
  color: #27ae60;
}

.event-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #ecf0f1;
}

.enter-button {
  width: 100%;
  padding: 0.8rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.3s ease;
}

.enter-button:hover {
  opacity: 0.9;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-text {
  color: #7f8c8d;
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .events-grid {
    grid-template-columns: 1fr;
  }
}
</style>
