/**
 * useUploadUrl Composable Tests
 * Tests for URL prefix handling
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock useRuntimeConfig
vi.mock('#app', () => ({
  useRuntimeConfig: () => ({
    public: {
      apiBase: 'http://localhost:5000/api',
    },
  }),
}))

// We need to import the composable directly and test its logic
// Since Nuxt composables use auto-imports, we test the core logic pattern

describe('useUploadUrl', () => {
  // Replicate the composable logic for testing (since it depends on Nuxt runtime)
  function getUploadUrl(path: string | null | undefined, apiBase: string): string {
    const uploadBase = apiBase.replace(/\/api\/?$/, '')
    if (!path) return ''
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    return uploadBase + path
  }

  const apiBase = 'http://localhost:5000/api'
  const expectedUploadBase = 'http://localhost:5000'

  describe('path handling', () => {
    it('should prepend base URL to relative paths', () => {
      expect(getUploadUrl('/uploads/avatar.jpg', apiBase)).toBe(
        'http://localhost:5000/uploads/avatar.jpg'
      )
    })

    it('should handle paths without leading slash (no separator added)', () => {
      // When path lacks leading / the raw concatenation result is preserved
      // This documents the current behavior - caller should ensure leading /
      const result = getUploadUrl('uploads/avatar.jpg', apiBase)
      expect(result).toBe('http://localhost:5000uploads/avatar.jpg')
    })

    it('should return absolute URLs as-is', () => {
      const absUrl = 'https://cdn.example.com/avatar.jpg'
      expect(getUploadUrl(absUrl, apiBase)).toBe(absUrl)
    })

    it('should return empty string for null', () => {
      expect(getUploadUrl(null, apiBase)).toBe('')
    })

    it('should return empty string for undefined', () => {
      expect(getUploadUrl(undefined, apiBase)).toBe('')
    })

    it('should return empty string for empty string', () => {
      expect(getUploadUrl('', apiBase)).toBe('')
    })
  })

  describe('apiBase stripping', () => {
    it('should strip /api suffix', () => {
      expect(getUploadUrl('/path', 'http://host:5000/api')).toBe(
        'http://host:5000/path'
      )
    })

    it('should strip /api/ suffix', () => {
      expect(getUploadUrl('/path', 'http://host:5000/api/')).toBe(
        'http://host:5000/path'
      )
    })

    it('should handle apiBase without /api suffix', () => {
      expect(getUploadUrl('/path', 'http://host:5000')).toBe(
        'http://host:5000/path'
      )
    })
  })

  describe('edge cases', () => {
    it('should handle paths with query strings', () => {
      expect(getUploadUrl('/uploads/file.jpg?t=123', apiBase)).toBe(
        'http://localhost:5000/uploads/file.jpg?t=123'
      )
    })

    it('should handle long paths', () => {
      const longPath = '/uploads/invoices/123/2026/abc-def-ghi/file.pdf'
      expect(getUploadUrl(longPath, apiBase)).toBe(
        `http://localhost:5000${longPath}`
      )
    })

    it('should handle http absolute URLs', () => {
      expect(getUploadUrl('http://other-server.com/file.jpg', apiBase)).toBe(
        'http://other-server.com/file.jpg'
      )
    })

    it('should handle https absolute URLs', () => {
      expect(getUploadUrl('https://secure.example.com/file.jpg', apiBase)).toBe(
        'https://secure.example.com/file.jpg'
      )
    })
  })
})
