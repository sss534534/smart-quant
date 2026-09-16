<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">限额总数</div>
          <div class="m-value">{{ dashboard.limit_summary?.total || 0 }}</div>
          <div class="m-sub">启用 {{ dashboard.limit_summary?.enabled || 0 }} / 停用 {{ dashboard.limit_summary?.disabled || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">预警总数</div>
          <div class="m-value" style="color:#e6a23c">{{ dashboard.alert_stats?.total || 0 }}</div>
          <div class="m-sub">
            DANGER {{ dashboard.alert_stats?.by_level?.danger || 0 }} / WARNING {{ dashboard.alert_stats?.by_level?.warning || 0 }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">检查次数</div>
          <div class="m-value">{{ dashboard.check_stats?.total || 0 }}</div>
          <div class="m-sub">拦截 {{ dashboard.check_stats?.blocked || 0 }} 次</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">检查通过率</div>
          <div class="m-value" :class="passRate >= 90 ? 'profit' : passRate >= 70 ? 'warn' : 'loss'">
            {{ passRate.toFixed(1) }}%
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>预警等级分布</span></template>
          <div ref="levelChart" style="height: 260px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>预警类型分布</span></template>
          <div ref="typeChart" style="height: 260px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>风险类型限额覆盖</span></template>
          <div ref="coverChart" style="height: 260px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>风控限额</span>
              <el-button size="small" type="primary" @click="limitDialogVisible = true">新增限额</el-button>
            </div>
          </template>
          <el-table :data="limits" size="small" stripe max-height="380">
            <el-table-column prop="risk_type" label="类型" width="150" />
            <el-table-column prop="limit_name" label="名称" />
            <el-table-column prop="limit_value" label="阈值" width="90" />
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" type="danger" @click="deleteLimit(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>风控检查记录</span></template>
          <el-table :data="checks" size="small" stripe max-height="380">
            <el-table-column prop="risk_type" label="风险类型" width="140" />
            <el-table-column label="实际值" width="90">
              <template #default="{ row }">{{ (row.actual_value * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="限额" width="80">
              <template #default="{ row }">{{ (row.limit_value * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="结果" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.passed ? 'success' : 'danger'">{{ row.passed ? '通过' : '拦截' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="说明" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 20px">
      <template #header><span>最近风险预警</span></template>
      <el-table :data="dashboard.recent_alerts || []" size="small" stripe>
        <el-table-column prop="risk_type" label="类型" width="150" />
        <el-table-column prop="level" label="等级" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="levelType(row.level)">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column prop="timestamp" label="时间" width="190" />
      </el-table>
    </el-card>

    <el-dialog v-model="limitDialogVisible" title="新增风控限额" width="420px">
      <el-form :model="limitForm" label-width="80px">
        <el-form-item label="类型">
          <el-select v-model="limitForm.risk_type" style="width:100%">
            <el-option v-for="t in riskTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="limitForm.limit_name" />
        </el-form-item>
        <el-form-item label="阈值">
          <el-input-number v-model="limitForm.limit_value" :min="0" :max="1" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-form-item label="预警值">
          <el-input-number v-model="limitForm.warning_value" :min="0" :max="1" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="limitForm.description" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="limitForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="limitDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createLimit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { riskAPI } from '../api'

const dashboard = ref({})
const limits = ref([])
const alerts = ref([])
const checks = ref([])
const limitDialogVisible = ref(false)
const limitForm = ref({ risk_type: 'position_percentage', limit_name: '', limit_value: 0.3, warning_value: 0.24, description: '', enabled: true })
const levelChart = ref(null)
const typeChart = ref(null)
const coverChart = ref(null)
let charts = {}

const riskTypes = [
  { label: '单票持仓比例', value: 'position_percentage' },
  { label: '单笔交易比例', value: 'single_trade_limit' },
  { label: '每日亏损比例', value: 'daily_limit' },
  { label: '最大亏损比例', value: 'max_loss_limit' },
  { label: '最大回撤', value: 'drawdown' },
]

const passRate = computed(() => dashboard.value.check_stats?.pass_rate ?? 100)

const levelType = (lvl) => {
  if (lvl === 'danger' || lvl === 'blocked') return 'danger'
  if (lvl === 'warning') return 'warning'
  return 'info'
}

const loadAll = async () => {
  try {
    const [d, l, a, c] = await Promise.all([
      riskAPI.getDashboard(),
      riskAPI.getLimits(),
      riskAPI.getAlerts(),
      riskAPI.getChecks(),
    ])
    dashboard.value = d.data || {}
    limits.value = l.data || []
    alerts.value = a.data || []
    checks.value = c.data || []
    await nextTick()
    renderCharts()
  } catch (e) {}
}

const renderCharts = () => {
  const byLevel = dashboard.value.alert_stats?.by_level || {}
  const byType = dashboard.value.alert_stats?.by_type || {}
  const typeDist = dashboard.value.risk_type_distribution || {}

  const refs = { levelChart, typeChart, coverChart }
  for (const [key, ref] of Object.entries(refs)) {
    if (ref.value) charts[key] = charts[key] || echarts.init(ref.value)
  }

  if (charts.levelChart) {
    charts.levelChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: [
          { name: 'normal', value: byLevel.normal || 0, itemStyle: { color: '#67c23a' } },
          { name: 'warning', value: byLevel.warning || 0, itemStyle: { color: '#e6a23c' } },
          { name: 'danger', value: byLevel.danger || 0, itemStyle: { color: '#f56c6c' } },
          { name: 'blocked', value: byLevel.blocked || 0, itemStyle: { color: '#b1b3b8' } },
        ].filter(d => d.value > 0),
      }],
    })
  }

  if (charts.typeChart) {
    charts.typeChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 80, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: Object.keys(byType), inverse: true },
      series: [{ type: 'bar', data: Object.values(byType), itemStyle: { color: '#409eff' }, barWidth: 16 }],
    })
  }

  if (charts.coverChart) {
    charts.coverChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 90, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'value', minInterval: 1 },
      yAxis: { type: 'category', data: Object.keys(typeDist), inverse: true },
      series: [{ type: 'bar', data: Object.values(typeDist), itemStyle: { color: '#67c23a' }, barWidth: 16 }],
    })
  }
}

const createLimit = async () => {
  try {
    await riskAPI.createLimit(limitForm.value)
    ElMessage.success('限额创建成功')
    limitDialogVisible.value = false
    limitForm.value = { risk_type: 'position_percentage', limit_name: '', limit_value: 0.3, warning_value: 0.24, description: '', enabled: true }
    loadAll()
  } catch (e) {}
}

const deleteLimit = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除此限额?', '提示', { type: 'warning' })
    await riskAPI.deleteLimit(row.id)
    ElMessage.success('已删除')
    loadAll()
  } catch (e) {}
}

onMounted(loadAll)
</script>

<style scoped>
.m-label { color: #909399; font-size: 13px; }
.m-value { font-size: 24px; font-weight: bold; margin-top: 8px; }
.m-sub { color: #909399; font-size: 12px; margin-top: 4px; }
.profit { color: #67c23a; }
.warn { color: #e6a23c; }
.loss { color: #f56c6c; }
</style>