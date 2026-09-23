<template>
  <div>
    <a-page-header title="调度任务" sub-title="创建并跟踪调度任务">
      <template #extra>
        <a-button type="primary" @click="showCreate = true">
          <plus-outlined /> 新建调度任务
        </a-button>
      </template>
    </a-page-header>

    <a-form layout="inline" style="margin: 16px 0">
      <a-form-item label="调度日期">
        <a-date-picker v-model:value="filter.date" value-format="YYYY-MM-DD" allow-clear />
      </a-form-item>
      <a-form-item label="状态">
        <a-select v-model:value="filter.status" style="width: 160px" allow-clear placeholder="全部">
          <a-select-option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item>
        <a-button @click="loadTasks">查询</a-button>
      </a-form-item>
      <a-form-item>
        <a-button @click="loadTasks">刷新</a-button>
      </a-form-item>
    </a-form>

    <a-table
      :columns="columns"
      :data-source="tasks"
      :loading="loading"
      row-key="id"
      :pagination="{ pageSize: 20 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'id'">
          <router-link :to="`/tasks/${record.id}`">{{ record.id.slice(0, 8) }}</router-link>
        </template>
        <template v-if="column.dataIndex === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-if="column.dataIndex === 'action'">
          <a-button size="small" type="link" :disabled="!canStart(record)" @click="onStart(record)">启动</a-button>
          <a-button size="small" type="link" @click="goDetail(record)">详情</a-button>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="showCreate" title="新建调度任务" @ok="onCreate" :confirm-loading="creating">
      <a-form :label-col="{ span: 6 }">
        <a-form-item label="调度日期" required>
          <a-date-picker v-model:value="form.schedule_date" value-format="YYYY-MM-DD" style="width: 100%" />
        </a-form-item>
        <a-form-item label="时段">
          <a-select v-model:value="form.time_window">
            <a-select-option value="all">全部</a-select-option>
            <a-select-option value="AM">上午</a-select-option>
            <a-select-option value="PM">下午</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="规则版本">
          <a-input v-model:value="form.rule_version" placeholder="留空使用当前激活版本" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { api } from '../api'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)

const filter = reactive({ date: undefined, status: undefined })
const form = reactive({ schedule_date: undefined, time_window: 'all', rule_version: '' })

const statusOptions = [
  { value: 'created', label: '已创建' },
  { value: 'running', label: '运行中' },
  { value: 'awaiting_confirmation', label: '等待确认' },
  { value: 'confirmed', label: '已确认' },
  { value: 'dispatched', label: '已下发' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'replanning', label: '重排中' },
]

const columns = [
  { title: '任务ID', dataIndex: 'id', width: 120 },
  { title: '调度日期', dataIndex: 'schedule_date', width: 120 },
  { title: '时段', dataIndex: 'time_window', width: 80 },
  { title: '状态', dataIndex: 'status', width: 140 },
  { title: '当前节点', dataIndex: 'current_node' },
  { title: '规则版本', dataIndex: 'rule_version', width: 100 },
  { title: '重排次数', dataIndex: 'replan_count', width: 90 },
  { title: '创建时间', dataIndex: 'created_at', width: 180 },
  { title: '操作', dataIndex: 'action', width: 140 },
]

function statusColor(s) {
  return { created: 'default', running: 'blue', awaiting_confirmation: 'orange', confirmed: 'cyan',
    dispatched: 'purple', completed: 'green', failed: 'red', replanning: 'gold' }[s] || 'default'
}
function statusLabel(s) {
  return Object.fromEntries(statusOptions.map((o) => [o.value, o.label]))[s] || s
}
function canStart(r) { return r.status === 'created' || r.status === 'failed' }

async function loadTasks() {
  loading.value = true
  try {
    tasks.value = await api.listTasks({ schedule_date: filter.date, status: filter.status, limit: 100 })
  } catch (e) {
    message.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.schedule_date) {
    message.warning('请选择调度日期')
    return
  }
  creating.value = true
  try {
    const payload = { schedule_date: form.schedule_date, time_window: form.time_window }
    if (form.rule_version) payload.rule_version = form.rule_version
    const task = await api.createTask(payload)
    message.success('任务已创建: ' + task.id.slice(0, 8))
    showCreate.value = false
    await loadTasks()
  } catch (e) {
    message.error('创建失败: ' + e.message)
  } finally {
    creating.value = false
  }
}

async function onStart(task) {
  try {
    await api.startTask(task.id)
    message.success('已启动')
    setTimeout(loadTasks, 500)
  } catch (e) {
    message.error('启动失败: ' + e.message)
  }
}

function goDetail(task) {
  router.push(`/tasks/${task.id}`)
}

onMounted(loadTasks)
</script>
