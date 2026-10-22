<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  duration: { type: Number, default: 700 },
  decimals: { type: Number, default: 0 },
  prefix: { type: String, default: '' },
  suffix: { type: String, default: '' }
})

const display = ref(0)
let raf = null

function animate(to) {
  const from = display.value
  const target = Number(to) || 0
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    display.value = target
    return
  }
  const start = performance.now()
  cancelAnimationFrame(raf)
  const step = now => {
    const p = Math.min(1, (now - start) / props.duration)
    const eased = 1 - Math.pow(1 - p, 3)
    display.value = from + (target - from) * eased
    if (p < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}

const text = computed(() => display.value.toLocaleString('zh-CN', {
  minimumFractionDigits: props.decimals,
  maximumFractionDigits: props.decimals
}))

onMounted(() => animate(props.value))
watch(() => props.value, animate)
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <span class="num">{{ prefix }}{{ text }}{{ suffix }}</span>
</template>
