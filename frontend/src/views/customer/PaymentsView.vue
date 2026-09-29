<template>
  <div>
    <a-page-header title="支付流水" sub-title="小程序端模拟支付流水记录">
      <template #extra>
        <a-button @click="load"><reload-outlined /> 刷新</a-button>
      </template>
    </a-page-header>

    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="支付流水总数" :value="stats.total" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="累计支付金额(元)" :value="stats.sumAmount" :precision="2" :value-style="{ color: '#cf1322' }" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="成功笔数" :value="stats.successCount" :value-style="{ color: '#389e0d' }" />
        </a-card>
      </a-col>
    </a-row>

    <a-card size="small" style="margin-bottom: 16px">
      <a-form layout="inline">
        <a-form-item label="状态">
          <a-select v-model:value="query.status" style="width: 160px" allow-clear placeholder="全部状态" @change="onSearch">
            <a-select-option value="success">支付成功</a-select-option>
            <a-select-option value="refunded">已退款</a-select-option>
            <a-select-option value="pending">处理中</a-select-option>
            <a-select-option value="failed">支付失败</a-select-option>
          </a-select>
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
        <template v-if="column.dataIndex === 'amount'">
          <span style="color: #cf1322; font-weight: 600">¥{{ Number(record.amount || 0).toFixed(2) }}</span>
        </template>
        <template v-if="column.dataIndex === 'channel'">
          {{ channelLabel(record.channel) }}
        </template>
        <template v-if="column.dataIndex === 'status'">
          <a-tag :color="record.status === 'success' ? 'green' : record.status === 'refunded' ? 'orange' : 'default'">
            {{ statusLabel(record.status) }}
          </a-tag>
        </template>
        <template v-if="column.dataIndex === 'paid_at'">
          {{ formatTime(record.paid_at) }}
        </template>
        <template v-if="column.dataIndex === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { api } from '../../api'

const rows = ref([])
const loading = ref(false)
const query = reactive({ status: undefined })
const pagination = reactive({ current: 1, pageSize: 10, total: 0, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` })

const columns = [
  { title: '流水号', dataIndex: 'payment_no', width: 200 },
  { title: '订单号', dataIndex: 'order_id', ellipsis: true },
  { title: '金额', dataIndex: 'amount', width: 110 },
  { title: '支付渠道', dataIndex: 'channel', width: 150 },
  { title: '状态', dataIndex: 'status', width: 110 },
  { title: '交易号', dataIndex: 'transaction_id', width: 170 },
  { title: '支付时间', dataIndex: 'paid_at', width: 160 },
  { title: '创建时间', dataIndex: 'created_at', width: 160 },
]

const CHANNEL = { wechat_mock: '微信支付（模拟）', balance: '平台余额', cash: '货到付款' }
const STATUS = { success: '支付成功', refunded: '已退款', pending: '处理中', failed: '支付失败' }

function channelLabel(c) { return CHANNEL[c] || c }
function statusLabel(s) { return STATUS[s] || s }
function formatTime(t) { return t ? String(t).replace('T', ' ').slice(0, 16) : '-' }

const stats = computed(() => {
  let sum = 0
  let successCount = 0
  rows.value.forEach((p) => {
    if (p.status === 'success') {
      sum += Number(p.amount || 0)
      successCount += 1
    }
  })
  return { total: pagination.total, sumAmount: sum, successCount }
})

async function load() {
  loading.value = true
  try {
    const res = await api.listPayments({
      status: query.status,
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

function onSearch() { pagination.current = 1; load() }
function onReset() { query.status = undefined; pagination.current = 1; load() }
function onTableChange(pg) {
  pagination.current = pg.current
  pagination.pageSize = pg.pageSize
  load()
}

onMounted(load)
</script>