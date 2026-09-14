<template>
  <div>
    <el-card shadow="hover" style="margin-bottom: 20px">
      <el-form :inline="true" :model="search" @submit.prevent="searchQuote">
        <el-form-item label="股票代码">
          <el-input v-model="search.code" placeholder="如: 600000" />
        </el-form-item>
        <el-form-item label="数据源">
          <el-select v-model="search.provider" style="width: 140px">
            <el-option label="Mock" value="mock" />
            <el-option label="Tushare" value="tushare" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期">
          <el-select v-model="search.interval" style="width: 120px">
            <el-option label="日线" value="1d" />
            <el-option label="周线" value="1w" />
            <el-option label="月线" value="1M" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchQuote" :loading="loading">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="20" v-if="quote">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="q-head">
            <div>
              <div class="q-name">{{ quote.name }}</div>
              <div class="q-code">{{ quote.code }}</div>
            </div>
            <div class="q-price" :class="quote.change_percent >= 0 ? 'up' : 'down'">
              {{ num(quote.price) }}
              <div class="q-chg">{{ fmtPct(quote.change_percent) }}</div>
            </div>
          </div>
          <div class="q-grid">
            <div><span>开盘</span><b>{{ num(quote.open) }}</b></div>
            <div><span>最高</span><b>{{ num(quote.high) }}</b></div>
            <div><span>最低</span><b>{{ num(quote.low) }}</b></div>
            <div><span>昨收</span><b>{{ num(quote.pre_close) }}</b></div>
            <div><span>成交量</span><b>{{ fmtVol(quote.volume) }}</b></div>
            <div><span>成交额</span><b>{{ fmtVol(quote.amount) }}</b></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>K 线图 - {{ search.code }}</span></template>
          <div ref="klineChart" style="height: 380px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 20px">
      <template #header><span>股票列表</span></template>
      <el-table :data="stocks" size="small" stripe @row-click="pickStock">
        <el-table-column prop="code" label="代码" width="120" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="exchange" label="交易所" width="100" />
        <el-table-column prop="industry" label="行业" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { marketAPI } from '../api'

const search = ref({ code: '600000', provider: 'mock', interval: '1d' })
const quote = ref(null)
const stocks = ref([])
const klineChart = ref(null)
const loading = ref(false)
let chart = null

const num = (v) => (Number(v) || 0).toFixed(2)
const fmtPct = (v) => {
  const n = Number(v) || 0
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%'
}
const fmtVol = (v) => {
  const n = Number(v) || 0
  if (n >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (n >= 1e4) return (n / 1e4).toFixed(2) + '万'
  return n.toFixed(0)
}

const searchQuote = async () => {
  loading.value = true
  try {
    const [qRes, kRes] = await Promise.all([
      marketAPI.getQuote(search.value.code, search.value.provider),
      marketAPI.getKLine(search.value.code, null, null, search.value.interval, search.value.provider),
    ])
    quote.value = qRes.data
    await nextTick()
    renderKLine(kRes.data || [])
  } catch (e) {} finally {
    loading.value = false
  }
}

const renderKLine = (data) => {
  if (!klineChart.value) return
  chart = chart || echarts.init(klineChart.value)
  const dates = data.map(d => d.date)
  const kdata = data.map(d => [d.open, d.close, d.low, d.high])
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45 } },
    yAxis: { scale: true },
    series: [{
      type: 'candlestick',
      data: kdata,
      itemStyle: { color: '#f56c6c', color0: '#67c23a', borderColor: '#f56c6c', borderColor0: '#67c23a' },
    }],
  })
}

const pickStock = (row) => {
  search.value.code = row.code
  searchQuote()
}

const loadStocks = async () => {
  try {
    const res = await marketAPI.getStocks(null, 50)
    stocks.value = res.data || []
  } catch (e) {}
}

onMounted(() => {
  loadStocks()
  searchQuote()
})
</script>

<style scoped>
.q-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.q-name { font-size: 20px; font-weight: bold; }
.q-code { color: #909399; font-size: 13px; margin-top: 4px; }
.q-price { font-size: 28px; font-weight: bold; }
.q-chg { font-size: 14px; text-align: right; }
.up { color: #f56c6c; }
.down { color: #67c23a; }
.q-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.q-grid > div { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
.q-grid span { color: #909399; }
</style>
