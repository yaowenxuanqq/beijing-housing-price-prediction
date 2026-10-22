<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchHouses, fetchMetaOptions } from '../api/endpoints'
import { fmtNumber } from '../utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const sort = ref('-trade_date')
const districts = ref([])
const drawer = ref(false)
const detail = ref(null)

const filters = reactive({
  district: '',
  min_price: undefined,
  max_price: undefined,
  min_square: undefined,
  max_square: undefined,
  subway: '',
  elevator: ''
})

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    Object.entries(filters).forEach(([k, v]) => { if (v !== '' && v !== undefined && v !== null) params[k] = v })
    if (sort.value) params.ordering = sort.value
    const data = await fetchHouses(params)
    rows.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function readQuery() {
  const q = route.query
  if (q.district) filters.district = String(q.district)
  for (const k of ['min_price', 'max_price', 'min_square', 'max_square']) {
    if (q[k]) filters[k] = Number(q[k])
  }
  if (q.subway !== undefined) filters.subway = String(q.subway)
  if (q.elevator !== undefined) filters.elevator = String(q.elevator)
  if (q.ordering) sort.value = String(q.ordering)
}

function syncQuery() {
  const q = {}
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== '' && v !== undefined && v !== null) q[k] = String(v)
  })
  if (sort.value) q.ordering = sort.value
  router.replace({ query: q })
}

function onSortChange({ prop, order }) {
  if (!order) sort.value = '-trade_date'
  else sort.value = (order === 'descending' ? '-' : '') + prop
  syncQuery()
  page.value = 1
  load()
}

async function search() {
  page.value = 1
  syncQuery()
  await load()
}

async function reset() {
  Object.assign(filters, { district: '', min_price: undefined, max_price: undefined, min_square: undefined, max_square: undefined, subway: '', elevator: '' })
  sort.value = '-trade_date'
  page.value = 1
  syncQuery()
  await load()
}

function onSizeChange() {
  // 页码本来就是 1 时，size-change 不会触发 current-change，需要主动加载一次
  if (page.value === 1) load()
  else page.value = 1
}

function openDetail(row) {
  detail.value = row
  drawer.value = true
}

onMounted(async () => {
  try { districts.value = (await fetchMetaOptions()).districts } catch (e) {}
  readQuery()
  await load()
})

watch(() => route.query.district, v => {
  if (v && v !== filters.district) {
    filters.district = String(v)
    page.value = 1
    load()
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>数据管理</h2>
      <span class="sub">清洗后房源明细 · 共 {{ fmtNumber(total) }} 条</span>
    </div>

    <section class="card filter-bar">
      <el-select v-model="filters.district" placeholder="全部区域" clearable style="width: 150px">
        <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
      </el-select>
      <el-input-number v-model="filters.min_price" :min="0" :controls="false" placeholder="最低总价（万）" style="width: 140px" />
      <el-input-number v-model="filters.max_price" :min="0" :controls="false" placeholder="最高总价（万）" style="width: 140px" />
      <el-input-number v-model="filters.min_square" :min="0" :controls="false" placeholder="最小面积（㎡）" style="width: 140px" />
      <el-select v-model="filters.subway" placeholder="地铁" clearable style="width: 100px">
        <el-option label="近地铁" value="1" /><el-option label="非地铁" value="0" />
      </el-select>
      <el-select v-model="filters.elevator" placeholder="电梯" clearable style="width: 100px">
        <el-option label="有电梯" value="1" /><el-option label="无电梯" value="0" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="reset">重置</el-button>
    </section>

    <section class="card mt-16">
      <el-table :data="rows" v-loading="loading" stripe height="560" @row-click="openDetail"
                @sort-change="onSortChange" :default-sort="{ prop: 'trade_date', order: 'descending' }"
                style="cursor: pointer">
        <el-table-column prop="district_name" label="区域" width="100" />
        <el-table-column prop="square" label="面积（㎡）" width="110" align="right" sortable="custom">
          <template #default="{ row }">{{ row.square.toFixed(1) }}</template>
        </el-table-column>
        <el-table-column label="户型" width="100">
          <template #default="{ row }">{{ row.rooms }}室{{ row.halls }}厅</template>
        </el-table-column>
        <el-table-column prop="floor_position" label="楼层" width="80" />
        <el-table-column prop="trade_date" label="成交日期" width="120" sortable="custom" />
        <el-table-column prop="total_price" label="总价（万）" width="110" align="right" sortable="custom">
          <template #default="{ row }">{{ fmtNumber(row.total_price) }}</template>
        </el-table-column>
        <el-table-column prop="unit_price" label="单价（元/㎡）" min-width="140" align="right" sortable="custom">
          <template #default="{ row }">{{ fmtNumber(row.unit_price) }}</template>
        </el-table-column>
        <el-table-column label="配套" min-width="140">
          <template #default="{ row }">
            <el-tag v-if="row.elevator" size="small" type="success" effect="plain">电梯</el-tag>
            <el-tag v-if="row.subway" size="small" type="primary" effect="plain" style="margin-left: 4px">地铁</el-tag>
            <el-tag v-if="row.five_years" size="small" type="warning" effect="plain" style="margin-left: 4px">满五</el-tag>
          </template>
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
          @size-change="onSizeChange"
        />
      </div>
    </section>

    <el-drawer v-model="drawer" title="房源详情" size="420px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="区域">{{ detail.district_name }}</el-descriptions-item>
        <el-descriptions-item label="成交日期">{{ detail.trade_date }}</el-descriptions-item>
        <el-descriptions-item label="面积">{{ detail.square }} ㎡</el-descriptions-item>
        <el-descriptions-item label="户型">{{ detail.rooms }}室{{ detail.halls }}厅{{ detail.bathrooms }}卫</el-descriptions-item>
        <el-descriptions-item label="楼层">{{ detail.floor_position }} / 共 {{ detail.total_floors ?? '-' }} 层</el-descriptions-item>
        <el-descriptions-item label="房龄">{{ detail.house_age ?? '-' }} 年</el-descriptions-item>
        <el-descriptions-item label="总价">{{ fmtNumber(detail.total_price) }} 万</el-descriptions-item>
        <el-descriptions-item label="单价">{{ fmtNumber(detail.unit_price) }} 元/㎡</el-descriptions-item>
        <el-descriptions-item label="小区均价">{{ fmtNumber(detail.community_average) }} 元/㎡</el-descriptions-item>
        <el-descriptions-item label="原始链接">
          <a v-if="detail.url" :href="detail.url" target="_blank" rel="noreferrer">链家房源页</a>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<style scoped>
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 14px 18px; }
.pager { display: flex; justify-content: flex-end; padding-top: 14px; }
</style>
