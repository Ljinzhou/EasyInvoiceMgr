import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const name = ref('EasyInvoice')

  function increment() {
    count.value++
  }

  function decrement() {
    count.value--
  }

  function reset() {
    count.value = 0
  }

  const doubleCount = computed(() => count.value * 2)

  return {
    count,
    name,
    doubleCount,
    increment,
    decrement,
    reset
  }
})