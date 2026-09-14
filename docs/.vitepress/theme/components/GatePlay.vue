<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useGame, type WorldSave } from '../composables/useGame'

const { refresh, isLoggedIn, user, login, register, logout, readRememberPrefs, loading } = useAuth()
const { loadWorldGate, worldNew, worldContinue, worldLoad } = useGame()

const gate = ref<Awaited<ReturnType<typeof loadWorldGate>> | null>(null)
const error = ref('')
const busy = ref(false)
const soloName = ref('')
const soloIronman = ref(false)
const showSoloNew = ref(false)
const loadScope = ref<'solo' | 'multi' | null>(null)

const authMode = ref<'login' | 'register'>('login')
const handle = ref('')
const password = ref('')
const email = ref('')
const remember = ref(false)
const prefs = readRememberPrefs()
handle.value = prefs.handle
remember.value = prefs.remember

onMounted(async () => {
  await refresh()
  if (isLoggedIn.value) {
    await reload()
  }
})

async function reload() {
  error.value = ''
  try {
    gate.value = await loadWorldGate()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
}

function enterCity() {
  window.location.assign('/miraworld/play/city.html')
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

async function onAuthSubmit() {
  error.value = ''
  busy.value = true
  try {
    if (authMode.value === 'register') {
      await register(handle.value.trim(), password.value, email.value || undefined, remember.value)
    } else {
      await login(handle.value.trim(), password.value, remember.value)
    }
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    busy.value = false
  }
}

async function onLogout() {
  busy.value = true
  error.value = ''
  try {
    await logout()
    gate.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '退出失败'
  } finally {
    busy.value = false
  }
}

function openSoloNew() {
  soloName.value = ''
  soloIronman.value = false
  showSoloNew.value = true
}

async function confirmSoloNew() {
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

function resumeActive() {
  enterCity()
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
  <div class="mw-gate">
    <h1>米拉世界 · 门控</h1>
    <p class="mw-lead">登录后选择单人 / 多人存档进入潮灯市。</p>
    <p v-if="error" class="mw-err">{{ error }}</p>

    <section v-if="!isLoggedIn" class="mw-block">
      <div class="mw-tabs">
        <button
          type="button"
          class="mw-tab"
          :class="{ active: authMode === 'login' }"
          @click="authMode = 'login'"
        >
          登录
        </button>
        <button
          type="button"
          class="mw-tab"
          :class="{ active: authMode === 'register' }"
          @click="authMode = 'register'"
        >
          注册
        </button>
      </div>
      <form class="mw-auth" @submit.prevent="onAuthSubmit">
        <label>
          <span>名字</span>
          <input v-model="handle" type="text" required minlength="2" maxlength="32" autocomplete="username" />
        </label>
        <label v-if="authMode === 'register'">
          <span>邮箱（可选）</span>
          <input v-model="email" type="email" autocomplete="email" />
        </label>
        <label>
          <span>密码</span>
          <input
            v-model="password"
            type="password"
            required
            :minlength="authMode === 'register' ? 8 : 1"
            :autocomplete="authMode === 'login' ? 'current-password' : 'new-password'"
          />
        </label>
        <label class="mw-check">
          <input v-model="remember" type="checkbox" />
          自动登录（记住账号，延长登录有效期）
        </label>
        <button type="submit" class="mw-btn" :disabled="busy || loading">
          {{ busy ? '请稍候…' : authMode === 'login' ? '登录' : '注册并进入' }}
        </button>
      </form>
    </section>

    <template v-else-if="gate">
      <div class="mw-userbar">
        <span>已登录：{{ user?.handle }}</span>
        <button type="button" class="mw-mini" :disabled="busy" @click="onLogout">退出登录</button>
      </div>

      <section v-if="gate.active_session" class="mw-block mw-resume">
        <h2>进行中的游戏</h2>
        <p>
          {{ gate.active_session.display_name }} · 第 {{ gate.active_session.world_day }} 日
          <span v-if="gate.active_session.ironman" class="mw-tag">铁人</span>
        </p>
        <button type="button" class="mw-btn" :disabled="busy" @click="resumeActive">继续进入潮灯市</button>
      </section>

      <section class="mw-block">
        <h2>单人模式</h2>
        <button type="button" class="mw-btn" :disabled="busy" @click="openSoloNew">新的单人模式</button>
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
    </template>

    <p v-else-if="isLoggedIn" class="mw-loading">加载存档…</p>

    <div v-if="showSoloNew" class="mw-modal">
      <div class="mw-modal-inner">
        <h3>新建单人存档</h3>
        <p class="mw-dim">铁人模式仅在新建时选择一次，之后不能更改。</p>
        <div class="mw-new">
          <input v-model="soloName" maxlength="32" placeholder="存档名（可选）" />
          <label class="mw-check">
            <input v-model="soloIronman" type="checkbox" />
            铁人模式（退出自动存，不能手动存）
          </label>
        </div>
        <div class="mw-row">
          <button type="button" class="mw-btn" :disabled="busy" @click="confirmSoloNew">开始</button>
          <button type="button" class="mw-mini" :disabled="busy" @click="showSoloNew = false">取消</button>
        </div>
      </div>
    </div>

    <div v-if="loadScope" class="mw-modal">
      <div class="mw-modal-inner">
        <h3>{{ loadScope === 'solo' ? '加载单人存档' : '加载多人存档' }}</h3>
        <ul class="mw-list">
          <li v-for="s in (loadScope === 'solo' ? gate?.solo_saves : gate?.multi_saves) || []" :key="s.id">
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
.mw-tabs { display: flex; gap: 0.35rem; margin-bottom: 0.85rem; }
.mw-tab {
  flex: 1;
  padding: 0.45rem;
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
  cursor: pointer;
}
.mw-tab.active {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
  font-weight: 600;
}
.mw-auth { display: flex; flex-direction: column; gap: 0.75rem; }
.mw-auth label span { display: block; margin-bottom: 0.25rem; font-size: 0.875rem; }
.mw-auth input[type='text'],
.mw-auth input[type='password'],
.mw-auth input[type='email'],
.mw-new input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg);
  font: inherit;
}
.mw-userbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin: 0.75rem 0;
  font-size: 0.9rem;
}
.mw-new { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0.75rem; }
.mw-check { font-size: 0.875rem; display: flex; gap: 0.4rem; align-items: center; }
.mw-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
.mw-btn {
  padding: 0.55rem 1rem;
  border: none;
  border-radius: 8px;
  background: var(--vp-c-brand-1);
  color: #fff;
  cursor: pointer;
  font: inherit;
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
.mw-resume p { margin: 0 0 0.75rem; }
</style>
