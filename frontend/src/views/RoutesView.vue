<template>
  <div>
    <a-page-header title="线路管理" sub-title="维护配送线路与地形限制" />
    <a-table :columns="columns" :data-source="routes" :loading="loading" row-key="id" :pagination="false" size="small">
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'terrain_type'">
          <a-tag :color="terrainColor(record.terrain_type)">{{ terrainLabel(record.terrain_type) }}</a-tag>
        </template>
        <template v-if="column.dataIndex === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { api } from '../api'

const routes = ref([])
const loading = ref(false)

const columns = [
  { title: '线路编码', dataIndex: 'id', width: 120 },
  { title: '线路名称', dataIndex: 'name' },
  { title: '地形', dataIndex: 'terrain_type', width: 100 },
  { title: '描述', dataIndex: 'description' },
  { title: '状态', dataIndex: 'enabled', width: 80 },
]

function terrainColor(t) { return { normal: 'green', mid: 'orange', strict: 'red' }[t] || 'default' }
function terrainLabel(t) { return { normal: '普通', mid: '中控', strict: '严控' }[t] || t }

async function load() {
  loading.value = true
  try { routes.value = await api.listRoutes() }
  catch (e) { message.error('加载失败: ' + e.message) }
  finally { loading.value = false }
}
onMounted(load)
</script>
