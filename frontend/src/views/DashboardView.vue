<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StatCard from '../components/StatCard.vue'
import ChartCard from '../components/ChartCard.vue'
import PageHeader from '../components/PageHeader.vue'
import BaseChart from '../components/BaseChart.vue'
import DotGrid from '../components/fx/DotGrid.vue'
import RevealOnScroll from '../components/fx/RevealOnScroll.vue'
import { fetchDistrictStats, fetchHeatmap, fetchOverview, fetchYearlyStats } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const router = useRouter()
const loading = ref(true)
const overviewError = ref(false)
const districtError = ref(false)
const heatmapError = ref(false)
const yearlyError = ref(false)
const overview = ref(null)
const districts = ref([])
const heatmap = ref([])
const yearly = ref([])

const failedLabels = computed(() => [
  overviewError.value && '概览指标',
  districtError.value && '区域均价',
  heatmapError.value && '空间分布',
  yearlyError.value && '年度趋势'
].filter(Boolean))

async function load() {
  loading.value = true
  overviewError.value = false
  districtError.value = false
  heatmapError.value = false
  yearlyError.value = false

  const [overviewResult, districtResult, heatmapResult, yearlyResult] = await Promise.allSettled([
    fetchOverview(), fetchDistrictStats(), fetchHeatmap(5000), fetchYearlyStats()
  ])

  if (overviewResult.status === 'fulfilled') overview.value = overviewResult.value
  else overviewError.value = true

  if (districtResult.status === 'fulfilled') districts.value = districtResult.value
  else districtError.value = true

  if (heatmapResult.status === 'fulfilled') heatmap.value = heatmapResult.value
  else heatmapError.value = true

  if (yearlyResult.status === 'fulfilled') yearly.value = yearlyResult.value
  else yearlyError.value = true

  loading.value = false
}

onMounted(load)

const toolbox = {
  right: 4, top: 0,
  feature: { saveAsImage: { title: '保存图片', pixelRatio: 2, backgroundColor: '#fff' } }
}

