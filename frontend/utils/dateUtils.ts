import dayjs from 'dayjs'

/**
 * Format date to YYYY-MM-DD
 */
export function formatDate(date: Date | string | number): string {
  return dayjs(date).format('YYYY-MM-DD')
}

/**
 * Format time to HH:mm:ss
 */
export function formatTime(date: Date | string | number): string {
  return dayjs(date).format('HH:mm:ss')
}

/**
 * Format datetime to YYYY-MM-DD HH:mm:ss
 */
export function formatDateTime(date: Date | string | number): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

/**
 * Get current date as YYYY-MM-DD
 */
export function getCurrentDate(): string {
  return formatDate(new Date())
}

/**
 * Get current datetime as YYYY-MM-DD HH:mm:ss
 */
export function getCurrentDateTime(): string {
  return formatDateTime(new Date())
}

/**
 * Add days to date
 */
export function addDays(date: Date | string | number, days: number): string {
  return dayjs(date).add(days, 'day').format('YYYY-MM-DD')
}

/**
 * Subtract days from date
 */
export function subtractDays(date: Date | string | number, days: number): string {
  return dayjs(date).subtract(days, 'day').format('YYYY-MM-DD')
}

/**
 * Check if date is today
 */
export function isToday(date: Date | string | number): boolean {
  return dayjs(date).isSame(dayjs(), 'day')
}

/**
 * Check if date is in future
 */
export function isFuture(date: Date | string | number): boolean {
  return dayjs(date).isAfter(dayjs())
}

/**
 * Check if date is in past
 */
export function isPast(date: Date | string | number): boolean {
  return dayjs(date).isBefore(dayjs())
}