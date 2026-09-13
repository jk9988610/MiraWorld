<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type CapitalStatus } from '../composables/useGame'

const { user, refresh, isLoggedIn } = useAuth()
const { loadCapitalStatus, claimDailyInvestment, createCompany } = useGame()
const status = ref<CapitalStatus | null>(null)
const error = ref('')
const message = ref('')
const loading = ref(true)
const busy = ref(false)
const companyName = ref('')

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  await reload()
})

async function reload() {
  loading.value = true
  error.value = ''
  try {
    status.value = await loadCapitalStatus()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function onClaim() {
  if (busy.value) return
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    const res = await claimDailyInvestment()
    message.value = `今日日投 +${res.grant.amount.toLocaleString('zh-CN')} 点`
    await reload()
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '领取失败'
  } finally {
    busy.value = false
  }
}

async function onCreateCompany() {
  if (busy.value || !companyName.value.trim()) return
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    await createCompany(companyName.value.trim())
    message.value = '公司已登记'
    companyName.value = ''
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登记失败'
  } finally {
    busy.value = false
  }
}

function fmt(n: number | undefined) {
  return (n ?? 0).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>资本家 · 日投</h1>
    <p class="mw-lead">外生补贴：乌托邦按你的总资产发放日投资金，不计入市民账本。</p>
    <p v-if="error" class="mw-err">{{ error }}</p>
    <p v-if="message" class="mw-ok">{{ message }}</p>
    <p v-if="loading" class="mw-dim">加载中…</p>

    <template v-if="status && !loading">
      <section class="mw-cards">
        <div class="mw-card">
          <span class="mw-label">总资产</span>
          <strong>{{ fmt(status.assets.total) }} 点</strong>
          <small>钱包 {{ fmt(status.assets.wallet_credits) }} · 店 {{ fmt(status.assets.shop_value) }} · 货 {{ fmt(status.assets.inventory_value) }}</small>
        </div>
        <div class="mw-card">
          <span class="mw-label">日投公式</span>
          <strong>{{ fmt(status.config.daily_investment_base) }} + {{ (status.config.asset_pct_min * 100).toFixed(0) }}–{{ (status.config.asset_pct_max * 100).toFixed(0) }}% 总资产</strong>
        </div>
        <div class="mw-card" v-if="status.last_grant">
          <span class="mw-label">上次领取</span>
          <strong>+{{ fmt(status.last_grant.amount) }} 点</strong>
          <small>{{ status.last_grant.grant_date }}</small>
        </div>
      </section>

      <p class="mw-actions">
        <button type="button" class="mw-btn" :disabled="!status.can_claim_today || busy" @click="onClaim">
          {{ status.can_claim_today ? '领取今日日投' : '今日已领' }}
        </button>
      </p>

      <section class="mw-company">
        <h2>公司层</h2>
        <p v-if="status.company" class="mw-ok">已登记：<strong>{{ status.company.display_name }}</strong></p>
        <template v-else>
          <p class="mw-dim">登记公司后，你的店会挂到公司名下（一玩家一公司）。</p>
          <p class="mw-form">
            <input v-model="companyName" maxlength="32" placeholder="公司名" />
            <button type="button" class="mw-btn" :disabled="busy || !companyName.trim()" @click="onCreateCompany">登记公司</button>
          </p>
        </template>
      </section>
    </template>

    <p class="mw-back">
      <a href="/miraworld/play/city.html">← 回潮灯市地图</a>
      · <a href="/miraworld/play/economy.html">城市经营</a>
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

.mw-err {
  color: #c0392b;
}

.mw-ok {
  color: var(--vp-c-brand-1);
}

.mw-dim {
  color: var(--vp-c-text-3);
  font-size: 0.875rem;
}

.mw-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: 0.65rem;
  margin: 1rem 0;
}

.mw-card {
  padding: 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-elv);
}

.mw-label {
  display: block;
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
  margin-bottom: 0.25rem;
}

.mw-card strong {
  display: block;
  font-size: 1.05rem;
  color: var(--vp-c-brand-1);
}

.mw-card small {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--vp-c-text-3);
}

.mw-actions {
  margin: 1rem 0;
}

.mw-btn {
  padding: 0.55rem 1rem;
  border-radius: 8px;
  border: none;
  background: var(--vp-c-brand-1);
  color: #fff;
  cursor: pointer;
}

.mw-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mw-company h2 {
  font-size: 1rem;
  margin: 1.25rem 0 0.5rem;
}

.mw-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.mw-form input {
  flex: 1;
  min-width: 10rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
}

.mw-back {
  margin-top: 1.5rem;
  font-size: 0.875rem;
}
</style>
