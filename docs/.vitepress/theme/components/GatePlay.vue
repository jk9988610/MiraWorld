<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type WorldSave } from '../composables/useGame'

const { refresh, isLoggedIn } = useAuth()
const { loadWorldGate, worldNew, worldContinue, worldLoad } = useGame()

const gate = ref<Awaited<ReturnType<typeof loadWorldGate>> | null>(null)
const error = ref('')
const busy = ref(false)
const soloName = ref('')
const soloIronman = ref(false)
const loadScope = ref<'solo' | 'multi' | null>(null)

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
    gate.value = await loadWorldGate()
    if (gate.value.active_session) {
      window.location.href = '/miraworld/play/city.html'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
}

function enterCity() {
  window.location.href = '/miraworld/play/city.html'
}

async function act(fn: () => Promise<unknown>) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await fn()
    enterCity()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
    loadScope.value = null
  }
}

async function onNewSolo() {
  await act(() => worldNew('solo', soloName.value.trim(), soloIronman.value))
}

async function onNewMulti() {
  await act(() => worldNew('multi', '', true))
}

async function onContinue(scope: 'solo' | 'multi') {
  await act(() => worldContinue(scope))
}

async function onPickSave(save: WorldSave) {
  const scope = save.scope as 'solo' | 'multi'
  await act(() => worldLoad(scope, save.id))
}

function fmtTime(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}
</script>

<template>
  <div class="mw-gate" v-if="gate">
    <h1>选择模式与存档</h1>
    <p class="mw-lead">单人模式 / 多人模式；铁人模式退出时自动存档。</p>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <section class="mw-block">
      <h2>单人模式</h2>
      <div class="mw-new">
        <input v-model="soloName" maxlength="32" placeholder="存档名（可选）" />
        <label class="mw-check">
          <input v-model="soloIronman" type="checkbox" />
          铁人模式（游戏内不手动存，退出自动存）
        </label>
        <button type="button" class="mw-btn" :disabled="busy" @click="onNewSolo">新的单人模式</button>
      </div>
      <div class="mw-row">
        <button
          type="button"
          class="mw-btn mw-btn--ghost"
          :disabled="busy || !gate.can_continue_solo"
          @click="onContinue('solo')"
        >
          继续单人模式
        </button>
        <button
          type="button"
          class="mw-btn mw-btn--ghost"
          :disabled="busy || !gate.can_load_solo"
          @click="loadScope = 'solo'"
        >
          加载单人存档
        </button>
      </div>
    </section>

    <section class="mw-block">
      <h2>多人模式</h2>
      <p class="mw-dim">共享潮灯市 · 固定中速 · 默认铁人</p>
      <button type="button" class="mw-btn" :disabled="busy || !gate.can_new_multi" @click="onNewMulti">
        新的多人模式
      </button>
      <p v-if="!gate.can_new_multi" class="mw-dim">已有多人档，请用继续或加载。</p>
      <div class="mw-row">
        <button
          type="button"
          class="mw-btn mw-btn--ghost"
          :disabled="busy || !gate.can_continue_multi"
          @click="onContinue('multi')"
        >
          继续多人模式
        </button>
        <button
          type="button"
          class="mw-btn mw-btn--ghost"
          :disabled="busy || !gate.can_load_multi"
          @click="loadScope = 'multi'"
        >
          加载多人存档
        </button>
      </div>
    </section>

    <div v-if="loadScope" class="mw-modal">
      <div class="mw-modal-inner">
        <h3>{{ loadScope === 'solo' ? '加载单人存档' : '加载多人存档' }}</h3>
        <ul class="mw-list">
          <li v-for="s in (loadScope === 'solo' ? gate.solo_saves : gate.multi_saves)" :key="s.id">
            <button type="button" class="mw-save" :disabled="busy" @click="onPickSave(s)">
              <strong>{{ s.display_name }}</strong>
              <span>第 {{ s.world_day }} 日</span>
              <span v-if="s.ironman" class="mw-tag">铁人</span>
              <small>{{ fmtTime(s.last_played_at) }}</small>
            </button>
          </li>
        </ul>
        <button type="button" class="mw-mini" @click="loadScope = null">取消</button>
      </div>
    </div>
  </div>
  <p v-else class="mw-loading">加载中…</p>
</template>

<style scoped>
.mw-gate {
  max-width: 28rem;
  margin: 1.5rem auto 5rem;
  padding: 0 1rem;
}
.mw-lead { color: var(--vp-c-text-2); }
.mw-err { color: #c0392b; }
.mw-dim { color: var(--vp-c-text-3); font-size: 0.875rem; }
.mw-block {
  margin: 1.25rem 0;
  padding: 1rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg-elv);
}
.mw-block h2 { margin: 0 0 0.75rem; font-size: 1.05rem; }
.mw-new { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0.75rem; }
.mw-new input {
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
}
.mw-check { font-size: 0.875rem; display: flex; gap: 0.4rem; align-items: center; }
.mw-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
.mw-btn {
  padding: 0.55rem 1rem;
  border: none;
  border-radius: 8px;
  background: var(--vp-c-brand-1);
  color: #fff;
  cursor: pointer;
}
.mw-btn--ghost {
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  border: 1px solid var(--vp-c-divider);
}
.mw-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.mw-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
}
.mw-modal-inner {
  background: var(--vp-c-bg-elv);
  border-radius: 12px;
  padding: 1rem;
  max-width: 24rem;
  width: 100%;
  max-height: 70vh;
  overflow: auto;
}
.mw-list { list-style: none; padding: 0; margin: 0.75rem 0; }
.mw-save {
  width: 100%;
  text-align: left;
  padding: 0.65rem;
  margin-bottom: 0.35rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
  cursor: pointer;
}
.mw-save strong { display: block; }
.mw-tag {
  display: inline-block;
  margin-left: 0.35rem;
  padding: 0 0.35rem;
  border-radius: 4px;
  background: #8e44ad;
  color: #fff;
  font-size: 0.75rem;
}
.mw-mini {
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
  cursor: pointer;
}
.mw-loading { text-align: center; padding: 3rem; color: var(--vp-c-text-3); }
</style>
