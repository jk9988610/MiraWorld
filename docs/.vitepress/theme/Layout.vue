<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
import UserNav from './components/UserNav.vue'

const Layout = DefaultTheme.Layout
</script>

<template>
  <Layout>
    <template #nav-bar-content-after>
      <UserNav />
    </template>
  </Layout>
</template>
