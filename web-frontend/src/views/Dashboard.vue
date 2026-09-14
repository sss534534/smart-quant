<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="metric-label">总资产</div>
          <div class="metric-value">¥ {{ fmt(summary.total_assets) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="metric-label">持仓市值</div>
          <div class="metric-value">¥ {{ fmt(summary.positions_value) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="metric-label">可用资金</div>
          <div class="metric-value">¥ {{ fmt(summary.cash) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="metric-label">总收益</div>
          <div class="metric-value" :class="profitClass">¥ {{ fmt(summary.total_profit) }}</div>
          <div class="metric-pct" :class="profitClass">{{ pct(summary.total_profit_pct) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>权益曲线</span></template>
          <div ref="equityChart" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>持仓概览</span></template>
          <el-table :data="positions" size="small" max-height="320">
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="name" label="名称" width="80" />
            <el-table-column prop="quantity" label="数量" width="80" />
            <el-table-column label="盈亏" width="100">
              <template #default="{ row }">
                <span :class="row.unrealized_pnl >= 0 ? 'profit' : 'loss'">
                  {{ fmt(row.unrealized_pnl) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>风险预警</span></template>
          <el-table :data="alerts" size="small" max-height="260">
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="message" label="消息" />
            <el-table-column prop="level" label="等级" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.level)" size="small">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>组合分析</span></template>
          <div ref="pieChart" style="height: 260px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { portfolioAPI, riskAPI } from '../api'

const summary = ref({ total_assets: 0, positions_value: 0, cash: 0, total_profit: 0, total_profit_pct: 0 })
const positions = ref([])
const alerts = ref([])
const equityChart = ref(null)
const pieChart = ref(null)
let eqChart = null
let pChart = null

const fmt = (v) => (Number(v) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const pct = (v) => ((Number(v) || 0) * 100).toFixed(2) + '%'
const profitClass = computed(() => (summary.value.total_profit >= 0 ? 'profit' : 'loss'))

const levelType = (lvl) => {
  if (lvl === 'danger' || lvl === 'blocked') return 'danger'
  if (lvl === 'warning') return 'warning'
  return 'info'
}

const loadData = async () => {
  try {
    const [sumRes, posRes, alertRes] = await Promise.all([
      portfolioAPI.getSummary(),
      portfolioAPI.getPositions(),
      riskAPI.getAlerts(),
    ])
    summary.value = sumRes.data
    positions.value = posRes.data || []
    alerts.value = alertRes.data || []
  } catch (e) {
    // handled
  }
}

const renderCharts = () => {
  if (equityChart.value) {
    eqChart = echarts.init(equityChart.value)
    eqChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [{
        name: '权益',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.1 },
        data: [],
        itemStyle: { color: '#409eff' },
      }],
    })
  }
  if (pieChart.value) {
    pChart = echarts.init(pieChart.value)
    pChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: positions.value.slice(0, 8).map(p => ({ name: p.code, value: p.market_value || 0 })),
      }],
    })
  }
}

onMounted(async () => {
  await loadData()
  await nextTick()
  renderCharts()
})
</script>

<style scoped>
.metric-label { color: #909399; font-size: 13px; }
.metric-value { font-size: 24px; font-weight: bold; margin-top: 8px; }
.metric-pct { font-size: 13px; margin-top: 4px; }
.profit { color: #67c23a; }
.loss { color: #f56c6c; }
</style>
