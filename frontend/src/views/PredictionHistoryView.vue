<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import { fetchPredictionExport, fetchPredictionHistory } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const drawer = ref(false)
const detail = ref(null)
const exporting = ref(false)
const filters = reactive({ model_version: '', source: '', date_from: '', date_to: '' })

function queryParams() {
  const params = { page: page.value, page_size: pageSize.value }
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params[key] = value
  })
  return params
}

async function load() {
  loading.value = true
  try {
    const data = await fetchPredictionHistory(queryParams())
    rows.value = data.results || []
    total.value = data.count || 0
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function reset() {
  filters.model_version = ''
  filters.source = ''
  filters.date_from = ''
  filters.date_to = ''
  page.value = 1
  load()
}

function openDetail(row) {
  detail.value = row
  drawer.value = true
}

async function exportCsv() {
  exporting.value = true
  try {
    const params = {}
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params[key] = value
    })
    const blob = await fetchPredictionExport(params)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'prediction_history.csv'
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('预测记录已导出')
  } finally {
    exporting.value = false
  }
}

function shortId(value) {
  return value ? String(value).slice(0, 8) : '-'
}

function formatTime(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '-'
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader
      title="预测记录"
      description="查看每次估价的可追溯记录，核对模型版本、价格区间与推理耗时。"
      eyebrow="History · 估价审计"
    >
      <template #actions>
        <el-tag type="info" effect="plain" round>共 {{ fmtNumber(total) }} 条</el-tag>
        <el-button type="primary" :loading="exporting" @click="exportCsv">导出 CSV</el-button>
      </template>
    </PageHeader>

    <section class="card filter-bar">
      <el-input v-model="filters.model_version" clearable placeholder="模型版本" style="width: 190px" />
      <el-select v-model="filters.source" clearable placeholder="记录来源" style="width: 130px">
        <el-option label="单条估价" value="single" />
        <el-option label="可解释估价" value="explain" />
        <el-option label="情景对比" value="scenario" />
        <el-option label="批量估价" value="batch" />
      </el-select>
      <el-date-picker v-model="filters.date_from" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width: 150px" />
      <el-date-picker v-model="filters.date_to" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width: 150px" />
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="reset">重置</el-button>
    </section>

    <section class="card mt-16">
      <el-table :data="rows" v-loading="loading" stripe height="580" @row-click="openDetail" style="cursor: pointer">
        <el-table-column label="请求编号" width="120">
          <template #default="{ row }"><span class="mono">{{ shortId(row.request_id) }}</span></template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="来源" width="105">
          <template #default="{ row }"><el-tag size="small" effect="plain">{{ { single: '单条', explain: '解释', scenario: '情景', batch: '批量' }[row.source] || row.source }}</el-tag></template>
        </el-table-column>
        <el-table-column label="区域" width="95">
          <template #default="{ row }">{{ row.input_json?.district_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="面积" width="90" align="right">
          <template #default="{ row }">{{ row.input_json?.square || '-' }}㎡</template>
        </el-table-column>
        <el-table-column label="预测单价" width="125" align="right">
          <template #default="{ row }">{{ fmtNumber(Math.round(row.predicted_unit_price || 0)) }} 元/㎡</template>
        </el-table-column>
        <el-table-column label="预测总价" width="110" align="right">
          <template #default="{ row }">{{ fmtNumber(row.predicted_total_price) }} 万</template>
        </el-table-column>
        <el-table-column label="校准区间" min-width="210">
          <template #default="{ row }">{{ fmtNumber(row.interval_low) }} – {{ fmtNumber(row.interval_high) }} 元/㎡</template>
        </el-table-column>
        <el-table-column label="模型" width="150" prop="model_version" />
        <el-table-column label="耗时" width="90" align="right">
          <template #default="{ row }">{{ row.duration_ms == null ? '-' : Number(row.duration_ms).toFixed(0) + ' ms' }}</template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="load"
          @size-change="() => { page = 1; load() }"
        />
      </div>
    </section>

    <el-drawer v-model="drawer" title="预测记录详情" size="480px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="请求编号"><span class="mono">{{ detail.request_id }}</span></el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="记录来源">{{ { single: '单条估价', explain: '可解释估价', scenario: '情景对比', batch: '批量估价' }[detail.source] || detail.source }}</el-descriptions-item>
          <el-descriptions-item label="批次编号"><span class="mono">{{ detail.batch_id || '-' }}</span></el-descriptions-item>
          <el-descriptions-item label="模型版本">{{ detail.model_version }}</el-descriptions-item>
          <el-descriptions-item label="预测单价">{{ fmtNumber(detail.predicted_unit_price) }} 元/㎡</el-descriptions-item>
          <el-descriptions-item label="预测总价">{{ fmtNumber(detail.predicted_total_price) }} 万元</el-descriptions-item>
          <el-descriptions-item label="校准区间">{{ fmtNumber(detail.interval_low) }} – {{ fmtNumber(detail.interval_high) }} 元/㎡</el-descriptions-item>
          <el-descriptions-item label="区间方法">{{ detail.interval_method || '-' }}</el-descriptions-item>
          <el-descriptions-item label="推理耗时">{{ detail.duration_ms == null ? '-' : Number(detail.duration_ms).toFixed(0) + ' ms' }}</el-descriptions-item>
        </el-descriptions>
        <h4 class="json-title">输入特征</h4>
        <pre class="json-block">{{ JSON.stringify(detail.input_json, null, 2) }}</pre>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 14px 18px; }
.pager { display: flex; justify-content: flex-end; padding-top: 14px; }
.mono { font-family: var(--font-mono, Consolas, monospace); font-size: 12px; }
.json-title { margin: 20px 0 8px; font-size: 13px; }
.json-block { padding: 12px; border-radius: 8px; background: #f5f7fa; color: #303133; font-size: 12px; line-height: 1.6; overflow: auto; }
</style>
