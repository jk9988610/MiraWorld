<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { useRoute } from 'vitepress'
import { useAuth } from '../composables/useAuth'
import { useGame } from '../composables/useGame'
import {
  clearHud,
  hudActive,
  hudDay,
  hudFocusLabel,
  hudTickNonce,
  hudScope,
  hudSpeedLabel,
  setHudFromClock,
} from '../composables/worldHud'

const route = useRoute()
const { isLoggedIn, refresh } = useAuth()
const { loadWorldSession, loadWorldClock, loadFocus, setWorldSpeed, advanceSoloTick } = useGame()

const ticking = ref(false)
const speedBusy = ref(false)
const hudError = ref('')
const localNavEl = ref<Element | null>(null)
let timer: ReturnType<typeof setInterval> | undefined
let observer: MutationObserver | undefined

const inGame = computed(() => {
  const p = route.path
  return p.includes('/play/') && !p.includes('/play/gate')
})

const showHud = computed(() => inGame.value && hudActive.value && isLoggedIn.value)

async function refreshHud() {
  document.documentElement.classList.toggle('mw-play-hud', inGame.value)
  if (!inGame.value || !isLoggedIn.value) {
    clearHud()
    return
  }
  try {
    const sess = await loadWorldSession()
    if (!sess.active || !sess.save) {
      clearHud()
      return
    }
    const clock = await loadWorldClock()
    let focusLabel = ''
    try {
      const focus = await loadFocus()
      focusLabel = focus.focus === 'company' ? '上班' : '下班'
    } catch {
      /* ignore */
    }
    setHudFromClock({
      active: true,
      scope: sess.save.scope,
      world_day: clock.world_day,
      speed_label: clock.speed_label,
      focusLabel,
    })
    hudError.value = ''
  } catch (e) {
    hudError.value = e instanceof Error ? e.message : '状态失败'
  }
}

function bindLocalNav() {
  localNavEl.value = document.querySelector('.VPLocalNav')
}

async function onAdvanceDay() {
  if (hudScope.value !== 'solo' || ticking.value) return
  ticking.value = true
  hudError.value = ''
  try {
    const result = await advanceSoloTick()
    hudDay.value = result.world_day
    hudTickNonce.value += 1
  } catch (e) {
    hudError.value = e instanceof Error ? e.message : '推进失败'
  } finally {
    ticking.value = false
  }
}

async function onSpeed(speed: string) {
  if (hudScope.value !== 'solo' || speedBusy.value) return
  speedBusy.value = true
  try {
    const clock = await setWorldSpeed(speed)
    hudSpeedLabel.value = clock.speed_label
    hudDay.value = clock.world_day
  } catch (e) {
    hudError.value = e instanceof Error ? e.message : '调速失败'
  } finally {
    speedBusy.value = false
  }
}

onMounted(async () => {
  await refresh()
  await nextTick()
  bindLocalNav()
  observer = new MutationObserver(() => bindLocalNav())
  observer.observe(document.body, { childList: true, subtree: true })
  await refreshHud()
  timer = setInterval(refreshHud, 1000)
})

watch(
  () => route.path,
  async () => {
    await nextTick()
    bindLocalNav()
    refreshHud()
  },
)

onUnmounted(() => {
  if (timer) clearInterval(timer)
  observer?.disconnect()
  document.documentElement.classList.remove('mw-play-hud')
})
</script>

<template>
  <Teleport v-if="localNavEl && showHud" :to="localNavEl">
    <div class="mw-local-hud" @click.stop>
      <span class="mw-hud-item">第 {{ hudDay }} 日</span>
      <span class="mw-hud-item">{{ hudSpeedLabel }}</span>
      <span v-if="hudFocusLabel" class="mw-hud-item mw-hud-focus">{{ hudFocusLabel }}</span>
      <template v-if="hudScope === 'solo'">
        <button type="button" class="mw-hud-btn mw-hud-advance" :disabled="ticking" @click.prevent="onAdvanceDay">
          {{ ticking ? '…' : '推进一日' }}
        </button>
        <button type="button" class="mw-hud-btn" :disabled="speedBusy" @click.prevent="onSpeed('pause')">停</button>
        <button type="button" class="mw-hud-btn" :disabled="speedBusy" @click.prevent="onSpeed('slow')">慢</button>
        <button type="button" class="mw-hud-btn" :disabled="speedBusy" @click.prevent="onSpeed('mid')">中</button>
        <button type="button" class="mw-hud-btn" :disabled="speedBusy" @click.prevent="onSpeed('fast')">快</button>
      </template>
      <span v-else class="mw-hud-item mw-dim">多人</span>
      <span v-if="hudError" class="mw-hud-err" :title="hudError">!</span>
    </div>
  </Teleport>
</template>

<style scoped>
.mw-local-hud {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  gap: 0.3rem 0.4rem;
  margin: 0 0.5rem;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  pointer-events: auto;
}

.mw-hud-item {
  font-size: 0.75rem;
  color: var(--vp-c-text-2);
  white-space: nowrap;
  flex-shrink: 0;
}

.mw-hud-focus {
  color: var(--vp-c-brand-1);
  font-weight: 600;
}

.mw-dim {
  color: var(--vp-c-text-3);
}

.mw-hud-err {
  color: #c0392b;
  font-weight: 700;
  cursor: help;
  flex-shrink: 0;
}

.mw-hud-btn {
  flex-shrink: 0;
  padding: 0.2rem 0.45rem;
  border-radius: 4px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 0.6875rem;
  line-height: 1.2;
  cursor: pointer;
}

.mw-hud-advance {
  border-color: var(--vp-c-brand-1);
  background: var(--vp-c-brand-1);
  color: #fff;
  font-weight: 600;
}

.mw-hud-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
</style>
