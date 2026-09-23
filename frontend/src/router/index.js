import { createRouter, createWebHashHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import { getToken } from '../api'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'tasks', name: 'tasks', component: () => import('../views/TasksView.vue') },
      { path: 'tasks/:id', name: 'task-detail', component: () => import('../views/TaskDetailView.vue') },
      { path: 'stores', name: 'stores', component: () => import('../views/StoresView.vue') },
      { path: 'vehicles', name: 'vehicles', component: () => import('../views/VehiclesView.vue') },
      { path: 'routes', name: 'routes', component: () => import('../views/RoutesView.vue') },
      { path: 'rules', name: 'rules', component: () => import('../views/RulesView.vue') },
      { path: 'reports', name: 'reports', component: () => import('../views/ReportsView.vue') },
      // 系统管理
      { path: 'system/users', name: 'sys-users', component: () => import('../views/system/UsersView.vue'), meta: { perm: 'system:user:list' } },
      { path: 'system/roles', name: 'sys-roles', component: () => import('../views/system/RolesView.vue'), meta: { perm: 'system:role:list' } },
      { path: 'system/permissions', name: 'sys-perms', component: () => import('../views/system/PermissionsView.vue'), meta: { perm: 'system:permission:list' } },
      { path: 'system/menus', name: 'sys-menus', component: () => import('../views/system/MenusView.vue'), meta: { perm: 'system:menu:list' } },
      { path: 'system/depts', name: 'sys-depts', component: () => import('../views/system/DeptsView.vue'), meta: { perm: 'system:dept:list' } },
      { path: 'system/dicts', name: 'sys-dicts', component: () => import('../views/system/DictsView.vue'), meta: { perm: 'system:dict:list' } },
      { path: 'system/params', name: 'sys-params', component: () => import('../views/system/ParamsView.vue'), meta: { perm: 'system:param:list' } },
      { path: 'system/logs', name: 'sys-logs', component: () => import('../views/system/LogsView.vue'), meta: { perm: 'system:log:list' } },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  if (to.meta?.public) return next()
  if (!getToken()) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  next()
})

export default router
