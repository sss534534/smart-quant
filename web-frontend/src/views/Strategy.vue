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
          <el-button size="small" @click="loadStrategies">刷新</el-button>
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
        <el-table-column label="操作" width="320">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="handleRun(row)" :disabled="row.status !== 'active'">运行</el-button>
            <el-button size="small" type="warning" @click="handleStop(row)">停止</el-button>
            <el-button size="small" @click="loadSignals(row)">信号</el-button>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { strategyAPI } from '../api'

const form = ref({ name: '', code: '', type: 'dual_ma', description: '' })
const strategies = ref([])
const signals = ref([])
const selectedStrategy = ref(null)

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

onMounted(loadStrategies)
</script>
