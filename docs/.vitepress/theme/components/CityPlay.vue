<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type GroundItem } from '../composables/useGame'
import { actionsForTags } from '../utils/itemActions'

const { user, refresh, isLoggedIn } = useAuth()
const { world, loadWorld, visit, spotPut, spotConsume, spotUse } = useGame()
const message = ref('')
const error = ref('')
const ground = ref<GroundItem | null>(null)
const groundBusy = ref(false)

const chaodeng = computed(() => world.value?.cities.find((c) => c.city === '潮灯市'))
const groundActions = computed(() => actionsForTags(ground.value?.tags))

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  await loadWorld()
  if (user.value) {
    try {
      const r = await visit(user.value.city)
      applyVisit(r.message, r.ground)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '打卡失败'
    }
  }
})

function applyVisit(msg?: string, g?: GroundItem) {
  if (msg) message.value = msg
  ground.value = g?.available ? g : null
}

async function visitSpot(spotId: string) {
  error.value = ''
  ground.value = null
  try {
    const r = await visit('潮灯市', spotId)
    applyVisit(r.message, r.ground)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '打卡失败'
  }
}

async function groundAction(kind: 'put' | 'consume' | 'use') {
  if (!ground.value || groundBusy.value) return
  groundBusy.value = true
  error.value = ''
  try {
    const spotId = ground.value.spot_id
    let msg = ''
    if (kind === 'put') {
      const r = await spotPut('潮灯市', spotId)
      msg = r.message
    } else if (kind === 'consume') {
      const r = await spotConsume('潮灯市', spotId)
      msg = r.message
    } else {
      const r = await spotUse('潮灯市', spotId)
      msg = r.message
    }
    message.value = msg
    ground.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    groundBusy.value = false
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad">
    <h1>{{ chaodeng?.city || '潮灯市' }}</h1>
    <p class="mw-lead">{{ chaodeng?.summary }}</p>
    <p v-if="user" class="mw-meta">你在 {{ user.city }} · {{ user.wallet_credits }} 点</p>
    <p v-if="message" class="mw-msg">{{ message }}</p>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <section v-if="ground" class="mw-ground">
      <h2>眼前</h2>
      <p class="mw-ground-item">
        <strong>{{ ground.display }}</strong>
        <span v-if="ground.qty > 1" class="mw-dim"> × {{ ground.qty }}</span>
      </p>
      <div class="mw-ground-actions">
        <button
          v-if="groundActions.consume"
          type="button"
          class="mw-act"
          :disabled="groundBusy"
          @click="groundAction('consume')"
        >
          食用
        </button>
        <button
          v-if="groundActions.use"
          type="button"
          class="mw-act mw-act--secondary"
          :disabled="groundBusy"
          @click="groundAction('use')"
        >
          使用
        </button>
        <button
          v-if="groundActions.put"
          type="button"
          class="mw-act mw-act--put"
          :disabled="groundBusy"
          @click="groundAction('put')"
        >
          放入背包
        </button>
      </div>
    </section>

    <section v-if="chaodeng?.explore_spots?.length">
      <h2>逛点</h2>
      <ul class="mw-list">
        <li v-for="s in chaodeng.explore_spots" :key="s.id">
          <button type="button" class="mw-spot" @click="visitSpot(s.id)">
            {{ s.name }}
            <small v-if="s.flavor">{{ s.flavor }}</small>
          </button>
        </li>
      </ul>
    </section>

    <section v-if="world?.npcs?.length">
      <h2>找人</h2>
      <ul class="mw-list">
        <li v-for="n in world.npcs" :key="n.id">
          <strong>{{ n.display }}</strong>
          <span class="mw-dim"> · {{ n.city }}</span>
          <p v-if="n.greeting" class="mw-quote">{{ n.greeting }}</p>
          <p v-if="n.extra" class="mw-extra">{{ n.extra }}</p>
          <p v-if="n.id === 'npc_chen'" class="mw-link">
            <a href="/miraworld/play/chen.html">→ 去食堂点面</a>
          </p>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.mw-play--pad {
  padding-bottom: 4.5rem;
}

.mw-play h1 {
  margin-top: 0;
}

.mw-lead {
  color: var(--vp-c-text-2);
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

.mw-ground {
  margin: 1rem 0 1.25rem;
  padding: 1rem;
  border-radius: 10px;
  border: 1px dashed var(--vp-c-brand-1);
  background: color-mix(in srgb, var(--vp-c-brand-1) 5%, var(--vp-c-bg-elv));
}

.mw-ground h2 {
  margin: 0 0 0.5rem;
  font-size: 0.9375rem;
  color: var(--vp-c-text-2);
}

.mw-ground-item {
  margin: 0 0 0.75rem;
}

.mw-ground-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.mw-act {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  background: var(--vp-c-brand-1);
  color: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.mw-act--secondary {
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  border: 1px solid var(--vp-c-divider);
}

.mw-act--put {
  background: var(--vp-c-bg-elv);
  color: var(--vp-c-brand-1);
  border: 1px solid var(--vp-c-brand-1);
}

.mw-act:disabled {
  opacity: 0.6;
  cursor: wait;
}

.mw-list {
  padding-left: 0;
  list-style: none;
}

.mw-spot {
  width: 100%;
  text-align: left;
  min-height: 48px;
  margin-bottom: 0.5rem;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-elv);
  cursor: pointer;
  font: inherit;
  -webkit-tap-highlight-color: transparent;
}

.mw-spot small {
  display: block;
  color: var(--vp-c-text-3);
  margin-top: 0.2rem;
}

.mw-dim {
  color: var(--vp-c-text-3);
}

.mw-quote {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: var(--vp-c-text-2);
}

.mw-extra {
  margin: 0.15rem 0 0.75rem;
  font-size: 0.8125rem;
  color: var(--vp-c-text-3);
  font-style: italic;
}

.mw-link {
  font-size: 0.875rem;
  margin: 0.25rem 0 0;
}
</style>
