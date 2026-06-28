import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'financial',
    component: () => import('@/views/FinancialView.vue'),
  },
  {
    path: '/invest',
    name: 'invest',
    component: () => import('@/views/InvestView.vue'),
  },
  {
    path: '/collect',
    name: 'collect',
    component: () => import('@/views/DataCollectView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
