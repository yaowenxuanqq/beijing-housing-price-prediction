<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  delay: { type: Number, default: 0 },
  distance: { type: Number, default: 16 },
  once: { type: Boolean, default: true }
})

const el = ref(null)
const visible = ref(false)
let observer = null

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    visible.value = true
    return
  }
  observer = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) {
      visible.value = true
      if (props.once) observer.disconnect()
    }
  }, { threshold: 0.12 })
  observer.observe(el.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div
    ref="el"
    class="reveal"
    :class="{ visible }"
    :style="{ transitionDelay: delay + 'ms', '--reveal-distance': distance + 'px' }"
  >
    <slot />
  </div>
</template>

<style scoped>
.reveal {
  opacity: 0;
  transform: translateY(var(--reveal-distance));
  transition: opacity .55s cubic-bezier(.22,.61,.36,1), transform .55s cubic-bezier(.22,.61,.36,1);
  will-change: opacity, transform;
}
.reveal.visible { opacity: 1; transform: translateY(0); }
@media (prefers-reduced-motion: reduce) {
  .reveal { opacity: 1; transform: none; transition: none; }
}
</style>
