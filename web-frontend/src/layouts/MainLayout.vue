<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" style="background: #001529; color: #fff">
      <div class="logo">
        <span style="font-size: 18px; font-weight: bold; color: #409eff">量化投资系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409eff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/market">
          <el-icon><TrendCharts /></el-icon>
          <span>行情</span>
        </el-menu-item>
        <el-menu-item index="/strategy">
          <el-icon><Cpu /></el-icon>
          <span>策略</span>
        </el-menu-item>
        <el-menu-item index="/backtest">
          <el-icon><DataAnalysis /></el-icon>
          <span>回测</span>
        </el-menu-item>
        <el-menu-item index="/trading">
          <el-icon><Money /></el-icon>
          <span>交易</span>
        </el-menu-item>
        <el-menu-item index="/portfolio">
          <el-icon><Wallet /></el-icon>
          <span>组合</span>
        </el-menu-item>
        <el-menu-item index="/risk">
          <el-icon><Warning /></el-icon>
          <span>风控</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background: #fff; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: flex-end">
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            {{ username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main style="background: #f5f7fa">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authAPI } from '../api'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)
const username = computed(() => {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.username || '用户'
})

const handleCommand = async (cmd) => {
  if (cmd === 'logout') {
    try {
      await authAPI.logout()
    } catch (e) {
      // ignore
    }
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #1f2d3d;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #303133;
}
</style>
