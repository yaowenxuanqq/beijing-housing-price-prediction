import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '概览大屏' } },
      { path: 'houses', name: 'houses', component: () => import('../views/HousesView.vue'), meta: { title: '数据管理' } },
      { path: 'analysis', name: 'analysis', component: () => import('../views/AnalysisView.vue'), meta: { title: '可视化分析' } },
      { path: 'models', name: 'models', component: () => import('../views/ModelsView.vue'), meta: { title: '模型对比' } },
      { path: 'predict', name: 'predict', component: () => import('../views/PredictView.vue'), meta: { title: '房价预测' } }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })
router.afterEach(to => { document.title = (to.meta.title ? to.meta.title + ' - ' : '') + '北京二手房房价分析与预测系统' })
export default router
