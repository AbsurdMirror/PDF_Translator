import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Upload',
    component: () => import('@/views/UploadView.vue')
  },
  {
    path: '/list',
    name: 'List',
    component: () => import('@/views/TranslationListView.vue')
  },
  {
    path: '/config',
    name: 'Config',
    component: () => import('@/views/ConfigView.vue')
  }
  ,
  {
    path: '/detail/:taskId',
    name: 'Detail',
    component: () => import('@/views/TranslationDetailView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
