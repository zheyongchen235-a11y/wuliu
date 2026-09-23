<template>
  <div>
    <div class="toolbar">
      <a-space>
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-button type="primary" v-if="hasPerm('system:role:create')" @click="openCreate"><template #icon><plus-outlined /></template>新建角色</a-button>
    </div>
    <a-table :columns="cols" :data-source="rows" rowKey="id" :pagination="false" size="middle">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '禁用' }}</a-tag>
        </template>
        <template v-if="column.key === 'data_scope'">
          {{ scopeLabel(record.data_scope) }}
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-if="hasPerm('system:role:update')" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm v-if="hasPerm('system:role:delete')" title="确认删除？" @confirm="remove(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="visible" :title="editing.id ? '编辑角色' : '新建角色'" @ok="submit" :confirm-loading="submitting" width="720px">
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :span="8"><a-form-item label="角色编码" required><a-input v-model:value="editing.code" :disabled="!!editing.id" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="角色名称" required><a-input v-model:value="editing.name" /></a-form-item></a-col>
          <a-col :span="8">
            <a-form-item label="数据范围">
              <a-select v-model:value="editing.data_scope">
                <a-select-option value="all">全部</a-select-option>
                <a-select-option value="dept">本部门</a-select-option>
                <a-select-option value="self">本人</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="描述"><a-textarea v-model:value="editing.description" :rows="2" /></a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="权限分配">
              <a-select v-model:value="editing.permission_ids" mode="multiple" :options="permOptions" :fieldNames="{ label: 'name', value: 'id' }" allow-clear show-search optionFilterProp="name" style="width:100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="菜单分配">
              <a-tree v-model:checkedKeys="editing.menu_ids" :tree-data="menuTreeForRole" :fieldNames="{ title: 'name', key: 'id', children: 'children' }" checkable default-expand-all />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="启用"><a-switch v-model:checked="editing.enabled" /></a-form-item>
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

const rows = ref([])
const perms = ref([])
const menuTree = ref([])
const menuTreeForRole = computed(() => menuTree.value)
const permOptions = computed(() => perms.value)
const cols = [
  { title: '编码', dataIndex: 'code', key: 'code' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '数据范围', key: 'data_scope', width: 100 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '启用', key: 'enabled', width: 80 },
  { title: '操作', key: 'action', width: 180 },
]
function scopeLabel(s) { return { all: '全部', dept: '本部门', self: '本人' }[s] || s }

const visible = ref(false)
const submitting = ref(false)
const editing = ref({})

async function load() {
  try {
    const [r, p, m] = await Promise.all([api.listRoles(), api.listPermissions(), api.menuTree()])
    rows.value = r
    perms.value = p
    menuTree.value = m
  } catch (e) { message.error(e.message) }
}
function openCreate() {
  editing.value = { code: '', name: '', data_scope: 'self', description: '', permission_ids: [], menu_ids: [], enabled: true, sort: 0 }
  visible.value = true
}
function openEdit(r) {
  editing.value = { ...r, permission_ids: [...(r.permission_ids || [])], menu_ids: [...(r.menu_ids || [])] }
  visible.value = true
}
async function submit() {
  if (!editing.value.code || !editing.value.name) { message.warning('请填写编码和名称'); return }
  submitting.value = true
  try {
    const payload = {
      name: editing.value.name,
      description: editing.value.description,
      data_scope: editing.value.data_scope,
      enabled: editing.value.enabled,
      sort: editing.value.sort || 0,
      permission_ids: editing.value.permission_ids,
      menu_ids: editing.value.menu_ids,
    }
    if (editing.value.id) {
      await api.updateRole(editing.value.id, payload)
    } else {
      await api.createRole({ ...payload, code: editing.value.code })
    }
    message.success('保存成功')
    visible.value = false
    load()
  } catch (e) { message.error(e.message) } finally { submitting.value = false }
}
async function remove(r) {
  try { await api.deleteRole(r.id); message.success('已删除'); load() } catch (e) { message.error(e.message) }
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
</style>
