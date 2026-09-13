<script setup lang="ts">
defineProps<{ title: string; hint: string }>()
</script>

<template>
  <div class="mw-play mw-play--pad">
    <h1>{{ title }}</h1>
    <p class="mw-dim">{{ hint }}</p>
  </div>
</template>

<style scoped>
.mw-play--pad {
  padding-bottom: 4.5rem;
}
.mw-dim {
  color: var(--vp-c-text-3);
}
</style>
