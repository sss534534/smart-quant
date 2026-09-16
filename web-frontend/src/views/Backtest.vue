<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>新建回测</span></template>
          <el-form :model="form" label-width="80px" @submit.prevent="handleCreate">
            <el-form-item label="名称">
              <el-input v-model="form.name" placeholder="回测名称" />
            </el-form-item>
            <el-form-item label="策略ID">
              <el-input-number v-model="form.strategy_id" :min="1" />
            </el-form-item>
            <el-form-item label="股票列表">
              <el-input v-model="form.code_list_str" placeholder="如: 600000,000001" />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="初始资金">
              <el-input-number v-model="form.initial_capital" :min="10000" :step="10000" />
            </el-form-item>
            <el-form-item label="佣金率">
              <el-input-number v-model="form.commission_rate" :min="0" :step="0.0001" :precision="4" />
            </el-form-item>
            <el-form-item label="滑点率">
              <el-input-number v-model="form.slip_rate" :min="0" :step="0.001" :precision="4" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleCreate">创建并运行</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>回测列表</span></template>
          <el-table :data="backtests" stripe size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="80">
              <template #default="{ row }">
                <el-progress :percentage="row.progress || 0" :status="row.status === 'failed' ? 'exception' : undefined" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="loadResult(row)">结果</el-button>
                <el-button size="small" type="success" @click="openReport(row)" :disabled="row.status !== 'completed'">报告</el-button>
                <el-button size="small" type="danger" @click="handleStop(row)" :disabled="row.status !== 'running'">停止</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 20px" v-if="result">
      <template #header><span>回测结果 - {{ result.backtest_id }}</span></template>
      <el-row :gutter="16" v-if="result.metrics">
        <el-col :span="4"><div class="m"><div class="l">总收益率</div><div class="v" :class="(result.metrics.total_return||0)>=0?'profit':'loss'">{{ pct(result.metrics.total_return) }}</div></div></el-col>
        <el-col :span="4"><div class="m"><div class="l">年化收益率</div><div class="v" :class="(result.metrics.annual_return||0)>=0?'profit':'loss'">{{ pct(result.metrics.annual_return) }}</div></div></el-col>
        <el-col :span="4"><div class="m"><div class="l">夏普比率</div><div class="v">{{ num(result.metrics.sharpe_ratio) }}</div></div></el-col>
        <el-col :span="4"><div class="m"><div class="l">最大回撤</div><div class="v loss">{{ pct(result.metrics.max_drawdown) }}</div></div></el-col>
        <el-col :span="4"><div class="m"><div class="l">胜率</div><div class="v">{{ pct(result.metrics.win_rate) }}</div></div></el-col>
        <el-col :span="4"><div class="m"><div class="l">总交易次数</div><div class="v">{{ result.metrics.total_trades }}</div></div></el-col>
      </el-row>
      <div v-if="result.equity_curve && result.equity_curve.length">
        <div ref="eqChart" style="height: 300px; margin-top: 20px"></div>
      </div>
      <el-table :data="result.trades || []" size="small" max-height="300" style="margin-top: 20px" v-if="result.trades">
        <el-table-column prop="code" label="代码" />
        <el-table-column prop="direction" label="方向" />
        <el-table-column prop="price" label="价格" />
        <el-table-column prop="quantity" label="数量" />
        <el-table-column prop="pnl" label="盈亏">
          <template #default="{ row }">
            <span :class="row.pnl >= 0 ? 'profit' : 'loss'">{{ num(row.pnl) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 完整报告对话框 -->
    <el-dialog v-model="reportVisible" title="回测分析报告" width="1200px" top="4vh">
      <template v-if="report">
        <el-row :gutter="12">
          <el-col :span="3"><div class="r-m"><div class="l">初始资金</div><div class="v">{{ fmtNum(report.initial_capital) }}</div></div></el-col>
          <el-col :span="3"><div class="r-m"><div class="l">结束权益</div><div class="v">{{ fmtNum(report.metrics?.end_balance) }}</div></div></el-col>
          <el-col :span="3"><div class="r-m"><div class="l">年化波动率</div><div class="v">{{ pct(report.risk_metrics?.annual_volatility) }}</div></div></el-col>
          <el-col :span="3"><div class="r-m"><div class="l">下行波动率</div><div class="v">{{ pct(report.risk_metrics?.downside_volatility) }}</div></div></el-col>
          <el-col :span="3"><div class="r-m"><div class="l">索提诺比率</div><div class="v">{{ num(report.risk_metrics?.sortino_ratio) }}</div></div></el-col>
          <el-col :span="3"><div class="r-m"><div class="l">卡尔玛比率</div><div class="v">{{ num(report.risk_metrics?.calmar_ratio) }}</div></div></el-col>
          <el-col :span="3"><div class="r-m"><div class="l">盈利因子</div><div class="v">{{ num(report.metrics?.profit_factor) }}</div></div></el-col>
          <el-col :span="3"><div class="r-m"><div class="l">最大回撤天</div><div class="v">{{ report.drawdown_analysis?.duration_days }}</div></div></el-col>
        </el-row>

        <el-row :gutter="12" style="margin-top: 12px">
          <el-col :span="14">
            <el-card shadow="never" size="small">
              <template #header><span style="font-size:13px">月度收益矩阵（{{ report.monthly_returns?.matrix ? Object.keys(report.monthly_returns.matrix).length : 0 }}年）</span></template>
              <el-table :data="monthlyRows" size="mini" border>
                <el-table-column prop="year" label="年" width="70" />
                <el-table-column v-for="m in MONTHS" :key="m" :label="m + '月'" width="62" align="center">
                  <template #default="{ row }">
                    <span v-if="row[m] !== null && row[m] !== undefined" :class="row[m] >= 0 ? 'profit' : 'loss'">{{ pct(row[m]) }}</span>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card shadow="never" size="small">
              <template #header><span style="font-size:13px">回撤分析</span></template>
              <div ref="ddChart" style="height: 200px"></div>
              <div v-if="report.drawdown_analysis" style="margin-top:8px">
                <div class="dd-line"><span>最大回撤</span><b class="loss">{{ pct(report.drawdown_analysis.max_drawdown) }}</b></div>
                <div class="dd-line"><span>起始</span><b>{{ report.drawdown_analysis.start_date }}</b></div>
                <div class="dd-line"><span>结束</span><b>{{ report.drawdown_analysis.end_date }}</b></div>
                <div class="dd-line"><span>持续（天）</span><b>{{ report.drawdown_analysis.duration_days }}</b></div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-card shadow="never" size="small" style="margin-top: 12px" v-if="report.trade_stats?.by_code?.length">
          <template #header><span style="font-size:13px">分标的收益（按收益排序）</span></template>
          <el-table :data="report.trade_stats.by_code" size="mini">
            <el-table-column prop="code" label="代码" width="120" />
            <el-table-column prop="buy" label="买入次数" width="100" />
            <el-table-column prop="sell" label="卖出次数" width="100" />
            <el-table-column label="净盈亏">
              <template #default="{ row }">
                <span :class="row.pnl >= 0 ? 'profit' : 'loss'">{{ fmtNum(row.pnl) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <div style="margin-top: 16px; text-align: right">
          <el-button @click="exportCsv('trades')">导出交易CSV</el-button>
          <el-button @click="exportCsv('equity')">导出权益CSV</el-button>
          <el-button type="primary" @click="exportReport">导出完整报告(ZIP)</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { backtestAPI, strategyAPI } from '../api'

const MONTHS = ['01','02','03','04','05','06','07','08','09','10','11','12']

const form = ref({
  name: '回测1', strategy_id: 1, code_list_str: '600000,000001',
  start_date: '2024-01-01', end_date: '2024-12-31',
  initial_capital: 100000, commission_rate: 0.0003, slip_rate: 0.001,
})
const backtests = ref([])
const result = ref(null)
const report = ref(null)
const reportVisible = ref(false)
const eqChart = ref(null)
const ddChart = ref(null)
let chart = null
let ddChartInstance = null

const pct = (v) => v == null ? '-' : ((Number(v) || 0) * 100).toFixed(2) + '%'
const num = (v) => (Number(v) || 0).toFixed(4)
const fmtNum = (v) => (Number(v) || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })

const statusType = (s) => {
  if (s === 'completed') return 'success'
  if (s === 'running' || s === 'pending') return 'warning'
  if (s === 'failed' || s === 'stopped') return 'danger'
  return 'info'
}

const monthlyRows = computed(() => {
  const matrix = report.value?.monthly_returns?.matrix || {}
  return Object.keys(matrix).sort().map(year => {
    const row = { year }
    MONTHS.forEach(m => { row[m] = matrix[year]?.[m] ?? null })
    return row
  })
})

const loadBacktests = async () => {
  try {
    const res = await backtestAPI.list()
    backtests.value = res.data.items || []
  } catch (e) {}
}

const handleCreate = async () => {
  const codeList = form.value.code_list_str.split(',').map(s => s.trim()).filter(Boolean)
  try {
    const res = await backtestAPI.create({
      name: form.value.name,
      strategy_id: form.value.strategy_id,
      code_list: codeList,
      start_date: form.value.start_date,
      end_date: form.value.end_date,
      initial_capital: form.value.initial_capital,
      commission_rate: form.value.commission_rate,
      slip_rate: form.value.slip_rate,
    })
    ElMessage.success('回测任务已创建并启动')
    loadBacktests()
    setTimeout(() => loadResult({ id: res.data.id }), 1000)
  } catch (e) {}
}

const handleStop = async (row) => {
  try {
    await backtestAPI.stop(row.id)
    ElMessage.success('已停止')
    loadBacktests()
  } catch (e) {}
}

const loadResult = async (row) => {
  try {
    const res = await backtestAPI.getResult(row.id)
    result.value = res.data
    await nextTick()
    if (eqChart.value && result.value.equity_curve) {
      chart = chart || echarts.init(eqChart.value)
      chart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 60, right: 20, top: 20, bottom: 30 },
        xAxis: { type: 'category', data: result.value.equity_curve.map(p => p.date) },
        yAxis: { type: 'value' },
        series: [{
          name: '权益', type: 'line', smooth: true,
          areaStyle: { opacity: 0.1 },
          data: result.value.equity_curve.map(p => p.equity),
          itemStyle: { color: '#67c23a' },
        }],
      })
    }
  } catch (e) {}
}

