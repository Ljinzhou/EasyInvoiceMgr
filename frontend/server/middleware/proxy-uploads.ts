/**
 * 将 /uploads/** 代理到后端，并保留完整路径。
 *
 * 替代 routeRules.proxy —— 后者会通过 _proxyStripBase 自动去掉 /uploads，
 * 导致后端收到的是 /avatars/... 而非 /uploads/avatars/...
 */
export default defineEventHandler(async (event) => {
  if (!event.path.startsWith('/uploads/')) return

  const backendHost = process.env.NODE_ENV === 'development'
    ? 'http://localhost:5000'
    : 'http://backend:5000'

  return proxyRequest(event, backendHost + event.path)
})