const districtOption = computed(() => {
  const rows = [...districts.value].reverse()
  return {
    toolbox,
    grid: { left: 76, right: 70, top: 30, bottom: 24 },
    xAxis: { type: 'value', axisLabel: { formatter: v => (v / 10000).toFixed(0) + '万' } },
    yAxis: { type: 'category', data: rows.map(r => r.district), axisLabel: { fontSize: 11 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => {
      const r = rows[p[0].dataIndex]
      return r.district + '<br/>均价：' + fmtNumber(Math.round(r.avg_unit_price)) + ' 元/㎡<br/>样本：' + fmtNumber(r.count)
    }},
    series: [{
      type: 'bar', name: '均价',
      data: rows.map(r => r.avg_unit_price),
      barWidth: 14,
      itemStyle: { color: '#2f6fed', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: p => fmtNumber(Math.round(p.value)), fontSize: 10, color: '#606266' },
      markLine: {
        symbol: 'none', silent: true,
        lineStyle: { color: '#909399', type: 'dashed' },
        label: { formatter: '全市均值', fontSize: 10, color: '#909399' },
        data: [{ type: 'average' }]
      }
    }]
  }
})

const heatmapOption = computed(() => {
  const prices = heatmap.value.map(r => r.unit_price).sort((a, b) => a - b)
  const lo = prices.length ? prices[Math.floor(prices.length * 0.02)] : 15000
  const hi = prices.length ? prices[Math.floor(prices.length * 0.98)] : 105000
  return {
    toolbox,
    grid: { left: 56, right: 24, top: 30, bottom: 48 },
    tooltip: { formatter: p => p.data[2] + '<br/>' + fmtNumber(Math.round(p.data[3])) + ' 元/㎡' },
    xAxis: { type: 'value', name: '经度', scale: true, nameTextStyle: { fontSize: 11 } },
    yAxis: { type: 'value', name: '纬度', scale: true, nameTextStyle: { fontSize: 11 } },
    visualMap: {
      dimension: 3, min: lo, max: hi,
      orient: 'horizontal', left: 'center', bottom: 4,
      text: ['高', '低'], textStyle: { fontSize: 10 }, itemWidth: 10, itemHeight: 80,
      inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#f46d43', '#d73027'] }
    },
    series: [{
      type: 'scatter', symbolSize: 4,
      data: heatmap.value.map(r => [r.lng, r.lat, r.district, r.unit_price]),
      itemStyle: { opacity: 0.6 }
    }]
  }
})

const yearlyOption = computed(() => ({
  toolbox,
  grid: { left: 56, right: 56, top: 52, bottom: 28 },
  tooltip: { trigger: 'axis' },
  legend: { top: 4, left: 68, itemWidth: 12, itemHeight: 8 },
  xAxis: { type: 'category', data: yearly.value.map(r => r.year) },
  yAxis: [
    { type: 'value', name: '成交量', nameTextStyle: { fontSize: 11 } },
    { type: 'value', name: '均价（元/㎡）', nameTextStyle: { fontSize: 11 }, axisLabel: { formatter: v => (v / 10000).toFixed(0) + '万' } }
  ],
  series: [
    { name: '成交量', type: 'bar', data: yearly.value.map(r => r.count), barWidth: 22, itemStyle: { color: '#d9e3f8', borderRadius: [4, 4, 0, 0] }, yAxisIndex: 0 },
    {
      name: '均价', type: 'line', smooth: true, symbolSize: 6,
      data: yearly.value.map(r => r.avg_unit_price),
      itemStyle: { color: '#f5222d' }, yAxisIndex: 1,
      markLine: {
        symbol: 'none', silent: true,
        lineStyle: { color: '#faad14', type: 'dashed' },
        label: { formatter: '2017 政策节点', position: 'insideEndTop', distance: 4, fontSize: 10, color: '#faad14' },
        data: [{ xAxis: '2017' }]
      }
    }
  ]
}))

function onDistrictClick(params) {
  if (params?.name) router.push({ path: '/houses', query: { district: params.name } })
}
</script>

<template>
  <div class="page">
    <div class="hero">
      <DotGrid :opacity="0.16" />
      <div class="hero-content">
        <PageHeader
          title="北京二手房市场概览"
          description="聚合 2011–2017 年链家成交记录，快速查看区域价格、空间分布与年度趋势。点击区域柱状图可下钻房源明细。"
          eyebrow="Overview · 数据总览"
          flush
        >
          <template #actions>
            <el-tag type="success" effect="plain" round>数据已汇总</el-tag>
          </template>
        </PageHeader>
      </div>
    </div>

    <div v-if="failedLabels.length" class="card error-banner">
      部分数据加载失败：{{ failedLabels.join('、') }}。其他区块仍可查看。
      <el-button size="small" type="primary" link @click="load">重试</el-button>
    </div>

    <div class="grid grid-4">
      <RevealOnScroll :delay="0">
        <StatCard label="房源总数" :value="overview?.count || 0" unit="条" :hint="overviewError ? '概览接口加载失败' : '清洗后有效样本'" />
      </RevealOnScroll>
      <RevealOnScroll :delay="60">
        <StatCard label="平均单价" :value="Math.round(overview?.avg_unit_price || 0)" unit="元/㎡" :hint="overviewError ? '概览接口加载失败' : '全样本算术平均'" accent="#13c2c2" />
      </RevealOnScroll>
      <RevealOnScroll :delay="120">
        <StatCard label="平均总价" :value="Number(overview?.avg_total_price || 0)" :decimals="1" unit="万" :hint="overviewError ? '概览接口加载失败' : '全样本算术平均'" accent="#faad14" />
      </RevealOnScroll>
      <RevealOnScroll :delay="180">
        <StatCard label="覆盖区域" :value="overview?.districts || 0" unit="个" :hint="overviewError ? '概览接口加载失败' : '含亦庄经开区'" accent="#8172b3" />
      </RevealOnScroll>
    </div>

    <div class="grid grid-2 mt-16">
      <RevealOnScroll :delay="80">
        <ChartCard title="各区二手房均价" :loading="loading" :error="districtError" :empty="!districts.length"
                   @retry="load">
          <BaseChart :option="districtOption" height="360px" @chart-click="onDistrictClick" />
        </ChartCard>
      </RevealOnScroll>
      <RevealOnScroll :delay="140">
        <ChartCard title="房价空间分布" :loading="loading" :error="heatmapError" :empty="!heatmap.length"
                   @retry="load">
          <BaseChart :option="heatmapOption" height="360px" />
        </ChartCard>
      </RevealOnScroll>
    </div>

    <RevealOnScroll :delay="100" class="mt-16 block-reveal">
      <ChartCard title="年度成交量与均价趋势" :loading="loading" :error="yearlyError" :empty="!yearly.length"
                 @retry="load">
        <BaseChart :option="yearlyOption" height="300px" />
      </ChartCard>
    </RevealOnScroll>

    <div class="note-card card mt-16">
      <b>说明：</b>热力图使用经纬度散点，<b>不绘制行政边界</b>；单点颜色表示该房源成交单价；色带范围取 p2–p98。
    </div>
  </div>
</template>

<style scoped>
.hero {
  position: relative; overflow: hidden; padding: 22px 24px;
  background: linear-gradient(120deg, #f2f6ff 0%, #ffffff 55%);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}
.hero-content { position: relative; z-index: 1; }
.note-card { font-size: 12px; color: var(--text-secondary); padding: 12px 18px; }
.error-banner { margin-bottom: var(--space-4); color: var(--color-danger); display: flex; align-items: center; gap: 8px; }
.block-reveal { display: block; }
</style>
