import { defineStore } from 'pinia'
import { useCacheStore } from './cache'

export interface EventItem {
  event_id: number
  event_name: string
  description: string | null
  status: string
  event_start_time: string | null
  event_end_time: string | null
  upload_start_time: string | null
  upload_end_time: string | null
  creator_id: number | null
  leader_id: number | null
  leader_name: string | null
  total_budget: number
  reimbursed_amount: number
  remaining_budget: number
  spent_amount: number
  invoice_total_amount: number
  purchase_total_amount: number
  invoice_count: number
  purchase_record_count: number
  voucher_count: number
  need_invoice_review: boolean
}

export interface EventStats {
  totalEvents: number
  totalRecords: number
  totalAmount: number
  invoiceTotal: number
  invoiceCount: number
  purchaseCount: number
  ongoingEvents: number
  reimbursedAmount: number
  pendingReimburse: number
  budgetUsageRate: number
  reimburseRate: number
  totalBudget: number
}

export interface TotalStatsSummary {
  totalAmount: number
  invoiceTotal: number
  pendingReimburse: number
  recordCount: number
}

export const useEventStore = defineStore('eventStore', {
  state: () => ({
    events: [] as EventItem[],
    totalCount: 0,
    dataVersion: 0,
    loading: false,
    error: null as string | null,
    lastFetchTime: 0,
    initialized: false
  }),

  getters: {
    /** Full aggregate statistics across all events (for dashboard) */
    fullStats(): EventStats {
      let totalAmount = 0
      let totalRecords = 0
      let invoiceTotal = 0
      let invoiceCount = 0
      let purchaseCount = 0
      let ongoingEvents = 0
      let totalBudget = 0
      let reimbursedAmount = 0

      for (const ev of this.events) {
        totalAmount += parseFloat(String(ev.spent_amount || 0))
        invoiceTotal += parseFloat(String(ev.invoice_total_amount || 0))
        invoiceCount += ev.invoice_count || 0
        purchaseCount += ev.purchase_record_count || 0
        totalRecords += (ev.invoice_count || 0) + (ev.purchase_record_count || 0)
        totalBudget += parseFloat(String(ev.total_budget || 0))
        reimbursedAmount += parseFloat(String(ev.reimbursed_amount || 0))

        if (ev.status === 'ongoing') ongoingEvents++
      }

      const pendingReimburse = Math.max(0, invoiceTotal - reimbursedAmount)
      const budgetUsageRate = totalBudget > 0 ? Number(((totalAmount / totalBudget) * 100).toFixed(1)) : 0
      const reimburseRate = invoiceTotal > 0 ? Number(((reimbursedAmount / invoiceTotal) * 100).toFixed(1)) : 0

      return {
        totalEvents: this.totalCount,
        totalRecords,
        totalAmount,
        invoiceTotal,
        invoiceCount,
        purchaseCount,
        ongoingEvents,
        reimbursedAmount,
        pendingReimburse,
        budgetUsageRate,
        reimburseRate,
        totalBudget
      }
    },

    /** Summary stats for purchases list page */
    totalStats(): TotalStatsSummary {
      let totalAmount = 0
      let invoiceTotal = 0
      let pendingReimburse = 0
      let recordCount = 0

      for (const ev of this.events) {
        totalAmount += parseFloat(String(ev.spent_amount || 0))
        recordCount += parseInt(String(ev.voucher_count || 0))
        invoiceTotal += parseFloat(String(ev.invoice_total_amount || 0))
        pendingReimburse += Math.max(0,
          parseFloat(String(ev.invoice_total_amount || 0)) -
          parseFloat(String(ev.reimbursed_amount || 0))
        )
      }

      return { totalAmount, invoiceTotal, pendingReimburse, recordCount }
    },

    /** Whether data is stale (older than 3 minutes) */
    isStale(): boolean {
      if (!this.lastFetchTime) return true
      return Date.now() - this.lastFetchTime > 3 * 60 * 1000
    },

    /** Get a single event by ID from the store */
    getEventById: (state) => (eventId: number): EventItem | undefined => {
      return state.events.find(e => e.event_id === eventId)
    }
  },

  actions: {
    /**
     * Unified fetch - the single entry point for loading event data.
     * All modules MUST use this method to ensure data consistency.
     *
     * @param options.pageSize - number of events per page
     * @param options.forceRefresh - bypass cache
     * @param options.status - filter by status
     */
    async fetchEvents(options: {
      pageSize?: number
      forceRefresh?: boolean
      status?: string
      api?: any  // injectable for testing
    } = {}) {
      const {
        pageSize = 100,
        forceRefresh = false,
        status,
        api
      } = options

      const cacheStore = useCacheStore()

      const params: Record<string, any> = { page: 1, page_size: pageSize }
      if (status) params.status = status

      const cacheKey = cacheStore.generateKey('/events', params)

      try {
        this.loading = true
        this.error = null

        const $api = api || useNuxtApp().$api
        const token = localStorage.getItem('token')

        const response = await cacheStore.fetchWithCache(
          cacheKey,
          async () => {
            return await $api.get('/events', {
              params,
              headers: { Authorization: `Bearer ${token}` }
            })
          },
          { forceRefresh, expiry: 3 * 60 * 1000 }
        )

        if (response.data.code === 200) {
          this.events = response.data.data.data || []
          this.totalCount = response.data.data.total || 0
          this.dataVersion++
          this.lastFetchTime = Date.now()
          this.initialized = true
        } else {
          this.error = response.data.message || '加载失败'
        }
      } catch (e: any) {
        this.error = e?.message || '网络错误'
        console.error('获取赛事列表失败:', e.message)
        throw e
      } finally {
        this.loading = false
      }
    },

    /**
     * Invalidate cache and re-fetch. Call this after any mutation
     * (create/update/delete record, approve/reimburse, etc.)
     */
    async invalidateAndRefresh(options: {
      eventId?: number
      pageSize?: number
      api?: any
    } = {}) {
      const cacheStore = useCacheStore()
      cacheStore.invalidateEventCache(options.eventId)
      await this.fetchEvents({ pageSize: options.pageSize, forceRefresh: true, api: options.api })
    },

    /**
     * Refresh a single event's data by re-fetching the full list.
     * This ensures aggregated stats (which depend on all events) stay accurate.
     */
    async refreshAfterMutation(eventId?: number) {
      await this.invalidateAndRefresh({ eventId })
    },

    /**
     * Ensure data is loaded (lazy init - fetches only if not yet initialized or stale).
     * Safe to call in onMounted of any component.
     */
    async ensureLoaded(options: { pageSize?: number; forceRefresh?: boolean; api?: any } = {}) {
      if (!this.initialized || this.isStale || options.forceRefresh) {
        await this.fetchEvents(options)
      }
    }
  }
})
