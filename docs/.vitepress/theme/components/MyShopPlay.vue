<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import {
  useGame,
  type OrderData,
  type PlayerOfferData,
  type ShopMeData,
} from '../composables/useGame'

const STATUS: Record<string, string> = {
  escrowed: '待接单',
  processing: '制作中',
  ready: '可以收进背包',
  settled: '已完成',
}

const { user, refresh, isLoggedIn } = useAuth()
const {
  loadShopMe,
  applyShop,
  setShopOpen,
  setShopAuto,
  createShopOffer,
  toggleShopOffer,
  loadSellingOrders,
  acceptOrder,
  markOrderReady,
  sendMessage,
} = useGame()

const data = ref<ShopMeData | null>(null)
const selling = ref<OrderData[]>([])
const shopName = ref('')
const offerDisplay = ref('家常汤面')
const offerPrice = ref(18)
const msgHandle = ref('')
const msgBody = ref('')
const error = ref('')
const busy = ref(false)

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  await reload()
})

async function reload() {
  error.value = ''
  try {
    data.value = await loadShopMe()
    if (data.value.shop) {
      const sell = await loadSellingOrders()
      selling.value = sell.orders.filter((o) => o.status !== 'settled')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
}

async function doApply() {
  if (!shopName.value.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await applyShop(shopName.value.trim())
    await refresh()
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '开店失败'
  } finally {
    busy.value = false
  }
}

async function toggleAuto() {
  if (!data.value?.shop || busy.value) return
  busy.value = true
  try {
    await setShopAuto(!data.value.shop.auto_on)
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

async function toggleOpen() {
  if (!data.value?.shop || busy.value) return
  busy.value = true
  try {
    await setShopOpen(!data.value.shop.open)
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

async function addOffer() {
  if (!data.value?.shop || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await createShopOffer({
      item_id: 'item_noodle_bowl',
      display: offerDisplay.value.trim(),
      price_credits: offerPrice.value,
    })
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '挂单失败'
  } finally {
    busy.value = false
  }
}

async function flipOffer(offer: PlayerOfferData) {
  if (busy.value) return
  busy.value = true
  try {
    await toggleShopOffer(offer.id, !offer.active)
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

async function accept(id: string) {
  if (busy.value) return
  busy.value = true
  try {
    await acceptOrder(id)
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '接单失败'
  } finally {
    busy.value = false
  }
}

async function markReady(id: string) {
  if (busy.value) return
  busy.value = true
  try {
    await markOrderReady(id)
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

async function sendMsg() {
  if (!msgHandle.value.trim() || !msgBody.value.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await sendMessage(msgHandle.value.trim(), msgBody.value.trim())
    msgBody.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : '发送失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user && data">
    <h1>我的店</h1>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <template v-if="!data.shop">
      <p class="mw-lead">
        在潮灯市挂自己的面。登记费 <strong>{{ data.registration_fee }}</strong> 点，扣一次。
      </p>
      <label class="mw-field">
        <span>店名</span>
        <input v-model="shopName" maxlength="32" placeholder="例如：少盐食堂" />
      </label>
      <button type="button" class="mw-btn" :disabled="busy" @click="doApply">
        申请开店
      </button>
    </template>

    <template v-else>
      <p><strong>{{ data.shop.display_name }}</strong> · {{ data.shop.open ? '营业中' : '歇业' }}<template v-if="data.shop.auto_on"> · 当班中</template></p>
      <p class="mw-meta">余额 {{ user.wallet_credits }} 点</p>
      <button type="button" class="mw-btn mw-btn--secondary" :disabled="busy" @click="toggleOpen">
        {{ data.shop.open ? '暂停营业' : '开始营业' }}
      </button>
      <button type="button" class="mw-btn mw-btn--secondary" :disabled="busy" @click="toggleAuto">
        {{ data.shop.auto_on ? '关闭当班（手动接单）' : '开启当班（自动接单）' }}
      </button>
      <p class="mw-dim">点单与当班均通过通知告知买家；开启当班后离线也能自动接单并标记好了。</p>

      <h2>挂单</h2>
      <ul v-if="data.offers.length" class="mw-list">
        <li v-for="o in data.offers" :key="o.id" class="mw-card">
          <strong>{{ o.display }}</strong> · {{ o.price_credits }} 点
          <span class="mw-dim">{{ o.active ? '上架' : '下架' }}</span>
          <button type="button" class="mw-mini" :disabled="busy" @click="flipOffer(o)">
            {{ o.active ? '下架' : '上架' }}
          </button>
        </li>
      </ul>
      <div class="mw-card">
        <label class="mw-field">
          <span>挂单名</span>
          <input v-model="offerDisplay" maxlength="64" />
        </label>
        <label class="mw-field">
          <span>价格（点）</span>
          <input v-model.number="offerPrice" type="number" min="1" max="9999" />
        </label>
        <button type="button" class="mw-btn" :disabled="busy" @click="addOffer">新增挂单</button>
      </div>

      <h2>待处理订单</h2>
      <ul v-if="selling.length" class="mw-list">
        <li v-for="o in selling" :key="o.id" class="mw-card">
          <strong>{{ o.display }}</strong> · {{ STATUS[o.status] || o.status }}
          <div class="mw-actions">
            <button
              v-if="o.status === 'escrowed'"
              type="button"
              class="mw-mini"
              :disabled="busy"
              @click="accept(o.id)"
            >
              接单
            </button>
            <button
              v-if="o.status === 'escrowed' || o.status === 'processing'"
              type="button"
              class="mw-mini"
              :disabled="busy"
              @click="markReady(o.id)"
            >
              标记好了
            </button>
            <a :href="`/miraworld/play/order.html?id=${encodeURIComponent(o.id)}`">查看</a>
          </div>
        </li>
      </ul>
      <p v-else class="mw-dim">还没有人点你的挂单。</p>

      <h2>发往来</h2>
      <label class="mw-field">
        <span>对方 handle</span>
        <input v-model="msgHandle" maxlength="32" />
      </label>
      <label class="mw-field">
        <span>内容</span>
        <textarea v-model="msgBody" rows="2" maxlength="500" />
      </label>
      <button type="button" class="mw-btn mw-btn--secondary" :disabled="busy" @click="sendMsg">
        发送
      </button>
    </template>

    <p class="mw-back">
      <a href="/miraworld/play/me.html">← 我的</a>
      ·
      <a href="/miraworld/play/city.html">地图</a>
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad { padding-bottom: 4.5rem; }
.mw-lead { color: var(--vp-c-text-2); }
.mw-meta { font-size: 0.9375rem; }
.mw-err { color: #c0392b; }
.mw-dim { color: var(--vp-c-text-3); font-size: 0.875rem; }
.mw-field { display: block; margin: 0.75rem 0; }
.mw-field input, .mw-field textarea {
  width: 100%; box-sizing: border-box; margin-top: 0.25rem; padding: 0.5rem;
  border-radius: 8px; border: 1px solid var(--vp-c-border); font: inherit;
}
.mw-list { list-style: none; padding: 0; }
.mw-card {
  border: 1px solid var(--vp-c-divider); border-radius: 8px;
  padding: 0.85rem; margin-bottom: 0.5rem; background: var(--vp-c-bg-elv);
}
.mw-btn {
  display: inline-block; min-height: 48px; padding: 0.65rem 1.25rem; margin: 0.5rem 0;
  border: none; border-radius: 8px; background: var(--vp-c-brand-1); color: #fff;
  font: inherit; font-weight: 600; cursor: pointer;
}
.mw-btn--secondary {
  background: var(--vp-c-bg-soft); color: var(--vp-c-text-1);
  border: 1px solid var(--vp-c-divider);
}
.mw-mini {
  min-height: 40px; padding: 0.4rem 0.85rem; margin-right: 0.35rem;
  border-radius: 8px; border: 1px solid var(--vp-c-brand-1);
  background: var(--vp-c-bg-elv); color: var(--vp-c-brand-1); font: inherit; cursor: pointer;
}
.mw-actions { margin-top: 0.5rem; }
.mw-back { margin-top: 1.5rem; font-size: 0.875rem; }
</style>
