import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEventStore } from '../../stores/eventStore'

// Mock the cache store
vi.mock('~/stores/cache', () => ({
  useCacheStore: () => ({
    generateKey: (endpoint: string, params?: Record<string, any>) =>
      `${endpoint}:${params ? JSON.stringify(params) : ''}`,
    fetchWithCache: vi.fn(async (_key: string, fetcher: () => Promise<any>, _opts?: any) => {
      return await fetcher()
    }),
    invalidateEventCache: vi.fn()
  })
}))

// Helper to create mock event data
function makeEvent(overrides: Partial<any> = {}) {
  return {
    event_id: overrides.event_id ?? 1,
    event_name: overrides.event_name ?? '测试项目',
    description: null,
    category: null,
    location: null,
    status: overrides.status ?? 'ongoing',
    event_start_time: null,
    event_end_time: null,
    upload_start_time: null,
    upload_end_time: null,
    creator_id: null,
    leader_id: null,
    leader_name: null,
    total_budget: overrides.total_budget ?? 0,
    reimbursed_amount: overrides.reimbursed_amount ?? 0,
    remaining_budget: overrides.remaining_budget ?? 0,
    spent_amount: overrides.spent_amount ?? 0,
    invoice_total_amount: overrides.invoice_total_amount ?? 0,
    purchase_total_amount: overrides.purchase_total_amount ?? 0,
    invoice_count: overrides.invoice_count ?? 0,
    purchase_record_count: overrides.purchase_record_count ?? 0,
    voucher_count: overrides.voucher_count ?? 0,
    need_invoice_review: true
  }
}

function createMockApi(responseData: any) {
  return {
    get: vi.fn().mockResolvedValue({
      data: { code: 200, data: responseData }
    })
  }
}

