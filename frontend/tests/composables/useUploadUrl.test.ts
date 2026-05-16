/**
 * useUploadUrl Composable Tests
 * Tests for URL path handling - returns relative paths for frontend proxy.
 *
 * In production, the Nitro server proxies /uploads/** to the backend,
 * so all upload paths are returned as relative URLs (same-origin).
 */
import { describe, it, expect } from 'vitest'

function getUploadUrl(path: string | null | undefined): string {
    if (!path) return ''
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    return path.startsWith('/') ? path : '/' + path
}

describe('useUploadUrl getUploadUrl logic', () => {

    describe('path handling', () => {
        it('should return relative path as-is when it starts with /', () => {
            expect(getUploadUrl('/uploads/avatar.jpg')).toBe('/uploads/avatar.jpg')
        })

        it('should add leading slash when path lacks it', () => {
            expect(getUploadUrl('uploads/avatar.jpg')).toBe('/uploads/avatar.jpg')
        })

        it('should return absolute URLs as-is', () => {
            const absUrl = 'https://cdn.example.com/avatar.jpg'
            expect(getUploadUrl(absUrl)).toBe(absUrl)
        })

        it('should return http absolute URLs as-is', () => {
            expect(getUploadUrl('http://other-server.com/file.jpg')).toBe(
                'http://other-server.com/file.jpg'
            )
        })

        it('should return empty string for null', () => {
            expect(getUploadUrl(null)).toBe('')
        })

        it('should return empty string for undefined', () => {
            expect(getUploadUrl(undefined)).toBe('')
        })

        it('should return empty string for empty string', () => {
            expect(getUploadUrl('')).toBe('')
        })
    })

    // ── Avatar-specific scenarios ──────────────────────────────────────────

    describe('avatar URL resolution', () => {
        it('should resolve local backend avatar path to same-origin relative URL', () => {
            // Backend returns: /uploads/avatars/1/20260516_abc12345.png
            // Frontend proxy serves it at same origin
            const avatarPath = '/uploads/avatars/1/20260516_abc12345.png'
            expect(getUploadUrl(avatarPath)).toBe(avatarPath)
            // This ensures browser requests http://frontend:3000/uploads/avatars/1/...
            // which Nitro proxies to http://backend:5000/uploads/avatars/1/...
        })

        it('should handle avatar path with COS-style subdirectory', () => {
            // LocalStorage generates: avatars/{user_id}/{timestamp}_{uuid}.{ext}
            const avatarPath = '/uploads/avatars/42/20260516120000_a1b2c3d4.png'
            expect(getUploadUrl(avatarPath)).toBe(avatarPath)
        })

        it('should handle avatar path with legacy flat format', () => {
            // Legacy format: /uploads/avatars/{user_id}_{uuid}.{ext}
            const avatarPath = '/uploads/avatars/5_e8f3a2b1.jpg'
            expect(getUploadUrl(avatarPath)).toBe(avatarPath)
        })

        it('should handle webp avatar format', () => {
            const avatarPath = '/uploads/avatars/10/20260516_ff00aa11.webp'
            expect(getUploadUrl(avatarPath)).toBe(avatarPath)
        })

        it('should return external COS URLs unchanged', () => {
            const cosUrl = 'https://cos.ap-guangzhou.myqcloud.com/avatars/1/xxx.png'
            expect(getUploadUrl(cosUrl)).toBe(cosUrl)
        })

        it('should return empty for null avatar (no avatar set)', () => {
            expect(getUploadUrl(null)).toBe('')
        })
    })

    // ── Proxy correctness ──────────────────────────────────────────────────

    describe('proxy path integrity', () => {
        it('should preserve path so Nitro proxy forwards correctly', () => {
            // The returned path must be exactly what the backend expects
            // Backend route: @app.route('/uploads/<path:filename>')
            // When the frontend proxies /uploads/avatars/1/xxx.png to backend:5000,
            // the backend receives: /uploads/avatars/1/xxx.png -> filename = 'avatars/1/xxx.png'
            const avatarPath = '/uploads/avatars/1/20260516_abc12345.png'
            const resolved = getUploadUrl(avatarPath)
            // Must start with /uploads/ so the Nitro route rule matches
            expect(resolved).toMatch(/^\/uploads\//)
            // Must end with the unique filename
            expect(resolved).toMatch(/20260516_abc12345\.png$/)
        })

        it('should handle paths with multiple path segments', () => {
            const deepPath = '/uploads/invoices/5/submissions/2026/doc.pdf'
            expect(getUploadUrl(deepPath)).toBe(deepPath)
        })
    })

    describe('edge cases', () => {
        it('should handle paths with query strings', () => {
            expect(getUploadUrl('/uploads/file.jpg?t=123')).toBe(
                '/uploads/file.jpg?t=123'
            )
        })

        it('should handle long paths', () => {
            const longPath = '/uploads/invoices/123/2026/abc-def-ghi/file.pdf'
            expect(getUploadUrl(longPath)).toBe(longPath)
        })

        it('should not mutate paths without uploads prefix', () => {
            expect(getUploadUrl('/some/other/path')).toBe('/some/other/path')
        })

        it('should not double-slash paths already starting with /', () => {
            expect(getUploadUrl('/uploads/avatar.jpg')).toBe('/uploads/avatar.jpg')
        })
    })
})
