<template>
  <div>
    <div class="toolbar">
      <a-space>
        <a-input v-model:value="filters.keyword" placeholder="参数编码/名称" allow-clear style="width:220px" @pressEnter="load" />
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-button type="primary" v-if="hasPerm('system:param:create')" @click="openCreate"><template #icon><plus-outlined /></template>新建参数</a-button>
    </div>
    <a-table :columns="cols" :data-source="rows" rowKey="id" :pagination="pager" @change="onPage" size="middle">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'type'">
          <a-tag>{{ record.type }}</a-tag>
        </template>
        <template v-if="column.key === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-if="hasPerm('system:param:update')" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm v-if="hasPerm('system:param:delete')" title="确认删除？" @confirm="remove(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="visible" :title="editing.id ? '编辑参数' : '新建参数'" @ok="submit" :confirm-loading="submitting">
      <a-form layout="vertical">
        <a-form-item label="参数编码" required>
          <a-input v-model:value="editing.code" :disabled="!!editing.id" placeholder="如 solver_time_limit" />
        </a-form-item>
        <a-form-item label="参数名称" required>
          <a-input v-model:value="editing.name" />
        </a-form-item>
        <a-form-item label="参数值" required>
          <a-input v-model:value="editing.value" />
        </a-form-item>
        <a-form-item label="类型">
          <a-select v-model:value="editing.type">
            <a-select-option value="string">string</a-select-option>
            <a-select-option value="number">number</a-select-option>
            <a-select-option value="bool">bool</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="editing.remark" />
        </a-form-item>
        <a-form-item label="启用">
          <a-switch v-model:checked="editing.enabled" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStore } from 'vuex'
import { message } from 'ant-design-vue'
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { api } from '../../api'

const store = useStore()
const hasPerm = (c) => store.getters['auth/hasPerm'](c)

const filters = ref({ keyword: '' })
const rows = ref([])
const pager = ref({ current: 1, pageSize: 20, total: 0 })
const cols = [
  { title: '编码', dataIndex: 'code', key: 'code' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '值', dataIndex: 'value', key: 'value', ellipsis: true },
  { title: '类型', key: 'type', width: 90 },
  { title: '备注', dataIndex: 'remark', key: 'remark', ellipsis: true },
  { title: '状态', key: 'enabled', width: 80 },
  { title: '操作', key: 'action', width: 160 },
]

const visible = ref(false)
const submitting = ref(false)
const editing = ref({})

async function load() {
  try {
    const data = await api.listParams({
      keyword: filters.value.keyword || undefined,
      page: pager.value.current,
      page_size: pager.value.pageSize,
    })
    rows.value = data.items || []
    pager.value.total = data.total || 0
  } catch (e) {
    message.error(e.message)
  }
}
function onPage(p) {
  pager.value.current = p.current
  pager.value.pageSize = p.pageSize
  load()
}
function openCreate() {
  editing.value = { code: '', name: '', value: '', type: 'string', remark: '', enabled: true }
  visible.value = true
}
function openEdit(r) {
  editing.value = { ...r }
  visible.value = true
}
async function submit() {
  if (!editing.value.code || !editing.value.name || editing.value.value === '') {
    message.warning('请填写完整')
    return
  }
  submitting.value = true
  try {
    if (editing.value.id) {
      await api.updateParam(editing.value.id, {
        name: editing.value.name,
        value: editing.value.value,
        type: editing.value.type,
        remark: editing.value.remark,
        enabled: editing.value.enabled,
      })
    } else {
      await api.createParam(editing.value)
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
    await api.deleteParam(r.id)
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
