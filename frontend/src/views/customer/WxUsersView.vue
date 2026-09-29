<template>
  <div>
    <a-page-header title="小程序用户管理" sub-title="微信小程序端注册用户（scope=wx，与后台 RBAC 用户隔离）">
      <template #extra>
        <a-button @click="load"><reload-outlined /> 刷新</a-button>
      </template>
    </a-page-header>

    <a-card size="small" style="margin-bottom: 16px">
      <a-form layout="inline">
        <a-form-item label="关键字">
          <a-input v-model:value="query.keyword" placeholder="昵称 / openid / 手机号" style="width: 240px" allow-clear @press-enter="onSearch" />
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="query.enabled" style="width: 140px" allow-clear placeholder="全部" @change="onSearch">
            <a-select-option :value="true">已启用</a-select-option>
            <a-select-option :value="false">已禁用</a-select-option>
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
        <template v-if="column.dataIndex === 'nickname'">
          <a-space>
            <a-avatar :src="record.avatar" style="background-color: #1e3c72">
              {{ (record.nickname || '微').slice(0, 1) }}
            </a-avatar>
            <span>{{ record.nickname || '微信用户' }}</span>
          </a-space>
        </template>
        <template v-if="column.dataIndex === 'openid'">
          <a-typography-text :content="record.openid" :ellipsis="{ tooltip: record.openid }" style="max-width: 200px" />
        </template>
        <template v-if="column.dataIndex === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'red'">{{ record.enabled ? '已启用' : '已禁用' }}</a-tag>
        </template>
        <template v-if="column.dataIndex === 'last_login_at'">
          {{ formatTime(record.last_login_at) }}
        </template>
        <template v-if="column.dataIndex === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>
        <template v-if="column.dataIndex === 'action'">
          <a-space>
            <a v-if="record.enabled" style="color: #cf1322" @click="toggle(record, false)">禁用</a>
            <a v-else @click="toggle(record, true)">启用</a>
            <a @click="openRemark(record)">备注</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="remarkOpen" title="修改备注" @ok="submitRemark" :confirm-loading="remarkSaving">
      <a-form layout="vertical">
        <a-form-item label="用户">
          <a-input :value="remarkTarget && (remarkTarget.nickname || remarkTarget.openid)" disabled />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="remarkText" :rows="3" placeholder="选填，例如：意向客户 / 测试账号" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { api } from '../../api'

const rows = ref([])
const loading = ref(false)
const query = reactive({ keyword: '', enabled: undefined })
const pagination = reactive({ current: 1, pageSize: 10, total: 0, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` })

const columns = [
  { title: '用户', dataIndex: 'nickname', width: 200 },
  { title: 'openid', dataIndex: 'openid', width: 230 },
  { title: '手机号', dataIndex: 'phone', width: 140 },
  { title: '订单数', dataIndex: 'order_count', width: 90 },
  {
    title: '累计消费',
    dataIndex: 'total_amount',
    width: 120,
    customRender: ({ text }) => `¥${Number(text || 0).toFixed(2)}`,
  },
  { title: '状态', dataIndex: 'enabled', width: 100 },
  { title: '最近登录', dataIndex: 'last_login_at', width: 160 },
  { title: '注册时间', dataIndex: 'created_at', width: 160 },
  { title: '操作', dataIndex: 'action', width: 160, fixed: 'right' },
]

function formatTime(t) { return t ? String(t).replace('T', ' ').slice(0, 16) : '-' }

async function load() {
  loading.value = true
  try {
    const res = await api.listWxUsers({
      keyword: query.keyword || undefined,
      enabled: query.enabled,
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
function onReset() {
  query.keyword = ''
  query.enabled = undefined
  pagination.current = 1
  load()
}
function onTableChange(pg) {
  pagination.current = pg.current
  pagination.pageSize = pg.pageSize
  load()
}

async function toggle(record, enabled) {
  try {
    const params = { enabled }
    if (record.remark) params.remark = record.remark
    await api.updateWxUser(record.id, params)
    message.success(enabled ? '已启用' : '已禁用')
    load()
  } catch (e) {
    message.error('操作失败: ' + e.message)
  }
}

const remarkOpen = ref(false)
const remarkSaving = ref(false)
const remarkTarget = ref(null)
const remarkText = ref('')

function openRemark(record) {
  remarkTarget.value = record
  remarkText.value = record.remark || ''
  remarkOpen.value = true
}

async function submitRemark() {
  if (!remarkTarget.value) return
  remarkSaving.value = true
  try {
    await api.updateWxUser(remarkTarget.value.id, { enabled: remarkTarget.value.enabled, remark: remarkText.value })
    message.success('备注已保存')
    remarkOpen.value = false
    load()
  } catch (e) {
    message.error('保存失败: ' + e.message)
  } finally {
    remarkSaving.value = false
  }
}

onMounted(load)
</script>