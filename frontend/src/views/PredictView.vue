<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import { useAppStore } from '../stores/app'
import { explainPrediction, fetchSimilarHouses } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const store = useAppStore()
const formRef = ref()
const loading = ref(false)
const metaLoading = ref(true)
const similarLoading = ref(false)
const similarError = ref(false)
const result = ref(null)
const explanation = ref(null)
const similar = ref([])
const similarCriteria = ref(null)

const form = reactive({
  district_name: '',
  square: 89.5,
  rooms: 2,
  halls: 1,
  bathrooms: 1,
  floor_position: '中',
  total_floors: 18,
  house_age: 12,
  renovation: 3,
  elevator: true,
  subway: true,
  five_years: true,
  market_median_unit_price: null
})

const rules = {
  district_name: [{ required: true, message: '请选择区域', trigger: 'change' }],
  square: [{ required: true, message: '请输入面积', trigger: 'blur' }],
  market_median_unit_price: [{ required: true, message: '请输入当期行情中位单价', trigger: 'blur' }]
}

const presets = [
  { key: 'starter', label: '刚需两居', values: { square: 70, rooms: 2, halls: 1, bathrooms: 1, floor_position: '中', total_floors: 18, house_age: 15, renovation: 2, elevator: true, subway: false, five_years: true } },
  { key: 'improve', label: '改善三居', values: { square: 110, rooms: 3, halls: 2, bathrooms: 2, floor_position: '中', total_floors: 12, house_age: 8, renovation: 3, elevator: true, subway: true, five_years: true } },
  { key: 'school', label: '学区房', values: { square: 60, rooms: 2, halls: 1, bathrooms: 1, floor_position: '低', total_floors: 6, house_age: 25, renovation: 3, elevator: false, subway: true, five_years: true } }
]

const renovationOptions = [
  { value: 1, label: '1 级（简装）' },
  { value: 2, label: '2 级' },
  { value: 3, label: '3 级（精装）' },
  { value: 4, label: '4 级（豪装）' }
]

onMounted(async () => {
  try {
    await store.loadMeta()
  } catch {
    // 错误已由 axios 拦截器提示
  } finally {
    metaLoading.value = false
  }
})

watch(() => form.district_name, (d) => {
  const m = store.meta?.market_median_unit_price?.[d]
  if (m) form.market_median_unit_price = m
})

async function submit() {
  if (!formRef.value) return
  await formRef.value.validate(async valid => {
    if (!valid) return
    loading.value = true
    similarLoading.value = true
    similarError.value = false
    explanation.value = null
    similar.value = []
    try {
      const payload = { ...form }
      const similarPayload = {
        district_name: form.district_name,
        square: form.square,
        rooms: form.rooms,
        floor_position: form.floor_position,
        subway: form.subway,
        elevator: form.elevator,
        limit: 6
      }
      const [predictionResult, similarResult] = await Promise.allSettled([
        explainPrediction(payload),
        fetchSimilarHouses(similarPayload)
      ])
      if (predictionResult.status === 'rejected') return

      result.value = predictionResult.value
      explanation.value = predictionResult.value.explanation || null
      if (similarResult.status === 'fulfilled') {
        similar.value = similarResult.value.results || []
        similarCriteria.value = similarResult.value.criteria || null
      } else {
        similarError.value = true
      }
      ElMessage.success('估价与解释生成完成')
    } finally {
      loading.value = false
      similarLoading.value = false
    }
  })
}

function reset() {
  formRef.value?.resetFields()
  result.value = null
  explanation.value = null
  similar.value = []
  similarCriteria.value = null
  similarError.value = false
}

function applyPreset(preset) {
  Object.assign(form, preset.values)
  result.value = null
  explanation.value = null
  similar.value = []
  similarCriteria.value = null
  similarError.value = false
}

const gaugeLeft = computed(() => {
  const r = Number(result.value?.ratio || 1)
  return Math.max(0, Math.min(100, ((r - 0.7) / 0.6) * 100))
})

