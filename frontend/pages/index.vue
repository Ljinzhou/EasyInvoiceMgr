<template>
  <div></div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false
})

onMounted(() => {
  const token = localStorage.getItem('token')
  if (token) {
    navigateTo('/dashboard')
  } else {
    navigateTo('/login')
  }
})
</script>
