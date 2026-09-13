import { ref, onMounted, onUnmounted } from 'vue'

const API_BASE = '/miraworld/api'
const POLL_MS = 60_000

/** 壳层共享：通知未读数 */
export const shellUnreadCount = ref(0)

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollListeners = 0

export async function refreshUnreadCount(): Promise<number> {
  if (typeof window === 'undefined') return 0
  try {
    const res = await fetch(`${API_BASE}/records/messages/summary`, {
      credentials: 'include',
    })
    if (res.status === 401) {
      shellUnreadCount.value = 0
      return 0
    }
    if (!res.ok) return shellUnreadCount.value
    const data = (await res.json()) as { unread_count?: number }
    shellUnreadCount.value = Math.max(0, Number(data.unread_count) || 0)
    return shellUnreadCount.value
  } catch {
    return shellUnreadCount.value
  }
}

function tick() {
  if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return
  void refreshUnreadCount()
}

function startPolling() {
  if (pollTimer !== null) return
  tick()
  pollTimer = setInterval(tick, POLL_MS)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') void refreshUnreadCount()
}

/** 游戏壳层：60s 慢轮询未读（标签页可见时） */
export function useShellPolling() {
  onMounted(() => {
    if (!window.location.pathname.includes('/play/')) return
    pollListeners += 1
    if (pollListeners === 1) {
      document.addEventListener('visibilitychange', onVisibilityChange)
      startPolling()
    } else {
      void refreshUnreadCount()
    }
  })

  onUnmounted(() => {
    pollListeners = Math.max(0, pollListeners - 1)
    if (pollListeners === 0) {
      stopPolling()
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  })

  return { shellUnreadCount, refreshUnreadCount }
}
