<script setup>
import { computed, onMounted, ref } from 'vue'
import ChartCard from '../components/ChartCard.vue'
import BaseChart from '../components/BaseChart.vue'
import { fetchCorrelation, fetchDistribution, fetchImportance } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const loading = ref(true)
const loadError = ref(false)
const dist = ref(null)
const corr = ref(null)
const importance = ref([])
const showAllImportance = ref(false)

async function load() {
  loading.value = true
  loadError.value = false
  try {
    const [d, c, i] = await Promise.all([fetchDistribution(), fetchCorrelation(), fetchImportance()])
    dist.value = d
    corr.value = c
    importance.value = i
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)

const toolbox = {
  right: 4, top: 0,
  feature: { saveAsImage: { title: '保存图片', pixelRatio: 2, backgroundColor: '#fff' } }
}

const histOption = computed(() => {
  const bins = dist.value?.histogram?.bins || []
  const counts = dist.value?.histogram?.counts || []
  const labels = counts.map((_, i) => ((bins[i] + bins[i + 1]) / 2).toFixed(0))
  return {
    toolbox,
    grid: { left: 50, right: 20, top: 30, bottom: 36 },
    tooltip: { trigger: 'axis', formatter: p => `总价约 ${p[0].name} 万<br/>房源数：${fmtNumber(p[0].value)}` },
    xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10, interval: 4 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: counts, barWidth: '82%', itemStyle: { color: '#2f6fed', borderRadius: [3, 3, 0, 0] } }]
  }
})

const scatterOption = computed(() => ({
  toolbox,
  grid: { left: 56, right: 24, top: 30, bottom: 42 },
  tooltip: { formatter: p => `${p.data[0]}㎡ / ${fmtNumber(p.data[1])}万` },
  xAxis: { type: 'value', name: '面积（㎡）' },
  yAxis: { type: 'value', name: '总价（万元）' },
  series: [{
    type: 'scatter', symbolSize: 5, data: (dist.value?.scatter || []).map(r => [r.square, r.total_price]),
    itemStyle: { color: 'rgba(47,111,237,.45)' }
  }]
}))

const corrOption = computed(() => {
  const fields = corr.value?.fields || []
  const matrix = corr.value?.matrix || []
  const data = []
  matrix.forEach((row, i) => row.forEach((v, j) => data.push([j, i, Number(v.toFixed(2))])))
  return {
    toolbox,
    grid: { left: 90, right: 20, top: 28, bottom: 70 },
    tooltip: { formatter: p => `${fields[p.data[0]]} ~ ${fields[p.data[1]]}: ${p.data[2]}` },
    xAxis: { type: 'category', data: fields, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'category', data: fields, axisLabel: { fontSize: 10 } },
    visualMap: { min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 10, itemHeight: 80, inRange: { color: ['#313695', '#ffffff', '#d73027'] } },
    series: [{ type: 'heatmap', data, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,.3)' } } }]
  }
})

const impOption = computed(() => {
  const list = showAllImportance.value ? importance.value : importance.value.slice(0, 8)
  const rows = [...list].reverse()
  return {
    toolbox,
    grid: { left: 120, right: 60, top: 28, bottom: 24 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: rows.map(r => r.feature), axisLabel: { fontSize: 11 } },
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}: ${p[0].value}` },
    series: [{ type: 'bar', data: rows.map(r => r.importance), barWidth: 13, itemStyle: { color: '#13c2c2', borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value } }]
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>可视化分析</h2>
      <span class="sub">分布、关系、相关性与特征重要性</span>
    </div>

    <div v-if="loadError" class="card error-banner">
      数据加载失败，请确认后端已启动
      <el-button size="small" type="primary" link @click="load">重试</el-button>
    </div>

    <div class="grid grid-2">
      <ChartCard title="总价分布" :loading="loading" :empty="!dist?.histogram?.counts?.length">
        <BaseChart :option="histOption" height="320px" />
      </ChartCard>
      <ChartCard title="面积与总价关系（抽样 3000）" :loading="loading" :empty="!dist?.scatter?.length">
        <BaseChart :option="scatterOption" height="320px" />
      </ChartCard>
      <ChartCard title="特征相关性矩阵" :loading="loading" :empty="!corr?.matrix?.length">
        <template #extra>
          <el-tag v-if="corr?.leakage_fields" size="small" type="warning" effect="plain">
            含泄漏字段：{{ corr.leakage_fields.join(' / ') }}
          </el-tag>
        </template>
        <BaseChart :option="corrOption" height="420px" />
      </ChartCard>
      <ChartCard title="特征重要性（部署模型）" :loading="loading" :empty="!importance.length">
        <template #extra>
          <el-button v-if="importance.length > 8" size="small" link type="primary"
                     @click="showAllImportance = !showAllImportance">
            {{ showAllImportance ? '收起' : '展开全部' }}
          </el-button>
        </template>
        <BaseChart :option="impOption" height="420px" />
      </ChartCard>
    </div>

    <div class="card mt-16 note">
      <b>说明：</b>相关性矩阵中的单价、总价、小区均价为<b>泄漏字段</b>，仅用于探索性分析，建模时已排除；
      相关性基于随机抽样 2 万行计算并在进程内缓存。
    </div>
  </div>
</template>

<style scoped>
.note { font-size: 12px; color: var(--text-secondary); padding: 12px 18px; line-height: 1.6; }
.error-banner { margin-bottom: var(--space-4); color: var(--color-danger); display: flex; align-items: center; gap: 8px; }
</style>
