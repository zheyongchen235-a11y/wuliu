<template>
  <div>
    <a-page-header title="客户订单管理" sub-title="微信小程序端订单：查看、调度排车、状态流转">
      <template #extra>
        <a-button @click="load"><reload-outlined /> 刷新</a-button>
      </template>
    </a-page-header>

    <!-- 概览 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="4">
        <a-card size="small"><a-statistic title="订单总数" :value="stats.order_total" /></a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small"><a-statistic title="待支付" :value="stats.order_pending_pay" :value-style="{ color: '#cf1322' }" /></a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small"><a-statistic title="待调度" :value="stats.order_paid" :value-style="{ color: '#d48806' }" /></a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small"><a-statistic title="已排车" :value="stats.order_scheduled" :value-style="{ color: '#1e3c72' }" /></a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small"><a-statistic title="已完成" :value="stats.order_completed" :value-style="{ color: '#389e0d' }" /></a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small">
          <a-statistic title="累计支付(元)" :value="stats.payment_total_amount" :precision="2" :value-style="{ color: '#cf1322' }" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 筛选 -->
    <a-card size="small" style="margin-bottom: 16px">
      <a-form layout="inline">
        <a-form-item label="状态">
          <a-select v-model:value="query.status" style="width: 150px" allow-clear placeholder="全部状态" @change="onSearch">
            <a-select-option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="门店">
          <a-select v-model:value="query.store_id" style="width: 200px" allow-clear show-search option-filter-prop="label"
                    :options="storeOptions" placeholder="全部门店" @change="onSearch" />
        </a-form-item>
        <a-form-item label="关键字">
          <a-input v-model:value="query.keyword" placeholder="订单号/门店/电话" style="width: 200px" allow-clear @press-enter="onSearch" />
        </a-form-item>
        <a-form-item label="下单日期">
          <a-range-picker v-model:value="dateRange" @change="onDateChange" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="onSearch"><search-outlined /> 查询</a-button>
          <a-button style="margin-left: 8px" @click="onReset">重置</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <a-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      row-key="id"
      size="small"
      :pagination="pagination"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-if="column.dataIndex === 'amount'">
          <span style="color: #cf1322; font-weight: 600">¥{{ Number(record.amount || 0).toFixed(2) }}</span>
        </template>
        <template v-if="column.dataIndex === 'cargo'">
          {{ cargoLabel(record.cargo_type) }} · {{ record.weight }}kg
        </template>
        <template v-if="column.dataIndex === 'dispatch'">
          <div v-if="record.plate">
            <div><a-tag color="blue">{{ record.plate }}</a-tag></div>
            <div style="font-size: 12px; color: #888">{{ record.driver_name || '-' }} {{ record.driver_phone || '' }}</div>
          </div>
          <span v-else style="color: #bbb">未排车</span>
        </template>
        <template v-if="column.dataIndex === 'expect_date'">
          {{ record.expect_date || '-' }} <a-tag>{{ windowLabel(record.time_window) }}</a-tag>
        </template>
        <template v-if="column.dataIndex === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>
        <template v-if="column.dataIndex === 'action'">
          <a-space>
            <a @click="openDetail(record)">详情</a>
            <a v-if="record.status === 'paid'" @click="openSchedule(record)">创建调度</a>
            <a-dropdown v-if="record.status !== 'completed' && record.status !== 'cancelled'">
              <a @click.prevent>更多 <down-outlined /></a>
              <template #overlay>
                <a-menu @click="({ key }) => onMore(key, record)">
                  <a-menu-item key="status">修改状态</a-menu-item>
                  <a-menu-item key="cancel" danger>取消订单</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 订单详情抽屉 -->
    <a-drawer v-model:open="detailOpen" title="订单详情" width="620">
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <a-descriptions bordered size="small" :column="2">
            <a-descriptions-item label="订单号" :span="2">{{ detail.order_no }}</a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-tag :color="statusColor(detail.status)">{{ statusLabel(detail.status) }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="金额">
              <span style="color: #cf1322; font-weight: 600">¥{{ Number(detail.amount || 0).toFixed(2) }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="门店">{{ detail.store_name }}</a-descriptions-item>
            <a-descriptions-item label="下单用户">{{ detail.nickname || '-' }}</a-descriptions-item>
            <a-descriptions-item label="联系人">{{ detail.contact_name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="联系电话">{{ detail.contact_phone || '-' }}</a-descriptions-item>
            <a-descriptions-item label="货物">{{ cargoLabel(detail.cargo_type) }} · {{ detail.weight }}kg</a-descriptions-item>
            <a-descriptions-item label="配送时段">{{ windowLabel(detail.time_window) }}</a-descriptions-item>
            <a-descriptions-item label="期望日期">{{ detail.expect_date || '-' }}</a-descriptions-item>
            <a-descriptions-item label="配送距离">{{ detail.distance_km ? detail.distance_km + ' km' : '-' }}</a-descriptions-item>
            <a-descriptions-item label="openid" :span="2">{{ detail.openid || '-' }}</a-descriptions-item>
            <a-descriptions-item label="备注" :span="2">{{ detail.remark || '无' }}</a-descriptions-item>
          </a-descriptions>

          <a-divider orientation="left" style="margin: 16px 0 8px">调度结果</a-divider>
          <a-descriptions bordered size="small" :column="2" v-if="detail.plate">
            <a-descriptions-item label="车辆">{{ detail.plate }}（{{ detail.vehicle_type }}）</a-descriptions-item>
            <a-descriptions-item label="司机">{{ detail.driver_name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="司机电话">{{ detail.driver_phone || '-' }}</a-descriptions-item>
            <a-descriptions-item label="配送时段">{{ windowLabel(detail.deliver_window) }}</a-descriptions-item>
            <a-descriptions-item label="预计送达" :span="2">{{ detail.estimated_arrival || '-' }}</a-descriptions-item>
            <a-descriptions-item label="调度任务" :span="2">
              <router-link v-if="detail.task_id" :to="`/tasks/${detail.task_id}`">{{ detail.task_id }}</router-link>
              <span v-else>-</span>
            </a-descriptions-item>
          </a-descriptions>
          <a-empty v-else description="尚未排车" :image-style="{ height: '60px' }" />

          <a-divider orientation="left" style="margin: 16px 0 8px">支付流水</a-divider>
          <a-list size="small" :data-source="detail.payments || []" bordered>
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta :title="item.payment_no" :description="`${channelLabel(item.channel)} · ${formatTime(item.paid_at)}`" />
                <template #actions>
                  <a-tag :color="item.status === 'success' ? 'green' : 'orange'">
                    {{ item.status === 'success' ? '支付成功' : item.status }}
                  </a-tag>
                  <span style="color: #cf1322">¥{{ Number(item.amount || 0).toFixed(2) }}</span>
                </template>
              </a-list-item>
            </template>
          </a-list>

          <a-divider orientation="left" style="margin: 16px 0 8px">状态轨迹</a-divider>
          <a-timeline>
            <a-timeline-item v-for="log in (detail.status_logs || []).slice().reverse()" :key="log.id"
                             :color="statusColor(log.to_status)">
              <div><b>{{ statusLabel(log.to_status) }}</b> <a-tag>{{ operatorLabel(log.operator) }}</a-tag></div>
              <div style="font-size: 12px; color: #888">{{ log.remark || '' }}</div>
              <div style="font-size: 12px; color: #aaa">{{ formatTime(log.created_at) }}</div>
            </a-timeline-item>
          </a-timeline>
        </template>
      </a-spin>
    </a-drawer>

    <!-- 创建调度 -->
    <a-modal v-model:open="scheduleOpen" title="为客户订单创建调度任务" @ok="submitSchedule" :confirm-loading="scheduling">
      <a-alert type="info" show-icon style="margin-bottom: 16px"
               message="系统将按订单门店与货量创建调度任务，Agent 求解完成后自动把车辆、司机、时段回填到该订单。" />
      <a-form layout="vertical">
        <a-form-item label="订单">
          <a-input :value="scheduleTarget && `${scheduleTarget.order_no} · ${scheduleTarget.store_name} · ${scheduleTarget.weight}kg`" disabled />
        </a-form-item>
        <a-form-item label="求解完成后自动确认最优方案">
          <a-switch v-model:checked="scheduleForm.auto_confirm" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 修改状态 -->
    <a-modal v-model:open="statusOpen" title="修改订单状态" @ok="submitStatus" :confirm-loading="statusSaving">
      <a-form layout="vertical">
        <a-form-item label="目标状态">
          <a-select v-model:value="statusForm.status">
            <a-select-option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="statusForm.remark" placeholder="选填" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { ReloadOutlined, SearchOutlined, DownOutlined } from '@ant-design/icons-vue'
import { api } from '../../api'

const rows = ref([])
const loading = ref(false)
const stats = ref({})
const storeOptions = ref([])

const query = reactive({ status: undefined, store_id: undefined, keyword: '', start_date: undefined, end_date: undefined })
const dateRange = ref([])
const pagination = reactive({ current: 1, pageSize: 10, total: 0, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` })

const statusOptions = [
  { value: 'pending_pay', label: '待支付' },
  { value: 'paid', label: '已支付待调度' },
  { value: 'scheduled', label: '已排车' },
  { value: 'delivering', label: '配送中' },
  { value: 'delivered', label: '已送达' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
]

const columns = [
  { title: '订单号', dataIndex: 'order_no', width: 190 },
  { title: '门店', dataIndex: 'store_name', width: 150, ellipsis: true },
  { title: '联系人', dataIndex: 'contact_name', width: 110 },
  { title: '货物', dataIndex: 'cargo', width: 130 },
  { title: '金额', dataIndex: 'amount', width: 100 },
  { title: '状态', dataIndex: 'status', width: 120 },
  { title: '排车情况', dataIndex: 'dispatch', width: 170 },
  { title: '期望配送', dataIndex: 'expect_date', width: 150 },
  { title: '下单时间', dataIndex: 'created_at', width: 150 },
  { title: '操作', dataIndex: 'action', width: 190, fixed: 'right' },
]

const STATUS_COLOR = {
  pending_pay: 'red',
  paid: 'orange',
  scheduled: 'blue',
  delivering: 'cyan',
  delivered: 'green',
  completed: 'green',
  cancelled: 'default',
}
const CARGO = { general: '普通货物', fresh: '生鲜冷链', fragile: '易碎品', bulk: '大宗货物' }
const CHANNEL = { wechat_mock: '微信支付（模拟）', balance: '平台余额', cash: '货到付款' }
const OPERATOR = { user: '用户', admin: '管理员', system: '系统' }

function statusLabel(s) { return (statusOptions.find((o) => o.value === s) || {}).label || s }
function statusColor(s) { return STATUS_COLOR[s] || 'default' }
function cargoLabel(c) { return CARGO[c] || c }
function channelLabel(c) { return CHANNEL[c] || c }
function operatorLabel(o) { return OPERATOR[o] || o }
function windowLabel(w) { return { AM: '上午', PM: '下午', any: '全天', all: '全天' }[w] || w || '-' }
function formatTime(t) { return t ? String(t).replace('T', ' ').slice(0, 16) : '-' }

async function load() {
  loading.value = true
  try {
    const res = await api.listCustomerOrders({
      status: query.status,
      store_id: query.store_id,
      keyword: query.keyword || undefined,
      start_date: query.start_date,
      end_date: query.end_date,
      page: pagination.current,
      page_size: pagination.pageSize,
    })
    rows.value = res.items || []
    pagination.total = res.total || 0
  } catch (e) {
    message.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try { stats.value = await api.customerStats() } catch (e) { /* ignore */ }
}

async function loadStores() {
  try {
    const list = await api.listStores()
    storeOptions.value = (list || []).map((s) => ({ value: s.id, label: `${s.name}（${s.id}）` }))
  } catch (e) { /* ignore */ }
}

function onSearch() { pagination.current = 1; load() }
function onReset() {
  query.status = undefined
  query.store_id = undefined
  query.keyword = ''
  query.start_date = undefined
  query.end_date = undefined
  dateRange.value = []
  pagination.current = 1
  load()
}
function onDateChange(v) {
  query.start_date = v && v[0] ? v[0].format('YYYY-MM-DD') : undefined
  query.end_date = v && v[1] ? v[1].format('YYYY-MM-DD') : undefined
}
function onTableChange(pg) {
  pagination.current = pg.current
  pagination.pageSize = pg.pageSize
  load()
}

// ---------- 详情 ----------
const detailOpen = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

async function openDetail(record) {
  detailOpen.value = true
  detailLoading.value = true
  detail.value = null
  try { detail.value = await api.getCustomerOrder(record.id) }
  catch (e) { message.error('加载详情失败: ' + e.message) }
  finally { detailLoading.value = false }
}

// ---------- 创建调度 ----------
const scheduleOpen = ref(false)
const scheduling = ref(false)
const scheduleTarget = ref(null)
const scheduleForm = reactive({ auto_confirm: true })

function openSchedule(record) {
  scheduleTarget.value = record
  scheduleForm.auto_confirm = true
  scheduleOpen.value = true
}

async function submitSchedule() {
  if (!scheduleTarget.value) return
  scheduling.value = true
  try {
    await api.scheduleCustomerOrder(scheduleTarget.value.id, { auto_confirm: scheduleForm.auto_confirm })
    message.success('调度任务已创建，Agent 正在求解，稍后自动回填车辆与司机')
    scheduleOpen.value = false
    load(); loadStats()
    // 求解通常需要数秒，稍后自动刷新列表以展示回填结果
    setTimeout(() => { load(); loadStats() }, 6000)
    setTimeout(() => { load() }, 15000)
  } catch (e) {
    message.error('创建失败: ' + e.message)
  } finally {
    scheduling.value = false
  }
}

// ---------- 修改状态 ----------
const statusOpen = ref(false)
const statusSaving = ref(false)
const statusForm = reactive({ id: null, status: undefined, remark: '' })

function onMore(key, record) {
  if (key === 'status') {
    statusForm.id = record.id
    statusForm.status = record.status
    statusForm.remark = ''
    statusOpen.value = true
  } else if (key === 'cancel') {
    Modal.confirm({
      title: '取消订单',
      content: `确认取消订单 ${record.order_no}？`,
      okType: 'danger',
      async onOk() {
        await api.cancelCustomerOrder(record.id, { reason: '管理员取消订单' })
        message.success('订单已取消')
        load(); loadStats()
      },
    })
  }
}

async function submitStatus() {
  if (!statusForm.status) { message.warning('请选择目标状态'); return }
  statusSaving.value = true
  try {
    await api.updateCustomerOrderStatus(statusForm.id, { status: statusForm.status, remark: statusForm.remark || undefined })
    message.success('状态已更新')
    statusOpen.value = false
    load(); loadStats()
  } catch (e) {
    message.error('更新失败: ' + e.message)
  } finally {
    statusSaving.value = false
  }
}

let timer = null
onMounted(() => {
  load(); loadStats(); loadStores()
  // 自动刷新，便于观察调度回填
  timer = setInterval(() => { load(); loadStats() }, 30000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
:deep(.ant-statistic-title) {
  font-size: 12px;
}
</style>