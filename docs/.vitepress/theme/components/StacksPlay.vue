<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type StackData } from '../composables/useGame'
import { actionsForTags } from '../utils/itemActions'

const { user, refresh, isLoggedIn } = useAuth()
const { loadStacks, consumeStack, useStack } = useGame()
const stacks = ref<StackData[]>([])
const error = ref('')
const feedback = ref('')
const acting = ref<string | null>(null)

async function reloadStacks() {
  const data = await loadStacks()
  stacks.value = data.stacks
}

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  try {
    await reloadStacks()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载背包失败'
  }
})

async function consume(item: StackData) {
  if (acting.value) return
  acting.value = item.item_id
  error.value = ''
  feedback.value = ''
  try {
    const r = await consumeStack(item.item_id)
    stacks.value = r.stacks
    feedback.value = r.message
  } catch (e) {
    error.value = e instanceof Error ? e.message : '食用失败'
  } finally {
    acting.value = null
  }
}

async function useItem(item: StackData) {
  if (acting.value) return
  acting.value = item.item_id
  error.value = ''
  feedback.value = ''
  try {
    const r = await useStack(item.item_id)
    stacks.value = r.stacks
    feedback.value = r.message
  } catch (e) {
    error.value = e instanceof Error ? e.message : '使用失败'
  } finally {
    acting.value = null
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>背包</h1>
    <p v-if="feedback" class="mw-msg">{{ feedback }}</p>
    <p v-if="error" class="mw-err">{{ error }}</p>
    <ul v-if="stacks.length" class="mw-list">
      <li v-for="s in stacks" :key="s.item_id" class="mw-row">
        <div class="mw-row-head">
          <strong>{{ s.display }}</strong>
          <span class="mw-qty">× {{ s.qty }}</span>
        </div>
        <div v-if="actionsForTags(s.tags).consume || actionsForTags(s.tags).use" class="mw-actions">
          <button
            v-if="actionsForTags(s.tags).consume"
            type="button"
            class="mw-act"
            :disabled="acting === s.item_id"
            @click="consume(s)"
          >
            {{ acting === s.item_id ? '…' : '食用' }}
          </button>
          <button
            v-if="actionsForTags(s.tags).use"
            type="button"
            class="mw-act mw-act--secondary"
            :disabled="acting === s.item_id"
            @click="useItem(s)"
          >
            {{ acting === s.item_id ? '…' : '使用' }}
          </button>
        </div>
      </li>
    </ul>
    <p v-else class="mw-dim">
      背包还空着。去<a href="/miraworld/play/chen.html">陈师傅</a>点一碗面，
      通知里会叫你<strong>确认收进背包</strong>。
    </p>
    <p class="mw-link">
      <a href="/miraworld/play/chen.html">→ 陈师傅食堂</a>
      ·
      <a href="/miraworld/play/city.html">→ 潮灯市地图</a>
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

.mw-row {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--vp-c-divider);
}

.mw-row-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
}

.mw-qty {
  color: var(--vp-c-brand-1);
  font-weight: 600;
}

.mw-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.65rem;
}

.mw-act {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  background: var(--vp-c-brand-1);
  color: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.mw-act--secondary {
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  border: 1px solid var(--vp-c-divider);
}

.mw-act:disabled {
  opacity: 0.6;
  cursor: wait;
}

.mw-msg {
  padding: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
  border-left: 3px solid var(--vp-c-brand-1);
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