const openReport = async (row) => {
  reportVisible.value = true
  try {
    const res = await backtestAPI.getReport(row.id)
    report.value = res.data
    await nextTick()
    renderDrawdownChart()
  } catch (e) {
    report.value = null
  }
}

const renderDrawdownChart = async () => {
  await nextTick()
  if (!ddChart.value) return
  // 用报告中的回撤分析渲染简单条形图（收益 vs 最大回撤）
  ddChartInstance = ddChartInstance || echarts.init(ddChart.value)
  const m = report.value.metrics || {}
  ddChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: ['总收益', '最大回撤'] },
    yAxis: { type: 'value', formatter: (v) => (v * 100).toFixed(1) + '%' },
    series: [{
      type: 'bar', barWidth: 40,
      data: [
        { value: m.total_return || 0, itemStyle: { color: '#67c23a' } },
        { value: -(Math.abs(m.max_drawdown || 0)), itemStyle: { color: '#f56c6c' } },
      ],
    }],
  })
}

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const extractFilename = (headers, fallback) => {
  const cd = headers?.['content-disposition'] || ''
  const m = cd.match(/filename="?([^";]+)"?/)
  return m ? m[1] : fallback
}

const exportCsv = async (kind) => {
  if (!report.value) return
  try {
    const res = await backtestAPI.getExportCsv(report.value.backtest_id, kind)
    downloadBlob(new Blob([res.data]), extractFilename(res.headers, `backtest_${report.value.backtest_id}_${kind}.csv`))
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const exportReport = async () => {
  if (!report.value) return
  try {
    const res = await backtestAPI.getExportReport(report.value.backtest_id)
    downloadBlob(new Blob([res.data]), extractFilename(res.headers, `backtest_${report.value.backtest_id}_report.zip`))
    ElMessage.success('报告已导出')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

onMounted(loadBacktests)
</script>

<style scoped>
.m { text-align: center; padding: 10px; background: #f5f7fa; border-radius: 4px; }
.m .l { color: #909399; font-size: 12px; }
.m .v { font-size: 18px; font-weight: bold; margin-top: 5px; }
.r-m { text-align: center; padding: 10px 4px; background: #f5f7fa; border-radius: 4px; }
.r-m .l { color: #909399; font-size: 12px; }
.r-m .v { font-size: 15px; font-weight: bold; margin-top: 5px; }
.dd-line { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.profit { color: #67c23a; }
.loss { color: #f56c6c; }
</style>