<script setup>
import EmptyState from './EmptyState.vue'
import SpotlightCard from './fx/SpotlightCard.vue'

defineProps({
  title: { type: String, required: true },
  loading: { type: Boolean, default: false },
  empty: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂无数据' }
})
</script>

<template>
  <SpotlightCard class="card chart-card">
    <div class="chart-head">
      <h3 class="card-title">{{ title }}</h3>
      <slot name="extra" />
    </div>
    <el-skeleton v-if="loading" :rows="5" animated />
    <EmptyState v-else-if="empty" :text="emptyText" />
    <slot v-else />
  </SpotlightCard>
</template>

<style scoped>
.chart-card { display: flex; flex-direction: column; min-width: 0; }
.chart-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
</style>
