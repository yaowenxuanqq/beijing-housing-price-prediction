<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  eyebrow: { type: String, default: '北京二手房数据平台' },
  flush: { type: Boolean, default: false }
})
</script>

<template>
  <div class="page-header" :class="{ flush }">
    <div class="heading">
      <div class="eyebrow"><span class="eyebrow-dot" />{{ eyebrow }}</div>
      <div class="title-row">
        <h2>{{ title }}</h2>
        <slot name="badge" />
      </div>
      <p v-if="description" class="description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  margin-bottom: 18px;
}
.page-header.flush { margin-bottom: 0; }
.heading { min-width: 0; }
.eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 7px;
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .1em;
}
.eyebrow-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 0 4px var(--color-primary-soft);
}
.title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: clamp(21px, 2vw, 26px);
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -.02em;
}
.description {
  max-width: 760px;
  margin: 7px 0 0;
  color: var(--text-secondary);
  font-size: var(--font-13);
  line-height: 1.65;
}
.actions { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; padding-bottom: 2px; }
@media (max-width: 720px) {
  .page-header { align-items: flex-start; flex-direction: column; gap: 12px; }
  .actions { padding-bottom: 0; }
}
</style>
