<template>
  <div class="dashboard">
    <a-page-header title="调度看板" sub-title="车辆智能调度 Agent 全局视图" />

    <a-row :gutter="16" style="margin-top: 16px">
      <a-col :span="6">
        <a-card>
          <a-statistic title="今日调度任务" :value="stats.taskTotal" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="进行中" :value="stats.running" :value-style="{ color: '#1677ff' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="等待确认" :value="stats.awaiting" :value-style="{ color: '#faad14' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="已完成" :value="stats.completed" :value-style="{ color: '#52c41a' }" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-top: 16px">
      <a-col :span="12">
        <a-card title="车队概览">
          <a-table
            :columns="fleetColumns"
            :data-source="fleetData"
            :pagination="false"
            size="small"
            row-key="vehicle_type"
          />
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="最近任务">
          <a-table
            :columns="taskColumns"
            :data-source="recentTasks"
            :pagination="{ pageSize: 5 }"
            size="small"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'status'">
                <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
              </template>
              <template v-if="column.dataIndex === 'id'">
                <router-link :to="`/tasks/${record.id}`">{{ record.id.slice(0, 8) }}</router-link>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="核心业务约束" style="margin-top: 16px">
      <a-descriptions :column="3" bordered size="small">
        <a-descriptions-item label="四米二">28 台 / 装载 630-800 / 日 2 趟（上午 1 + 下午 1）</a-descriptions-item>
        <a-descriptions-item label="大包">3 台 / 装载 300-420 / 日 2 趟（上午 1 + 下午 1）</a-descriptions-item>
        <a-descriptions-item label="小包">9 台 / 装载 1-300 / 日 4 趟（上午 2 + 下午 2）</a-descriptions-item>
        <a-descriptions-item label="发车规则">达到最低装载量才发车</a-descriptions-item>
        <a-descriptions-item label="时段规则">上午门店上午送，下午门店下午送</a-descriptions-item>
        <a-descriptions-item label="地形规则">普通 / 中控 / 严控 + 车辆能力匹配</a-descriptions-item>
        <a-descriptions-item label="货量不足">优先保障大包、小包日出车次数</a-descriptions-item>
        <a-descriptions-item label="车型优先">多种派车方案优先用四米二</a-descriptions-item>
        <a-descriptions-item label="动态调节">不保障每天 28/3/9 台满勤</a-descriptions-item>
      </a-descriptions>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '../api'

const tasks = ref([])
const fleetData = ref([])

const stats = computed(() => ({
  taskTotal: tasks.value.length,
  running: tasks.value.filter((t) => t.status === 'running' || t.status === 'replanning').length,
  awaiting: tasks.value.filter((t) => t.status === 'awaiting_confirmation').length,
  completed: tasks.value.filter((t) => t.status === 'completed').length,
}))

const recentTasks = computed(() => tasks.value.slice(0, 10))

const fleetColumns = [
  { title: '车型', dataIndex: 'vehicle_type', customRender: ({ text }) => vehicleTypeLabel(text) },
  { title: '总台数', dataIndex: 'total' },
  { title: '装载范围', dataIndex: 'load_range' },
  { title: '日趟次', dataIndex: 'trips' },
  { title: '地形能力', dataIndex: 'terrain' },
]

const taskColumns = [
  { title: '任务ID', dataIndex: 'id', width: 120 },
  { title: '调度日期', dataIndex: 'schedule_date', width: 120 },
  { title: '时段', dataIndex: 'time_window', width: 80 },
  { title: '状态', dataIndex: 'status', width: 140 },
  { title: '当前节点', dataIndex: 'current_node' },
]

function vehicleTypeLabel(t) {
  return { '4m2': '四米二', big: '大包', small: '小包' }[t] || t
}

function statusColor(s) {
  return {
    created: 'default',
    running: 'blue',
    awaiting_confirmation: 'orange',
    confirmed: 'cyan',
    dispatched: 'purple',
    completed: 'green',
    failed: 'red',
    replanning: 'gold',
  }[s] || 'default'
}

function statusLabel(s) {
  return {
    created: '已创建',
    running: '运行中',
    awaiting_confirmation: '等待确认',
    confirmed: '已确认',
    dispatched: '已下发',
    completed: '已完成',
    failed: '失败',
    replanning: '重排中',
  }[s] || s
}

onMounted(async () => {
  try {
    tasks.value = await api.listTasks({ limit: 50 })
  } catch (e) {
    // ignore
  }
  fleetData.value = [
    { vehicle_type: '4m2', total: 28, load_range: '630-800', trips: '2 (1+1)', terrain: '全能去' },
    { vehicle_type: 'big', total: 3, load_range: '300-420', trips: '2 (1+1)', terrain: '大小包能去' },
    { vehicle_type: 'small', total: 9, load_range: '1-300', trips: '4 (2+2)', terrain: '小包能去' },
  ]
})
</script>

<style scoped>
.dashboard {
  padding-bottom: 16px;
}
</style>
