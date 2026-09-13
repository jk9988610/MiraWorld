<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const API_BASE = '/miraworld/api'
const { user, refresh, isLoggedIn } = useAuth()
const visits = ref<Array<{ city: string; spot_id: string; first_at: string }>>([])
const bio = ref('')
const saving = ref(false)

onMounted(async () => {
  await refresh()
  if (!isLoggedIn.value) {
    window.location.href = '/miraworld/auth/login.html'
    return
  }
  if (user.value) bio.value = user.value.bio
  const res = await fetch(`${API_BASE}/me/visits`, { credentials: 'include' })
  if (res.ok) {
    const data = await res.json()
    visits.value = data.visits || []
  }
})

async function saveBio() {
  saving.value = true
  try {
    await fetch(`${API_BASE}/me`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bio: bio.value }),
    })
    await refresh()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mw-play mw-play--pad" v-if="user">
    <h1>我的</h1>
    <p><strong>{{ user.handle }}</strong></p>
    <p>所在：{{ user.city }}</p>
    <p>余额：<strong>{{ user.wallet_credits }}</strong> 点</p>

    <label class="mw-bio">
      <span>简介</span>
      <textarea v-model="bio" rows="3" maxlength="280" />
      <button type="button" :disabled="saving" @click="saveBio">保存</button>
    </label>

    <h2>足迹</h2>
    <ul v-if="visits.length" class="mw-visits">
      <li v-for="(v, i) in visits" :key="i">
        {{ v.city }}<template v-if="v.spot_id"> · {{ v.spot_id }}</template>
      </li>
    </ul>
    <p v-else class="mw-dim">
      还没有足迹。去<a href="/miraworld/play/city.html">潮灯市地图</a>打卡，
      逛点里每个地方都有第一次到访的小句子。
    </p>
  </div>
</template>

<style scoped>
.mw-play--pad {
  padding-bottom: 4.5rem;
}

.mw-bio {
  display: block;
  margin: 1rem 0;
}

.mw-bio textarea {
  width: 100%;
  box-sizing: border-box;
  margin: 0.35rem 0;
  padding: 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--vp-c-border);
  font: inherit;
}

.mw-visits {
  padding-left: 1.2rem;
}

.mw-dim {
  color: var(--vp-c-text-3);
}
</style>
