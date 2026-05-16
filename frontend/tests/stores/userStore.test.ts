/**
 * UserStore Tests
 * Tests for localStorage-based user state management
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../../stores/userStore'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

vi.stubGlobal('localStorage', localStorageMock)

// Mock process.client - userStore checks process.client before accessing localStorage
vi.stubGlobal('process', { client: true, env: { NODE_ENV: 'test' } })

describe('useUserStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorageMock.clear()
  })

  describe('initial state', () => {
    it('should have null user by default', () => {
      const store = useUserStore()
      expect(store.user).toBeNull()
      expect(store.avatarUrl).toBe('')
    })

    it('should have correct computed defaults', () => {
      const store = useUserStore()
      expect(store.realName).toBe('未登录')
      expect(store.userType).toBe('')
      expect(store.userRole).toBe('未知')
    })
  })

  describe('loadFromStorage', () => {
    it('should load user from localStorage when present', () => {
      const mockUser = {
        user_id: 1,
        username: 'testuser',
        real_name: 'Test User',
        user_type: 'student',
        avatar_url: '/uploads/avatar.jpg',
      }
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockUser))

      const store = useUserStore()
      store.loadFromStorage()

      expect(store.user).toEqual(mockUser)
      expect(store.avatarUrl).toBe('/uploads/avatar.jpg')
      expect(store.realName).toBe('Test User')
      expect(store.userType).toBe('student')
      expect(store.userRole).toBe('学生')
    })

    it('should handle missing localStorage gracefully', () => {
      localStorageMock.getItem.mockReturnValueOnce(null)

      const store = useUserStore()
      store.loadFromStorage()

      expect(store.user).toBeNull()
      expect(store.realName).toBe('未登录')
    })
  })

  describe('saveToStorage', () => {
    it('should persist user to localStorage', () => {
      const store = useUserStore()
      store.saveToStorage({
        user_id: 2,
        username: 'newuser',
        real_name: 'New User',
        user_type: 'teacher',
        avatar_url: '/uploads/new.jpg',
      })

      expect(localStorageMock.setItem).toHaveBeenCalled()
      const savedData = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1]
      )
      expect(savedData.username).toBe('newuser')
      expect(savedData.user_type).toBe('teacher')
    })

    it('should merge with existing user data', () => {
      const store = useUserStore()
      store.saveToStorage({
        user_id: 1,
        username: 'original',
        real_name: 'Original',
        user_type: 'student',
      })
      store.saveToStorage({ real_name: 'Updated Name' })

      const savedData = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1]
      )
      expect(savedData.real_name).toBe('Updated Name')
      expect(savedData.username).toBe('original')
    })
  })

  describe('updateAvatar', () => {
    it('should update avatar URL and persist', () => {
      const store = useUserStore()
      store.saveToStorage({
        user_id: 1,
        username: 'u',
        real_name: 'U',
        user_type: 'student',
        avatar_url: '/old.jpg',
      })

      store.updateAvatar('/uploads/new_avatar.jpg')
      expect(store.avatarUrl).toBe('/uploads/new_avatar.jpg')

      const savedData = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1]
      )
      expect(savedData.avatar_url).toBe('/uploads/new_avatar.jpg')
    })
  })

  describe('clearUser', () => {
    it('should reset all user state', () => {
      const store = useUserStore()
      store.saveToStorage({
        user_id: 1,
        username: 'test',
        real_name: 'Test',
        user_type: 'admin',
        avatar_url: '/avatar.jpg',
      })

      store.clearUser()

      expect(store.user).toBeNull()
      expect(store.avatarUrl).toBe('')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('user')
    })
  })

  describe('userRole mapping', () => {
    it.each([
      ['admin', '管理员'],
      ['teacher', '教师'],
      ['student_admin', '学生管理员'],
      ['student', '学生'],
    ])('should map %s to %s', (type, label) => {
      const store = useUserStore()
      store.saveToStorage({
        user_id: 1,
        username: 'u',
        real_name: 'U',
        user_type: type,
      })
      expect(store.userRole).toBe(label)
    })

    it('should return 未知 for unknown type', () => {
      const store = useUserStore()
      store.saveToStorage({
        user_id: 1,
        username: 'u',
        real_name: 'U',
        user_type: 'super_admin',
      })
      expect(store.userRole).toBe('未知')
    })
  })

  describe('initial getter', () => {
    it('should return uppercase first char of real name', () => {
      const store = useUserStore()
      store.saveToStorage({
        user_id: 1,
        username: 'zhangsan',
        real_name: '张三',
        user_type: 'student',
      })
      expect(store.initial).toBe('张')
    })

    it('should return initial from default display name when no user', () => {
      const store = useUserStore()
      // Pinia unwraps refs: store.user is the raw value, not a Ref
      expect(store.user).toBeNull()
      // When no user, realName is '未登录', so initial = '未'
      expect(store.realName).toBe('未登录')
      expect(store.initial).toBe(store.realName.charAt(0).toUpperCase())
    })
  })
})
