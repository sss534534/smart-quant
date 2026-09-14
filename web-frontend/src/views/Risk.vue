<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">今日检查次数</div>
          <div class="m-value">{{ stats.today_checks || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">通过</div>
          <div class="m-value profit">{{ stats.passed || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">警告</div>
          <div class="m-value" style="color: #e6a23c">{{ stats.warned || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="m-label">拦截</div>
          <div class="m-value loss">{{ stats.blocked || 0 }}</div>
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
          <el-table :data="limits" size="small" stripe>
            <el-table-column prop="risk_type" label="类型" width="150" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="threshold" label="阈值" width="100" />
            <el-table-column prop="action" label="动作" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.action === 'block' ? 'danger' : 'warning'">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="启用" width="80">
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
          <el-table :data="checks" size="small" stripe>
            <el-table-column prop="code" label="代码" width="90" />
            <el-table-column prop="direction" label="方向" width="70" />
            <el-table-column prop="price" label="价格" width="80" />
            <el-table-column prop="quantity" label="数量" width="80" />
            <el-table-column prop="amount" label="金额" width="110" />
            <el-table-column label="结果" width="90">
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
      <template #header><span>风险预警</span></template>
      <el-table :data="alerts" size="small" stripe>
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="risk_type" label="类型" width="150" />
        <el-table-column prop="level" label="等级" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="levelType(row.level)">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </el-card>

    <el-dialog v-model="limitDialogVisible" title="新增风控限额" width="420px">
      <el-form :model="limitForm" label-width="90px">
        <el-form-item label="类型">
          <el-select v-model="limitForm.risk_type" style="width:100%">
            <el-option label="单票仓位" value="single_position" />
            <el-option label="行业仓位" value="industry_position" />
            <el-option label="总仓位" value="total_position" />
            <el-option label="单笔金额" value="single_amount" />
            <el-option label="最大亏损" value="max_loss" />
            <el-option label="回撤限制" value="drawdown" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="limitForm.name" />
        </el-form-item>
        <el-form-item label="阈值">
          <el-input-number v-model="limitForm.threshold" :min="0" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-form-item label="动作">
          <el-select v-model="limitForm.action" style="width:100%">
            <el-option label="警告" value="warn" />
            <el-option label="拦截" value="block" />
          </el-select>
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
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { riskAPI } from '../api'

const stats = ref({})
const limits = ref([])
const alerts = ref([])
const checks = ref([])
const limitDialogVisible = ref(false)
const limitForm = ref({ risk_type: 'single_position', name: '', threshold: 0.1, action: 'warn', enabled: true })

const levelType = (lvl) => {
  if (lvl === 'danger' || lvl === 'blocked') return 'danger'
  if (lvl === 'warning' || lvl === 'warn') return 'warning'
  return 'info'
}

const loadAll = async () => {
  try {
    const [s, l, a, c] = await Promise.all([
      riskAPI.getStats(),
      riskAPI.getLimits(),
      riskAPI.getAlerts(),
      riskAPI.getChecks(),
    ])
    stats.value = s.data || {}
    limits.value = l.data || []
    alerts.value = a.data || []
    checks.value = c.data || []
  } catch (e) {}
}

const createLimit = async () => {
  try {
    await riskAPI.createLimit(limitForm.value)
    ElMessage.success('限额创建成功')
    limitDialogVisible.value = false
    limitForm.value = { risk_type: 'single_position', name: '', threshold: 0.1, action: 'warn', enabled: true }
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
.profit { color: #67c23a; }
.loss { color: #f56c6c; }
</style>
