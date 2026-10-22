<script setup>
import { computed, onMounted, ref } from 'vue'
import ChartCard from '../components/ChartCard.vue'
import BaseChart from '../components/BaseChart.vue'
import { fetchModelMetrics } from '../api/endpoints'
import { fmtNumber, fmtR2, fmtPct } from '../utils/format'

const loading = ref(true)
const metrics = ref(null)
const experiment = ref('ES3_time_ratio')

const experiments = [
  { value: 'ES1_random_logtotal', label: 'ES-1 随机 + 总价' },
  { value: 'ES2_time_logtotal', label: 'ES-2 时序 + 总价' },
  { value: 'ES3_time_ratio', label: 'ES-3 时序 + ratio（部署）' },
  { value: 'ES4_random_ratio', label: 'ES-4 随机 + ratio（对照）' }
]

const modelNames = { baseline: '朴素基线', linear: '线性回归', tree: '决策树', rf: '随机森林', xgboost: 'XGBoost', mlp: 'MLP' }

onMounted(async () => {
  try { metrics.value = await fetchModelMetrics() } finally { loading.value = false }
})

const baseExp = computed(() => metrics.value?.baseline?.experiments?.find(e => e.experiment === experiment.value))

const maeDisplay = (row) => row.mae_unit_price ?? row.mae
const noTunedData = computed(() => tunedRows.value.length === 0)
const bestBaseR2 = computed(() => Math.max(...baseRows.value.filter(r => r.model !== '朴素基线').map(r => r.r2_unit)))
const bestTunedR2 = computed(() => Math.max(...tunedRows.value.map(r => r.r2_unit)))
const baselineByModel = computed(() => Object.fromEntries(baseRows.value.map(r => [r.model, r.r2_unit])))

function deltaFor(row) {
  const b = baselineByModel.value[row.model]
  return b == null ? null : row.r2_unit - b
}
function deltaText(row) {
  const d = deltaFor(row)
  if (d == null) return '—'
  return (d >= 0 ? '↑ +' : '↓ ') + (d * 100).toFixed(2) + ' pp'
}
function deltaClass(row) {
  const d = deltaFor(row)
  return d == null ? '' : (d >= 0 ? 'up' : 'down')
}

const baseRows = computed(() => {
  const e = baseExp.value
  if (!e) return []
  return Object.entries(e.models).map(([k, v]) => ({ model: modelNames[k] || k, ...v, isBaseline: k === 'baseline' }))
})

const tunedRows = computed(() => {
  const list = metrics.value?.tuned?.experiments || []
  return list.filter(e => e.metrics[experiment.value]).map(e => ({
    model: modelNames[e.model] || e.model,
    ...e.metrics[experiment.value]
  }))
})

const compareOption = computed(() => {
  const base = baseRows.value.filter(r => !r.isBaseline)
  const tuned = tunedRows.value
  return {
    toolbox: { right: 4, top: 0, feature: { saveAsImage: { title: '保存图片', pixelRatio: 2, backgroundColor: '#fff' } } },
    grid: { left: 50, right: 20, top: 48, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    xAxis: { type: 'category', data: base.map(r => r.model) },
    yAxis: { type: 'value', min: -0.6, max: 1, name: 'R²（单价）' },
    series: [
      { name: '基线参数', type: 'bar', data: base.map(r => r.r2_unit), itemStyle: { color: '#a0b4e8', borderRadius: [4, 4, 0, 0] } },
      { name: '调参后', type: 'bar', data: base.map(r => {
          const t = tuned.find(x => x.model === r.model)
          return t ? t.r2_unit : null
        }), itemStyle: { color: '#2f6fed', borderRadius: [4, 4, 0, 0] } }
    ]
  }
})

const stability = computed(() => metrics.value?.stability)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>模型对比</h2>
      <span class="sub">基线 / 调参 / 稳定性 · 统一单价口径 R²</span>
    </div>

    <div class="toolbar card">
      <el-radio-group v-model="experiment">
        <el-radio-button v-for="e in experiments" :key="e.value" :value="e.value">{{ e.label }}</el-radio-button>
      </el-radio-group>
    </div>

    <div class="grid grid-2 mt-16" v-loading="loading">
      <section class="card">
        <h3 class="card-title">基线参数结果</h3>
        <el-table :data="baseRows" stripe size="small" height="330">
          <el-table-column label="模型" width="120">
            <template #default="{ row }">
              {{ row.model }}
              <el-tag v-if="row.model !== '朴素基线' && row.r2_unit === bestBaseR2" size="small" type="warning" effect="plain" style="margin-left: 4px">最优</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="R²（单价）" width="110" align="right">
            <template #default="{ row }">{{ fmtR2(row.r2_unit) }}</template>
          </el-table-column>
          <el-table-column label="MAE（元/㎡）" width="120" align="right">
            <template #default="{ row }">{{ fmtNumber(Math.round(maeDisplay(row))) }}</template>
          </el-table-column>
          <el-table-column label="MAPE" align="right">
            <template #default="{ row }">{{ fmtPct(row.mape_pct) }}</template>
          </el-table-column>
        </el-table>
      </section>

      <section class="card">
        <h3 class="card-title">调参后结果</h3>
        <el-empty v-if="noTunedData" description="该实验未纳入调参范围（ES-4 仅作对照）" :image-size="70" />
        <el-table v-else :data="tunedRows" stripe size="small" height="330">
          <el-table-column label="模型" width="120">
            <template #default="{ row }">
              {{ row.model }}
              <el-tag v-if="row.r2_unit === bestTunedR2" size="small" type="warning" effect="plain" style="margin-left: 4px">最优</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="R²（单价）" width="100" align="right">
            <template #default="{ row }">{{ fmtR2(row.r2_unit) }}</template>
          </el-table-column>
          <el-table-column label="相对基线" width="110" align="right">
            <template #default="{ row }"><span :class="deltaClass(row)">{{ deltaText(row) }}</span></template>
          </el-table-column>
          <el-table-column label="MAE（元/㎡）" width="110" align="right">
            <template #default="{ row }">{{ fmtNumber(Math.round(maeDisplay(row))) }}</template>
          </el-table-column>
          <el-table-column label="MAPE" align="right">
            <template #default="{ row }">{{ fmtPct(row.mape_pct) }}</template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <ChartCard title="基线 vs 调参（R² 单价）" :loading="loading" :empty="!baseRows.length" class="mt-16">
      <BaseChart :option="compareOption" height="340px" />
    </ChartCard>

    <div class="card mt-16 stability" v-if="stability">
      <div>
        <div class="muted">部署模型 · 3 种子稳定性</div>
        <div class="big num">{{ fmtR2(stability.r2_mean) }} <span class="pm">± {{ stability.r2_std.toFixed(4) }}</span></div>
        <div class="muted">单价 MAE {{ fmtNumber(Math.round(stability.mae_mean)) }} ± {{ Math.round(stability.mae_std) }} 元/㎡</div>
      </div>
      <div class="model-tag">
        <el-tag type="success" effect="plain">{{ stability.model }}</el-tag>
        <el-tag type="info" effect="plain" style="margin-left: 8px">ratio 口径</el-tag>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar { padding: 12px 16px; }
.stability { display: flex; align-items: center; justify-content: space-between; }
.big { font-size: 30px; font-weight: 700; color: var(--primary); margin: 4px 0; }
.pm { font-size: 15px; color: var(--text-secondary); font-weight: 500; }
.up { color: #67c23a; font-weight: 600; }
.down { color: #f56c6c; font-weight: 600; }
</style>
