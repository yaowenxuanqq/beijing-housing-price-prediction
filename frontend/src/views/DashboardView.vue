<script setup>
import { computed, onMounted, ref } from 'vue'
import StatCard from '../components/StatCard.vue'
import ChartCard from '../components/ChartCard.vue'
import BaseChart from '../components/BaseChart.vue'
import { fetchOverview, fetchDistrictStats, fetchHeatmap, fetchYearlyStats } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const loading = ref(true)
const overview = ref(null)
const districts = ref([])
const heatmap = ref([])
const yearly = ref([])

onMounted(async () => {
  try {
    const [o, d, h, y] = await Promise.all([
      fetchOverview(),
      fetchDistrictStats(),
      fetchHeatmap(5000),
      fetchYearlyStats()
    ])
    overview.value = o
    districts.value = d
    heatmap.value = h
    yearly.value = y
  } finally {
    loading.value = false
  }
})

const districtOption = computed(() => {
  const rows = [...districts.value].reverse()
  return {
    grid: { left: 76, right: 70, top: 16, bottom: 24 },
    xAxis: { type: 'value', axisLabel: { formatter: v => (v / 10000).toFixed(0) + '万' } },
    yAxis: { type: 'category', data: rows.map(r => r.district), axisLabel: { fontSize: 11 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => {
      const r = rows[p[0].dataIndex]
      return `${r.district}<br/>均价：${fmtNumber(Math.round(r.avg_unit_price))} 元/㎡<br/>样本：${fmtNumber(r.count)}`
    }},
    series: [{
      type: 'bar',
      data: rows.map(r => r.avg_unit_price),
      barWidth: 14,
      itemStyle: { color: '#2f6fed', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: p => fmtNumber(Math.round(p.value)), fontSize: 10, color: '#606266' }
    }]
  }
})

const heatmapOption = computed(() => {
  const prices = heatmap.value.map(r => r.unit_price).sort((a, b) => a - b)
  const lo = prices.length ? prices[Math.floor(prices.length * 0.02)] : 15000
  const hi = prices.length ? prices[Math.floor(prices.length * 0.98)] : 105000
  return {
    grid: { left: 56, right: 24, top: 20, bottom: 48 },
    tooltip: {
      formatter: p => `${p.data[2]}<br/>${fmtNumber(Math.round(p.data[3]))} 元/㎡`
    },
    xAxis: { type: 'value', name: '经度', scale: true, nameTextStyle: { fontSize: 11 } },
    yAxis: { type: 'value', name: '纬度', scale: true, nameTextStyle: { fontSize: 11 } },
    visualMap: {
      // 关键：显式指定第 4 维（unit_price）为颜色映射维度
      dimension: 3,
      min: lo, max: hi,
      orient: 'horizontal', left: 'center', bottom: 4,
      text: ['高', '低'], textStyle: { fontSize: 10 }, itemWidth: 10, itemHeight: 80,
      inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#f46d43', '#d73027'] }
    },
    series: [{
      // 5000 点无需 large 模式；large 会削弱 visualMap 的颜色映射
      type: 'scatter', symbolSize: 4,
      data: heatmap.value.map(r => [r.lng, r.lat, r.district, r.unit_price]),
      itemStyle: { opacity: 0.6 }
    }]
  }
})

const yearlyOption = computed(() => ({
  grid: { left: 56, right: 56, top: 28, bottom: 28 },
  tooltip: { trigger: 'axis' },
  legend: { top: 0, right: 0, itemWidth: 12, itemHeight: 8 },
  xAxis: { type: 'category', data: yearly.value.map(r => r.year) },
  yAxis: [
    { type: 'value', name: '成交量', nameTextStyle: { fontSize: 11 } },
    { type: 'value', name: '均价（元/㎡）', nameTextStyle: { fontSize: 11 }, axisLabel: { formatter: v => (v / 10000).toFixed(0) + '万' } }
  ],
  series: [
    { name: '成交量', type: 'bar', data: yearly.value.map(r => r.count), barWidth: 22, itemStyle: { color: '#d9e3f8', borderRadius: [4, 4, 0, 0] }, yAxisIndex: 0 },
    { name: '均价', type: 'line', smooth: true, symbolSize: 6, data: yearly.value.map(r => r.avg_unit_price), itemStyle: { color: '#f5222d' }, yAxisIndex: 1 }
  ]
}))
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>概览大屏</h2>
      <span class="sub">北京二手房成交数据 2011–2017</span>
    </div>

    <div class="grid grid-4">
      <StatCard label="房源总数" :value="fmtNumber(overview?.count)" unit="条" hint="清洗后有效样本" />
      <StatCard label="平均单价" :value="fmtNumber(Math.round(overview?.avg_unit_price || 0))" unit="元/㎡" hint="全样本算术平均" accent="#13c2c2" />
      <StatCard label="平均总价" :value="(overview?.avg_total_price || 0).toFixed(1)" unit="万" hint="全样本算术平均" accent="#faad14" />
      <StatCard label="覆盖区域" :value="overview?.districts || 0" unit="个" hint="含亦庄经开区" accent="#8172b3" />
    </div>

    <div class="grid grid-2 mt-16">
      <ChartCard title="各区二手房均价" :loading="loading" :empty="!districts.length">
        <BaseChart :option="districtOption" height="360px" />
      </ChartCard>
      <ChartCard title="房价空间分布" :loading="loading" :empty="!heatmap.length">
        <BaseChart :option="heatmapOption" height="360px" />
      </ChartCard>
    </div>

    <ChartCard title="年度成交量与均价趋势" :loading="loading" :empty="!yearly.length" class="mt-16">
      <BaseChart :option="yearlyOption" height="300px" />
    </ChartCard>

    <div class="note-card card mt-16">
      <b>说明：</b>热力图使用经纬度散点，<b>不绘制行政边界</b>；单点颜色表示该房源成交单价。
    </div>
  </div>
</template>

<style scoped>
.note-card { font-size: 12px; color: var(--text-secondary); padding: 12px 18px; }
</style>
