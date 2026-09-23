<template>
  <div>
    <div class="toolbar">
      <a-space>
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-button type="primary" v-if="hasPerm('system:dept:create')" @click="openCreate(null)"><template #icon><plus-outlined /></template>新建部门</a-button>
    </div>
    <a-table :columns="cols" :data-source="tree" rowKey="id" :pagination="false" size="middle" :defaultExpandAllRows="true">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-if="hasPerm('system:dept:create')" size="small" @click="openCreate(record)">新增子部门</a-button>
            <a-button v-if="hasPerm('system:dept:update')" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm v-if="hasPerm('system:dept:delete')" title="确认删除？" @confirm="remove(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="visible" :title="editing.id ? '编辑部门' : '新建部门'" @ok="submit" :confirm-loading="submitting">
      <a-form layout="vertical">
        <a-form-item label="上级部门">
          <a-tree-select v-model:value="editing.parent_id" :tree-data="deptTreeForSelect" :fieldNames="{ label: 'name', value: 'id', children: 'children' }" allow-clear placeholder="顶级部门" tree-default-expand-all />
        </a-form-item>
        <a-form-item label="部门编码" required>
          <a-input v-model:value="editing.code" :disabled="!!editing.id" />
        </a-form-item>
        <a-form-item label="部门名称" required>
          <a-input v-model:value="editing.name" />
        </a-form-item>
        <a-form-item label="排序">
          <a-input-number v-model:value="editing.sort" />
        </a-form-item>
        <a-form-item label="启用">
          <a-switch v-model:checked="editing.enabled" />
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

const tree = ref([])
const cols = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '编码', dataIndex: 'code', key: 'code' },
  { title: '排序', dataIndex: 'sort', key: 'sort', width: 80 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 80, customRender: ({ text }) => (text ? '是' : '否') },
  { title: '操作', key: 'action', width: 240 },
]
const deptTreeForSelect = computed(() => tree.value)

const visible = ref(false)
const submitting = ref(false)
const editing = ref({})

async function load() {
  try {
    tree.value = await api.deptTree()
  } catch (e) {
    message.error(e.message)
  }
}
function openCreate(parent) {
  editing.value = { parent_id: parent?.id || null, code: '', name: '', sort: 0, enabled: true }
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
      await api.updateDept(editing.value.id, { name: editing.value.name, parent_id: editing.value.parent_id, sort: editing.value.sort, enabled: editing.value.enabled })
    } else {
      await api.createDept(editing.value)
    }
    message.success('保存成功')
    visible.value = false
    load()
  } catch (e) { message.error(e.message) } finally { submitting.value = false }
}
async function remove(r) {
  try { await api.deleteDept(r.id); message.success('已删除'); load() } catch (e) { message.error(e.message) }
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
</style>
