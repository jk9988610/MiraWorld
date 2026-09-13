<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame } from '../composables/useGame'

const { user, refresh, isLoggedIn } = useAuth()
const { world, loadWorld, visit } = useGame()
const message = ref('')
const error = ref('')

const chaodeng = computed(() => world.value?.cities.find((c) => c.city === '潮灯市'))

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
      if (r.first_visit) message.value = world.value?.onboarding_message || ''
    } catch (e) {
      error.value = e instanceof Error ? e.message : '打卡失败'
    }
  }
})

async function visitSpot(spotId: string, name: string) {
  error.value = ''
  try {
    const r = await visit('潮灯市', spotId)
    message.value = r.first_visit ? `你第一次到「${name}」。` : `你又来过「${name}」。`
  } catch (e) {
    error.value = e instanceof Error ? e.message : '打卡失败'
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

    <section v-if="chaodeng?.explore_spots?.length">
      <h2>逛点</h2>
      <ul class="mw-list">
        <li v-for="s in chaodeng.explore_spots" :key="s.id">
          <button type="button" class="mw-spot" @click="visitSpot(s.id, s.name)">
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
        </li>
      </ul>
      <p class="mw-hint">食堂：找 <strong>陈师傅</strong>（点面 · Phase 2）</p>
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

.mw-list {
  padding-left: 0;
  list-style: none;
}

.mw-spot {
  width: 100%;
  text-align: left;
  margin-bottom: 0.5rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-elv);
  cursor: pointer;
  font: inherit;
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
  margin: 0.25rem 0 0.75rem;
  font-size: 0.875rem;
  color: var(--vp-c-text-2);
}

.mw-hint {
  font-size: 0.875rem;
  color: var(--vp-c-text-3);
}
</style>
