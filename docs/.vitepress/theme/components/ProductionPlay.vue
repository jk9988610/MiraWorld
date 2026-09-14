<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type ProductionStatus } from '../composables/useGame'
import { hudTickNonce } from '../composables/worldHud'

const { user, refresh, isLoggedIn } = useAuth()
const {
  loadProductionStatus,
  setupProduction,
  updateProductionLines,
  transferToInstitution,
  createProductionOffer,
  toggleProductionOffer,
  applyShop,
  createCompany,
} = useGame()

const data = ref<ProductionStatus | null>(null)
const error = ref('')
const message = ref('')
const busy = ref(false)
const transferAmount = ref(5000)
const transferSource = ref<'company' | 'player'>('company')
const offerItemId = ref('item_smart_terminal')
const offerDisplay = ref('智能终端')
const offerPrice = ref(20)
const shopName = ref('')
const companyName = ref('')

const hubResources = computed(() => data.value?.hub?.resources ?? [])
const lineState = ref<Record<string, boolean>>({})

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  await reload()
})

watch(hudTickNonce, async (n, prev) => {
  if (!n || n === prev || !isLoggedIn.value) return
  await reload()
  const stock = data.value?.inventory.reduce((s, i) => s + i.qty, 0) ?? 0
  const wallet = data.value?.institution?.wallet_credits ?? 0
  if (stock > 0) {
    message.value = `日 tick 已结算：成品仓 ${stock} 件 · 运营账 ${wallet.toLocaleString('zh-CN')} 点`
  } else if ((data.value?.next_batch_cost ?? 0) > wallet) {
    message.value = ''
    error.value = `运营账不够买一轮 Hub 原料（约 ${data.value?.next_batch_cost} 点），成品不会增加`
  } else {
    error.value = '日 tick 已过，成品仍为 0（缺编制岗或 Hub 缺货）'
  }
})

async function reload() {
  error.value = ''
  try {
    data.value = await loadProductionStatus()
    const next: Record<string, boolean> = {}
    for (const recipe of data.value.available_recipes) {
      const existing = data.value.production_lines.find((l) => l.recipe_id === recipe.id)
      next[recipe.id] = existing?.enabled ?? false
    }
    lineState.value = next
    if (data.value.inventory.length && !offerItemId.value) {
      offerItemId.value = data.value.inventory[0].item_id
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
}

async function onSetup() {
  if (busy.value) return
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    data.value = await setupProduction()
    message.value = '已开通设备厂：编制机器员工后，日 tick 从 Hub 采购并生产'
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '开通失败'
  } finally {
    busy.value = false
  }
}

async function onSaveLines() {
  if (busy.value || !data.value) return
  busy.value = true
  error.value = ''
  try {
    const lines = Object.entries(lineState.value).map(([recipe_id, enabled]) => ({
      recipe_id,
      enabled,
    }))
    data.value = await updateProductionLines(lines)
    message.value = '生产配方已保存'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    busy.value = false
  }
}

async function onTransfer() {
  if (busy.value || transferAmount.value <= 0) return
  busy.value = true
  error.value = ''
  try {
    await transferToInstitution(transferSource.value, transferAmount.value)
    message.value = '已划入机构运营账（用于 Hub 采购）'
    await reload()
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '划转失败'
  } finally {
    busy.value = false
  }
}

async function onCreateOffer() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await createProductionOffer({
      item_id: offerItemId.value,
      display: offerDisplay.value.trim(),
      price_credits: offerPrice.value,
      qty: 1,
    })
    message.value = '已挂成品进市场（有库存才可见）'
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '挂单失败'
  } finally {
    busy.value = false
  }
}

