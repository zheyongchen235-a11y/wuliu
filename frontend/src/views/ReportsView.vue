<template>
  <div>
    <a-page-header title="报表中心" sub-title="出勤 / 装载率 / 趟次达成">
      <template #extra>
        <a-date-picker v-model:value="date" value-format="YYYY-MM-DD" @change="loadAll" />
      </template>
    </a-page-header>

    <a-row :gutter="16" style="margin-top: 16px">
      <a-col :span="8">
        <a-card title="车辆出勤报表" size="small">
          <a-table :columns="attCols" :data-source="attendance" :pagination="false" size="small" row-key="vehicle_type">
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'vehicle_type'">{{ vehicleTypeLabel(record.vehicle_type) }}</template>
              <template v-if="column.dataIndex === 'attendance_rate'">{{ (record.attendance_rate * 100).toFixed(1) }}%</template>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="趟次达成报表" size="small">
          <a-table :columns="tripCols" :data-source="trips" :pagination="false" size="small" row-key="vehicle_type">
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'vehicle_type'">{{ vehicleTypeLabel(record.vehicle_type) }}</template>
              <template v-if="column.dataIndex === 'achievement_rate'">{{ (record.achievement_rate * 100).toFixed(1) }}%</template>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="装载率报表（前 20 趟）" size="small">
          <a-table :columns="loadCols" :data-source="loadRates.slice(0, 20)" :pagination="false" size="small" row-key="vehicle_id">
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'vehicle_type'">{{ vehicleTypeLabel(record.vehicle_type) }}</template>
              <template v-if="column.dataIndex === 'load_rate'">{{ (record.load_rate * 100).toFixed(1) }}%</template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import { api } from '../api'

const date = ref(dayjs().format('YYYY-MM-DD'))
const attendance = ref([])
const trips = ref([])
const loadRates = ref([])

const attCols = [
  { title: '车型', dataIndex: 'vehicle_type' },
  { title: '总台数', dataIndex: 'total_vehicles' },
  { title: '出勤', dataIndex: 'used_vehicles' },
  { title: '闲置', dataIndex: 'idle_vehicles' },
  { title: '出勤率', dataIndex: 'attendance_rate' },
]
const tripCols = [
  { title: '车型', dataIndex: 'vehicle_type' },
  { title: '计划趟次', dataIndex: 'planned_trips' },
  { title: '完成趟次', dataIndex: 'completed_trips' },
  { title: '达成率', dataIndex: 'achievement_rate' },
]
const loadCols = [
  { title: '车辆', dataIndex: 'vehicle_id' },
  { title: '车型', dataIndex: 'vehicle_type', width: 80 },
  { title: '趟次', dataIndex: 'trip_no', width: 60 },
  { title: '装载', dataIndex: 'load_amount', width: 80 },
  { title: '上限', dataIndex: 'max_load', width: 80 },
  { title: '装载率', dataIndex: 'load_rate' },
]

function vehicleTypeLabel(t) { return { '4m2': '四米二', big: '大包', small: '小包' }[t] || t }

async function loadAll() {
  if (!date.value) return
  try {
    const [a, t, l] = await Promise.all([
      api.attendanceReport(date.value),
      api.tripAchievementReport(date.value),
      api.loadRateReport(date.value),
    ])
    attendance.value = a
    trips.value = t
    loadRates.value = l
  } catch (e) { message.error('加载失败: ' + e.message) }
}
onMounted(loadAll)
</script>
