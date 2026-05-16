/**
 * Proxy /uploads/** to the backend preserving the full path.
 *
 * Replaces routeRules.proxy which auto-strips /uploads via _proxyStripBase
 * causing the backend to receive /avatars/... instead of /uploads/avatars/...
 */
export default defineEventHandler(async (event) => {
  if (!event.path.startsWith('/uploads/')) return

  const backendHost = process.env.NODE_ENV === 'development'
    ? 'http://localhost:5000'
    : 'http://backend:5000'

  return proxyRequest(event, backendHost + event.path)
})
