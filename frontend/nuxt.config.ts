export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: ['@pinia/nuxt'],
  typescript: {
    strict: true,
    typeCheck: false
  },
  css: [],
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:5000/api'
    }
  }
})