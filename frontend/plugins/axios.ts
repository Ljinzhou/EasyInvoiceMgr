import axios from 'axios'

export default defineNuxtPlugin((nuxtApp) => {
  const api = axios.create({
    baseURL: nuxtApp.$config.public.apiBase,
    timeout: 30000
  })

  api.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      
      if (config.data instanceof FormData) {
        // Let axios set the correct Content-Type with boundary for FormData
        delete config.headers['Content-Type']
      } else if (!config.headers['Content-Type']) {
        config.headers['Content-Type'] = 'application/json'
      }
      
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )

  api.interceptors.response.use(
    (response) => {
      return response
    },
    (error) => {
      if (error.response?.status === 401) {
        const currentPath = window.location.pathname
        if (currentPath !== '/login') {
          window.location.href = '/login'
        }
      }
      return Promise.reject(error)
    }
  )

  nuxtApp.provide('api', api)
})

export type ApiInstance = ReturnType<typeof axios.create>