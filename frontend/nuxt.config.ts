export default defineNuxtConfig({
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
  }
})