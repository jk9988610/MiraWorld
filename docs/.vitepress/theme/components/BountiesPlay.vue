<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type BountyData } from '../composables/useGame'

const STATUS: Record<string, string> = {
  open: '待接',
  taken: '进行中',
  submitted: '待确认',
  settled: '已完成',
  cancelled: '已取消',
}

type TabKey = 'open' | 'issued' | 'taken'

const { user, refresh, isLoggedIn } = useAuth()
const {
  loadBounties,
  createBounty,
  takeBounty,
  submitBounty,
  settleBounty,
  cancelBounty,
} = useGame()

const tab = ref<TabKey>('open')
const openList = ref<BountyData[]>([])
const issuedList = ref<BountyData[]>([])
const takenList = ref<BountyData[]>([])
const title = ref('')
const body = ref('')
const price = ref(30)
const inPerson = ref(true)
const error = ref('')
const busy = ref(false)

const currentList = computed(() => {
  if (tab.value === 'open') return openList.value
  if (tab.value === 'issued') return issuedList.value
  return takenList.value
})

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
    const data = await loadBounties()
    openList.value = data.open
    issuedList.value = data.issued
    takenList.value = data.taken
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
}

async function doCreate() {
  if (!title.value.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await createBounty({
      title: title.value.trim(),
      body: body.value.trim(),
      price_credits: price.value,
      in_person: inPerson.value,
    })
    title.value = ''
    body.value = ''
    await refresh()
    await reload()
    tab.value = 'issued'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '发委托失败'
  } finally {
    busy.value = false
  }
}

async function doTake(id: string) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await takeBounty(id)
    await reload()
    tab.value = 'taken'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '接委托失败'
  } finally {
    busy.value = false
  }
}

async function doSubmit(id: string) {
  if (busy.value) return
  busy.value = true
  try {
    await submitBounty(id)
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '交差失败'
  } finally {
    busy.value = false
  }
}

async function doSettle(id: string) {
  if (busy.value) return
  busy.value = true
  try {
    await settleBounty(id)
    await refresh()
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '确认交差失败'
  } finally {
    busy.value = false
  }
}

async function doCancel(id: string) {
  if (busy.value) return
  busy.value = true
  try {
    await cancelBounty(id)
    await refresh()
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取消失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>悬赏栏</h1>
    <p class="mw-lead">发「我要」委托，别人自愿接单、交差结算。仍无配送。</p>
    <p class="mw-meta">余额 {{ user.wallet_credits }} 点</p>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <section class="mw-form">
      <h2>发委托</h2>
      <label>
        <span>标题</span>
        <input v-model="title" maxlength="64" placeholder="例如：找一份晚霞岸线索" />
      </label>
      <label>
        <span>说明（可选）</span>
        <textarea v-model="body" rows="2" maxlength="500" placeholder="具体要什么" />
      </label>
      <label class="mw-inline">
        <span>托管</span>
        <input v-model.number="price" type="number" min="1" max="9999" /> 点
      </label>
      <label class="mw-check">
        <input v-model="inPerson" type="checkbox" />
        当面交差（不发通知）
      </label>
      <button type="button" class="mw-primary" :disabled="busy || !title.trim()" @click="doCreate">
        {{ busy ? '提交中…' : '发委托' }}
      </button>
    </section>

    <nav class="mw-tabs">
      <button type="button" :class="{ active: tab === 'open' }" @click="tab = 'open'">悬赏栏</button>
      <button type="button" :class="{ active: tab === 'issued' }" @click="tab = 'issued'">我发的</button>
      <button type="button" :class="{ active: tab === 'taken' }" @click="tab = 'taken'">我接的</button>
    </nav>

    <ul v-if="currentList.length" class="mw-list">
      <li v-for="b in currentList" :key="b.id" class="mw-card">
        <div class="mw-card-head">
          <strong>{{ b.title }}</strong>
          <span class="mw-price">{{ b.price_credits }} 点</span>
        </div>
        <p v-if="b.body" class="mw-body">{{ b.body }}</p>
        <p class="mw-meta">
          {{ STATUS[b.status] || b.status }}
          · 发单人 {{ b.issuer_handle }}
          <template v-if="b.worker_handle"> · 接单人 {{ b.worker_handle }}</template>
          <template v-if="b.in_person"> · 当面</template>
        </p>
        <div class="mw-actions">
          <button
            v-if="tab === 'open'"
            type="button"
            :disabled="busy"
            @click="doTake(b.id)"
          >
            接委托
          </button>
          <button
            v-if="tab === 'taken' && b.status === 'taken'"
            type="button"
            :disabled="busy"
            @click="doSubmit(b.id)"
          >
            交差
          </button>
          <button
            v-if="tab === 'issued' && b.status === 'submitted'"
            type="button"
            class="mw-primary"
            :disabled="busy"
            @click="doSettle(b.id)"
          >
            确认交差
          </button>
          <button
            v-if="tab === 'issued' && b.status === 'open'"
            type="button"
            :disabled="busy"
            @click="doCancel(b.id)"
          >
            取消
          </button>
        </div>
      </li>
    </ul>
    <p v-else class="mw-dim">
      <template v-if="tab === 'open'">还没有人发委托，你可以先在上面发一单。</template>
      <template v-else-if="tab === 'issued'">你还没有发过委托。</template>
      <template v-else>你还没有接过委托。</template>
    </p>

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
.mw-meta { font-size: 0.875rem; color: var(--vp-c-text-3); }
.mw-err { color: #c0392b; }
.mw-form {
  border: 1px solid var(--vp-c-divider); border-radius: 8px; padding: 1rem;
  margin: 1rem 0; background: var(--vp-c-bg-elv);
}
.mw-form label { display: block; margin-bottom: 0.75rem; }
.mw-form label span { display: block; font-size: 0.875rem; margin-bottom: 0.25rem; }
.mw-form input[type='text'],
.mw-form input[type='number'],
.mw-form textarea {
  width: 100%; box-sizing: border-box; padding: 0.5rem;
  border: 1px solid var(--vp-c-border); border-radius: 6px; font: inherit;
}
.mw-inline input { width: 5rem; display: inline-block; margin-right: 0.35rem; }
.mw-check { display: flex !important; align-items: center; gap: 0.5rem; }
.mw-tabs { display: flex; gap: 0.5rem; margin: 1rem 0; flex-wrap: wrap; }
.mw-tabs button {
  min-height: 40px; padding: 0.4rem 0.85rem; border-radius: 999px;
  border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg); font: inherit; cursor: pointer;
}
.mw-tabs button.active { border-color: var(--vp-c-brand-1); color: var(--vp-c-brand-1); }
.mw-list { list-style: none; padding: 0; }
.mw-card {
  border: 1px solid var(--vp-c-divider); border-radius: 8px; padding: 1rem;
  margin-bottom: 0.75rem; background: var(--vp-c-bg-elv);
}
.mw-card-head { display: flex; justify-content: space-between; gap: 0.5rem; align-items: flex-start; }
.mw-price { color: var(--vp-c-brand-1); font-weight: 600; white-space: nowrap; }
.mw-body { margin: 0.35rem 0; color: var(--vp-c-text-2); }
.mw-actions { margin-top: 0.75rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.mw-actions button, .mw-primary {
  min-height: 44px; padding: 0.5rem 1rem; border-radius: 8px;
  border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg); font: inherit; cursor: pointer;
}
.mw-primary { border: none; background: var(--vp-c-brand-1); color: #fff; font-weight: 600; }
.mw-dim { color: var(--vp-c-text-3); }
.mw-back { margin-top: 1.5rem; font-size: 0.875rem; }
</style>
