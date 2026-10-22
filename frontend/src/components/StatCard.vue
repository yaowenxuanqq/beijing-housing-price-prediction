<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: '' },
  hint: { type: String, default: '' },
  accent: { type: String, default: 'var(--primary)' }
})
</script>

<template>
  <div class="card stat">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value num" :style="{ color: accent }">
      {{ value }}<span v-if="unit" class="stat-unit">{{ unit }}</span>
    </div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </div>
</template>

<style scoped>
.stat { display: flex; flex-direction: column; gap: 8px; min-height: 108px; justify-content: center; }
.stat-label { font-size: 13px; color: var(--text-secondary); }
.stat-value { font-size: 30px; font-weight: 700; line-height: 1.1; letter-spacing: .5px; }
.stat-unit { font-size: 13px; font-weight: 500; margin-left: 4px; color: var(--text-secondary); }
.stat-hint { font-size: 12px; color: #909399; }
</style>
