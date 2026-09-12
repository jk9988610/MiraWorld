<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'

const { user, loading, isLoggedIn, refresh, logout } = useAuth()

onMounted(() => {
  refresh()
})

async function handleLogout() {
  await logout()
}
</script>

<template>
  <div class="mw-user-nav" v-if="!loading || isLoggedIn">
    <template v-if="isLoggedIn && user">
      <span class="mw-user-name" :title="user.email">{{ user.display_name }}</span>
      <button type="button" class="mw-auth-btn mw-auth-btn--ghost" @click="handleLogout">
        退出
      </button>
    </template>
    <template v-else>
      <a class="mw-auth-btn" href="/miraworld/auth/login.html">登录</a>
      <a class="mw-auth-btn mw-auth-btn--primary" href="/miraworld/auth/register.html">注册</a>
    </template>
  </div>
</template>

<style scoped>
.mw-user-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: 0.75rem;
}

.mw-user-name {
  max-width: 8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.875rem;
  color: var(--vp-c-text-2);
}

.mw-auth-btn {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  text-decoration: none;
  border: 1px solid var(--vp-c-divider);
  color: var(--vp-c-text-1);
  background: var(--vp-c-bg-elv);
  cursor: pointer;
}

.mw-auth-btn--primary {
  border-color: var(--vp-c-brand-1);
  background: var(--vp-c-brand-1);
  color: #fff;
}

.mw-auth-btn--ghost {
  background: transparent;
}

.mw-auth-btn:hover {
  opacity: 0.9;
}
</style>
