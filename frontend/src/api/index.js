import axios from 'axios'
import { message } from 'ant-design-vue'

const http = axios.create({
  baseURL: process.env.VUE_APP_API_BASE || '/api/v1',
  timeout: 30000,
})

const TOKEN_KEY = 'sched_access_token'
const REFRESH_KEY = 'sched_refresh_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}
export function setToken(access, refresh) {
  if (access) localStorage.setItem(TOKEN_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// 请求拦截：注入 Bearer token
http.interceptors.request.use((config) => {
  const t = getToken()
  if (t && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${t}`
  }
  return config
})

let redirecting = false
// 响应拦截：业务码 + 401 自动跳转登录
http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        return Promise.reject(new Error(body.message || 'API error'))
      }
      return body.data
    }
    return body
  },
  (err) => {
    const status = err.response?.status
    if (status === 401 && !redirecting) {
      redirecting = true
      clearToken()
      message.error('登录已过期，请重新登录')
      setTimeout(() => {
        redirecting = false
        if (location.hash !== '#/login') location.hash = '#/login'
      }, 600)
    }
    const msg = err.response?.data?.detail || err.response?.data?.message || err.message
    return Promise.reject(new Error(msg || 'Network error'))
  }
)

export default http

export const api = {
  // 认证
  login: (data) => http.post('/auth/login', data),
  logout: () => http.post('/auth/logout'),
  getMe: () => http.get('/auth/me'),
  changePassword: (data) => http.put('/auth/password', data),

  // 用户
  listUsers: (params) => http.get('/users', { params }),
  createUser: (data) => http.post('/users', data),
  updateUser: (id, data) => http.put(`/users/${id}`, data),
  deleteUser: (id) => http.delete(`/users/${id}`),
  resetUserPassword: (id, data) => http.put(`/users/${id}/password/reset`, data),

  // 角色
  listRoles: () => http.get('/roles'),
  createRole: (data) => http.post('/roles', data),
  updateRole: (id, data) => http.put(`/roles/${id}`, data),
  deleteRole: (id) => http.delete(`/roles/${id}`),

  // 权限
  listPermissions: (params) => http.get('/permissions', { params }),
  createPermission: (data) => http.post('/permissions', data),
  updatePermission: (id, data) => http.put(`/permissions/${id}`, data),
  deletePermission: (id) => http.delete(`/permissions/${id}`),

  // 菜单
  listMenus: () => http.get('/menus'),
  menuTree: () => http.get('/menus/tree'),
  createMenu: (data) => http.post('/menus', data),
  updateMenu: (id, data) => http.put(`/menus/${id}`, data),
  deleteMenu: (id) => http.delete(`/menus/${id}`),

  // 部门
  listDepts: () => http.get('/depts'),
  deptTree: () => http.get('/depts/tree'),
  createDept: (data) => http.post('/depts', data),
  updateDept: (id, data) => http.put(`/depts/${id}`, data),
  deleteDept: (id) => http.delete(`/depts/${id}`),

  // 字典管理
  listDicts: (params) => http.get('/dicts', { params }),
  createDict: (data) => http.post('/dicts', data),
  updateDict: (id, data) => http.put(`/dicts/${id}`, data),
  deleteDict: (id) => http.delete(`/dicts/${id}`),
  listDictItems: (dictId) => http.get(`/dicts/${dictId}/items`),
  createDictItem: (dictId, data) => http.post(`/dicts/${dictId}/items`, data),
  updateDictItem: (dictId, itemId, data) => http.put(`/dicts/${dictId}/items/${itemId}`, data),
  deleteDictItem: (dictId, itemId) => http.delete(`/dicts/${dictId}/items/${itemId}`),

  // 系统参数
  listParams: (params) => http.get('/params', { params }),
  createParam: (data) => http.post('/params', data),
  updateParam: (id, data) => http.put(`/params/${id}`, data),
  deleteParam: (id) => http.delete(`/params/${id}`),

  // 系统日志
  listLogs: (params) => http.get('/logs', { params }),
  deleteLog: (id) => http.delete(`/logs/${id}`),
  clearLogs: () => http.delete('/logs'),

  // 基础数据
  listStores: (params) => http.get('/stores', { params }),
  upsertStore: (data) => http.post('/stores', data),
  listRoutes: (params) => http.get('/routes', { params }),
  listVehicles: (params) => http.get('/vehicles', { params }),
  upsertVehicle: (data) => http.post('/vehicles', data),
  listDrivers: () => http.get('/drivers'),

  // 规则
  listTerrainRules: () => http.get('/rules/terrain'),
  listTripRules: () => http.get('/rules/trip'),
  listLoadRules: () => http.get('/rules/load'),
  listConstraints: (params) => http.get('/rules/constraints', { params }),
  upsertConstraint: (data) => http.post('/rules/constraints', data),

  // 调度任务
  createTask: (data) => http.post('/scheduling/tasks', data),
  listTasks: (params) => http.get('/scheduling/tasks', { params }),
  getTask: (id) => http.get(`/scheduling/tasks/${id}`),
  startTask: (id) => http.post(`/scheduling/tasks/${id}/start`),
  listPlans: (id) => http.get(`/scheduling/tasks/${id}/plans`),
  getPlan: (id, planId) => http.get(`/scheduling/tasks/${id}/plans/${planId}`),
  confirmTask: (id, data) => http.post(`/scheduling/tasks/${id}/confirm`, data),
  replanTask: (id, data) => http.post(`/scheduling/tasks/${id}/replan`, data),
  getReport: (id) => http.get(`/scheduling/tasks/${id}/report`),
  getAgentState: (id) => http.get(`/scheduling/tasks/${id}/agent-state`),
  listExceptions: (id) => http.get(`/scheduling/tasks/${id}/exceptions`),
  createException: (id, data) => http.post(`/scheduling/tasks/${id}/exceptions`, data),
  sendExecutionFeedback: (id, data) => http.post(`/scheduling/tasks/${id}/execution-feedback`, data),

  // 报表
  attendanceReport: (date) => http.get('/reports/attendance', { params: { date } }),
  loadRateReport: (date) => http.get('/reports/load-rate', { params: { date } }),
  tripAchievementReport: (date) => http.get('/reports/trip-achievement', { params: { date } }),
}

export function openProgressSocket(taskId, onMessage) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const base = process.env.VUE_APP_WS_BASE || `${proto}//${window.location.host}/ws`
  const url = `${base}/scheduling/${taskId}`
  const ws = new WebSocket(url)
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data))
    } catch (e) {
      console.warn('invalid ws message', ev.data)
    }
  }
  ws.onclose = () => {
    console.log('ws closed', taskId)
  }
  ws.onerror = (e) => {
    console.error('ws error', e)
  }
  return ws
}
