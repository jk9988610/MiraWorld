<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
import UserNav from './components/UserNav.vue'
import GameShell from './components/GameShell.vue'
import PlayLocalHud from './components/PlayLocalHud.vue'
import PlayMenuExtras from './components/PlayMenuExtras.vue'

const Layout = DefaultTheme.Layout
</script>

<template>
  <Layout>
    <template #nav-bar-content-after>
      <UserNav />
    </template>
    <template #sidebar-nav-after>
      <PlayMenuExtras />
    </template>
    <template #nav-screen-content-after>
      <PlayMenuExtras />
    </template>
    <template #layout-bottom>
      <PlayLocalHud />
      <GameShell />
    </template>
  </Layout>
</template>
