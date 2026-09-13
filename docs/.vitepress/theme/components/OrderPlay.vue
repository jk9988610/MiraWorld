<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
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
const { loadOrder, pickupOrder, acceptOrder, markOrderReady } = useGame()
const order = ref<OrderData | null>(null)
const error = ref('')
const picking = ref(false)
const acting = ref(false)

const isBuyer = computed(
  () => order.value && user.value && order.value.buyer_id === user.value.id,
)
const isSeller = computed(
  () =>
    order.value &&
    user.value &&
    order.value.seller_kind === 'player' &&
    order.value.seller_id === String(user.value.id),
)
const isPlayerOrder = computed(() => order.value?.seller_kind === 'player')

function orderIdFromUrl(): string {
  return new URLSearchParams(window.location.search).get('id') || ''
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

async function accept() {
  if (!order.value || acting.value) return
  acting.value = true
  error.value = ''
  try {
    order.value = await acceptOrder(order.value.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '接单失败'
  } finally {
    acting.value = false
  }
}

async function markReady() {
  if (!order.value || acting.value) return
  acting.value = true
  error.value = ''
  try {
    order.value = await markOrderReady(order.value.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    acting.value = false
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
        <li :class="{ done: !isPlayerOrder || order.status !== 'escrowed' }">
          {{ isPlayerOrder ? '店主接单' : '厨房制作' }}
        </li>
        <li :class="{ done: ['ready', 'completed', 'settled'].includes(order.status) }">好了</li>
        <li :class="{ done: order.status === 'settled' }">确认收进背包</li>
      </ol>

      <template v-if="isBuyer">
        <p v-if="order.status === 'escrowed' && isPlayerOrder" class="mw-hint">
          已下单，等店主接单。好了会发通知。
        </p>
        <p v-if="order.status === 'processing'" class="mw-hint">店主正在做，好了会发通知。</p>
        <p v-if="order.status === 'ready'" class="mw-hint">好了。点下面按钮，确认收进背包。</p>
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
      </template>

      <template v-if="isSeller">
        <p class="mw-hint">你是卖家视角。</p>
        <button
          v-if="order.status === 'escrowed'"
          type="button"
          class="mw-btn"
          :disabled="acting"
          @click="accept"
        >
          接单
        </button>
        <button
          v-if="order.status === 'escrowed' || order.status === 'processing'"
          type="button"
          class="mw-btn mw-btn--secondary"
          :disabled="acting"
          @click="markReady"
        >
          标记好了
        </button>
      </template>

      <p class="mw-meta">余额 {{ user.wallet_credits }} 点</p>
    </template>

    <p class="mw-back">
      <a href="/miraworld/play/messages.html">通知</a>
      ·
      <a href="/miraworld/play/my-shop.html">我的店</a>
      ·
      <a href="/miraworld/play/city.html">地图</a>
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad { padding-bottom: 4.5rem; }
.mw-status { font-size: 1.05rem; color: var(--vp-c-brand-1); }
.mw-steps { padding-left: 1.25rem; margin: 1rem 0; color: var(--vp-c-text-3); line-height: 1.65; }
.mw-steps li.done { color: var(--vp-c-text-1); }
.mw-hint { margin: 0.75rem 0 0; font-size: 0.9375rem; color: var(--vp-c-text-2); }
.mw-btn {
  display: block; width: 100%; max-width: 22rem; margin: 1rem 0; min-height: 48px;
  padding: 0.75rem 1.25rem; border: none; border-radius: 8px;
  background: var(--vp-c-brand-1); color: #fff; font: inherit; font-weight: 600; cursor: pointer;
}
.mw-btn--secondary {
  background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); border: 1px solid var(--vp-c-divider);
}
.mw-msg { padding: 0.75rem 1rem; border-radius: 8px; background: var(--vp-c-bg-soft); }
.mw-err { color: #c0392b; }
.mw-meta { font-size: 0.9375rem; }
.mw-back { margin-top: 1.5rem; font-size: 0.875rem; }
</style>
