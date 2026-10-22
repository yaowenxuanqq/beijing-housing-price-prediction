<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { predict } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const store = useAppStore()
const formRef = ref()
const loading = ref(false)
const metaLoading = ref(true)
const result = ref(null)

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
    try {
      result.value = await predict({ ...form })
      ElMessage.success('预测完成')
    } catch {
      // 拦截器已提示
    } finally {
      loading.value = false
    }
  })
}

function reset() {
  formRef.value?.resetFields()
  result.value = null
}

function applyPreset(preset) {
  Object.assign(form, preset.values)
  result.value = null
}

const gaugeLeft = computed(() => {
  const r = Number(result.value?.ratio || 1)
  return Math.max(0, Math.min(100, ((r - 0.7) / 0.6) * 100))
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>房价预测</h2>
      <span class="sub">基于房屋特征的相对行情估值（ratio × 当期区中位单价）</span>
    </div>

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
            <el-button type="primary" :loading="loading" @click="submit">开始预测</el-button>
            <el-button @click="reset">重置</el-button>
          </el-form-item>
        </el-form>
      </section>

      <section class="result-wrap">
        <div v-if="!result" class="card result-empty">
          <div class="empty-icon">✦</div>
          <div>填写左侧信息后点击「开始预测」</div>
          <div class="muted">系统将输出相对行情估值与折算总价</div>
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
            80% 经验区间：{{ fmtNumber(result.interval_low) }} – {{ fmtNumber(result.interval_high) }} 元/㎡
          </div>
          <div class="interval">
            总价区间：{{ fmtNumber(result.interval_total_low) }} – {{ fmtNumber(result.interval_total_high) }} 万元
          </div>

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
  </div>
</template>

<style scoped>
.predict-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, 1fr); gap: 16px; align-items: start; }
.result-wrap { position: sticky; top: 0; }
.result-empty {
  min-height: 320px; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; color: var(--text-secondary); font-size: 14px;
}
.empty-icon { font-size: 36px; color: var(--primary); }
.result-card { background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%); }
.result-label { font-size: 13px; color: var(--text-secondary); }
.result-price { font-size: 40px; font-weight: 700; color: var(--primary); line-height: 1.2; margin-top: 6px; }
.result-price .unit { font-size: 14px; font-weight: 500; color: var(--text-secondary); margin-left: 6px; }
.result-total { margin-top: 4px; font-size: 15px; }
.result-total b { color: var(--text-main); }
.kv { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 6px 0; color: var(--text-secondary); }
.kv b { color: var(--text-main); }
.result-note { margin-top: 12px; font-size: 12px; color: #909399; line-height: 1.6; }
.interval { margin-top: 6px; font-size: 12px; color: var(--text-secondary); }
.preset-row { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.gauge { margin-top: 14px; }
.gauge-track { position: relative; height: 6px; border-radius: 3px; background: #e8eefc; }
.gauge-zone { position: absolute; left: 33.3%; width: 33.3%; height: 100%; background: #c9dcff; border-radius: 3px; }
.gauge-marker { position: absolute; top: -3px; width: 12px; height: 12px; border-radius: 50%; background: var(--color-primary); border: 2px solid #fff; box-shadow: 0 1px 4px rgba(0,0,0,.2); transform: translateX(-6px); transition: left .4s ease; }
.gauge-labels { display: flex; justify-content: space-between; margin-top: 6px; font-size: 10px; color: var(--text-muted); }
@media (max-width: 1000px) {
  .predict-grid { grid-template-columns: 1fr; }
  .result-wrap { position: static; }
}
</style>