const maxFactor = computed(() => {
  const values = (explanation.value?.features || []).map(x => Math.abs(Number(x.contribution_unit_price || 0)))
  return Math.max(1, ...values)
})

function factorWidth(value) {
  return Math.max(6, Math.abs(Number(value || 0)) / maxFactor.value * 100) + '%'
}

function factorTone(value) {
  return Number(value || 0) >= 0 ? 'positive' : 'negative'
}

function signedPrice(value) {
  const number = Number(value || 0)
  return (number >= 0 ? '+' : '') + fmtNumber(Math.round(number)) + ' 元/㎡'
}

function formatReason(row) {
  return (row.match_reasons || []).join(' · ')
}
</script>

<template>
  <div class="page">
    <PageHeader
      title="房价预测"
      description="输入房屋特征与当期区域行情，输出相对行情估值、价格区间、模型解释与相似历史成交。"
      eyebrow="Prediction · 可解释估价"
    >
      <template #actions>
        <el-tag type="success" effect="plain" round>{{ store.modelVersion }}</el-tag>
      </template>
    </PageHeader>

    <div class="predict-grid">
      <section class="card">
        <h3 class="card-title">房屋信息</h3>
        <div class="preset-row">
          <span class="muted">快速填充：</span>
          <el-button v-for="p in presets" :key="p.key" size="small" @click="applyPreset(p)">{{ p.label }}</el-button>
        </div>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="left">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="区域" prop="district_name">
                <el-select v-model="form.district_name" placeholder="请选择区域" filterable style="width: 100%">
                  <el-option v-for="d in store.meta?.districts || []" :key="d" :label="d" :value="d" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="建筑面积">
                <el-input-number v-model="form.square" :min="10" :max="500" :step="1" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="卧室">
                <el-input-number v-model="form.rooms" :min="0" :max="20" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="客厅">
                <el-input-number v-model="form.halls" :min="0" :max="20" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="卫生间">
                <el-input-number v-model="form.bathrooms" :min="0" :max="10" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="楼层位置">
                <el-select v-model="form.floor_position" style="width: 100%">
                  <el-option v-for="p in store.meta?.floor_positions || []" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="总层数">
                <el-input-number v-model="form.total_floors" :min="1" :max="100" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="房龄（年）">
                <el-input-number v-model="form.house_age" :min="0" :max="70" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="装修">
                <el-select v-model="form.renovation" style="width: 100%">
                  <el-option v-for="o in renovationOptions" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="配套">
            <el-checkbox v-model="form.elevator">有电梯</el-checkbox>
            <el-checkbox v-model="form.subway">近地铁</el-checkbox>
            <el-checkbox v-model="form.five_years">满五年</el-checkbox>
          </el-form-item>

          <el-form-item label="当期行情" prop="market_median_unit_price">
            <el-input-number
              v-model="form.market_median_unit_price"
              :min="1000"
              :max="300000"
              :step="1000"
              :disabled="metaLoading"
              style="width: 100%"
            />
            <div class="muted" style="margin-top: 4px">
              该区当期成交中位单价（元/㎡），选择区域后自动带出 2017 年行情
            </div>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="loading" @click="submit">开始估价</el-button>
            <el-button @click="reset">重置</el-button>
          </el-form-item>
        </el-form>
      </section>

      <section class="result-wrap">
        <div v-if="!result" class="card result-empty">
          <div class="empty-icon">✦</div>
          <div>填写左侧信息后点击「开始估价」</div>
          <div class="muted">系统将输出估价、模型解释与相似成交案例</div>
        </div>
        <div v-else class="card result-card">
          <div class="result-label">预测单价</div>
          <div class="result-price num">
            {{ fmtNumber(Math.round(result.predicted_unit_price)) }}<span class="unit">元/㎡</span>
          </div>
          <div class="result-total">
            折算总价 <b class="num">{{ fmtNumber(result.predicted_total_price) }} 万元</b>
          </div>
          <div class="interval">
            {{ Math.round((result.interval_level || 0.8) * 100) }}% 时序交叉验证校准区间：
            {{ fmtNumber(result.interval_low) }} – {{ fmtNumber(result.interval_high) }} 元/㎡
          </div>
          <div class="interval">
            总价区间：{{ fmtNumber(result.interval_total_low) }} – {{ fmtNumber(result.interval_total_high) }} 万元
          </div>
          <div v-if="result.interval_note" class="interval-note">{{ result.interval_note }}</div>

          <div class="gauge">
            <div class="gauge-track">
              <div class="gauge-zone"></div>
              <div class="gauge-marker" :style="{ left: gaugeLeft + '%' }"></div>
            </div>
            <div class="gauge-labels">
              <span>0.9 偏低</span><span>1.0 行情</span><span>1.1 偏高</span>
            </div>
          </div>
          <el-divider />
          <div class="kv"><span>相对行情 ratio</span><b class="num">{{ result.ratio }}</b></div>
          <div class="kv"><span>当期区中位单价</span><b class="num">{{ fmtNumber(result.market_median_unit_price) }} 元/㎡</b></div>
          <div class="kv"><span>模型版本</span><el-tag size="small" type="success" effect="plain">{{ result.model_version }}</el-tag></div>
          <div class="result-note">{{ result.note }}</div>
        </div>
      </section>
    </div>

    <section v-if="explanation" class="card explanation-card mt-16">
      <div class="section-head">
        <div>
          <h3 class="card-title">为什么是这个价格？</h3>
          <div class="muted">TreeSHAP 局部贡献 · 以当期区中位单价为换算基准</div>
        </div>
        <el-tag type="info" effect="plain">{{ explanation.method }}</el-tag>
      </div>
      <div class="explain-base">
        模型基准估值 <b class="num">{{ fmtNumber(explanation.base_unit_price) }} 元/㎡</b>
        <span class="muted">，当前估价相对基准 {{ explanation.predicted_ratio >= explanation.base_ratio ? '上浮' : '下调' }}</span>
      </div>
      <div class="factor-list">
        <div v-for="item in explanation.features" :key="item.feature" class="factor-row">
          <div class="factor-name">
            <b>{{ item.label }}</b>
            <small>{{ item.value }}</small>
          </div>
          <div class="factor-track">
            <div class="factor-bar" :class="factorTone(item.contribution_unit_price)" :style="{ width: factorWidth(item.contribution_unit_price) }"></div>
          </div>
          <div class="factor-value" :class="factorTone(item.contribution_unit_price)">
            {{ signedPrice(item.contribution_unit_price) }}
          </div>
        </div>
      </div>
      <div class="explain-note">{{ explanation.method_note }}</div>
    </section>

    <section class="card mt-16" v-if="result">
      <div class="section-head">
        <div>
          <h3 class="card-title">相似历史成交</h3>
          <div class="muted" v-if="similarCriteria">
            同区域 · 面积上下 30% · 近两年优先 · 候选 {{ similarCriteria.candidate_count }} 条
          </div>
        </div>
        <el-tag type="success" effect="plain" round>{{ similar.length }} 条参考</el-tag>
      </div>
      <el-skeleton v-if="similarLoading" :rows="4" animated />
      <div v-else-if="similarError" class="section-error">相似成交加载失败，不影响本次估价。</div>
      <el-table v-else :data="similar" size="small" stripe>
        <el-table-column prop="district_name" label="区域" width="90" />
        <el-table-column prop="trade_date" label="成交日期" width="110" />
        <el-table-column label="面积" width="100" align="right">
          <template #default="{ row }">{{ Number(row.square).toFixed(1) }}㎡</template>
        </el-table-column>
        <el-table-column label="总价" width="110" align="right">
          <template #default="{ row }">{{ fmtNumber(row.total_price) }} 万</template>
        </el-table-column>
        <el-table-column label="单价" width="130" align="right">
          <template #default="{ row }">{{ fmtNumber(Math.round(row.unit_price)) }} 元/㎡</template>
        </el-table-column>
        <el-table-column label="相似度" width="90" align="center">
          <template #default="{ row }"><el-tag type="success" effect="plain">{{ row.similarity_score }}</el-tag></template>
        </el-table-column>
        <el-table-column label="匹配原因" min-width="220">
          <template #default="{ row }">{{ formatReason(row) }}</template>
        </el-table-column>
        <el-table-column label="来源" width="80" align="center">
          <template #default="{ row }">
            <a v-if="row.url" :href="row.url" target="_blank" rel="noreferrer">查看</a>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.predict-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, 1fr); gap: 16px; align-items: start; }
