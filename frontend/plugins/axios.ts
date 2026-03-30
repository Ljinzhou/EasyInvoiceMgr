import axios from 'axios'

export default defineNuxtPlugin((nuxtApp) => {
  // Create axios instance
  const api = axios.create({
    baseURL: nuxtApp.$config.public.apiBase,
    timeout: 10000,
    headers: {
      'Content-Type': 'application/json'
    }
  })

  // Request interceptor
  api.interceptors.request.use(
    (config) => {
      // Add token if available
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )

  // Response interceptor
  api.interceptors.response.use(
    (response) => {
      return response
    },
    (error) => {
      // Handle error responses
      if (error.response?.status === 401) {
        // Unauthorized - redirect to login
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )

  // Provide the api instance to Nuxt app
  nuxtApp.provide('api', api)
})

export type ApiInstance = ReturnType<typeof axios.create>