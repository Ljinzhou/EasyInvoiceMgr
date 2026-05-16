import { defineStore } from 'pinia'

interface CacheItem<T> {
  data: T
  timestamp: number
  expiry: number
  version: string
}

interface CacheStats {
  hits: number
  misses: number
  totalRequests: number
  averageLoadTime: number
  loadTimes: number[]
}

interface PerformanceMetric {
  cacheKey: string
  loadTime: number
  fromCache: boolean
  timestamp: number
}

export const useCacheStore = defineStore('cache', {
  state: () => ({
    cache: new Map<string, CacheItem<any>>(),
    stats: {
      hits: 0,
      misses: 0,
      totalRequests: 0,
      averageLoadTime: 0,
      loadTimes: [] as number[]
    } as CacheStats,
    performanceMetrics: [] as PerformanceMetric[],
    version: '1.0.0',
    defaultExpiry: 5 * 60 * 1000,
    maxCacheSize: 50,
    maxMetricsSize: 100
  }),

  getters: {
    hitRate: (state) => {
      if (state.stats.totalRequests === 0) return 0
      return (state.stats.hits / state.stats.totalRequests * 100).toFixed(2)
    },
    
    cacheSize: (state) => state.cache.size,
    
    getStats: (state) => ({
      ...state.stats,
      hitRate: state.stats.totalRequests > 0 
        ? (state.stats.hits / state.stats.totalRequests * 100).toFixed(2) + '%'
        : '0%',
      cacheSize: state.cache.size
    })
  },

  actions: {
    generateKey(endpoint: string, params?: Record<string, any>): string {
      const paramString = params ? JSON.stringify(params) : ''
      return `${endpoint}:${paramString}`
    },

    set<T>(key: string, data: T, customExpiry?: number): void {
      if (this.cache.size >= this.maxCacheSize) {
        this.evictOldest()
      }

      const expiry = customExpiry || this.defaultExpiry
      
      this.cache.set(key, {
        data,
        timestamp: Date.now(),
        expiry,
        version: this.version
      })
    },

    get<T>(key: string): T | null {
      const item = this.cache.get(key)
      
      if (!item) {
        return null
      }

      if (Date.now() - item.timestamp > item.expiry) {
        this.cache.delete(key)
        return null
      }

      if (item.version !== this.version) {
        this.cache.delete(key)
        return null
      }

      return item.data as T
    },

    has(key: string): boolean {
      const item = this.cache.get(key)
      if (!item) return false
      
      if (Date.now() - item.timestamp > item.expiry) {
        this.cache.delete(key)
        return false
      }

      if (item.version !== this.version) {
        this.cache.delete(key)
        return false
      }

      return true
    },

    delete(key: string): boolean {
      const result = this.cache.delete(key)
      return result
    },

    deleteByPrefix(prefix: string): number {
      let count = 0
      const keysToDelete: string[] = []
      
      this.cache.forEach((_, key) => {
        if (key.startsWith(prefix)) {
          keysToDelete.push(key)
        }
      })

      keysToDelete.forEach(key => {
        this.cache.delete(key)
        count++
      })

      return count
    },

    clear(): void {
      this.cache.clear()
    },

    evictOldest(): void {
      let oldestKey: string | null = null
      let oldestTimestamp = Infinity

      this.cache.forEach((item, key) => {
        if (item.timestamp < oldestTimestamp) {
          oldestTimestamp = item.timestamp
          oldestKey = key
        }
      })

      if (oldestKey) {
        this.cache.delete(oldestKey)
      }
    },

    invalidateEventCache(eventId?: number): void {
      if (eventId) {
        this.deleteByPrefix(`/events/${eventId}`)
        this.deleteByPrefix(`/purchases?event_id=${eventId}`)
        this.deleteByPrefix(`/events/${eventId}/records`)
      }
      this.deleteByPrefix('/events')
    },

    invalidateInvoiceCache(eventId?: number): void {
      if (eventId) {
        this.deleteByPrefix(`/purchases?event_id=${eventId}`)
        this.deleteByPrefix(`/events/${eventId}/records`)
      }
      this.deleteByPrefix('/purchases')
    },

    invalidateUserCache(): void {
      this.deleteByPrefix('/auth/users')
    },

    recordRequest(fromCache: boolean, loadTime: number, cacheKey?: string): void {
      this.stats.totalRequests++
      
      if (fromCache) {
        this.stats.hits++
      } else {
        this.stats.misses++
      }

      this.stats.loadTimes.push(loadTime)
      if (this.stats.loadTimes.length > 100) {
        this.stats.loadTimes.shift()
      }

      const sum = this.stats.loadTimes.reduce((a, b) => a + b, 0)
      this.stats.averageLoadTime = sum / this.stats.loadTimes.length

      if (cacheKey) {
        this.performanceMetrics.push({
          cacheKey,
          loadTime,
          fromCache,
          timestamp: Date.now()
        })

        if (this.performanceMetrics.length > this.maxMetricsSize) {
          this.performanceMetrics.shift()
        }
      }
    },

    getPerformanceReport(): object {
      const cacheMetrics = this.performanceMetrics.reduce((acc, metric) => {
        if (!acc[metric.cacheKey]) {
          acc[metric.cacheKey] = {
            totalRequests: 0,
            cacheHits: 0,
            cacheMisses: 0,
            avgLoadTime: 0,
            avgCacheLoadTime: 0,
            avgDbLoadTime: 0,
            loadTimes: []
          }
        }
        
        const keyStats = acc[metric.cacheKey]
        keyStats.totalRequests++
        if (metric.fromCache) {
          keyStats.cacheHits++
        } else {
          keyStats.cacheMisses++
        }
        keyStats.loadTimes.push(metric.loadTime)
        
        return acc
      }, {} as Record<string, any>)

      Object.keys(cacheMetrics).forEach(key => {
        const stats = cacheMetrics[key]
        const cacheTimes = this.performanceMetrics
          .filter(m => m.cacheKey === key && m.fromCache)
          .map(m => m.loadTime)
        const dbTimes = this.performanceMetrics
          .filter(m => m.cacheKey === key && !m.fromCache)
          .map(m => m.loadTime)
        
        stats.avgLoadTime = stats.loadTimes.reduce((a: number, b: number) => a + b, 0) / stats.loadTimes.length
        stats.avgCacheLoadTime = cacheTimes.length > 0 
          ? cacheTimes.reduce((a, b) => a + b, 0) / cacheTimes.length 
          : 0
        stats.avgDbLoadTime = dbTimes.length > 0 
          ? dbTimes.reduce((a, b) => a + b, 0) / dbTimes.length 
          : 0
        stats.hitRate = stats.totalRequests > 0 
          ? ((stats.cacheHits / stats.totalRequests) * 100).toFixed(2) + '%'
          : '0%'
        
        delete stats.loadTimes
      })

      return {
        summary: {
          totalRequests: this.stats.totalRequests,
          hits: this.stats.hits,
          misses: this.stats.misses,
          hitRate: this.hitRate + '%',
          averageLoadTime: this.stats.averageLoadTime.toFixed(2) + 'ms',
          cacheSize: this.cacheSize
        },
        details: cacheMetrics
      }
    },

    printPerformanceReport(): void {
      const report = this.getPerformanceReport()
    },

    async fetchWithCache<T>(
      key: string,
      fetcher: () => Promise<T>,
      options?: {
        expiry?: number
        forceRefresh?: boolean
      }
    ): Promise<T> {
      const startTime = performance.now()
      
      if (!options?.forceRefresh) {
        const cachedData = this.get<T>(key)
        if (cachedData !== null) {
          const loadTime = performance.now() - startTime
          this.recordRequest(true, loadTime, key)
          return cachedData
        }
      }

      const data = await fetcher()

      this.set(key, data, options?.expiry)

      const loadTime = performance.now() - startTime
      this.recordRequest(false, loadTime, key)

      return data
    },

    persistToLocalStorage(): void {
      try {
        const cacheData = {
          version: this.version,
          timestamp: Date.now(),
          items: {} as Record<string, any>
        }

        this.cache.forEach((item, key) => {
          if (Date.now() - item.timestamp <= item.expiry) {
            cacheData.items[key] = item
          }
        })

        localStorage.setItem('app_cache', JSON.stringify(cacheData))
      } catch (error) {
        console.error('Cache persist failed:', error.message)
      }
    },

    restoreFromLocalStorage(): void {
      try {
        const cacheStr = localStorage.getItem('app_cache')
        if (!cacheStr) return

        const cacheData = JSON.parse(cacheStr)
        
        if (cacheData.version !== this.version) {
          localStorage.removeItem('app_cache')
          return
        }

        const now = Date.now()
        let restored = 0

        Object.entries(cacheData.items).forEach(([key, item]: [string, any]) => {
          if (now - item.timestamp <= item.expiry) {
            this.cache.set(key, item)
            restored++
          }
        })
      } catch (error) {
        console.error('Cache restore failed:', error.message)
        localStorage.removeItem('app_cache')
      }
    },

    clearLocalStorage(): void {
      localStorage.removeItem('app_cache')
    }
  }
})
