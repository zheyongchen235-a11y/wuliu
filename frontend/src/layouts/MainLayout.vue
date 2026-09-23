<template>
  <a-layout class="main-layout">
    <a-layout-sider v-model:collapsed="collapsed" collapsible :trigger="null" width="220">
      <div class="logo">
        <span v-if="!collapsed">车辆智能调度 Agent</span>
        <span v-else>调度</span>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        theme="dark"
        mode="inline"
        @click="onMenuClick"
      >
        <a-menu-item key="dashboard"><dashboard-outlined /> 看板</a-menu-item>
        <a-sub-menu v-if="hasAny(bizMenuKeys)" key="business">
          <template #icon><carry-out-outlined /></template>
          <template #title>调度业务</template>
          <a-menu-item v-if="hasPerm('business:task:list')" key="tasks">调度任务</a-menu-item>
          <a-menu-item v-if="hasPerm('business:store:list')" key="stores">门店管理</a-menu-item>
          <a-menu-item v-if="hasPerm('business:vehicle:list')" key="vehicles">车辆管理</a-menu-item>
          <a-menu-item v-if="hasPerm('business:route:list')" key="routes">线路管理</a-menu-item>
          <a-menu-item v-if="hasPerm('business:rule:list')" key="rules">规则配置</a-menu-item>
          <a-menu-item v-if="hasPerm('business:report:list')" key="reports">报表中心</a-menu-item>
        </a-sub-menu>
        <a-sub-menu v-if="hasAny(sysMenuKeys)" key="system">
          <template #icon><setting-outlined /></template>
          <template #title>系统管理</template>
          <a-menu-item v-if="hasPerm('system:user:list')" key="sys-users">用户管理</a-menu-item>
          <a-menu-item v-if="hasPerm('system:role:list')" key="sys-roles">角色管理</a-menu-item>
          <a-menu-item v-if="hasPerm('system:permission:list')" key="sys-perms">权限管理</a-menu-item>
          <a-menu-item v-if="hasPerm('system:menu:list')" key="sys-menus">菜单管理</a-menu-item>
          <a-menu-item v-if="hasPerm('system:dept:list')" key="sys-depts">部门管理</a-menu-item>
          <a-menu-item v-if="hasPerm('system:dict:list')" key="sys-dicts">字典管理</a-menu-item>
          <a-menu-item v-if="hasPerm('system:param:list')" key="sys-params">参数管理</a-menu-item>
          <a-menu-item v-if="hasPerm('system:log:list')" key="sys-logs">日志管理</a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>
    <a-layout>
      <a-layout-header class="header">
        <menu-unfold-outlined v-if="collapsed" @click="collapsed = false" />
        <menu-fold-outlined v-else @click="collapsed = true" />
        <span class="header-title">车辆智能调度 Agent 平台</span>
        <a-tag color="green">RBAC · MySQL</a-tag>
        <a-dropdown>
          <div class="user-zone">
            <a-avatar style="background-color: #1e3c72">
              {{ (user && (user.nickname || user.username) || 'U').slice(0, 1) }}
            </a-avatar>
            <span class="user-name">{{ user?.nickname || user?.username || '未登录' }}</span>
            <a-tag v-if="user?.is_super" color="red" style="margin-left:6px">超管</a-tag>
          </div>
          <template #overlay>
            <a-menu @click="onUserMenu">
              <a-menu-item key="password"><key-outlined /> 修改密码</a-menu-item>
              <a-menu-divider />
              <a-menu-item key="logout"><logout-outlined /> 退出登录</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </a-layout-header>
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
      <a-layout-footer class="footer">
        车辆智能调度 Agent © 2026 - RBAC + MySQL
      </a-layout-footer>
    </a-layout>

    <a-modal v-model:open="pwdVisible" title="修改密码" @ok="submitPwd" :confirm-loading="pwdLoading">
      <a-form layout="vertical">
        <a-form-item label="原密码" required>
          <a-input-password v-model:value="pwdForm.old_password" />
        </a-form-item>
        <a-form-item label="新密码" required>
          <a-input-password v-model:value="pwdForm.new_password" />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-layout>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { message } from 'ant-design-vue'
