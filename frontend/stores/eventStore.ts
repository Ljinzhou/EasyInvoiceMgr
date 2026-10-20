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
  /** 加入审核方式：auto=自动审核加入，manual=人工审核加入 */
  join_review_mode?: 'auto' | 'manual'
  /** 当前用户在该比赛最近一次加入申请的状态 */
  join_request_status?: 'pending' | 'approved' | 'rejected' | null
  /** 当前用户是否已是该比赛成员 */
  is_member?: boolean
  /** 该比赛待审核的加入申请数量（仅当前用户有权审核时才有值） */
  pending_join_request_count?: number
  total_budget: number
  reimbursed_amount: number
  remaining_budget: number
  spent_amount: number
  invoice_total_amount: number
  purchase_total_amount: number
  invoice_count: number
  purchase_record_count: number
  voucher_count: number
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
  remainingBudget: number
}

export const useEventStore = defineStore('eventStore', {
  state: () => ({
    events: [] as EventItem[],
    totalCount: 0,
    dataVersion: 0,
    loading: false,
    error: null as string | null,
    lastFetchTime: 0,
    initialized: false,
    /** 各比赛待审核加入申请数量（红点用）：{ [event_id]: count } */
    pendingJoinCounts: {} as Record<number, number>,
    /** 当前用户可审核的待处理加入申请总数（侧边栏红点用） */
    pendingJoinTotal: 0,
    pendingJoinFetchedAt: 0
  }),

  getters: {
    /** 所有项目的完整汇总统计（用于总览面板） */
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
      const budgetUsageRate = totalBudget > 0 ? Number(((totalAmount / totalBudget) * 100).toFixed(2)) : 0
      const reimburseRate = invoiceTotal > 0 ? Number(((reimbursedAmount / invoiceTotal) * 100).toFixed(2)) : 0

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

    /** 购买记录列表页的汇总统计 */
    totalStats(): TotalStatsSummary {
      let totalAmount = 0
      let invoiceTotal = 0
      let pendingReimburse = 0
      let recordCount = 0
      let remainingBudget = 0

      for (const ev of this.events) {
        totalAmount += parseFloat(String(ev.spent_amount || 0))
        recordCount += parseInt(String(ev.voucher_count || 0))
        invoiceTotal += parseFloat(String(ev.invoice_total_amount || 0))
        pendingReimburse += Math.max(0,
          parseFloat(String(ev.invoice_total_amount || 0)) -
          parseFloat(String(ev.reimbursed_amount || 0))
        )
        remainingBudget += Math.max(0,
          parseFloat(String(ev.total_budget || 0)) -
          parseFloat(String(ev.spent_amount || 0))
        )
      }

      return { totalAmount, invoiceTotal, pendingReimburse, recordCount, remainingBudget }
    },

    /** 数据是否已过期（超过 3 分钟） */
    isStale(): boolean {
      if (!this.lastFetchTime) return true
      return Date.now() - this.lastFetchTime > 3 * 60 * 1000
    },

    /** 从 store 中按 ID 获取单个项目 */
    getEventById: (state) => (eventId: number): EventItem | undefined => {
      return state.events.find(e => e.event_id === eventId)
    },

    /** 某场比赛待审核的加入申请数量（红点用，汇总接口优先） */
    pendingJoinCountFor: (state) => (eventId: number): number => {
      // 一旦拉过汇总接口，就以它为准，避免列表数据过期导致红点不消失
      if (state.pendingJoinFetchedAt > 0) {
        return state.pendingJoinCounts[eventId] || 0
      }
      const row = state.events.find(e => e.event_id === eventId)
      return Number(row?.pending_join_request_count || 0)
    }
  },

  actions: {
    /**
     * 统一拉取——加载项目数据的唯一入口。
     * 所有模块必须使用此方法，以确保数据一致性。
     *
     * @param options.pageSize - 每页项目数量
     * @param options.forceRefresh - 绕过缓存
     * @param options.status - 按状态筛选
     */
    async fetchEvents(options: {
      pageSize?: number
      forceRefresh?: boolean
      status?: string
      api?: any  // 可注入，用于测试
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
     * 使缓存失效并重新拉取。任何变更操作后都应调用
     * （新增/更新/删除记录、审批/报销等）。
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
     * 通过重新拉取完整列表来刷新单个项目的数据。
     * 这样可以确保汇总统计（依赖所有项目）保持准确。
     */
    async refreshAfterMutation(eventId?: number) {
      await this.invalidateAndRefresh({ eventId })
    },

    /**
     * 确保数据已加载（惰性初始化——仅在尚未初始化或已过期时拉取）。
     * 可在任何组件的 onMounted 中安全调用。
     */
    async ensureLoaded(options: { pageSize?: number; forceRefresh?: boolean; api?: any } = {}) {
      if (!this.initialized || this.isStale || options.forceRefresh) {
        await this.fetchEvents(options)
      }
    },

    /**
     * 刷新「待审核加入申请」数量，供侧边栏与项目卡片红点使用。
     *
     * 红点是辅助提示：失败时只 warn，不抛异常、不打扰用户。
     */
    async fetchPendingJoinCounts(options: { api?: any } = {}) {
      const token = import.meta.client ? localStorage.getItem('token') : null
      if (!token) {
        this.clearPendingJoinCounts()
        return
      }

      try {
        const $api = options.api || useNuxtApp().$api
        const response = await $api.get('/events/join-requests/pending-summary', {
          headers: { Authorization: `Bearer ${token}` }
        })

        if (response.data.code === 200) {
          const byEvent = response.data.data?.by_event || {}
          const counts: Record<number, number> = {}
          Object.keys(byEvent).forEach((key) => {
            const count = Number(byEvent[key]) || 0
            if (count > 0) counts[Number(key)] = count
          })
          this.pendingJoinCounts = counts
          this.pendingJoinTotal = Number(response.data.data?.total) || 0
          this.pendingJoinFetchedAt = Date.now()
        }
      } catch (e: any) {
        console.warn('获取待审核加入申请数量失败:', e?.message || e)
      }
    },

    clearPendingJoinCounts() {
      this.pendingJoinCounts = {}
      this.pendingJoinTotal = 0
      this.pendingJoinFetchedAt = 0
    }
  }
})
