export function useUploadUrl() {
  const config = useRuntimeConfig()
  const apiBase: string = config.public.apiBase // e.g. "http://localhost:5000/api"
  const uploadBase = apiBase.replace(/\/api\/?$/, '')

  function getUploadUrl(path: string | null | undefined): string {
    if (!path) return ''
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    return uploadBase + path
  }

  return { getUploadUrl }
}
