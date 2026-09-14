<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vitepress'
import { useGame, type PlayerFocus, type WorldClock } from '../composables/useGame'

const route = useRoute()
const { loadWorldClock, loadFocus, loadWorldSession, setWorldSpeed } = useGame()

const clock = ref<WorldClock | null>(null)
const focus = ref<PlayerFocus | null>(null)
const sessionScope = ref<string | null>(null)
let timer: ReturnType<typeof setInterval> | undefined

const show = computed(
  () => route.path.startsWith('/play/') && !route.path.includes('/play/gate'),
)

const focusLabel = computed(() => {
  if (!focus.value) return ''
  return focus.value.focus === 'company' ? '上班' : '下班'
})

async function refreshBar() {
  try {
    const sess = await loadWorldSession()
    if (!sess.active) return
    sessionScope.value = sess.save?.scope ?? null
    clock.value = await loadWorldClock()
    focus.value = await loadFocus()
  } catch {
    /* ignore */
  }
}

async function onSpeed(speed: string) {
  if (sessionScope.value !== 'solo') return
  clock.value = await setWorldSpeed(speed)
}

onMounted(() => {
  refreshBar()
  timer = setInterval(refreshBar, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div v-if="show && clock" class="mw-status">
    <span class="mw-status-item">第 {{ clock.world_day }} 日</span>
    <span class="mw-status-item">速度 {{ clock.speed_label }}</span>
    <span v-if="focusLabel" class="mw-status-item mw-status-focus">{{ focusLabel }}</span>
    <span v-if="clock.next_tick_hint" class="mw-status-item mw-dim">{{ clock.next_tick_hint }}</span>
    <span v-if="sessionScope === 'solo'" class="mw-speeds">
      <button type="button" class="mw-spd" @click="onSpeed('pause')">停</button>
      <button type="button" class="mw-spd" @click="onSpeed('slow')">慢</button>
      <button type="button" class="mw-spd" @click="onSpeed('mid')">中</button>
      <button type="button" class="mw-spd" @click="onSpeed('fast')">快</button>
    </span>
  </div>
</template>

<style scoped>
.mw-status {
  position: fixed;
  top: var(--vp-nav-height, 64px);
  left: 0;
  right: 0;
  z-index: 40;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 0.75rem;
  align-items: center;
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
  border-bottom: 1px solid var(--vp-c-divider);
  background: color-mix(in srgb, var(--vp-c-bg-elv) 92%, transparent);
}
.mw-status-item { color: var(--vp-c-text-2); }
.mw-status-focus { color: var(--vp-c-brand-1); font-weight: 600; }
.mw-dim { color: var(--vp-c-text-3); }
.mw-speeds { display: flex; gap: 0.25rem; margin-left: auto; }
.mw-spd {
  min-width: 1.75rem;
  padding: 0.15rem 0.35rem;
  border-radius: 4px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg);
  font-size: 0.6875rem;
  cursor: pointer;
}
</style>
