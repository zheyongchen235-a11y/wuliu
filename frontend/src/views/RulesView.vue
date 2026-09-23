<template>
  <div>
    <a-page-header title="规则配置中心" sub-title="地形规则 / 趟次规则 / 装载规则 / 约束配置版本" />

    <a-tabs v-model:activeKey="tab">
      <a-tab-pane key="terrain" tab="地形规则">
        <a-table :columns="terrainCols" :data-source="terrainRules" row-key="id" :pagination="false" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'allowed_vehicle_types'">
              <a-tag v-for="v in record.allowed_vehicle_types" :key="v">{{ vehicleTypeLabel(v) }}</a-tag>
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="trip" tab="趟次规则">
        <a-table :columns="tripCols" :data-source="tripRules" row-key="id" :pagination="false" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'vehicle_type'">{{ vehicleTypeLabel(record.vehicle_type) }}</template>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="load" tab="装载规则">
        <a-table :columns="loadCols" :data-source="loadRules" row-key="id" :pagination="false" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'vehicle_type'">{{ vehicleTypeLabel(record.vehicle_type) }}</template>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="constraints" tab="约束配置版本">
        <a-table :columns="constraintCols" :data-source="constraints" row-key="id" :pagination="false" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'is_active'">
              <a-tag :color="record.is_active ? 'green' : 'default'">{{ record.is_active ? '激活' : '未激活' }}</a-tag>
            </template>
            <template v-if="column.dataIndex === 'action'">
              <a-button size="small" type="link" @click="showConstraint(record)">查看</a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="detailVisible" :title="current && `约束配置 ${current.version}`" width="800px" :footer="null">
      <a-tabs v-model:activeKey="detailTab">
        <a-tab-pane key="hard" tab="硬约束">
          <pre style="background: #f5f5f5; padding: 12px; font-size: 12px; overflow: auto">{{ JSON.stringify(current && current.hard_constraints, null, 2) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="soft" tab="软约束">
          <pre style="background: #f5f5f5; padding: 12px; font-size: 12px; overflow: auto">{{ JSON.stringify(current && current.soft_constraints, null, 2) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="weights" tab="评分权重">
          <pre style="background: #f5f5f5; padding: 12px; font-size: 12px; overflow: auto">{{ JSON.stringify(current && current.weights, null, 2) }}</pre>
        </a-tab-pane>
      </a-tabs>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { api } from '../api'

const tab = ref('terrain')
const terrainRules = ref([])
const tripRules = ref([])
const loadRules = ref([])
const constraints = ref([])
const detailVisible = ref(false)
const current = ref(null)
const detailTab = ref('hard')

const terrainCols = [
  { title: '地形编码', dataIndex: 'id' },
  { title: '地形', dataIndex: 'terrain_type' },
  { title: '描述', dataIndex: 'description' },
  { title: '允许车型', dataIndex: 'allowed_vehicle_types' },
]
const tripCols = [
  { title: '车型', dataIndex: 'vehicle_type' },
  { title: '日趟次', dataIndex: 'daily_trips', width: 90 },
  { title: '上午', dataIndex: 'am_trips', width: 90 },
  { title: '下午', dataIndex: 'pm_trips', width: 90 },
]
const loadCols = [
  { title: '车型', dataIndex: 'vehicle_type' },
  { title: '最低装载', dataIndex: 'min_load' },
  { title: '最高装载', dataIndex: 'max_load' },
]
const constraintCols = [
  { title: '版本', dataIndex: 'version', width: 100 },
  { title: '名称', dataIndex: 'name' },
  { title: '描述', dataIndex: 'description' },
  { title: '状态', dataIndex: 'is_active', width: 90 },
  { title: '操作', dataIndex: 'action', width: 80 },
]

function vehicleTypeLabel(t) { return { '4m2': '四米二', big: '大包', small: '小包' }[t] || t }

async function load() {
  try {
    const [t, tr, l, c] = await Promise.all([
      api.listTerrainRules(), api.listTripRules(), api.listLoadRules(), api.listConstraints(),
    ])
    terrainRules.value = t
    tripRules.value = tr
    loadRules.value = l
    constraints.value = c
  } catch (e) { message.error('加载失败: ' + e.message) }
}
function showConstraint(c) { current.value = c; detailVisible.value = true }
onMounted(load)
</script>
