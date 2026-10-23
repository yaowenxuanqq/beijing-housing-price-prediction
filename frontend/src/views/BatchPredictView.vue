<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import { fetchBatchTemplate, uploadBatchPredictions } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const fileInput = ref()
const selectedFile = ref(null)
const loading = ref(false)
const result = ref(null)

const resultRows = computed(() => (result.value?.results || []).slice(0, 50))

function onFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null
  result.value = null
}

function chooseFile() {
  fileInput.value?.click()
}

async function submit() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 CSV 文件')
    return
  }
  loading.value = true
  try {
    result.value = await uploadBatchPredictions(selectedFile.value)
    ElMessage.success(`批量估价完成：成功 ${result.value.success} 条`)
  } catch {
    result.value = null
  } finally {
    loading.value = false
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

async function downloadTemplate() {
  try {
    downloadBlob(await fetchBatchTemplate(), 'batch_prediction_template.csv')
  } catch {
    // 拦截器已提示
  }
}

function csvCell(value) {
  const text = String(value ?? '')
  return '"' + text.replaceAll('"', '""') + '"'
}

function downloadResults() {
  if (!result.value?.results?.length) {
    ElMessage.warning('没有可导出的成功结果')
    return
  }
  const headers = ['row', 'request_id', 'district_name', 'square', 'predicted_unit_price', 'predicted_total_price', 'interval_low', 'interval_high', 'model_version']
  const lines = [headers.join(',')]
  result.value.results.forEach(row => {
    const input = row.input_json || {}
    lines.push([
      row.row, row.request_id, input.district_name ?? '', input.square ?? '',
      row.predicted_unit_price, row.predicted_total_price, row.interval_low,
      row.interval_high, row.model_version
    ].map(csvCell).join(','))
  })
  downloadBlob(new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' }), 'batch_prediction_results.csv')
}
</script>

<template>
  <div class="page">
    <PageHeader
      title="批量估价"
      description="上传 CSV，一次完成最多 200 条房源的相对行情估值与区间计算。同步处理，无需启动额外服务。"
      eyebrow="Batch · 批量计算"
    >
      <template #actions>
        <el-button @click="downloadTemplate">下载模板</el-button>
      </template>
    </PageHeader>

    <section class="card upload-card">
      <div class="upload-icon">⇪</div>
      <div>
        <h3 class="card-title">选择 CSV 文件</h3>
        <p class="muted">支持 UTF-8 编码，必填列：district_name、square、market_median_unit_price。单文件不超过 5 MB、200 行。</p>
        <input ref="fileInput" class="hidden-input" type="file" accept=".csv,text/csv" @change="onFileChange" />
        <el-button type="primary" plain @click="chooseFile">选择文件</el-button>
        <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
      </div>
    </section>

    <div class="action-row">
      <el-button type="primary" :loading="loading" :disabled="!selectedFile" @click="submit">开始批量估价</el-button>
      <el-button :disabled="!result?.results?.length" @click="downloadResults">导出结果</el-button>
    </div>

    <template v-if="result">
      <div class="grid grid-3 mt-16">
        <div class="card metric"><span>总行数</span><b>{{ result.total }}</b></div>
        <div class="card metric"><span>成功</span><b class="success">{{ result.success }}</b></div>
        <div class="card metric"><span>失败</span><b :class="{ danger: result.failed }">{{ result.failed }}</b></div>
      </div>
      <div class="card mt-16" v-if="result.errors?.length">
        <h3 class="card-title">失败行</h3>
        <el-table :data="result.errors" size="small" stripe>
          <el-table-column prop="row" label="CSV 行号" width="100" />
          <el-table-column label="错误">
            <template #default="{ row }"><pre class="error-json">{{ JSON.stringify(row.errors) }}</pre></template>
          </el-table-column>
        </el-table>
      </div>
      <div class="card mt-16" v-if="resultRows.length">
        <div class="section-head">
          <h3 class="card-title">成功结果</h3>
          <span class="muted">展示前 {{ resultRows.length }} 条，导出包含全部成功结果</span>
        </div>
        <el-table :data="resultRows" size="small" stripe height="500">
          <el-table-column prop="row" label="行号" width="75" />
          <el-table-column label="区域" width="95">
            <template #default="{ row }">{{ row.input_json?.district_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="面积" width="95" align="right">
            <template #default="{ row }">{{ row.input_json?.square || '-' }}㎡</template>
          </el-table-column>
          <el-table-column label="单价" width="145" align="right">
            <template #default="{ row }">{{ fmtNumber(Math.round(row.predicted_unit_price)) }} 元/㎡</template>
          </el-table-column>
          <el-table-column label="总价" width="125" align="right">
            <template #default="{ row }">{{ fmtNumber(row.predicted_total_price) }} 万</template>
          </el-table-column>
          <el-table-column label="80% 校准区间" min-width="200">
            <template #default="{ row }">{{ fmtNumber(row.interval_low) }} – {{ fmtNumber(row.interval_high) }} 元/㎡</template>
          </el-table-column>
          <el-table-column prop="model_version" label="模型" width="150" />
        </el-table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.upload-card { display: flex; align-items: flex-start; gap: 16px; padding: 22px; }
.upload-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: #eaf2ff; color: var(--color-primary); font-size: 24px; }
.hidden-input { display: none; }
.file-name { margin-left: 12px; color: var(--text-secondary); font-size: 13px; }
.action-row { display: flex; gap: 10px; margin-top: 14px; }
.metric { padding: 18px 22px; display: flex; flex-direction: column; gap: 8px; }
.metric span { color: var(--text-muted); font-size: 12px; }
.metric b { font-size: 28px; color: var(--color-primary); }
.metric b.success { color: #4b9b58; }
.metric b.danger { color: #c84f5d; }
.section-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.error-json { margin: 0; white-space: pre-wrap; color: #c84f5d; font-size: 12px; }
@media (max-width: 760px) {
  .upload-card { flex-direction: column; }
  .grid-3 { grid-template-columns: 1fr; }
  .action-row { flex-wrap: wrap; }
}
</style>
