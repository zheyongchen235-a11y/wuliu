<template>
  <div>
    <div class="toolbar">
      <a-space>
        <a-input v-model:value="filters.keyword" placeholder="用户名/昵称/邮箱" allow-clear style="width:220px" @pressEnter="load" />
        <a-select v-model:value="filters.dept_id" placeholder="部门" allow-clear style="width:160px" @change="load">
          <a-select-option v-for="d in flatDepts" :key="d.id">{{ d.name }}</a-select-option>
        </a-select>
        <a-select v-model:value="filters.enabled" placeholder="状态" allow-clear style="width:100px" @change="load">
          <a-select-option :value="true">启用</a-select-option>
          <a-select-option :value="false">禁用</a-select-option>
        </a-select>
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-button type="primary" v-if="hasPerm('system:user:create')" @click="openCreate"><template #icon><plus-outlined /></template>新建用户</a-button>
    </div>
    <a-table :columns="cols" :data-source="rows" rowKey="id" :pagination="pager" size="middle" @change="onPage">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '禁用' }}</a-tag>
        </template>
        <template v-if="column.key === 'is_super'">
          <a-tag v-if="record.is_super" color="red">超管</a-tag>
          <span v-else>{{ (record.role_codes || []).join(',') }}</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-if="hasPerm('system:user:update')" size="small" @click="openEdit(record)">编辑</a-button>
            <a-button v-if="hasPerm('system:user:reset')" size="small" @click="openReset(record)">重置密码</a-button>
            <a-popconfirm v-if="hasPerm('system:user:delete')" title="确认删除？" @confirm="remove(record)">
              <a-button size="small" danger :disabled="record.username === 'admin'">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="visible" :title="editing.id ? '编辑用户' : '新建用户'" @ok="submit" :confirm-loading="submitting" width="600px">
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="用户名" required>
              <a-input v-model:value="editing.username" :disabled="!!editing.id" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="昵称"><a-input v-model:value="editing.nickname" /></a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12"><a-form-item label="邮箱"><a-input v-model:value="editing.email" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="手机"><a-input v-model:value="editing.phone" /></a-form-item></a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="部门">
              <a-select v-model:value="editing.dept_id" allow-clear>
                <a-select-option v-for="d in flatDepts" :key="d.id">{{ d.name }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="角色">
              <a-select v-model:value="editing.role_ids" mode="multiple" allow-clear>
                <a-select-option v-for="r in roles" :key="r.id">{{ r.name }}（{{ r.code }}）</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12" v-if="!editing.id">
          <a-col :span="12"><a-form-item label="密码" required><a-input-password v-model:value="editing.password" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="超级管理员"><a-switch v-model:checked="editing.is_super" :disabled="editing.username === 'admin'" /></a-form-item>
        <a-form-item label="启用"><a-switch v-model:checked="editing.enabled" /></a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="resetVisible" title="重置密码" @ok="submitReset" :confirm-loading="resetSubmitting">
      <a-form layout="vertical">
        <a-form-item :label="`重置 ${resetTarget?.username} 的密码`" required>
          <a-input-password v-model:value="resetForm.new_password" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useStore } from 'vuex'
import { message } from 'ant-design-vue'
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { api } from '../../api'

const store = useStore()
const hasPerm = (c) => store.getters['auth/hasPerm'](c)

const filters = ref({ keyword: '', dept_id: undefined, enabled: undefined })
const rows = ref([])
const pager = ref({ current: 1, pageSize: 20, total: 0 })
const depts = ref([])
const roles = ref([])
const flatDepts = computed(() => {
  const out = []
  const walk = (list, prefix = '') => {
    list.forEach((d) => {
      out.push({ ...d, name: prefix + d.name })
      if (d.children) walk(d.children, prefix + '  └ ')
    })
  }
  walk(depts.value)
  return out
})

const cols = [
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '昵称', dataIndex: 'nickname', key: 'nickname' },
  { title: '部门', dataIndex: 'dept_name', key: 'dept_name' },
  { title: '角色', key: 'is_super' },
  { title: '状态', key: 'enabled', width: 80 },
  { title: '最近登录', dataIndex: 'last_login_at', key: 'last_login_at', ellipsis: true },
  { title: '操作', key: 'action', width: 260 },
]

const visible = ref(false)
const submitting = ref(false)
const editing = ref({})

const resetVisible = ref(false)
const resetSubmitting = ref(false)
const resetTarget = ref(null)
const resetForm = ref({ new_password: '' })

async function load() {
  try {
    const [data, d, r] = await Promise.all([
      api.listUsers({ page: pager.value.current, page_size: pager.value.pageSize, keyword: filters.value.keyword, dept_id: filters.value.dept_id, enabled: filters.value.enabled }),
      api.deptTree(),
      api.listRoles(),
    ])
    rows.value = data.items
    pager.value.total = data.total
    depts.value = d
    roles.value = r
  } catch (e) { message.error(e.message) }
}
function onPage(p) {
  pager.value.current = p.current
  pager.value.pageSize = p.pageSize
  load()
}
function openCreate() {
  editing.value = { username: '', nickname: '', email: '', phone: '', dept_id: undefined, role_ids: [], password: '', is_super: false, enabled: true }
  visible.value = true
}
function openEdit(r) {
  editing.value = { ...r, role_ids: [...(r.role_ids || [])], password: '' }
  visible.value = true
}
async function submit() {
  if (!editing.value.username) { message.warning('请填写用户名'); return }
  if (!editing.value.id && !editing.value.password) { message.warning('请填写密码'); return }
  submitting.value = true
  try {
    if (editing.value.id) {
      await api.updateUser(editing.value.id, {
        nickname: editing.value.nickname, email: editing.value.email, phone: editing.value.phone,
        dept_id: editing.value.dept_id, role_ids: editing.value.role_ids, is_super: editing.value.is_super, enabled: editing.value.enabled,
      })
    } else {
      await api.createUser(editing.value)
    }
    message.success('保存成功')
    visible.value = false
    load()
  } catch (e) { message.error(e.message) } finally { submitting.value = false }
}
function openReset(r) {
  resetTarget.value = r
  resetForm.value = { new_password: '' }
  resetVisible.value = true
}
async function submitReset() {
  if (!resetForm.value.new_password) { message.warning('请输入新密码'); return }
  resetSubmitting.value = true
  try {
    await api.resetUserPassword(resetTarget.value.id, resetForm.value)
    message.success('密码已重置')
    resetVisible.value = false
  } catch (e) { message.error(e.message) } finally { resetSubmitting.value = false }
}
async function remove(r) {
  try { await api.deleteUser(r.id); message.success('已删除'); load() } catch (e) { message.error(e.message) }
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
</style>
