<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
  -webkit-text-size-adjust: 100%;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  min-height: 100vh;
  min-height: 100dvh;
}

/* iOS safe area support */
body::before {
  content: '';
  display: block;
  height: env(safe-area-inset-top);
}

/* Prevent iOS auto-zoom on inputs < 16px */
@media (max-width: 768px) {
  input[type="text"],
  input[type="password"],
  input[type="email"],
  input[type="tel"],
  input[type="number"],
  input[type="search"],
  input[type="url"],
  input[type="date"],
  input[type="datetime-local"],
  select,
  textarea {
    font-size: 16px !important;
  }
}

/* Respect reduced motion preferences */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>