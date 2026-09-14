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
              <template #default="{ row }">{{ row.progress }}%</template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="loadResult(row)">结果</el-button>
                <el-button size="small" type="danger" @click="handleStop(row)" :disabled="row.status !== 'running'">停止</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 20px" v-if="result">
      <template #header><span>回测结果 - {{ result.backtest_id }}</span></template>
      <el-row :gutter="20" v-if="result.metrics">
        <el-col :span="4"><div class="m"><div class="l">总收益率</div><div class="v">{{ pct(result.metrics.total_return) }}</div></div></el-col>
        <el-col :span="4"><div class="m"><div class="l">年化收益率</div><div class="v">{{ pct(result.metrics.annual_return) }}</div></div></el-col>
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
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { backtestAPI, strategyAPI } from '../api'

const form = ref({
  name: '回测1', strategy_id: 1, code_list_str: '600000,000001',
  start_date: '2024-01-01', end_date: '2024-12-31',
  initial_capital: 100000, commission_rate: 0.0003, slip_rate: 0.001,
})
const backtests = ref([])
const result = ref(null)
const eqChart = ref(null)
let chart = null

const pct = (v) => ((Number(v) || 0) * 100).toFixed(2) + '%'
const num = (v) => (Number(v) || 0).toFixed(4)

const statusType = (s) => {
  if (s === 'completed') return 'success'
  if (s === 'running' || s === 'pending') return 'warning'
  if (s === 'failed' || s === 'stopped') return 'danger'
  return 'info'
}

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
    // 自动加载结果
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
      chart = echarts.init(eqChart.value)
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

onMounted(loadBacktests)
</script>

<style scoped>
.m { text-align: center; padding: 10px; background: #f5f7fa; border-radius: 4px; }
.m .l { color: #909399; font-size: 12px; }
.m .v { font-size: 18px; font-weight: bold; margin-top: 5px; }
.profit { color: #67c23a; }
.loss { color: #f56c6c; }
</style>