describe('useEventStore', () => {
  let store: ReturnType<typeof useEventStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useEventStore()
    // Mock localStorage
    vi.stubGlobal('localStorage', {
      getItem: vi.fn().mockReturnValue('test-token'),
      setItem: vi.fn(),
      removeItem: vi.fn()
    })
  })

  describe('initial state', () => {
    it('should have empty events array', () => {
      expect(store.events).toEqual([])
    })

    it('should have dataVersion 0', () => {
      expect(store.dataVersion).toBe(0)
    })

    it('should have loading false', () => {
      expect(store.loading).toBe(false)
    })

    it('should have initialized false', () => {
      expect(store.initialized).toBe(false)
    })

    it('isStale should return true when no data fetched', () => {
      expect(store.isStale).toBe(true)
    })
  })

  describe('fullStats', () => {
    it('should return all zeros when no events', () => {
      const stats = store.fullStats
      expect(stats.totalAmount).toBe(0)
      expect(stats.invoiceTotal).toBe(0)
      expect(stats.pendingReimburse).toBe(0)
      expect(stats.totalEvents).toBe(0)
      expect(stats.budgetUsageRate).toBe(0)
      expect(stats.reimburseRate).toBe(0)
    })

    it('should compute correct statistics from events', () => {
      store.events = [
        makeEvent({
          event_id: 1,
          event_name: '比赛1',
          total_budget: 10000,
          spent_amount: 3000,
          invoice_total_amount: 2500,
          reimbursed_amount: 1500,
          invoice_count: 3,
          purchase_record_count: 2,
          voucher_count: 5,
          status: 'ongoing'
        }),
        makeEvent({
          event_id: 2,
          event_name: '比赛2',
          total_budget: 20000,
          spent_amount: 7000,
          invoice_total_amount: 6000,
          reimbursed_amount: 4000,
          invoice_count: 5,
          purchase_record_count: 3,
          voucher_count: 8,
          status: 'ongoing'
        })
      ]
      store.totalCount = 2

      const stats = store.fullStats

      expect(stats.totalEvents).toBe(2)
      expect(stats.totalAmount).toBe(10000) // 3000 + 7000
      expect(stats.invoiceTotal).toBe(8500) // 2500 + 6000
      expect(stats.invoiceCount).toBe(8) // 3 + 5
      expect(stats.purchaseCount).toBe(5) // 2 + 3
      expect(stats.totalRecords).toBe(13) // (3+2) + (5+3)
      expect(stats.reimbursedAmount).toBe(5500) // 1500 + 4000
      expect(stats.pendingReimburse).toBe(3000) // 8500 - 5500
      expect(stats.totalBudget).toBe(30000) // 10000 + 20000
      expect(stats.ongoingEvents).toBe(2)
      expect(stats.budgetUsageRate).toBe(33.3) // (10000/30000)*100
      expect(stats.reimburseRate).toBe(64.7) // (5500/8500)*100
    })

    it('should handle events with zero budget correctly', () => {
      store.events = [
        makeEvent({
          event_id: 1,
          total_budget: 0,
          spent_amount: 500,
          invoice_total_amount: 500,
          reimbursed_amount: 0
        })
      ]

      const stats = store.fullStats
      expect(stats.budgetUsageRate).toBe(0) // no division by zero
      expect(stats.reimburseRate).toBe(0)
    })

    it('pendingReimburse should never be negative', () => {
      store.events = [
        makeEvent({
          event_id: 1,
          invoice_total_amount: 500,
          reimbursed_amount: 1000 // more than invoice total
        })
      ]

      const stats = store.fullStats
      expect(stats.pendingReimburse).toBe(0)
    })
  })

  describe('totalStats', () => {
    it('should compute summary stats correctly', () => {
      store.events = [
        makeEvent({
          event_id: 1,
          spent_amount: 3000,
          invoice_total_amount: 2500,
          reimbursed_amount: 1500,
          voucher_count: 5
        }),
        makeEvent({
          event_id: 2,
          spent_amount: 7000,
          invoice_total_amount: 6000,
          reimbursed_amount: 4000,
          voucher_count: 8
        })
      ]

      const stats = store.totalStats
      expect(stats.totalAmount).toBe(10000)
      expect(stats.invoiceTotal).toBe(8500)
      expect(stats.pendingReimburse).toBe(3000)
      expect(stats.recordCount).toBe(13)
    })
  })

  describe('getEventById', () => {
    it('should return event when found', () => {
      store.events = [
        makeEvent({ event_id: 1, event_name: '比赛1' }),
        makeEvent({ event_id: 2, event_name: '比赛2' })
      ]

      const event = store.getEventById(2)
      expect(event).toBeDefined()
      expect(event!.event_name).toBe('比赛2')
    })

    it('should return undefined when not found', () => {
      store.events = [makeEvent({ event_id: 1 })]
      expect(store.getEventById(999)).toBeUndefined()
    })
  })

  describe('fetchEvents', () => {
    it('should populate events from API response', async () => {
      const mockApi = createMockApi({
        total: 1,
        page: 1,
        page_size: 100,
        data: [
          makeEvent({
            event_id: 1,
            event_name: '比赛1',
            total_budget: 10000,
            spent_amount: 3000
          })
        ]
      })

      await store.fetchEvents({ api: mockApi })

      expect(store.events).toHaveLength(1)
      expect(store.events[0].event_name).toBe('比赛1')
      expect(store.events[0].total_budget).toBe(10000)
      expect(store.events[0].spent_amount).toBe(3000)
      expect(store.totalCount).toBe(1)
      expect(store.dataVersion).toBe(1)
      expect(store.initialized).toBe(true)
      expect(store.loading).toBe(false)
    })

    it('should set error on API failure', async () => {
      const mockApi = {
        get: vi.fn().mockRejectedValue(new Error('网络错误'))
      }

      await expect(store.fetchEvents({ api: mockApi })).rejects.toThrow('网络错误')
      expect(store.error).toBe('网络错误')
      expect(store.loading).toBe(false)
    })

    it('should set error on bad API response code', async () => {
      const mockApi = {
        get: vi.fn().mockResolvedValue({
          data: { code: 500, message: '服务器错误' }
        })
      }

      await store.fetchEvents({ api: mockApi })
      expect(store.error).toBe('服务器错误')
    })

    it('should increment dataVersion on successful fetch', async () => {
      const mockApi = createMockApi({ total: 0, page: 1, page_size: 100, data: [] })

      expect(store.dataVersion).toBe(0)
      await store.fetchEvents({ api: mockApi })
      expect(store.dataVersion).toBe(1)

      await store.fetchEvents({ api: mockApi, forceRefresh: true })
      expect(store.dataVersion).toBe(2)
    })
  })

  describe('ensureLoaded', () => {
    it('should fetch if not initialized', async () => {
      const mockApi = createMockApi({ total: 1, page: 1, page_size: 100, data: [makeEvent()] })

      await store.ensureLoaded({ pageSize: 10, api: mockApi })
      expect(store.initialized).toBe(true)
      expect(store.events).toHaveLength(1)
    })

    it('should skip fetch if already loaded and not stale', async () => {
      store.events = [makeEvent()]
      store.initialized = true
      store.lastFetchTime = Date.now()

      await store.ensureLoaded()
      expect(store.events).toHaveLength(1) // unchanged, no fetch triggered
    })
  })

  describe('invalidateAndRefresh', () => {
    it('should invalidate cache and re-fetch events', async () => {
      const mockApi = createMockApi({
        total: 1,
        page: 1,
        page_size: 100,
        data: [makeEvent({ event_id: 1, event_name: '更新后的项目' })]
      })

      // First fetch
      await store.fetchEvents({ api: mockApi })
      expect(store.events[0].event_name).toBe('更新后的项目')

      // Simulate data update response
      const updatedApi = createMockApi({
        total: 1,
        page: 1,
        page_size: 100,
        data: [makeEvent({ event_id: 1, event_name: '更新后的项目', spent_amount: 5000 })]
      })

      await store.invalidateAndRefresh({ api: updatedApi, eventId: 1 })
      expect(store.events[0].spent_amount).toBe(5000)
    })
  })

  describe('reactive updates (data sync)', () => {
    it('fullStats should update reactively when events change', () => {
      store.events = [makeEvent({ event_id: 1, spent_amount: 1000 })]
      expect(store.fullStats.totalAmount).toBe(1000)

      // Update events directly (simulating API refresh)
      store.events = [
        makeEvent({ event_id: 1, spent_amount: 2000 }),
        makeEvent({ event_id: 2, spent_amount: 3000 })
      ]
      expect(store.fullStats.totalAmount).toBe(5000) // 2000 + 3000
    })

    it('dataVersion should track changes for watch-based sync', async () => {
      const mockApi = createMockApi({
        total: 1,
        page: 1,
        page_size: 100,
        data: [makeEvent({ event_id: 1 })]
      })

      const versions: number[] = []
      // Simulate what components do with watch
      store.$subscribe(() => {
        versions.push(store.dataVersion)
      })

      await store.fetchEvents({ api: mockApi })
      expect(versions).toContain(1)
    })

    it('refreshAfterMutation should invalidate and refresh', async () => {
      const mockApi = createMockApi({
        total: 1,
        page: 1,
        page_size: 100,
        data: [makeEvent({ event_id: 1, spent_amount: 9999 })]
      })

      // Use invalidateAndRefresh directly with api injection for testing
      await store.invalidateAndRefresh({ eventId: 1, api: mockApi })
      expect(store.events[0].spent_amount).toBe(9999)
    })
  })

  describe('isStale', () => {
    it('should return true when no fetch has occurred', () => {
      expect(store.isStale).toBe(true)
    })

    it('should return false when recently fetched', () => {
      store.lastFetchTime = Date.now()
      expect(store.isStale).toBe(false)
    })

    it('should return true when cache expired', () => {
      store.lastFetchTime = Date.now() - 4 * 60 * 1000 // 4 minutes ago
      expect(store.isStale).toBe(true)
    })
  })
})
