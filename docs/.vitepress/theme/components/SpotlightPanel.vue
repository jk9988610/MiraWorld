<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useGame, type SpotlightItem } from '../composables/useGame'

const props = defineProps<{
  institutionId: string
  title?: string
}>()

const { loadSpotlight } = useGame()
const items = ref<SpotlightItem[]>([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await loadSpotlight(props.institutionId)
    items.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section v-if="!loading && items.length" class="mw-spotlight">
    <h2>{{ title || '今日来客' }}</h2>
    <p class="mw-dim">市民买了什么，姓与职业来自真实岗位（最多 10 条）。</p>
    <ul class="mw-spotlist">
      <li v-for="(item, idx) in items" :key="`${item.order_id}-${idx}`">
        <strong>{{ item.display_name }}</strong>
        <span class="mw-dim"> · {{ item.job_display }}</span>
      </li>
    </ul>
  </section>
  <p v-else-if="error" class="mw-err">{{ error }}</p>
</template>

<style scoped>
.mw-spotlight {
  margin: 1.25rem 0;
  padding: 1rem;
  border-radius: 10px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
}

.mw-spotlight h2 {
  margin: 0 0 0.35rem;
  font-size: 1rem;
}

.mw-dim {
  color: var(--vp-c-text-3);
  font-size: 0.8125rem;
  margin: 0 0 0.75rem;
}

.mw-spotlist {
  list-style: none;
  padding: 0;
  margin: 0;
}

.mw-spotlist li {
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--vp-c-divider);
  font-size: 0.9375rem;
}

.mw-spotlist li:last-child {
  border-bottom: none;
}

.mw-err {
  color: #c0392b;
  font-size: 0.875rem;
}
</style>
