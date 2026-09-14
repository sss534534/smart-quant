<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>下单</span></template>
          <el-form :model="orderForm" label-width="70px" @submit.prevent="handleOrder">
            <el-form-item label="股票代码">
              <el-input v-model="orderForm.code" placeholder="如: 600000" />
            </el-form-item>
            <el-form-item label="方向">
              <el-radio-group v-model="orderForm.direction">
                <el-radio-button value="buy">买入</el-radio-button>
                <el-radio-button value="sell">卖出</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="价格">
              <el-input-number v-model="orderForm.price" :min="0" :step="0.01" :precision="2" />
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="orderForm.quantity" :min="100" :step="100" />
            </el-form-item>
            <el-form-item label="订单类型">
              <el-select v-model="orderForm.order_type" style="width: 100%">
                <el-option label="限价单" value="limit" />
                <el-option label="市价单" value="market" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleOrder" :loading="ordering">
                {{ orderForm.direction === 'buy' ? '买入' : '卖出' }}
              </el-button>
              <el-button @click="loadData">刷新</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" style="margin-top: 20px">
          <template #header><span>资金账户</span></template>
          <div class="acct-item"><span>总资产</span><b>¥ {{ fmt(capital.total_assets) }}</b></div>
          <div class="acct-item"><span>可用资金</span><b>¥ {{ fmt(capital.available) }}</b></div>
          <div class="acct-item"><span>冻结资金</span><b>¥ {{ fmt(capital.frozen) }}</b></div>
          <div class="acct-item"><span>持仓市值</span><b>¥ {{ fmt(capital.market_value) }}</b></div>
          <div class="acct-item"><span>总盈亏</span><b :class="capital.total_pnl >= 0 ? 'profit' : 'loss'">¥ {{ fmt(capital.total_pnl) }}</b></div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>持仓</span></template>
          <el-table :data="positions" size="small" stripe>
            <el-table-column prop="code" label="代码" width="90" />
            <el-table-column prop="name" label="名称" width="100" />
            <el-table-column prop="quantity" label="持仓" width="80" />
            <el-table-column prop="available" label="可用" width="80" />
            <el-table-column prop="avg_cost" label="成本" width="90" />
            <el-table-column prop="current_price" label="现价" width="90" />
            <el-table-column label="市值" width="110">
              <template #default="{ row }">{{ fmt(row.market_value) }}</template>
            </el-table-column>
            <el-table-column label="浮动盈亏" width="120">
              <template #default="{ row }">
                <span :class="row.unrealized_pnl >= 0 ? 'profit' : 'loss'">{{ fmt(row.unrealized_pnl) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-tabs v-model="activeTab" style="margin-top: 20px">
          <el-tab-pane label="订单" name="orders">
            <el-card shadow="hover">
              <el-table :data="orders" size="small" stripe>
                <el-table-column prop="order_no" label="订单号" width="180" />
                <el-table-column prop="code" label="代码" width="90" />
                <el-table-column prop="direction" label="方向" width="70">
                  <template #default="{ row }">
                    <el-tag :type="row.direction === 'buy' ? 'success' : 'danger'" size="small">{{ row.direction }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="price" label="价格" width="80" />
                <el-table-column prop="quantity" label="数量" width="80" />
                <el-table-column prop="filled_quantity" label="已成交" width="80" />
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="orderStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="{ row }">
                    <el-button size="small" type="danger" @click="cancelOrder(row)" :disabled="row.status !== 'submitted' && row.status !== 'partial_filled'">撤单</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-tab-pane>
          <el-tab-pane label="成交" name="trades">
            <el-card shadow="hover">
              <el-table :data="trades" size="small" stripe>
                <el-table-column prop="trade_id" label="成交号" width="180" />
                <el-table-column prop="code" label="代码" width="90" />
                <el-table-column prop="direction" label="方向" width="70">
                  <template #default="{ row }">
                    <el-tag :type="row.direction === 'buy' ? 'success' : 'danger'" size="small">{{ row.direction }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="price" label="成交价" width="90" />
                <el-table-column prop="quantity" label="成交量" width="90" />
                <el-table-column prop="amount" label="成交金额" width="120" />
                <el-table-column prop="created_at" label="时间" />
              </el-table>
            </el-card>
          </el-tab-pane>
        </el-tabs>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { tradingAPI } from '../api'

const orderForm = ref({ code: '', direction: 'buy', price: 0, quantity: 100, order_type: 'limit' })
const positions = ref([])
const orders = ref([])
const trades = ref([])
const capital = ref({ total_assets: 0, available: 0, frozen: 0, market_value: 0, total_pnl: 0 })
const activeTab = ref('orders')
const ordering = ref(false)

const fmt = (v) => (Number(v) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const orderStatusType = (s) => {
  if (s === 'filled') return 'success'
  if (s === 'submitted' || s === 'partial_filled') return 'warning'
  if (s === 'cancelled' || s === 'rejected') return 'info'
  return ''
}

const loadData = async () => {
  try {
    const [posRes, ordRes, trdRes, capRes] = await Promise.all([
      tradingAPI.getPositions(),
      tradingAPI.listOrders(),
      tradingAPI.listTrades(),
      tradingAPI.getCapital(),
    ])
    positions.value = posRes.data || []
    orders.value = ordRes.data || []
    trades.value = trdRes.data || []
    capital.value = capRes.data || {}
  } catch (e) {}
}

const handleOrder = async () => {
  if (!orderForm.value.code) {
    ElMessage.warning('请输入股票代码')
    return
  }
  ordering.value = true
  try {
    const res = await tradingAPI.createOrder(orderForm.value)
    ElMessage.success(res.data.message || '订单已提交')
    loadData()
  } catch (e) {} finally {
    ordering.value = false
  }
}

const cancelOrder = async (row) => {
  try {
    await tradingAPI.cancelOrder(row.order_id || row.id)
    ElMessage.success('已撤单')
    loadData()
  } catch (e) {}
}

onMounted(loadData)
</script>

<style scoped>
.acct-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
.acct-item:last-child { border-bottom: none; }
.profit { color: #67c23a; }
.loss { color: #f56c6c; }
</style>
