<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const props = defineProps<{
  mode: 'login' | 'register'
}>()

const { login, register } = useAuth()

const email = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const submitting = ref(false)

async function onSubmit() {
  error.value = ''
  submitting.value = true
  try {
    if (props.mode === 'register') {
      await register(email.value, password.value, displayName.value)
    } else {
      await login(email.value, password.value)
    }
    window.location.href = '/miraworld/'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="mw-auth-form" @submit.prevent="onSubmit">
    <h1>{{ mode === 'login' ? '登录' : '注册账号' }}</h1>
    <p class="mw-auth-lead">
      {{ mode === 'login' ? '登录后可保存探索进度与个性化设置。' : '创建账号以参与 MiraWorld 的探索。' }}
    </p>

    <label v-if="mode === 'register'">
      <span>显示名称</span>
      <input v-model="displayName" type="text" required maxlength="64" autocomplete="nickname" />
    </label>

    <label>
      <span>邮箱</span>
      <input v-model="email" type="email" required autocomplete="email" />
    </label>

    <label>
      <span>密码</span>
      <input
        v-model="password"
        type="password"
        required
        :minlength="mode === 'register' ? 8 : 1"
        :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
      />
      <small v-if="mode === 'register'">至少 8 位</small>
    </label>

    <p v-if="error" class="mw-auth-error">{{ error }}</p>

    <button type="submit" class="mw-auth-submit" :disabled="submitting">
      {{ submitting ? '请稍候…' : mode === 'login' ? '登录' : '注册' }}
    </button>

    <p class="mw-auth-switch">
      <template v-if="mode === 'login'">
        还没有账号？
        <a href="/miraworld/auth/register.html">去注册</a>
      </template>
      <template v-else>
        已有账号？
        <a href="/miraworld/auth/login.html">去登录</a>
      </template>
    </p>
  </form>
</template>

<style scoped>
.mw-auth-form {
  max-width: 24rem;
  margin: 2rem auto 4rem;
  padding: 1.5rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-elv);
}

.mw-auth-form h1 {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
}

.mw-auth-lead {
  margin: 0 0 1.25rem;
  color: var(--vp-c-text-2);
  font-size: 0.9375rem;
}

label {
  display: block;
  margin-bottom: 1rem;
}

label span {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.875rem;
  font-weight: 500;
}

input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--vp-c-border);
  border-radius: 8px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font: inherit;
}

small {
  display: block;
  margin-top: 0.25rem;
  color: var(--vp-c-text-3);
  font-size: 0.8125rem;
}

.mw-auth-error {
  color: #c0392b;
  font-size: 0.875rem;
}

.mw-auth-submit {
  width: 100%;
  margin-top: 0.5rem;
  padding: 0.65rem 1rem;
  border: none;
  border-radius: 8px;
  background: var(--vp-c-brand-1);
  color: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.mw-auth-submit:disabled {
  opacity: 0.7;
  cursor: wait;
}

.mw-auth-switch {
  margin: 1rem 0 0;
  text-align: center;
  font-size: 0.875rem;
  color: var(--vp-c-text-2);
}
</style>
