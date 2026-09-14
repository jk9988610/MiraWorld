import { ref, computed } from 'vue'

export interface AuthUser {
  id: number
  handle: string
  email: string | null
  city: string
  wallet_credits: number
  bio: string
  created_at: string
  visit_count?: number
}

const API_BASE = '/miraworld/api'
const REMEMBER_KEY = 'mw_remember'
const HANDLE_KEY = 'mw_handle'

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

function readRememberPrefs() {
  try {
    return {
      remember: localStorage.getItem(REMEMBER_KEY) === '1',
      handle: localStorage.getItem(HANDLE_KEY) || '',
    }
  } catch {
    return { remember: false, handle: '' }
  }
}

function writeRememberPrefs(remember: boolean, handle: string) {
  try {
    if (remember) {
      localStorage.setItem(REMEMBER_KEY, '1')
      localStorage.setItem(HANDLE_KEY, handle)
    } else {
      localStorage.removeItem(REMEMBER_KEY)
      localStorage.removeItem(HANDLE_KEY)
    }
  } catch {
    /* ignore */
  }
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

  async function register(handle: string, password: string, email?: string, remember = false) {
    loading.value = true
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handle, password, email: email || null, remember }),
      })
      user.value = await parseJson<AuthUser>(res)
      writeRememberPrefs(remember, handle)
      return user.value
    } finally {
      loading.value = false
      checked.value = true
    }
  }

  async function login(handle: string, password: string, remember = false) {
    loading.value = true
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handle, password, remember }),
      })
      user.value = await parseJson<AuthUser>(res)
      writeRememberPrefs(remember, handle)
      return user.value
    } finally {
      loading.value = false
      checked.value = true
    }
  }

  async function logout() {
    loading.value = true
    try {
      await fetch(`${API_BASE}/world/autosave`, {
        method: 'POST',
        credentials: 'include',
      }).catch(() => {})
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
    readRememberPrefs,
  }
}
