<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type StackData } from '../composables/useGame'

const { user, refresh, isLoggedIn } = useAuth()
const { loadStacks } = useGame()
const stacks = ref<StackData[]>([])
const error = ref('')

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  try {
    const data = await loadStacks()
    stacks.value = data.stacks
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载背包失败'
  }
})
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>背包</h1>
    <p v-if="error" class="mw-err">{{ error }}</p>
    <ul v-if="stacks.length" class="mw-list">
      <li v-for="s in stacks" :key="s.item_id">
        <strong>{{ s.display }}</strong>
        <span class="mw-qty">× {{ s.qty }}</span>
      </li>
    </ul>
    <p v-else class="mw-dim">
      背包还空着。去<a href="/miraworld/play/chen.html">陈师傅</a>点一碗面，
      通知里会叫你<strong>确认收进背包</strong>。
    </p>
    <p class="mw-link">
      <a href="/miraworld/play/chen.html">→ 陈师傅食堂</a>
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad {
  padding-bottom: 4.5rem;
}

.mw-list {
  list-style: none;
  padding: 0;
}

.mw-list li {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--vp-c-divider);
}

.mw-qty {
  margin-left: 0.5rem;
  color: var(--vp-c-brand-1);
}

.mw-dim {
  color: var(--vp-c-text-3);
}

.mw-err {
  color: #c0392b;
}

.mw-link {
  margin-top: 1.5rem;
  font-size: 0.875rem;
}
</style>
