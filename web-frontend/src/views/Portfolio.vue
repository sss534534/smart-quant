<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">总资产</div>
          <div class="m-value">¥ {{ fmt(summary.total_assets) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">持仓市值</div>
          <div class="m-value">¥ {{ fmt(summary.positions_value) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">可用资金</div>
          <div class="m-value">¥ {{ fmt(summary.cash) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">总收益</div>
          <div class="m-value" :class="summary.total_profit >= 0 ? 'profit' : 'loss'">¥ {{ fmt(summary.total_profit) }}</div>
          <div class="m-pct" :class="summary.total_profit >= 0 ? 'profit' : 'loss'">{{ pct(summary.total_profit_pct) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>持仓明细</span>
              <el-button-group>
                <el-button size="small" @click="loadPositions('all')">全部</el-button>
                <el-button size="small" type="primary" @click="loadPositions('open')">持仓中</el-button>
                <el-button size="small" @click="loadPositions('closed')">已平仓</el-button>
              </el-button-group>
            </div>
          </template>
          <el-table :data="positions" size="small" stripe>
            <el-table-column prop="code" label="代码" width="90" />
            <el-table-column prop="name" label="名称" width="100" />
            <el-table-column prop="quantity" label="持仓" width="80" />
            <el-table-column prop="avg_cost" label="均价" width="90" />
            <el-table-column prop="current_price" label="现价" width="90" />
            <el-table-column label="市值" width="110">
              <template #default="{ row }">{{ fmt(row.market_value) }}</template>
            </el-table-column>
            <el-table-column label="浮动盈亏" width="110">
              <template #default="{ row }">
                <span :class="row.unrealized_pnl >= 0 ? 'profit' : 'loss'">{{ fmt(row.unrealized_pnl) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="收益率" width="100">
              <template #default="{ row }">
                <span :class="row.return_rate >= 0 ? 'profit' : 'loss'">{{ pct(row.return_rate) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="hover" style="margin-top: 20px">
          <template #header><span>资金流水</span></template>
          <el-table :data="logs" size="small" max-height="300">
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="logType(row.type)">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" width="120">
              <template #default="{ row }">
                <span :class="row.amount >= 0 ? 'profit' : 'loss'">{{ fmt(row.amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="balance_after" label="变动后余额" width="130" />
            <el-table-column prop="description" label="说明" />
            <el-table-column prop="created_at" label="时间" width="170" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>账户操作</span></template>
          <el-form :model="acctForm" label-width="70px">
            <el-form-item label="金额">
              <el-input-number v-model="acctForm.amount" :min="0" :step="1000" style="width:100%" />
            </el-form-item>
            <el-form-item label="说明">
              <el-input v-model="acctForm.description" />
            </el-form-item>
            <el-form-item>
              <el-button type="success" @click="deposit">存入</el-button>
              <el-button type="warning" @click="withdraw">取出</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" style="margin-top: 20px">
          <template #header><span>账户详情</span></template>
          <div class="acct-item"><span>初始资金</span><b>¥ {{ fmt(account.initial_capital) }}</b></div>
          <div class="acct-item"><span>当前现金</span><b>¥ {{ fmt(account.cash) }}</b></div>
          <div class="acct-item"><span>累计存入</span><b class="profit">¥ {{ fmt(account.total_deposit) }}</b></div>
          <div class="acct-item"><span>累计取出</span><b class="loss">¥ {{ fmt(account.total_withdraw) }}</b></div>
          <div class="acct-item"><span>累计交易盈亏</span><b :class="account.total_pnl >= 0 ? 'profit' : 'loss'">¥ {{ fmt(account.total_pnl) }}</b></div>
          <div class="acct-item"><span>累计手续费</span><b class="loss">¥ {{ fmt(account.total_commission) }}</b></div>
          <div class="acct-item"><span>累计滑点</span><b class="loss">¥ {{ fmt(account.total_slippage) }}</b></div>
        </el-card>

        <el-card shadow="hover" style="margin-top: 20px">
          <template #header><span>持仓分布</span></template>
          <div ref="pieChart" style="height: 240px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { portfolioAPI } from '../api'

const summary = ref({ total_assets: 0, positions_value: 0, cash: 0, total_profit: 0, total_profit_pct: 0 })
const account = ref({})
const positions = ref([])
const logs = ref([])
const acctForm = ref({ amount: 10000, description: '现金存入' })
const pieChart = ref(null)
let chart = null

const fmt = (v) => (Number(v) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const pct = (v) => ((Number(v) || 0) * 100).toFixed(2) + '%'

const logType = (t) => {
  if (t === 'deposit') return 'success'
  if (t === 'withdraw') return 'warning'
  if (t === 'trade') return ''
  return 'info'
}

const loadAll = async () => {
  try {
    const [s, a, p, l] = await Promise.all([
      portfolioAPI.getSummary(),
      portfolioAPI.getAccount(),
      portfolioAPI.getPositions('open'),
      portfolioAPI.getLogs(100),
    ])
    summary.value = s.data
    account.value = a.data
    positions.value = p.data || []
    logs.value = l.data || []
  } catch (e) {}
}

const loadPositions = async (status) => {
  try {
    const res = await portfolioAPI.getPositions(status)
    positions.value = res.data || []
  } catch (e) {}
}

const deposit = async () => {
  try {
    await portfolioAPI.deposit(acctForm.value.amount, acctForm.value.description)
    ElMessage.success('存入成功')
    loadAll()
  } catch (e) {}
}

const withdraw = async () => {
  try {
    await portfolioAPI.withdraw(acctForm.value.amount, acctForm.value.description)
    ElMessage.success('取出成功')
    loadAll()
  } catch (e) {}
}

const renderPie = async () => {
  await nextTick()
  if (pieChart.value) {
    chart = echarts.init(pieChart.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, type: 'scroll' },
      series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: positions.value.map(p => ({ name: p.code, value: p.market_value || 0 })),
      }],
    })
  }
}

onMounted(async () => {
  await loadAll()
  renderPie()
})
</script>

<style scoped>
.m-label { color: #909399; font-size: 13px; }
.m-value { font-size: 22px; font-weight: bold; margin-top: 6px; }
.m-pct { font-size: 12px; margin-top: 4px; }
.profit { color: #67c23a; }
.loss { color: #f56c6c; }
.acct-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
.acct-item:last-child { border-bottom: none; }
</style>
