<template>
  <div class="hello">
    <h2>{{ msg }}</h2>
    <p>This is a sample component built with Vue 3 and Nuxt 3.</p>
    <div class="date-time">
      <p>Current Date: {{ currentDate }}</p>
      <p>Current Time: {{ currentTime }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import dayjs from 'dayjs'

interface Props {
  msg: string
}

const props = defineProps<Props>()

const currentDate = ref(dayjs().format('YYYY-MM-DD'))
const currentTime = ref(dayjs().format('HH:mm:ss'))
let timer: NodeJS.Timeout | null = null

onMounted(() => {
  timer = setInterval(() => {
    currentDate.value = dayjs().format('YYYY-MM-DD')
    currentTime.value = dayjs().format('HH:mm:ss')
  }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.hello {
  margin: 2rem 0;
  padding: 2rem;
  background: #42b883;
  color: white;
  border-radius: 8px;
}

.hello h2 {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.date-time {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 0.9rem;
}

.date-time p {
  margin: 0.5rem 0;
}
</style>