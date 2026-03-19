const BASE_URL = '/api'

function getToken(): string | null {
  return localStorage.getItem('gromo-token')
}

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    // Token expired or invalid — clear auth and redirect to login
    localStorage.removeItem('gromo-token')
    localStorage.removeItem('gromo-user')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}
