<script setup>
import echarts from '../utils/echartsTheme'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' }
})
const emit = defineEmits(['chart-click'])

const el = ref(null)
let chart = null
let observer = null

function render() {
  if (!chart) return
  chart.setOption(props.option, true)
  chart.resize()
}

onMounted(() => {
  chart = echarts.init(el.value, 'housing')
  render()
  chart.on('click', params => emit('chart-click', params))
  observer = new ResizeObserver(() => chart && chart.resize())
  observer.observe(el.value)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  if (chart) chart.dispose()
  chart = null
})
</script>

<template>
  <div ref="el" :style="{ height, width: '100%' }" />
</template>
