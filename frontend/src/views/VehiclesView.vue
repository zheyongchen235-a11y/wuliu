<template>
  <div>
    <a-page-header title="车辆管理" sub-title="维护车辆档案与地形能力">
      <template #extra>
        <a-button type="primary" @click="showForm = true"><plus-outlined /> 新增车辆</a-button>
      </template>
    </a-page-header>

    <a-form layout="inline" style="margin-bottom: 16px">
      <a-form-item label="车型">
        <a-select v-model:value="filter.type" style="width: 140px" allow-clear placeholder="全部" @change="load">
          <a-select-option value="4m2">四米二</a-select-option>
          <a-select-option value="big">大包</a-select-option>
          <a-select-option value="small">小包</a-select-option>
        </a-select>
      </a-form-item>
    </a-form>

    <a-table :columns="columns" :data-source="vehicles" :loading="loading" row-key="id" :pagination="{ pageSize: 20 }" size="small">
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'vehicle_type'">{{ vehicleTypeLabel(record.vehicle_type) }}</template>
        <template v-if="column.dataIndex === 'load_range'">{{ record.min_load }} - {{ record.max_load }}</template>
        <template v-if="column.dataIndex === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="showForm" title="新增车辆" @ok="onSubmit" :confirm-loading="submitting">
      <a-form :label-col="{ span: 6 }">
        <a-form-item label="车辆编码" required><a-input v-model:value="form.id" /></a-form-item>
        <a-form-item label="车牌" required><a-input v-model:value="form.plate" /></a-form-item>
        <a-form-item label="车型" required>
          <a-select v-model:value="form.vehicle_type">
            <a-select-option value="4m2">四米二</a-select-option>
            <a-select-option value="big">大包</a-select-option>
            <a-select-option value="small">小包</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="最低装载" required><a-input-number v-model:value="form.min_load" :min="0" /></a-form-item>
        <a-form-item label="最高装载" required><a-input-number v-model:value="form.max_load" :min="0" /></a-form-item>
        <a-form-item label="日趟次"><a-input-number v-model:value="form.max_trips_per_day" :min="1" :max="10" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { api } from '../api'

const vehicles = ref([])
const loading = ref(false)
const showForm = ref(false)
const submitting = ref(false)
const filter = reactive({ type: undefined })
const form = reactive({ id: '', plate: '', vehicle_type: '4m2', min_load: 630, max_load: 800, max_trips_per_day: 2 })

const columns = [
  { title: '车辆编码', dataIndex: 'id' },
  { title: '车牌', dataIndex: 'plate' },
  { title: '车型', dataIndex: 'vehicle_type', width: 100 },
  { title: '装载范围', dataIndex: 'load_range', width: 120 },
  { title: '日趟次', dataIndex: 'max_trips_per_day', width: 90 },
  { title: '司机', dataIndex: 'driver_id', width: 120 },
  { title: '状态', dataIndex: 'status', width: 100 },
]

function vehicleTypeLabel(t) { return { '4m2': '四米二', big: '大包', small: '小包' }[t] || t }
function statusColor(s) { return { available: 'green', maintenance: 'orange', dispatched: 'blue', disabled: 'default' }[s] || 'default' }
function statusLabel(s) { return { available: '可用', maintenance: '维修', dispatched: '已派', disabled: '停用' }[s] || s }

async function load() {
  loading.value = true
  try { vehicles.value = await api.listVehicles({ vehicle_type: filter.type }) }
  catch (e) { message.error('加载失败: ' + e.message) }
  finally { loading.value = false }
}
async function onSubmit() {
  if (!form.id || !form.plate) { message.warning('请填写编码与车牌'); return }
  submitting.value = true
  try {
    const caps = form.vehicle_type === '4m2' ? { normal: true, mid: true, strict: true }
      : form.vehicle_type === 'big' ? { normal: true, mid: true, strict: false }
      : { normal: true, mid: true, strict: true }
    await api.upsertVehicle({ ...form, enabled: true, status: 'available', terrain_capabilities: caps })
    message.success('已保存')
    showForm.value = false
    form.id = ''; form.plate = ''
    await load()
  } catch (e) { message.error('保存失败: ' + e.message) }
  finally { submitting.value = false }
}
onMounted(load)
</script>
