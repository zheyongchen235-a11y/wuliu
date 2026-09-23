<template>
  <div>
    <div class="toolbar">
      <a-space wrap>
        <a-input v-model:value="filters.keyword" placeholder="操作/URL/错误" allow-clear style="width:200px" @pressEnter="load" />
        <a-input v-model:value="filters.username" placeholder="用户名" allow-clear style="width:140px" @pressEnter="load" />
        <a-input v-model:value="filters.module" placeholder="模块" allow-clear style="width:120px" @pressEnter="load" />
        <a-select v-model:value="filters.status" placeholder="状态" allow-clear style="width:120px" @change="load">
          <a-select-option :value="200">2xx 成功</a-select-option>
          <a-select-option :value="2">非 2xx 异常</a-select-option>
        </a-select>
        <a-button @click="load"><template #icon><reload-outlined /></template>刷新</a-button>
      </a-space>
      <a-popconfirm v-if="hasPerm('system:log:delete')" title="确认清空全部日志？此操作不可恢复" @confirm="clearAll">
        <a-button danger>清空日志</a-button>
      </a-popconfirm>
    </div>
    <a-table :columns="cols" :data-source="rows" rowKey="id" :pagination="pager" @change="onPage" size="middle" :scroll="{ x: 1100 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'method'">
          <a-tag :color="methodColor(record.method)">{{ record.method }}</a-tag>
        </template>
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status >= 200 && record.status < 300 ? 'green' : 'red'">{{ record.status }}</a-tag>
        </template>
        <template v-if="column.key === 'latency'">
          <span>{{ record.latency_ms }} ms</span>
        </template>
        <template v-if="column.key === 'created_at'">
          <span>{{ fmtDate(record.created_at) }}</span>
        </template>
        <template v-if="column.key === 'action_col'">
          <a-popconfirm v-if="hasPerm('system:log:delete')" title="确认删除？" @confirm="remove(record)">
            <a-button size="small" danger>删除</a-button>
          </a-popconfirm>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStore } from 'vuex'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { api } from '../../api'

const store = useStore()
const hasPerm = (c) => store.getters['auth/hasPerm'](c)

const filters = ref({ keyword: '', username: '', module: '', status: undefined })
const rows = ref([])
const pager = ref({ current: 1, pageSize: 20, total: 0 })
const cols = [
  { title: '时间', key: 'created_at', width: 170 },
  { title: '用户', dataIndex: 'username', key: 'username', width: 110 },
  { title: '模块', dataIndex: 'module', key: 'module', width: 100 },
  { title: '操作', dataIndex: 'action', key: 'action', width: 90 },
  { title: '方法', key: 'method', width: 80 },
  { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
  { title: 'IP', dataIndex: 'ip', key: 'ip', width: 120 },
  { title: '状态', key: 'status', width: 80 },
  { title: '耗时', key: 'latency', width: 90 },
  { title: '操作', key: 'action_col', width: 90, fixed: 'right' },
]

function methodColor(m) {
  return { GET: 'blue', POST: 'green', PUT: 'orange', DELETE: 'red' }[m] || 'default'
}
function fmtDate(s) {
  if (!s) return ''
  try {
    const d = new Date(s)
    if (isNaN(d.getTime())) return s
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return s
  }
}

async function load() {
  try {
    const data = await api.listLogs({
      keyword: filters.value.keyword || undefined,
      username: filters.value.username || undefined,
      module: filters.value.module || undefined,
      status: filters.value.status,
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
async function remove(r) {
  try {
    await api.deleteLog(r.id)
    message.success('已删除')
    load()
  } catch (e) {
    message.error(e.message)
  }
}
async function clearAll() {
  try {
    await api.clearLogs()
    message.success('已清空')
    pager.value.current = 1
    load()
  } catch (e) {
    message.error(e.message)
  }
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
</style>
