<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type CatalogOffer } from '../composables/useGame'
import SpotlightPanel from './SpotlightPanel.vue'

const { user, refresh, isLoggedIn } = useAuth()
const { loadCatalog, placeOrder, loadWorld, world } = useGame()
const offers = ref<CatalogOffer[]>([])
const message = ref('')
const error = ref('')
const ordering = ref(false)

const chenOffers = computed(() =>
  offers.value.filter((o) => o.seller?.id === 'npc_chen'),
)

const chenNpc = computed(() => world.value?.npcs.find((n) => n.id === 'npc_chen'))

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  try {
    await loadWorld()
    const catalog = await loadCatalog()
    offers.value = catalog.offers
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载菜单失败'
  }
})

async function order(offer: CatalogOffer) {
  if (ordering.value) return
  error.value = ''
  message.value = ''
  ordering.value = true
  try {
    const order = await placeOrder(offer.id)
    await refresh()
    window.location.href = `/miraworld/play/order.html?id=${encodeURIComponent(order.id)}`
  } catch (e) {
    error.value = e instanceof Error ? e.message : '下单失败'
  } finally {
    ordering.value = false
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>陈师傅 · 食堂</h1>
    <p class="mw-lead">潮灯市 · 点完即做，好了发通知。</p>
    <p v-if="chenNpc?.greeting" class="mw-quote">{{ chenNpc.greeting }}</p>
    <p v-if="chenNpc?.extra" class="mw-extra">{{ chenNpc.extra }}</p>
    <p class="mw-meta">余额 {{ user.wallet_credits }} 点</p>
    <p v-if="message" class="mw-msg">{{ message }}</p>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <ul v-if="chenOffers.length" class="mw-menu">
      <li v-for="offer in chenOffers" :key="offer.id">
        <div class="mw-offer">
          <strong>{{ offer.display }}</strong>
          <span class="mw-price">{{ offer.price_credits }} 点</span>
          <p class="mw-dim">出餐：一碗面</p>
          <button type="button" :disabled="ordering" @click="order(offer)">
            {{ ordering ? '下单中…' : '点这一碗' }}
          </button>
        </div>
      </li>
    </ul>
    <p v-else class="mw-dim">灶还没热。过会儿再来看看，或先回<a href="/miraworld/play/city.html">潮灯市</a>转转。</p>

    <SpotlightPanel institution-id="inst_chen_noodle" title="面坊来客" />

    <p class="mw-back">
      <a href="/miraworld/play/city.html">← 回潮灯市地图</a>
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad {
  padding-bottom: 4.5rem;
}

.mw-lead {
  color: var(--vp-c-text-2);
}

.mw-quote {
  margin: 0.5rem 0 0;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
  font-size: 0.9375rem;
  color: var(--vp-c-text-1);
}

.mw-extra {
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  color: var(--vp-c-text-3);
  font-style: italic;
}

.mw-meta {
  font-size: 0.9375rem;
}

.mw-msg {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
  border-left: 3px solid var(--vp-c-brand-1);
}

.mw-err {
  color: #c0392b;
}

.mw-menu {
  list-style: none;
  padding: 0;
}

.mw-offer {
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 0.75rem;
  background: var(--vp-c-bg-elv);
}

.mw-price {
  float: right;
  color: var(--vp-c-brand-1);
  font-weight: 600;
}

.mw-dim {
  color: var(--vp-c-text-3);
  font-size: 0.875rem;
}

.mw-offer button {
  margin-top: 0.75rem;
  min-height: 48px;
  min-width: 8rem;
  padding: 0.65rem 1.25rem;
  border-radius: 8px;
  border: none;
  background: var(--vp-c-brand-1);
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-size: 1rem;
  font-weight: 600;
  -webkit-tap-highlight-color: transparent;
}

.mw-offer button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.mw-back {
  margin-top: 1.5rem;
  font-size: 0.875rem;
}
</style>
