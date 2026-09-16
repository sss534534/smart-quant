<template>
  <div>
    <el-card shadow="hover" style="margin-bottom: 20px">
      <el-form :inline="true" :model="form" @submit.prevent="handleCreate">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="策略名称" />
        </el-form-item>
        <el-form-item label="代码">
          <el-input v-model="form.code" placeholder="策略代码" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 160px">
            <el-option label="双均线" value="dual_ma" />
            <el-option label="RSI均值回归" value="rsi_mean_reversion" />
            <el-option label="MACD" value="macd" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="描述" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleCreate">创建策略</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>策略列表</span>
          <div>
            <el-button size="small" @click="loadStrategies">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="strategies" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="code" label="代码" />
        <el-table-column prop="type" label="类型" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="390">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="handleRun(row)" :disabled="row.status !== 'active'">运行</el-button>
            <el-button size="small" type="warning" @click="handleStop(row)">停止</el-button>
            <el-button size="small" @click="loadSignals(row)">信号</el-button>
            <el-button size="small" type="primary" @click="openAnalysis(row)">分析</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="hover" style="margin-top: 20px" v-if="selectedStrategy">
      <template #header><span>策略信号 - {{ selectedStrategy.name }}</span></template>
      <el-table :data="signals" size="small">
        <el-table-column prop="code" label="代码" />
        <el-table-column prop="action" label="操作">
          <template #default="{ row }">
            <el-tag :type="row.action === 'buy' ? 'success' : row.action === 'sell' ? 'danger' : 'info'" size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" />
        <el-table-column prop="quantity" label="数量" />
        <el-table-column prop="reason" label="理由" />
        <el-table-column prop="strength" label="强度" />
        <el-table-column prop="created_at" label="时间" />
      </el-table>
    </el-card>

    <!-- 策略分析对话框 -->
    <el-dialog v-model="analysisVisible" :title="'策略分析 - ' + (analysis?.name || '')" width="1100px" top="5vh">
      <template v-if="analysis">
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="a-card">
              <div class="a-label">窗口内信号</div>
              <div class="a-value">{{ analysis.total_signals }}</div>
              <div class="a-sub">日均 {{ analysis.signal_rate_per_day }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="a-card">
              <div class="a-label">买入信号</div>
              <div class="a-value success">{{ analysis.action_distribution.buy }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="a-card">
              <div class="a-label">卖出信号</div>
              <div class="a-value warning">{{ analysis.action_distribution.sell }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="a-card">
              <div class="a-label">平均强度</div>
              <div class="a-value">{{ analysis.avg_strength }}</div>
              <div class="a-sub">{{ analysis.days }}天窗口</div>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top: 8px">
          <el-col :span="14">
            <el-card shadow="never" size="small">
              <template #header><span style="font-size: 13px">信号趋势（{{ analysis.days }}天）</span></template>
              <div ref="trendChart" style="height: 260px"></div>
            </el-card>
          </el-col>
          <el-col :span="5">
            <el-card shadow="never" size="small">
              <template #header><span style="font-size: 13px">操作分布</span></template>
              <div ref="actionChart" style="height: 260px"></div>
            </el-card>
          </el-col>
          <el-col :span="5">
            <el-card shadow="never" size="small">
              <template #header><span style="font-size: 13px">强度分布</span></template>
              <div ref="strengthChart" style="height: 260px"></div>
            </el-card>
          </el-col>
        </el-row>

        <el-row v-if="analysis.code_distribution && analysis.code_distribution.length" :gutter="16" style="margin-top: 8px">
          <el-col :span="24">
            <el-card shadow="never" size="small">
              <template #header><span style="font-size: 13px">标的分布 Top10</span></template>
              <div ref="codeChart" style="height: 180px"></div>
            </el-card>
          </el-col>
        </el-row>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { strategyAPI } from '../api'

const form = ref({ name: '', code: '', type: 'dual_ma', description: '' })
const strategies = ref([])
const signals = ref([])
const selectedStrategy = ref(null)

// 分析相关
const analysisVisible = ref(false)
const analysis = ref(null)
const trendChart = ref(null)
const actionChart = ref(null)
const strengthChart = ref(null)
const codeChart = ref(null)
let charts = []

const loadStrategies = async () => {
  try {
    const res = await strategyAPI.list()
    strategies.value = res.data.items || []
  } catch (e) {}
}

const handleCreate = async () => {
  if (!form.value.name || !form.value.code) {
    ElMessage.warning('请填写名称和代码')
    return
  }
  try {
    await strategyAPI.create({ ...form.value, params: {} })
    ElMessage.success('创建成功')
    form.value = { name: '', code: '', type: 'dual_ma', description: '' }
    loadStrategies()
  } catch (e) {}
}

const handleRun = async (row) => {
  try {
    const res = await strategyAPI.run(row.id)
    ElMessage.success(res.data.message || '策略已启动')
  } catch (e) {}
}

const handleStop = async (row) => {
  try {
    const res = await strategyAPI.stop(row.id)
    ElMessage.success(res.data.message || '策略已停止')
  } catch (e) {}
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除策略 ${row.name}?`, '提示', { type: 'warning' })
    await strategyAPI.remove(row.id)
    ElMessage.success('已删除')
    loadStrategies()
  } catch (e) {}
}

const loadSignals = async (row) => {
  selectedStrategy.value = row
  try {
    const res = await strategyAPI.getSignals(row.id)
    signals.value = res.data || []
  } catch (e) {}
}

const disposeCharts = () => {
  charts.forEach(c => { if (c) c.dispose() })
  charts = []
}

const renderAnalysisCharts = async () => {
  await nextTick()
  if (!analysis.value) return
  if (trendChart.value) {
    const c = echarts.init(trendChart.value)
    charts.push(c)
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 15, top: 15, bottom: 25 },
      xAxis: { type: 'category', data: analysis.value.daily_trend.map(d => d.date.slice(5)), axisLabel: { interval: 'auto' } },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{
        type: 'line', smooth: true, showSymbol: false,
        areaStyle: { opacity: 0.1 }, itemStyle: { color: '#409eff' },
        data: analysis.value.daily_trend.map(d => d.count),
      }],
    })
  }
  if (actionChart.value) {
    const c = echarts.init(actionChart.value)
    charts.push(c)
    const dist = analysis.value.action_distribution
    c.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: [
          { name: '买入', value: dist.buy, itemStyle: { color: '#67c23a' } },
          { name: '卖出', value: dist.sell, itemStyle: { color: '#f56c6c' } },
          { name: '持有', value: dist.hold, itemStyle: { color: '#909399' } },
        ],
      }],
    })
  }
  if (strengthChart.value) {
    const c = echarts.init(strengthChart.value)
    charts.push(c)
    const s = analysis.value.strength_distribution
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 20, right: 15, top: 15, bottom: 25 },
      xAxis: { type: 'category', data: Object.keys(s) },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{
        type: 'bar',
        itemStyle: { color: '#e6a23c' },
        data: Object.values(s),
      }],
    })
  }
  if (codeChart.value && analysis.value.code_distribution.length) {
    const c = echarts.init(codeChart.value)
    charts.push(c)
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 15, top: 15, bottom: 25 },
      xAxis: { type: 'category', data: analysis.value.code_distribution.map(d => d.code) },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{
        type: 'bar', barWidth: 20,
        itemStyle: { color: '#409eff' },
        data: analysis.value.code_distribution.map(d => d.count),
      }],
    })
  }
}

const openAnalysis = async (row) => {
  analysisVisible.value = true
  disposeCharts()
  try {
    const res = await strategyAPI.analyze(row.id, 90)
    analysis.value = res.data
    renderAnalysisCharts()
  } catch (e) {
    analysis.value = null
  }
}

onMounted(loadStrategies)
</script>

<style scoped>
.a-card { text-align: center; padding: 16px 8px; background: #f5f7fa; border-radius: 6px; }
.a-label { color: #909399; font-size: 12px; }
.a-value { font-size: 22px; font-weight: bold; margin-top: 6px; }
.a-sub { color: #909399; font-size: 12px; margin-top: 4px; }
.success { color: #67c23a; }
.warning { color: #e6a23c; }
</style>