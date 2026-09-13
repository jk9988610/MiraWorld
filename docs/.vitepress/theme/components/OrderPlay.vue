<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type OrderData } from '../composables/useGame'

const STATUS_LABEL: Record<string, string> = {
  escrowed: '已托管',
  processing: '制作中',
  ready: '可以收进背包',
  completed: '已收进背包',
  settled: '已完成',
}

const { user, refresh, isLoggedIn } = useAuth()
const { loadOrder, pickupOrder } = useGame()
const order = ref<OrderData | null>(null)
const error = ref('')
const picking = ref(false)

function orderIdFromUrl(): string {
  const params = new URLSearchParams(window.location.search)
  return params.get('id') || ''
}

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  const id = orderIdFromUrl()
  if (!id) {
    error.value = '缺少订单号'
    return
  }
  try {
    order.value = await loadOrder(id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载订单失败'
  }
})

async function pickup() {
  if (!order.value || picking.value) return
  picking.value = true
  error.value = ''
  try {
    order.value = await pickupOrder(order.value.id)
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '收进背包失败'
  } finally {
    picking.value = false
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>订单</h1>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <template v-if="order">
      <p><strong>{{ order.display }}</strong> · {{ order.price_credits }} 点</p>
      <p class="mw-status">状态：{{ STATUS_LABEL[order.status] || order.status }}</p>

      <ol class="mw-steps">
        <li :class="{ done: true }">下单 · 托管 {{ order.price_credits }} 点</li>
        <li :class="{ done: order.status !== 'escrowed' }">厨房制作</li>
        <li :class="{ done: ['ready', 'completed', 'settled'].includes(order.status) }">面好了</li>
        <li :class="{ done: order.status === 'settled' }">确认收进背包</li>
      </ol>

      <button
        v-if="order.status === 'ready'"
        type="button"
        class="mw-btn"
        :disabled="picking"
        @click="pickup"
      >
        {{ picking ? '收进背包中…' : '确认收进背包' }}
      </button>
      <p v-else-if="order.status === 'settled'" class="mw-msg">已收进背包，去背包看看。</p>

      <p class="mw-meta">余额 {{ user.wallet_credits }} 点</p>
    </template>

    <p class="mw-back">
      <a href="/miraworld/play/messages.html">通知</a>
      ·
      <a href="/miraworld/play/stacks.html">背包</a>
      ·
      <a href="/miraworld/play/city.html">地图</a>
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad {
  padding-bottom: 4.5rem;
}

.mw-status {
  font-size: 1.05rem;
  color: var(--vp-c-brand-1);
}

.mw-steps {
  padding-left: 1.2rem;
  color: var(--vp-c-text-3);
}

.mw-steps li.done {
  color: var(--vp-c-text-1);
}

.mw-btn {
  margin: 1rem 0;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 6px;
  background: var(--vp-c-brand-1);
  color: #fff;
  font: inherit;
  cursor: pointer;
}

.mw-msg {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
}

.mw-err {
  color: #c0392b;
}

.mw-meta {
  font-size: 0.9375rem;
}

.mw-back {
  margin-top: 1.5rem;
  font-size: 0.875rem;
}
</style>
