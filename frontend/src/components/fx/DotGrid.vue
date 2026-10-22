<script setup>
defineProps({
  size: { type: Number, default: 18 },
  opacity: { type: Number, default: 0.18 }
})
</script>

<template>
  <div
    class="dot-grid"
    :style="{
      backgroundSize: size + 'px ' + size + 'px',
      '--dot-opacity': opacity
    }"
  />
</template>

<style scoped>
.dot-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(circle, rgba(47, 111, 237, var(--dot-opacity)) 1px, transparent 1px);
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, .65), transparent 88%);
  -webkit-mask-image: linear-gradient(to bottom, rgba(0, 0, 0, .65), transparent 88%);
}
</style>
