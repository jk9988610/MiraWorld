<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type EconomyStatus } from '../composables/useGame'

const { user, refresh, isLoggedIn } = useAuth()
const { loadEconomyStatus } = useGame()
const status = ref<EconomyStatus | null>(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  try {
    status.value = await loadEconomyStatus('潮灯市')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
})

function fmt(n: number | undefined) {
  return (n ?? 0).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>潮灯市 · 经营</h1>
    <p class="mw-lead">城市自己转：机构发薪、福利补贴、市民消费。数字来自最近一次日 tick。</p>
    <p v-if="error" class="mw-err">{{ error }}</p>
    <p v-if="loading" class="mw-dim">加载中…</p>

    <template v-if="status && !loading">
      <section class="mw-cards">
        <div class="mw-card">
          <span class="mw-label">福利基金</span>
          <strong>{{ fmt(status.dashboard.welfare_fund_balance) }} 点</strong>
        </div>
        <div class="mw-card">
          <span class="mw-label">机构现金合计</span>
          <strong>{{ fmt(status.dashboard.institution_wallet_total) }} 点</strong>
        </div>
        <div class="mw-card">
          <span class="mw-label">上轮工资支出</span>
          <strong>{{ fmt(status.dashboard.last_payroll_total) }} 点</strong>
          <small>{{ status.dashboard.last_payroll_groups }} 组 · 欠薪 {{ status.dashboard.last_payroll_underpaid }}</small>
        </div>
        <div class="mw-card">
          <span class="mw-label">上轮生活补贴</span>
          <strong>{{ fmt(status.dashboard.last_subsidy_total) }} 点</strong>
          <small>{{ status.dashboard.last_subsidy_groups }} 组无岗</small>
        </div>
        <div class="mw-card">
          <span class="mw-label">上轮市民购买</span>
          <strong>{{ fmt(status.dashboard.last_purchases) }} 笔</strong>
          <small>累计 {{ fmt(status.dashboard.pop_orders_total) }} 笔</small>
        </div>
        <div class="mw-card">
          <span class="mw-label">市民钱包</span>
          <strong>在岗 {{ fmt(status.pop_groups.employed_wallet_total) }}</strong>
          <small>无岗 {{ fmt(status.pop_groups.unemployed_wallet_total) }} · {{ status.pop_groups.employed_count }}/{{ status.pop_groups.count }} 组在岗</small>
        </div>
      </section>

      <p v-if="status.last_tick" class="mw-meta">
        最近 tick：{{ status.last_tick.tick_date }}
      </p>

      <section class="mw-config">
        <h2>乌托邦底线</h2>
        <ul>
          <li>最低工资 {{ status.config.min_wage }} 点 / 人 / 日</li>
          <li>无岗补贴 {{ status.config.min_subsidy }} 点 / 人 / 日</li>
          <li>城市日注入 {{ fmt(status.config.welfare_grant) }} 点</li>
        </ul>
      </section>

      <section>
        <h2>机构</h2>
        <ul class="mw-inst">
          <li v-for="inst in status.institutions" :key="inst.id">
            <strong>{{ inst.display_name }}</strong>
            <span class="mw-dim"> · {{ inst.wallet_credits }} 点</span>
            <span v-if="inst.offer_id">
              · <a :href="'/miraworld/play/chen.html'">Spotlight</a>
            </span>
          </li>
        </ul>
      </section>
    </template>

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

.mw-err {
  color: #c0392b;
}

.mw-dim {
  color: var(--vp-c-text-3);
  font-size: 0.875rem;
}

.mw-meta {
  font-size: 0.8125rem;
  color: var(--vp-c-text-3);
  margin: 0.5rem 0 1rem;
}

.mw-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
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

.mw-config ul,
.mw-inst {
  list-style: none;
  padding: 0;
}

.mw-inst li {
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--vp-c-divider);
}

.mw-back {
  margin-top: 1.5rem;
  font-size: 0.875rem;
}
</style>