import {
  DashboardOutlined,
  CarryOutOutlined,
  SettingOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  KeyOutlined,
  LogoutOutlined,
} from '@ant-design/icons-vue'
import { api } from '../api'

const router = useRouter()
const route = useRoute()
const store = useStore()
const collapsed = ref(false)
const selectedKeys = ref(['dashboard'])
const openKeys = ref([])

const user = computed(() => store.state.auth.user)
const hasPerm = (code) => store.getters['auth/hasPerm'](code)
const bizMenuKeys = ['tasks', 'stores', 'vehicles', 'routes', 'rules', 'reports']
const sysMenuKeys = ['sys-users', 'sys-roles', 'sys-perms', 'sys-menus', 'sys-depts', 'sys-dicts', 'sys-params', 'sys-logs']
function hasAny(keys) {
  return keys.some((k) => {
    const map = {
      tasks: 'business:task:list',
      stores: 'business:store:list',
      vehicles: 'business:vehicle:list',
      routes: 'business:route:list',
      rules: 'business:rule:list',
      reports: 'business:report:list',
      'sys-users': 'system:user:list',
      'sys-roles': 'system:role:list',
      'sys-perms': 'system:permission:list',
      'sys-menus': 'system:menu:list',
      'sys-depts': 'system:dept:list',
      'sys-dicts': 'system:dict:list',
      'sys-params': 'system:param:list',
      'sys-logs': 'system:log:list',
    }
    return hasPerm(map[k])
  })
}

const keyToPath = {
  dashboard: '/',
  tasks: '/tasks',
  stores: '/stores',
  vehicles: '/vehicles',
  routes: '/routes',
  rules: '/rules',
  reports: '/reports',
  'sys-users': '/system/users',
  'sys-roles': '/system/roles',
  'sys-perms': '/system/permissions',
  'sys-menus': '/system/menus',
  'sys-depts': '/system/depts',
  'sys-dicts': '/system/dicts',
  'sys-params': '/system/params',
  'sys-logs': '/system/logs',
}
const pathToKey = Object.fromEntries(Object.entries(keyToPath).map(([k, v]) => [v, k]))

function onMenuClick({ key }) {
  if (keyToPath[key]) router.push(keyToPath[key])
}

watch(
  () => route.path,
  (p) => {
    if (p === '/' || p === '') {
      selectedKeys.value = ['dashboard']
      openKeys.value = []
      return
    }
    const key = pathToKey[p]
    if (key) selectedKeys.value = [key]
    if (bizMenuKeys.includes(key)) openKeys.value = ['business']
    else if (sysMenuKeys.includes(key)) openKeys.value = ['system']
  },
  { immediate: true }
)

// 修改密码
const pwdVisible = ref(false)
const pwdLoading = ref(false)
const pwdForm = ref({ old_password: '', new_password: '' })

function onUserMenu({ key }) {
  if (key === 'password') {
    pwdForm.value = { old_password: '', new_password: '' }
    pwdVisible.value = true
  } else if (key === 'logout') {
    store.dispatch('auth/logout').then(() => router.replace('/login'))
  }
}
async function submitPwd() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    message.warning('请填写完整')
    return
  }
  pwdLoading.value = true
  try {
    await api.changePassword(pwdForm.value)
    message.success('密码已修改，请重新登录')
    pwdVisible.value = false
    await store.dispatch('auth/logout')
    router.replace('/login')
  } catch (e) {
    message.error(e.message)
  } finally {
    pwdLoading.value = false
  }
}

onMounted(async () => {
  if (!store.state.auth.loaded) {
    await store.dispatch('auth/fetchMe')
  }
})
</script>

<style scoped>
.main-layout {
  height: 100vh;
}
.logo {
  height: 48px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.05);
}
.header {
  background: #fff;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}
.header-title {
  font-size: 16px;
  font-weight: 600;
  margin-right: auto;
}
.user-zone {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 0 8px;
}
.user-name {
  font-size: 14px;
}
.content {
  margin: 16px;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  overflow: auto;
}
.footer {
  text-align: center;
  color: #999;
  font-size: 12px;
}
</style>
