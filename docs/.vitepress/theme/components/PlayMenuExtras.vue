<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vitepress'
import { useAuth } from '../composables/useAuth'
import { useGame } from '../composables/useGame'
import { clearHud, hudActive } from '../composables/worldHud'

const route = useRoute()
const { isLoggedIn, logout } = useAuth()
const { worldExit } = useGame()
const exiting = ref(false)
const loggingOut = ref(false)

const inGame = computed(() => {
  const p = route.path
  return p.includes('/play/') && !p.includes('/play/gate')
})

const showExitGame = computed(() => inGame.value && isLoggedIn.value && hudActive.value)

async function onExitGame() {
  if (exiting.value) return
  exiting.value = true
  try {
    await worldExit()
  } catch {
    /* still gate */
  } finally {
    clearHud()
    window.location.assign('/miraworld/play/gate.html')
  }
}

async function onLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await logout()
    clearHud()
  } finally {
    window.location.assign('/miraworld/play/gate.html')
  }
}
</script>

<template>
  <div v-if="isLoggedIn" class="mw-menu-extras">
    <a class="mw-menu-link" href="/miraworld/play/gate.html">门控选档</a>
    <button v-if="showExitGame" type="button" class="mw-menu-link mw-menu-danger" :disabled="exiting" @click="onExitGame">
      {{ exiting ? '退出中…' : '退出游戏' }}
    </button>
    <button type="button" class="mw-menu-link" :disabled="loggingOut" @click="onLogout">
      {{ loggingOut ? '…' : '退出登录' }}
    </button>
  </div>
</template>

<style scoped>
.mw-menu-extras {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin: 1rem 0 0.5rem;
  padding: 0.75rem 0 0;
  border-top: 1px solid var(--vp-c-divider);
}

.mw-menu-link {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.55rem 0.75rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--vp-c-text-1);
  font: inherit;
  font-size: 0.9rem;
  text-decoration: none;
  cursor: pointer;
}

.mw-menu-link:hover {
  background: var(--vp-c-bg-soft);
}

.mw-menu-danger {
  color: #c0392b;
  font-weight: 600;
}

.mw-menu-link:disabled {
  opacity: 0.6;
  cursor: wait;
}
</style>
