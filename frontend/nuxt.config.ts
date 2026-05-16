export default defineNuxtConfig({
  compatibilityDate: '2026-05-09',
  devtools: { enabled: true },
  modules: ['@pinia/nuxt'],
  typescript: {
    strict: true,
    typeCheck: false
  },
  css: [],
  experimental: {
    appManifest: false
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:5000/api'
    }
  },
  nitro: {}
})