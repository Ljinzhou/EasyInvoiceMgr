import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', () => {
  const user = ref<any>(null)
  const avatarUrl = ref('')

  function loadFromStorage() {
    if (process.client) {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        user.value = JSON.parse(userStr)
        avatarUrl.value = user.value?.avatar_url || ''
      }
    }
  }

  function saveToStorage(updatedUser?: any) {
    if (updatedUser) {
      user.value = { ...user.value, ...updatedUser }
    }
    if (user.value) {
      localStorage.setItem('user', JSON.stringify(user.value))
      avatarUrl.value = user.value?.avatar_url || ''
    }
  }

  function updateAvatar(newUrl: string) {
    avatarUrl.value = newUrl || ''
    if (user.value) {
      user.value.avatar_url = newUrl || null
      localStorage.setItem('user', JSON.stringify(user.value))
    }
  }

  function clearUser() {
    user.value = null
    avatarUrl.value = ''
    localStorage.removeItem('user')
  }

  const realName = computed(() => user.value?.real_name || '未登录')
  const userType = computed(() => user.value?.user_type || '')
  const userRole = computed(() => {
    const roles: Record<string, string> = {
      admin: '管理员',
      teacher: '教师',
      student_admin: '学生管理员',
      student: '学生'
    }
    return roles[userType.value] || '未知'
  })
  const userId = computed(() => user.value?.user_id)
  const initial = computed(() => realName.value.charAt(0).toUpperCase())

  return {
    user,
    avatarUrl,
    loadFromStorage,
    saveToStorage,
    updateAvatar,
    clearUser,
    realName,
    userType,
    userRole,
    userId,
    initial,
  }
})
