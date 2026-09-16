<template>
  <div>
    <el-row :gutter="20">
      <!-- 自选股管理 -->
      <el-col :span="7">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>自选股</span>
              <el-button size="small" @click="refreshWatchlist">刷新</el-button>
            </div>
          </template>
          <div style="margin-bottom:12px;display:flex;gap:8px">
            <el-input v-model="addForm.code" placeholder="股票代码" style="flex:1" />
            <el-input v-model="addForm.remark" placeholder="备注" style="flex:1" />
            <el-button type="primary" size="small" @click="handleAddWatchlist">添加</el-button>
          </div>
          <el-table :data="watchlist" size="small" @row-click="pickWatchlist" highlight-current-row>
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="latest_price" label="最新价" width="80">
              <template #default="{ row }">{{ row.latest_price != null ? num(row.latest_price) : '-' }}</template>
            </el-table-column>
            <el-table-column label="涨跌幅" width="85">
              <template #default="{ row }">
                <span v-if="row.change_percent != null" :class="row.change_percent >= 0 ? 'up' : 'down'">
                  {{ fmtPct(row.change_percent) }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="" width="50">
              <template #default="{ row }">
                <el-button size="mini" type="danger" link @click.stop="handleRemoveWatchlist(row)">删</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="hover" style="margin-top: 16px">
          <template #header><span>行情看板</span></template>
          <el-table :data="boardQuotes" size="small" stripe @row-click="pickBoard" highlight-current-row max-height="400">
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="price" label="价格" width="80">
              <template #default="{ row }">{{ num(row.price) }}</template>
            </el-table-column>
            <el-table-column label="涨跌" width="80">
              <template #default="{ row }">
                <span :class="row.change >= 0 ? 'up' : 'down'">{{ num(row.change) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="涨幅" width="80">
              <template #default="{ row }">
                <span :class="row.change_pct >= 0 ? 'up' : 'down'">{{ fmtPct(row.change_pct) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="成交量" width="85">
              <template #default="{ row }">{{ fmtVol(row.volume) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 个股详情 + K线 -->
      <el-col :span="17">
        <el-card shadow="hover">
          <el-form :inline="true" :model="search" @submit.prevent="searchQuote">
            <el-form-item label="股票代码">
              <el-input v-model="search.code" placeholder="如: 600000" style="width:120px" />
            </el-form-item>
            <el-form-item label="数据源">
              <el-select v-model="search.provider" style="width: 120px">
                <el-option label="东财" value="eastmoney" />
                <el-option label="Tushare" value="tushare" />
                <el-option label="Mock" value="mock" />
              </el-select>
            </el-form-item>
            <el-form-item label="周期">
              <el-select v-model="search.interval" style="width: 100px">
                <el-option label="日线" value="1d" />
                <el-option label="周线" value="1w" />
                <el-option label="月线" value="1M" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="searchQuote" :loading="loading">查询</el-button>
              <el-button @click="handleAddWatchlistCode" :disabled="!search.code">加自选</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-row :gutter="16" style="margin-top:16px" v-if="quote">
          <el-col :span="6">
            <el-card shadow="hover">
              <div class="q-head">
                <div>
                  <div class="q-name">{{ quote.name }}</div>
                  <div class="q-code">{{ quote.code }}</div>
                </div>
                <div class="q-price" :class="quote.change >= 0 ? 'up' : 'down'">
                  {{ num(quote.price) }}
                  <div class="q-chg">{{ fmtPct(quote.change_pct) }}</div>
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
          <el-col :span="18">
            <el-card shadow="hover">
              <template #header><span>K 线图 - {{ search.code }}</span></template>
              <div ref="klineChart" style="height: 420px"></div>
            </el-card>
          </el-col>
        </el-row>
        <el-row v-else style="margin-top:20px">
          <el-col :span="24">
            <el-card shadow="hover" style="text-align:center;padding:60px 0;color:#909399">请在左侧输入股票代码查询行情</el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { marketAPI } from '../api'

const search = ref({ code: '600000', provider: 'eastmoney', interval: '1d' })
const quote = ref(null)
const stocks = ref([])
const klineChart = ref(null)
const loading = ref(false)
let chart = null

// 自选股
const watchlist = ref([])
const addForm = ref({ code: '', remark: '' })

// 行情看板
const boardQuotes = ref([])

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
  if (!search.value.code) return
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
  const volumes = data.map(d => d.volume || 0)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: [
      { left: 55, right: 20, top: 20, height: '65%' },
      { left: 55, right: 20, top: '80%', height: '12%' }
    ],
    xAxis: [
      { type: 'category', data: dates, axisLabel: { show: false }, gridIndex: 0 },
      { type: 'category', data: dates, axisLabel: { rotate: 45 }, gridIndex: 1 },
    ],
    yAxis: [
      { scale: true, gridIndex: 0 },
      { scale: true, gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], bottom: 0, height: 16 },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0, data: kdata,
        itemStyle: { color: '#f56c6c', color0: '#67c23a', borderColor: '#f56c6c', borderColor0: '#67c23a' },
      },
      {
        name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: kdata[i][1] >= kdata[i][0] ? '#f56c6c' : '#67c23a' },
        })),
      },
    ],
  })
}

const pickStock = (code) => {
  search.value.code = code
  searchQuote()
}

const pickWatchlist = (row) => pickStock(row.code)
const pickBoard = (row) => pickStock(row.code)

// ---- 自选股 ----
const refreshWatchlist = async () => {
  try {
    const res = await marketAPI.getWatchlist()
    watchlist.value = res.data || []
  } catch (e) {}
}

const handleAddWatchlist = async () => {
  const code = (addForm.value.code || '').trim()
  if (!code) { ElMessage.warning('请输入股票代码'); return }
  try {
    await marketAPI.addToWatchlist(code, addForm.value.remark)
    ElMessage.success('添加成功')
    addForm.value = { code: '', remark: '' }
    refreshWatchlist()
  } catch (e) {}
}

const handleAddWatchlistCode = async () => {
  if (!search.value.code) return
  try {
    await marketAPI.addToWatchlist(search.value.code, quote.value?.name || '')
    ElMessage.success('已添加到自选')
    refreshWatchlist()
  } catch (e) {}
}

const handleRemoveWatchlist = async (row) => {
  try {
    await marketAPI.removeFromWatchlist(row.code)
    ElMessage.success('已删除')
    refreshWatchlist()
  } catch (e) {}
}

// ---- 行情看板 ----
const loadBoard = async () => {
  try {
    const res = await marketAPI.getBoard()
    boardQuotes.value = res.data?.quotes || []
  } catch (e) {}
}

let boardTimer = null

onMounted(async () => {
  await Promise.all([refreshWatchlist(), loadBoard(), searchQuote()])
  boardTimer = setInterval(loadBoard, 15000)
})

onUnmounted(() => { if (boardTimer) clearInterval(boardTimer) })
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