<script setup>
import { onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  radius: { type: Number, default: 260 },
  disabled: { type: Boolean, default: false }
})

const el = ref(null)
let raf = null

function onMove(e) {
  if (props.disabled || !window.matchMedia('(pointer: fine)').matches) return
  const rect = el.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  cancelAnimationFrame(raf)
  raf = requestAnimationFrame(() => {
    el.value.style.setProperty('--mx', x + 'px')
    el.value.style.setProperty('--my', y + 'px')
  })
}

function onLeave() {
  el.value?.style.setProperty('--mx', '-999px')
  el.value?.style.setProperty('--my', '-999px')
}

onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <div ref="el" class="spotlight" @mousemove="onMove" @mouseleave="onLeave">
    <slot />
  </div>
</template>

<style scoped>
.spotlight { position: relative; overflow: hidden; }
.spotlight::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle 260px at var(--mx, -999px) var(--my, -999px),
              rgba(47, 111, 237, .11), transparent 65%);
  opacity: 0;
  transition: opacity .25s ease;
  z-index: 0;
}
.spotlight:hover::before { opacity: 1; }
.spotlight > :deep(*) { position: relative; z-index: 1; }
@media (prefers-reduced-motion: reduce) {
  .spotlight::before { display: none; }
}
</style>
