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
      apiBase: 'http://localhost:5000/api'
    }
  },
  nitro: {
    devProxy: {
      '/uploads': {
        target: 'http://localhost:5000/uploads',
        changeOrigin: true
      }
    }
  }
})