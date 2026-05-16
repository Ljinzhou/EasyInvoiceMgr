import { ref, watch, onBeforeUnmount } from 'vue'

export function useUserSearch(options: { filter?: (user: any) => boolean } = {}) {
  const { $api } = useNuxtApp()
  const searchText = ref('')
  const results = ref<any[]>([])
  let timer: ReturnType<typeof setTimeout> | null = null

  watch(searchText, (val) => {
    if (timer) clearTimeout(timer)

    if (!val) {
      results.value = []
      return
    }

    results.value = []

    timer = setTimeout(async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) return

        const response = await $api.get('/auth/users', {
          params: { search: val },
          headers: { Authorization: `Bearer ${token}` }
        })

        if (response.data.code === 200) {
          const users = response.data.data.data || response.data.data || []
          const arr = Array.isArray(users) ? users : []
          results.value = options.filter ? arr.filter(options.filter) : arr
        }
      } catch (e) {
        console.error('搜索用户失败:', e.message)
      }
    }, 300)
  })

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return { searchText, results }
}
