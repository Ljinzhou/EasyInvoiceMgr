export function useUploadUrl() {
  function getUploadUrl(path: string | null | undefined): string {
    if (!path) return ''
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    return path.startsWith('/') ? path : '/' + path
  }

  return { getUploadUrl }
}
