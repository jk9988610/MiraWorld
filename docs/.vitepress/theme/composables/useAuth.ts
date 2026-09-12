import { ref, computed } from 'vue'

export interface AuthUser {
  id: number
  email: string
  display_name: string
  created_at: string
}

const API_BASE = '/miraworld/api'
const user = ref<AuthUser | null>(null)
const loading = ref(false)
const checked = ref(false)

async function parseJson<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const message =
      typeof data.detail === 'string'
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('；')
          : '请求失败'
    throw new Error(message || `HTTP ${res.status}`)
  }
  return data as T
}

export function useAuth() {
  const isLoggedIn = computed(() => user.value !== null)

  async function refresh() {
    loading.value = true
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
      if (res.status === 401) {
        user.value = null
        return null
      }
      user.value = await parseJson<AuthUser>(res)
      return user.value
    } catch {
      user.value = null
      return null
    } finally {
      loading.value = false
      checked.value = true
    }
  }

  async function register(email: string, password: string, displayName: string) {
    loading.value = true
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          display_name: displayName,
        }),
      })
      user.value = await parseJson<AuthUser>(res)
      return user.value
    } finally {
      loading.value = false
      checked.value = true
    }
  }

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      user.value = await parseJson<AuthUser>(res)
      return user.value
    } finally {
      loading.value = false
      checked.value = true
    }
  }

  async function logout() {
    loading.value = true
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
      user.value = null
    } finally {
      loading.value = false
      checked.value = true
    }
  }

  return {
    user,
    loading,
    checked,
    isLoggedIn,
    refresh,
    register,
    login,
    logout,
  }
}
