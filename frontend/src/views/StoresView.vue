<template>
  <div>
    <a-page-header title="门店管理" sub-title="维护门店基础数据与线路映射">
      <template #extra>
        <a-button type="primary" @click="showForm = true"><plus-outlined /> 新增门店</a-button>
      </template>
    </a-page-header>
    <a-table :columns="columns" :data-source="stores" :loading="loading" row-key="id" :pagination="{ pageSize: 20 }" size="small">
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'terrain_type'">
          <a-tag :color="terrainColor(record.terrain_type)">{{ terrainLabel(record.terrain_type) }}</a-tag>
        </template>
        <template v-if="column.dataIndex === 'time_window'">
          <a-tag>{{ timeWindowLabel(record.time_window) }}</a-tag>
        </template>
        <template v-if="column.dataIndex === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="showForm" title="新增门店" @ok="onSubmit" :confirm-loading="submitting">
      <a-form :label-col="{ span: 6 }">
        <a-form-item label="门店编码" required><a-input v-model:value="form.id" /></a-form-item>
        <a-form-item label="门店名称" required><a-input v-model:value="form.name" /></a-form-item>
        <a-form-item label="地址"><a-input v-model:value="form.address" /></a-form-item>
        <a-form-item label="地形">
          <a-select v-model:value="form.terrain_type">
            <a-select-option value="normal">普通</a-select-option>
            <a-select-option value="mid">中控</a-select-option>
            <a-select-option value="strict">严控</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="时段">
          <a-select v-model:value="form.time_window">
            <a-select-option value="any">不限</a-select-option>
            <a-select-option value="AM">上午</a-select-option>
            <a-select-option value="PM">下午</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="优先级"><a-input-number v-model:value="form.priority" :min="1" :max="9" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { api } from '../api'

const stores = ref([])
const loading = ref(false)
const showForm = ref(false)
const submitting = ref(false)
const form = reactive({ id: '', name: '', address: '', terrain_type: 'normal', time_window: 'any', priority: 5 })

const columns = [
  { title: '门店编码', dataIndex: 'id', width: 120 },
  { title: '门店名称', dataIndex: 'name' },
  { title: '地形', dataIndex: 'terrain_type', width: 100 },
  { title: '时段', dataIndex: 'time_window', width: 100 },
  { title: '优先级', dataIndex: 'priority', width: 80 },
  { title: '地址', dataIndex: 'address' },
  { title: '状态', dataIndex: 'enabled', width: 80 },
]

function terrainColor(t) { return { normal: 'green', mid: 'orange', strict: 'red' }[t] || 'default' }
function terrainLabel(t) { return { normal: '普通', mid: '中控', strict: '严控' }[t] || t }
function timeWindowLabel(t) { return { any: '不限', AM: '上午', PM: '下午' }[t] || t }

async function load() {
  loading.value = true
  try { stores.value = await api.listStores() }
  catch (e) { message.error('加载失败: ' + e.message) }
  finally { loading.value = false }
}
async function onSubmit() {
  if (!form.id || !form.name) { message.warning('请填写编码与名称'); return }
  submitting.value = true
  try {
    await api.upsertStore({ ...form, enabled: true, route_mappings: [] })
    message.success('已保存')
    showForm.value = false
    form.id = ''; form.name = ''; form.address = ''
    await load()
  } catch (e) { message.error('保存失败: ' + e.message) }
  finally { submitting.value = false }
}
onMounted(load)
</script>
