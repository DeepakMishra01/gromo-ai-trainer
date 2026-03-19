/**
 * Authenticated fetch wrapper. Adds JWT Bearer token to all requests.
 * Use this instead of raw `fetch()` for API calls.
 */
export function authFetch(url: string, options?: RequestInit): Promise<Response> {
  const token = localStorage.getItem('gromo-token')
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  }

  // Add Content-Type for JSON bodies (unless it's FormData)
  if (options?.body && typeof options.body === 'string') {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return fetch(url, { ...options, headers }).then(res => {
    if (res.status === 401) {
      localStorage.removeItem('gromo-token')
      localStorage.removeItem('gromo-user')
      window.location.href = '/login'
    }
    return res
  })
}
