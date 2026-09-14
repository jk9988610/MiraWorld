<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
import UserNav from './components/UserNav.vue'
import GameShell from './components/GameShell.vue'
import WorldStatusBar from './components/WorldStatusBar.vue'

const Layout = DefaultTheme.Layout
</script>

<template>
  <Layout>
    <template #nav-bar-content-after>
      <UserNav />
    </template>
    <template #layout-bottom>
      <WorldStatusBar />
      <GameShell />
    </template>
  </Layout>
</template>
