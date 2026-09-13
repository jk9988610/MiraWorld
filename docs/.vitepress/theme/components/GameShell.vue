<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vitepress'

const route = useRoute()
const show = computed(() => route.path.startsWith('/play/'))
</script>

<template>
  <nav v-if="show" class="mw-game-shell" aria-label="游戏导航">
    <a href="/miraworld/play/city.html" class="mw-tab">地图</a>
    <a href="/miraworld/play/messages.html" class="mw-tab">通知</a>
    <a href="/miraworld/play/stacks.html" class="mw-tab">背包</a>
    <a href="/miraworld/play/me.html" class="mw-tab">我的</a>
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
  padding: 0.5rem 0 calc(0.5rem + env(safe-area-inset-bottom));
  border-top: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-elv);
}

.mw-tab {
  flex: 1;
  text-align: center;
  padding: 0.35rem;
  font-size: 0.875rem;
  color: var(--vp-c-text-2);
  text-decoration: none;
}

.mw-tab:hover {
  color: var(--vp-c-brand-1);
}
</style>
