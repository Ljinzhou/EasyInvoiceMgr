import dayjs from 'dayjs'

/**
 * 将日期格式化为 YYYY-MM-DD
 */
export function formatDate(date: Date | string | number): string {
  return dayjs(date).format('YYYY-MM-DD')
}

/**
 * 将时间格式化为 HH:mm:ss
 */
export function formatTime(date: Date | string | number): string {
  return dayjs(date).format('HH:mm:ss')
}

/**
 * 将日期时间格式化为 YYYY-MM-DD HH:mm:ss
 */
export function formatDateTime(date: Date | string | number): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 获取当前日期，格式为 YYYY-MM-DD
 */
export function getCurrentDate(): string {
  return formatDate(new Date())
}

/**
 * 获取当前日期时间，格式为 YYYY-MM-DD HH:mm:ss
 */
export function getCurrentDateTime(): string {
  return formatDateTime(new Date())
}

/**
 * 在日期上增加天数
 */
export function addDays(date: Date | string | number, days: number): string {
  return dayjs(date).add(days, 'day').format('YYYY-MM-DD')
}

/**
 * 从日期中减去天数
 */
export function subtractDays(date: Date | string | number, days: number): string {
  return dayjs(date).subtract(days, 'day').format('YYYY-MM-DD')
}

/**
 * 判断日期是否为今天
 */
export function isToday(date: Date | string | number): boolean {
  return dayjs(date).isSame(dayjs(), 'day')
}

/**
 * 判断日期是否在未来
 */
export function isFuture(date: Date | string | number): boolean {
  return dayjs(date).isAfter(dayjs())
}

/**
 * 判断日期是否在过去
 */
export function isPast(date: Date | string | number): boolean {
  return dayjs(date).isBefore(dayjs())
}