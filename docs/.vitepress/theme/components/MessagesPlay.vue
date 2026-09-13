<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type MessageData } from '../composables/useGame'
import { refreshUnreadCount } from '../composables/useShellState'

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
    await refreshUnreadCount()
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
    await refreshUnreadCount()
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
          <span v-if="msg.from_kind === 'player' && msg.from_display" class="mw-from">
            {{ msg.from_display }}：
          </span>
          <span class="mw-body">{{ msg.body }}</span>
          <small>{{ msg.created_at.slice(0, 19).replace('T', ' ') }}</small>
        </button>
      </li>
    </ul>
    <p v-else class="mw-dim">
      还没有通知。去<a href="/miraworld/play/chen.html">陈师傅</a>点面，
      面好了会在这里叫你<strong>确认收进背包</strong>。
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

.mw-msg-btn {
  width: 100%;
  text-align: left;
  min-height: 48px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.5rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-elv);
  cursor: pointer;
  font: inherit;
  -webkit-tap-highlight-color: transparent;
}

li.unread .mw-msg-btn {
  border-left: 3px solid var(--vp-c-brand-1);
  background: color-mix(in srgb, var(--vp-c-brand-1) 6%, var(--vp-c-bg-elv));
}

.mw-from {
  display: block;
  font-size: 0.8125rem;
  color: var(--vp-c-text-3);
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
