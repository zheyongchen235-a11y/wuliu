<template>
  <div>
    <div class="toolbar">
      <a-space>
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-button type="primary" v-if="hasPerm('system:menu:create')" @click="openCreate(null)"><template #icon><plus-outlined /></template>新建菜单</a-button>
    </div>
    <a-table :columns="cols" :data-source="tree" rowKey="id" :pagination="false" size="middle" :defaultExpandAllRows="true">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'type'">
          <a-tag :color="record.type === 'catalog' ? 'blue' : record.type === 'button' ? 'orange' : 'green'">{{ record.type }}</a-tag>
        </template>
        <template v-if="column.key === 'visible'">
          <a-tag :color="record.visible ? 'green' : 'default'">{{ record.visible ? '显示' : '隐藏' }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-if="hasPerm('system:menu:create')" size="small" @click="openCreate(record)">新增子菜单</a-button>
            <a-button v-if="hasPerm('system:menu:update')" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm v-if="hasPerm('system:menu:delete')" title="确认删除？" @confirm="remove(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="visible" :title="editing.id ? '编辑菜单' : '新建菜单'" @ok="submit" :confirm-loading="submitting" width="600px">
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="上级菜单">
              <a-tree-select v-model:value="editing.parent_id" :tree-data="menuTreeForSelect" :fieldNames="{ label: 'name', value: 'id', children: 'children' }" allow-clear placeholder="顶级菜单" tree-default-expand-all />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="类型">
              <a-radio-group v-model:value="editing.type">
                <a-radio value="catalog">目录</a-radio>
                <a-radio value="menu">菜单</a-radio>
                <a-radio value="button">按钮</a-radio>
              </a-radio-group>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12"><a-form-item label="名称" required><a-input v-model:value="editing.name" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="图标"><a-input v-model:value="editing.icon" placeholder="如 SettingOutlined" /></a-form-item></a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12"><a-form-item label="路由路径"><a-input v-model:value="editing.path" placeholder="/system/users" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="组件"><a-input v-model:value="editing.component" placeholder="system/UsersView" /></a-form-item></a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12"><a-form-item label="权限编码"><a-input v-model:value="editing.permission_code" placeholder="system:user:list" /></a-form-item></a-col>
          <a-col :span="6"><a-form-item label="排序"><a-input-number v-model:value="editing.sort" style="width:100%" /></a-form-item></a-col>
          <a-col :span="6">
            <a-form-item label="显示">
              <a-switch v-model:checked="editing.visible" />
            </a-form-item>
          </a-col>
        </a-row>
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

const tree = ref([])
const menuTreeForSelect = computed(() => tree.value)
const cols = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '类型', key: 'type', width: 90 },
  { title: '路径', dataIndex: 'path', key: 'path', ellipsis: true },
  { title: '组件', dataIndex: 'component', key: 'component', ellipsis: true },
  { title: '权限码', dataIndex: 'permission_code', key: 'permission_code', ellipsis: true },
  { title: '排序', dataIndex: 'sort', key: 'sort', width: 70 },
  { title: '显示', key: 'visible', width: 80 },
  { title: '操作', key: 'action', width: 240 },
]

const visible = ref(false)
const submitting = ref(false)
const editing = ref({})

async function load() {
  try { tree.value = await api.menuTree() } catch (e) { message.error(e.message) }
}
function openCreate(parent) {
  editing.value = { parent_id: parent?.id || null, name: '', path: '', component: '', icon: '', type: 'menu', permission_code: '', sort: 0, visible: true, keep_alive: false }
  visible.value = true
}
function openEdit(r) {
  editing.value = { ...r }
  visible.value = true
}
async function submit() {
  if (!editing.value.name) { message.warning('请填写名称'); return }
  submitting.value = true
  try {
    if (editing.value.id) {
      const { id, ...rest } = editing.value
      await api.updateMenu(id, rest)
    } else {
      await api.createMenu(editing.value)
    }
    message.success('保存成功')
    visible.value = false
    load()
  } catch (e) { message.error(e.message) } finally { submitting.value = false }
}
async function remove(r) {
  try { await api.deleteMenu(r.id); message.success('已删除'); load() } catch (e) { message.error(e.message) }
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
</style>
