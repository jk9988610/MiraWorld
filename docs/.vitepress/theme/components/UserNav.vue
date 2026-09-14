<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'

const { user, loading, isLoggedIn, refresh } = useAuth()

onMounted(() => {
  refresh()
})
</script>

<template>
  <div class="mw-user-nav" v-if="!loading || isLoggedIn">
    <template v-if="isLoggedIn && user">
      <a class="mw-user-name" href="/miraworld/play/me.html" :title="`${user.wallet_credits} 点`">
        {{ user.handle }}
      </a>
    </template>
    <template v-else>
      <a class="mw-auth-btn mw-auth-btn--primary" href="/miraworld/play/gate.html">登录</a>
    </template>
  </div>
</template>

<style scoped>
.mw-user-nav {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-left: 0.5rem;
}

.mw-user-name {
  max-width: 6rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8125rem;
  color: var(--vp-c-text-2);
  text-decoration: none;
}

.mw-auth-btn {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  text-decoration: none;
  border: 1px solid var(--vp-c-divider);
  cursor: pointer;
}

.mw-auth-btn--primary {
  border-color: var(--vp-c-brand-1);
  background: var(--vp-c-brand-1);
  color: #fff;
}
</style>
