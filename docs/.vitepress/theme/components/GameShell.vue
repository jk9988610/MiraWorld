<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vitepress'
import { useShellPolling, shellUnreadCount } from '../composables/useShellState'
import { useAuth } from '../composables/useAuth'
import { useGame } from '../composables/useGame'

const route = useRoute()
const { refresh, isLoggedIn, checked } = useAuth()
const { loadWorldSession } = useGame()
useShellPolling()

function playPath(path: string) {
  return path.includes('/play/')
}

function isGatePath(path: string) {
  return path.includes('/play/gate')
}

const show = computed(() => playPath(route.path))
const path = computed(() => route.path)
const isGate = computed(() => isGatePath(path.value))
const showTabs = computed(() => show.value && !isGate.value)

async function enforceAccess() {
  if (!show.value) return
  await refresh()
  if (!isLoggedIn.value) {
    if (!isGate.value) {
      window.location.replace('/miraworld/play/gate.html')
    }
    return
  }
  if (isGate.value) return
  try {
    const sess = await loadWorldSession()
    if (!sess.active) {
      window.location.replace('/miraworld/play/gate.html')
    }
  } catch {
    window.location.replace('/miraworld/play/gate.html')
  }
}

onMounted(() => {
  enforceAccess()
})

watch(
  () => route.path,
  () => {
    enforceAccess()
  },
)

const unreadBadge = computed(() => {
  const n = shellUnreadCount.value
  if (n <= 0) return ''
  return n > 99 ? '99+' : String(n)
})
</script>

<template>
  <nav v-if="showTabs && checked" class="mw-game-shell" aria-label="游戏导航">
    <a
      href="/miraworld/play/city.html"
      class="mw-tab"
      :class="{ active: path.includes('/play/city') }"
    >
      地图
    </a>
    <a
      href="/miraworld/play/messages.html"
      class="mw-tab mw-tab--notify"
      :class="{ active: path.includes('/play/messages') }"
      :aria-label="unreadBadge ? `通知，${unreadBadge} 条未读` : '通知'"
    >
      <span class="mw-tab-label">通知</span>
      <span v-if="unreadBadge" class="mw-badge" aria-hidden="true">{{ unreadBadge }}</span>
    </a>
    <a
      href="/miraworld/play/stacks.html"
      class="mw-tab"
      :class="{ active: path.includes('/play/stacks') }"
    >
      背包
    </a>
    <a
      href="/miraworld/play/me.html"
      class="mw-tab"
      :class="{ active: path.includes('/play/me') }"
    >
      我的
    </a>
  </nav>
</template>

<style scoped>
.mw-game-shell {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  display: flex;
  justify-content: space-around;
  gap: 0.25rem;
  padding: 0.35rem 0.5rem calc(0.35rem + env(safe-area-inset-bottom));
  border-top: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-elv);
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
}

.mw-tab {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0.5rem 0.35rem;
  font-size: 0.8125rem;
  color: var(--vp-c-text-2);
  text-decoration: none;
  border-radius: 8px;
  border: none;
  background: transparent;
  font: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.mw-tab:active {
  background: var(--vp-c-bg-soft);
}

.mw-tab.active {
  color: var(--vp-c-brand-1);
  font-weight: 600;
  background: color-mix(in srgb, var(--vp-c-brand-1) 8%, transparent);
}

.mw-tab--notify {
  flex-direction: column;
  gap: 0.15rem;
}

.mw-tab-label {
  line-height: 1.2;
}

.mw-badge {
  position: absolute;
  top: 4px;
  right: calc(50% - 2rem);
  min-width: 1.125rem;
  height: 1.125rem;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: #e74c3c;
  color: #fff;
  font-size: 0.6875rem;
  font-weight: 700;
  line-height: 1.125rem;
  text-align: center;
}

@media (min-width: 480px) {
  .mw-badge {
    right: calc(50% - 2.25rem);
  }
}
</style>
