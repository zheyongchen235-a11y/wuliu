<template>
  <div>
    <div class="toolbar">
      <a-space>
        <a-input v-model:value="filters.keyword" placeholder="权限编码/名称" allow-clear style="width:220px" @pressEnter="load" />
        <a-select v-model:value="filters.module" placeholder="模块" allow-clear style="width:160px" @change="load">
          <a-select-option v-for="m in modules" :key="m">{{ m }}</a-select-option>
        </a-select>
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-button type="primary" v-if="hasPerm('system:permission:create')" @click="openCreate"><template #icon><plus-outlined /></template>新建权限</a-button>
    </div>
    <a-table :columns="cols" :data-source="rows" rowKey="id" :pagination="{ pageSize: 20 }" size="middle">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-if="hasPerm('system:permission:update')" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm v-if="hasPerm('system:permission:delete')" title="确认删除？" @confirm="remove(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="visible" :title="editing.id ? '编辑权限' : '新建权限'" @ok="submit" :confirm-loading="submitting">
      <a-form layout="vertical">
        <a-form-item label="权限编码" required>
          <a-input v-model:value="editing.code" :disabled="!!editing.id" placeholder="如 system:user:create" />
        </a-form-item>
        <a-form-item label="名称" required>
          <a-input v-model:value="editing.name" />
        </a-form-item>
        <a-form-item label="模块">
          <a-input v-model:value="editing.module" placeholder="system / business" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="editing.description" :rows="2" />
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

const filters = ref({ keyword: '', module: undefined })
const rows = ref([])
const modules = computed(() => [...new Set(rows.value.map((r) => r.module).filter(Boolean))])
const cols = [
  { title: '编码', dataIndex: 'code', key: 'code' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '模块', dataIndex: 'module', key: 'module' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 180 },
]

const visible = ref(false)
const submitting = ref(false)
const editing = ref({})

async function load() {
  try {
    rows.value = await api.listPermissions({ module: filters.value.module })
    if (filters.value.keyword) {
      const k = filters.value.keyword.toLowerCase()
      rows.value = rows.value.filter((r) => r.code?.toLowerCase().includes(k) || r.name?.toLowerCase().includes(k))
    }
  } catch (e) {
    message.error(e.message)
  }
}
function openCreate() {
  editing.value = { code: '', name: '', module: 'system', description: '' }
  visible.value = true
}
function openEdit(r) {
  editing.value = { ...r }
  visible.value = true
}
async function submit() {
  if (!editing.value.code || !editing.value.name) {
    message.warning('请填写编码和名称')
    return
  }
  submitting.value = true
  try {
    if (editing.value.id) {
      await api.updatePermission(editing.value.id, { name: editing.value.name, module: editing.value.module, description: editing.value.description })
    } else {
      await api.createPermission(editing.value)
    }
    message.success('保存成功')
    visible.value = false
    load()
  } catch (e) {
    message.error(e.message)
  } finally {
    submitting.value = false
  }
}
async function remove(r) {
  try {
    await api.deletePermission(r.id)
    message.success('已删除')
    load()
  } catch (e) {
    message.error(e.message)
  }
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
</style>
