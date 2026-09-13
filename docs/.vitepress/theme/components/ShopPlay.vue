<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type MarketShopData, type PlayerOfferData } from '../composables/useGame'

const { user, refresh, isLoggedIn } = useAuth()
const { loadMarket, placeOrder } = useGame()
const shop = ref<MarketShopData | null>(null)
const error = ref('')
const ordering = ref(false)

function sellerIdFromUrl(): string {
  return new URLSearchParams(window.location.search).get('id') || ''
}

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  const id = sellerIdFromUrl()
  if (!id) {
    error.value = '缺少店铺'
    return
  }
  try {
    const market = await loadMarket()
    shop.value = market.shops.find((s) => String(s.player_id) === id) || null
    if (!shop.value) error.value = '这家店还没营业或没有挂单'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
})

const activeOffers = computed(() => shop.value?.offers.filter((o) => o.active) || [])

async function order(offer: PlayerOfferData) {
  if (ordering.value) return
  ordering.value = true
  error.value = ''
  try {
    const o = await placeOrder(offer.id, true)
    await refresh()
    window.location.href = `/miraworld/play/order.html?id=${encodeURIComponent(o.id)}`
  } catch (e) {
    error.value = e instanceof Error ? e.message : '下单失败'
  } finally {
    ordering.value = false
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>{{ shop?.display_name || '玩家店' }}</h1>
    <p v-if="shop" class="mw-lead">潮灯市 · {{ shop.handle }} 的店</p>
    <p class="mw-meta">余额 {{ user.wallet_credits }} 点</p>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <ul v-if="activeOffers.length" class="mw-menu">
      <li v-for="offer in activeOffers" :key="offer.id">
        <div class="mw-offer">
          <strong>{{ offer.display }}</strong>
          <span class="mw-price">{{ offer.price_credits }} 点</span>
          <button type="button" :disabled="ordering" @click="order(offer)">
            {{ ordering ? '下单中…' : '点这一碗' }}
          </button>
        </div>
      </li>
    </ul>

    <p class="mw-back">
      <a href="/miraworld/play/city.html">← 回潮灯市地图</a>
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad { padding-bottom: 4.5rem; }
.mw-lead { color: var(--vp-c-text-2); }
.mw-meta { font-size: 0.9375rem; }
.mw-err { color: #c0392b; }
.mw-menu { list-style: none; padding: 0; }
.mw-offer {
  border: 1px solid var(--vp-c-divider); border-radius: 8px; padding: 1rem;
  margin-bottom: 0.75rem; background: var(--vp-c-bg-elv);
}
.mw-price { float: right; color: var(--vp-c-brand-1); font-weight: 600; }
.mw-offer button {
  margin-top: 0.75rem; min-height: 48px; min-width: 8rem; padding: 0.65rem 1.25rem;
  border-radius: 8px; border: none; background: var(--vp-c-brand-1); color: #fff;
  font: inherit; font-weight: 600; cursor: pointer;
}
.mw-back { margin-top: 1.5rem; font-size: 0.875rem; }
</style>
