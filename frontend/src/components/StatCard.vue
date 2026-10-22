<script setup>
import SpotlightCard from './fx/SpotlightCard.vue'
import NumberTicker from './fx/NumberTicker.vue'

defineProps({
  label: { type: String, required: true },
  value: { type: Number, default: 0 },
  unit: { type: String, default: '' },
  hint: { type: String, default: '' },
  decimals: { type: Number, default: 0 },
  accent: { type: String, default: 'var(--color-primary)' }
})
</script>

<template>
  <SpotlightCard class="card interactive stat">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value" :style="{ color: accent }">
      <NumberTicker :value="value" :decimals="decimals" />
      <span v-if="unit" class="stat-unit">{{ unit }}</span>
    </div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </SpotlightCard>
</template>

<style scoped>
.stat { display: flex; flex-direction: column; gap: 8px; min-height: 112px; justify-content: center; }
.stat-label { font-size: var(--font-13); color: var(--text-secondary); }
.stat-value { font-size: var(--font-28); font-weight: 700; line-height: 1.15; letter-spacing: .4px; }
.stat-unit { font-size: var(--font-13); font-weight: 500; margin-left: 4px; color: var(--text-secondary); }
.stat-hint { font-size: var(--font-12); color: var(--text-muted); }
</style>