async function onToggleOffer(id: string, active: boolean) {
  if (busy.value) return
  busy.value = true
  try {
    await toggleProductionOffer(id, active)
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

async function quickApplyShop() {
  if (!shopName.value.trim() || busy.value) return
  busy.value = true
  try {
    await applyShop(shopName.value.trim())
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '开店失败'
  } finally {
    busy.value = false
  }
}

async function quickCreateCompany() {
  if (!companyName.value.trim() || busy.value) return
  busy.value = true
  try {
    await createCompany(companyName.value.trim())
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登记公司失败'
  } finally {
    busy.value = false
  }
}

function fmt(n: number | undefined) {
  return (n ?? 0).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user && data">
    <h1>生产 · 挂市场</h1>
    <p class="mw-lead">Hub 采购 → 机构生产 → 成品进市场；买了即用，不可再加工。</p>
    <p v-if="error" class="mw-err">{{ error }}</p>
    <p v-if="message" class="mw-ok">{{ message }}</p>

    <section v-if="!data.has_shop" class="mw-card">
      <h2>先开店</h2>
      <input v-model="shopName" maxlength="32" placeholder="店名" />
      <button type="button" class="mw-btn" :disabled="busy" @click="quickApplyShop">申请开店</button>
    </section>

    <section v-else-if="!data.has_company" class="mw-card">
      <h2>先登记公司</h2>
      <input v-model="companyName" maxlength="32" placeholder="公司名" />
      <button type="button" class="mw-btn" :disabled="busy" @click="quickCreateCompany">登记公司</button>
    </section>

    <template v-else>
      <section class="mw-cards">
        <div class="mw-card">
          <span class="mw-label">机构运营账</span>
          <strong>{{ fmt(data.institution?.wallet_credits) }} 点</strong>
          <small>{{ data.institution?.display_name }} · {{ data.institution?.kind }}</small>
        </div>
        <div class="mw-card">
          <span class="mw-label">公司账</span>
          <strong>{{ fmt(data.company_wallet) }} 点</strong>
        </div>
        <div class="mw-card">
          <span class="mw-label">成品库存</span>
          <strong>{{ data.inventory.reduce((s, i) => s + i.qty, 0) }} 件</strong>
        </div>
      </section>

      <section v-if="!data.institution?.production_ready" class="mw-card">
        <h2>开通设备厂</h2>
        <p class="mw-dim">将机构升级为 device_plant，编制机器员工（工程师 / QC），启用智能终端配方。无员工不生产。</p>
        <button type="button" class="mw-btn" :disabled="busy" @click="onSetup">开通生产</button>
      </section>

      <template v-else>
        <section class="mw-card">
          <h2>划入机构运营账</h2>
          <p class="mw-dim">日 tick 生产时从 Hub 扣款，需机构账有钱；无编制岗则跳过生产。</p>
          <div class="mw-form">
            <select v-model="transferSource">
              <option value="company">公司账</option>
              <option value="player">个人钱包</option>
            </select>
            <input v-model.number="transferAmount" type="number" min="1" />
            <button type="button" class="mw-btn" :disabled="busy" @click="onTransfer">划入</button>
          </div>
        </section>

        <section class="mw-card">
          <h2>员工编制</h2>
          <p v-if="!data.staff.length" class="mw-err">没有在岗编制，日 tick 不会生产。</p>
          <ul v-else class="mw-list">
            <li v-for="slot in data.staff" :key="slot.job_type">
              {{ slot.job_display }} × {{ slot.headcount }}
              <span class="mw-dim"> · 日薪 {{ slot.wage_per_capita }} 点/人 · 在岗组 {{ slot.employed_groups }}</span>
            </li>
          </ul>
        </section>

        <section class="mw-card">
          <h2>Hub 市价（L0）</h2>
          <ul class="mw-list">
            <li v-for="r in hubResources" :key="r.resource_id">
              {{ r.display }} · {{ r.price_credits }} 点/单位 · 库存 {{ fmt(r.qty) }}
            </li>
          </ul>
        </section>

        <section class="mw-card">
          <h2>生产配方</h2>
          <ul class="mw-list">
            <li v-for="recipe in data.available_recipes" :key="recipe.id" class="mw-recipe">
              <label>
                <input type="checkbox" v-model="lineState[recipe.id]" />
                <strong>{{ recipe.display }}</strong>
              </label>
              <small class="mw-dim">
                耗：
                <span v-for="(inp, idx) in recipe.inputs" :key="inp.resource">
                  {{ inp.resource }}×{{ inp.qty }}<span v-if="idx < recipe.inputs.length - 1"> · </span>
                </span>
                → {{ recipe.outputs[0]?.item_id }}
              </small>
            </li>
          </ul>
          <button type="button" class="mw-btn mw-btn--ghost" :disabled="busy" @click="onSaveLines">保存配方</button>
        </section>

        <section class="mw-card">
          <h2>机构成品仓</h2>
          <ul v-if="data.inventory.length" class="mw-list">
            <li v-for="item in data.inventory" :key="item.item_id">
              {{ item.display }} × {{ item.qty }}
            </li>
          </ul>
          <p v-else class="mw-dim">暂无库存，等日 tick 生产或先划入运营账。</p>
        </section>

        <section class="mw-card">
          <h2>挂成品市场</h2>
          <div class="mw-form">
            <select v-model="offerItemId">
              <option v-for="item in data.inventory" :key="item.item_id" :value="item.item_id">
                {{ item.display }} ({{ item.qty }})
              </option>
            </select>
            <input v-model="offerDisplay" placeholder="挂单名" maxlength="64" />
            <input v-model.number="offerPrice" type="number" min="1" placeholder="价格" />
            <button type="button" class="mw-btn" :disabled="busy || !data.inventory.length" @click="onCreateOffer">
              挂市场
            </button>
          </div>
          <ul v-if="data.offers.length" class="mw-list">
            <li v-for="o in data.offers" :key="o.id">
              <strong>{{ o.display }}</strong> · {{ o.price_credits }} 点 · 库存 {{ o.stock }}
              <span class="mw-dim">{{ o.active ? '上架' : '下架' }}</span>
              <button type="button" class="mw-mini" :disabled="busy" @click="onToggleOffer(o.id, !o.active)">
                {{ o.active ? '下架' : '上架' }}
              </button>
            </li>
          </ul>
        </section>
      </template>
    </template>

    <p class="mw-back">
      <a href="/miraworld/play/capital.html">← 资本家</a>
      · <a href="/miraworld/play/economy.html">城市经营</a>
      · <a href="/miraworld/play/my-shop.html">我的店</a>
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad { padding-bottom: 4.5rem; }
.mw-lead { color: var(--vp-c-text-2); }
.mw-err { color: #c0392b; }
.mw-ok { color: var(--vp-c-brand-1); }
.mw-dim { color: var(--vp-c-text-3); font-size: 0.875rem; }
.mw-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr)); gap: 0.65rem; margin: 1rem 0; }
.mw-card { padding: 0.85rem; border: 1px solid var(--vp-c-divider); border-radius: 8px; background: var(--vp-c-bg-elv); margin-bottom: 0.75rem; }
.mw-card h2 { font-size: 1rem; margin: 0 0 0.5rem; }
.mw-label { display: block; font-size: 0.75rem; color: var(--vp-c-text-3); }
.mw-card strong { color: var(--vp-c-brand-1); }
.mw-list { list-style: none; padding: 0; margin: 0.5rem 0; }
.mw-list li { padding: 0.35rem 0; border-bottom: 1px solid var(--vp-c-divider); font-size: 0.875rem; }
.mw-recipe label { display: flex; gap: 0.5rem; align-items: center; }
.mw-form { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.mw-form input, .mw-form select { padding: 0.45rem 0.6rem; border-radius: 8px; border: 1px solid var(--vp-c-divider); }
.mw-btn { padding: 0.55rem 1rem; border-radius: 8px; border: none; background: var(--vp-c-brand-1); color: #fff; cursor: pointer; }
.mw-btn--ghost { background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); border: 1px solid var(--vp-c-divider); }
.mw-mini { min-height: 36px; padding: 0.3rem 0.7rem; margin-left: 0.35rem; border-radius: 8px; border: 1px solid var(--vp-c-brand-1); background: var(--vp-c-bg-elv); color: var(--vp-c-brand-1); cursor: pointer; }
.mw-back { margin-top: 1.5rem; font-size: 0.875rem; }
</style>
