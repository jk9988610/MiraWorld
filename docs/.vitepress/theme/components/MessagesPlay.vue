<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type MessageData } from '../composables/useGame'

const { refresh, isLoggedIn } = useAuth()
const { loadMessages, markMessageRead } = useGame()
const messages = ref<MessageData[]>([])
const error = ref('')

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  try {
    const data = await loadMessages()
    messages.value = data.messages
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载通知失败'
  }
})

async function openMessage(msg: MessageData) {
  if (msg.read_at) {
    if (msg.ref_type === 'order' && msg.ref_id) {
      window.location.href = `/miraworld/play/order.html?id=${encodeURIComponent(msg.ref_id)}`
    }
    return
  }
  try {
    await markMessageRead(msg.id)
    msg.read_at = new Date().toISOString()
    if (msg.ref_type === 'order' && msg.ref_id) {
      window.location.href = `/miraworld/play/order.html?id=${encodeURIComponent(msg.ref_id)}`
    }
  } catch {
    /* ignore */
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad">
    <h1>通知</h1>
    <p v-if="error" class="mw-err">{{ error }}</p>
    <ul v-if="messages.length" class="mw-list">
      <li
        v-for="msg in messages"
        :key="msg.id"
        :class="{ unread: !msg.read_at }"
      >
        <button type="button" class="mw-msg-btn" @click="openMessage(msg)">
          <span class="mw-body">{{ msg.body }}</span>
          <small>{{ msg.created_at.slice(0, 19).replace('T', ' ') }}</small>
        </button>
      </li>
    </ul>
    <p v-else class="mw-dim">还没有通知。</p>
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

.mw-msg-btn {
  width: 100%;
  text-align: left;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-elv);
  cursor: pointer;
  font: inherit;
}

li.unread .mw-msg-btn {
  border-left: 3px solid var(--vp-c-brand-1);
}

.mw-body {
  display: block;
}

small {
  color: var(--vp-c-text-3);
}

.mw-dim {
  color: var(--vp-c-text-3);
}

.mw-err {
  color: #c0392b;
}
</style>
