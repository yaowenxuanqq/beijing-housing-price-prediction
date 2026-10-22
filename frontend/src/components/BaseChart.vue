<script setup>
import echarts from '../utils/echartsTheme'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' }
})
const emit = defineEmits(['chart-click'])

const el = ref(null)
const renderError = ref(false)
let chart = null
let observer = null
let resizeHandler = null

function render() {
  if (!chart) return
  chart.setOption(props.option, true)
  chart.resize()
}

onMounted(() => {
  try {
    if (!el.value) throw new Error('chart container missing')
    chart = echarts.init(el.value, 'housing')
    render()
    chart.on('click', params => emit('chart-click', params))
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(() => chart && chart.resize())
      observer.observe(el.value)
    } else {
      resizeHandler = () => chart && chart.resize()
      window.addEventListener('resize', resizeHandler)
    }
  } catch {
    renderError.value = true
    if (chart) chart.dispose()
    chart = null
  }
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (chart) chart.dispose()
  chart = null
})
</script>

<template>
  <div v-if="renderError" class="chart-fallback" role="alert" :style="{ height }">
    <span class="fallback-title">图表初始化失败</span>
    <span class="fallback-text">请刷新页面后重试</span>
  </div>
  <div v-else ref="el" :style="{ height, width: '100%' }" />
</template>

<style scoped>
.chart-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--text-secondary);
  background: #fafbfc;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
}
.fallback-title { font-size: 13px; font-weight: 600; color: var(--text-main); }
.fallback-text { font-size: 12px; }
</style>