.result-wrap { position: sticky; top: 0; }
.result-empty {
  min-height: 320px; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; color: var(--text-secondary); font-size: 14px;
}
.empty-icon { font-size: 36px; color: var(--color-primary); }
.result-card { background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%); }
.result-label { font-size: 13px; color: var(--text-secondary); }
.result-price { font-size: 40px; font-weight: 700; color: var(--color-primary); line-height: 1.2; margin-top: 6px; }
.result-price .unit { font-size: 14px; font-weight: 500; color: var(--text-secondary); margin-left: 6px; }
.result-total { margin-top: 4px; font-size: 15px; }
.result-total b { color: var(--text-primary); }
.kv { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 6px 0; color: var(--text-secondary); }
.kv b { color: var(--text-primary); }
.result-note { margin-top: 12px; font-size: 12px; color: #909399; line-height: 1.6; }
.interval { margin-top: 6px; font-size: 12px; color: var(--text-secondary); }
.interval-note { margin-top: 5px; font-size: 11px; color: var(--text-muted); line-height: 1.5; }
.preset-row { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.gauge { margin-top: 14px; }
.gauge-track { position: relative; height: 6px; border-radius: 3px; background: #e8eefc; }
.gauge-zone { position: absolute; left: 33.3%; width: 33.3%; height: 100%; background: #c9dcff; border-radius: 3px; }
.gauge-marker { position: absolute; top: -3px; width: 12px; height: 12px; border-radius: 50%; background: var(--color-primary); border: 2px solid #fff; box-shadow: 0 1px 4px rgba(0,0,0,.2); transform: translateX(-6px); transition: left .4s ease; }
.gauge-labels { display: flex; justify-content: space-between; margin-top: 6px; font-size: 10px; color: var(--text-muted); }
.explanation-card { background: linear-gradient(155deg, #fff 0%, #f8fbff 100%); }
.section-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.explain-base { margin: 16px 0 12px; padding: 10px 12px; border-radius: 8px; background: #eef5ff; color: var(--text-secondary); font-size: 13px; }
.factor-list { display: flex; flex-direction: column; gap: 10px; }
.factor-row { display: grid; grid-template-columns: 150px minmax(0, 1fr) 150px; gap: 12px; align-items: center; font-size: 12px; }
.factor-name { display: flex; flex-direction: column; gap: 2px; }
.factor-name small { color: var(--text-muted); font-size: 11px; }
.factor-track { height: 12px; background: #eef1f6; border-radius: 6px; overflow: hidden; }
.factor-bar { height: 100%; min-width: 6px; border-radius: 6px; }
.factor-bar.positive { background: linear-gradient(90deg, #79b8ff, #2f6fed); }
.factor-bar.negative { background: linear-gradient(90deg, #f2a0a0, #e15b64); }
.factor-value { text-align: right; font-weight: 650; }
.factor-value.positive { color: #2457c8; }
.factor-value.negative { color: #c84f5d; }
.explain-note { margin-top: 14px; color: var(--text-muted); font-size: 11px; line-height: 1.6; }
.section-error { padding: 22px 0; text-align: center; color: var(--color-danger); font-size: 13px; }
@media (max-width: 1000px) {
  .predict-grid { grid-template-columns: 1fr; }
  .result-wrap { position: static; }
  .factor-row { grid-template-columns: 110px minmax(0, 1fr) 120px; gap: 8px; }
}
@media (max-width: 640px) {
  .factor-row { grid-template-columns: 90px minmax(0, 1fr); }
  .factor-value { grid-column: 2; text-align: left; }
  .section-head { flex-direction: column; }
}
</style>
