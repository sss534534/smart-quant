import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import Strategy from '../views/Strategy.vue'
import Backtest from '../views/Backtest.vue'
import Trading from '../views/Trading.vue'
import Portfolio from '../views/Portfolio.vue'
import Market from '../views/Market.vue'
import Risk from '../views/Risk.vue'

const routes = [
  { path: '/login', component: Login, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: Dashboard },
      { path: 'strategy', component: Strategy },
      { path: 'backtest', component: Backtest },
      { path: 'trading', component: Trading },
      { path: 'portfolio', component: Portfolio },
      { path: 'market', component: Market },
      { path: 'risk', component: Risk },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录跳转到 /login
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) {
    next()
  } else if (!token) {
    next('/login')
  } else {
    next()
  }
})

export default router
